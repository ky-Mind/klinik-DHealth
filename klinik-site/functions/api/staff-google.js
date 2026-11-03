// /api/staff-google — sign staff in with their Google account instead of the shared password.
// GET tells /admin whether Google sign-in is set up (and which OAuth client to use);
// POST exchanges a Google ID token for the same staff token the password gives, but only for emails in ADMIN_EMAILS.
import { json, fail, staffToken, overLimit } from '../_lib/util.js';

const allowed = (env) => (env.ADMIN_EMAILS || '').split(',').map((e) => e.trim().toLowerCase()).filter(Boolean);
const ready = (env) => !!(env.GOOGLE_CLIENT_ID && env.STAFF_PASSWORD && allowed(env).length);

export async function onRequestGet({ env }) {
  return json(ready(env) ? { clientId: env.GOOGLE_CLIENT_ID } : { clientId: null });
}

export async function onRequestPost({ request, env }) {
  if (!ready(env)) return fail('unavailable', 'Login Google belum dikonfigurasi.', 503);
  if (await overLimit(env, request, 'staff-google', 10)) return fail('rate_limited', 'Terlalu banyak percobaan.', 429);
  let credential;
  try { ({ credential } = await request.json()); } catch (_) { return fail('bad_request', 'Permintaan tidak valid.', 400); }
  if (typeof credential !== 'string' || credential.length > 4096) return fail('bad_request', 'Permintaan tidak valid.', 400);

  // Google's tokeninfo endpoint checks the signature and expiry; we check it was issued for this site and to whom.
  const res = await fetch('https://oauth2.googleapis.com/tokeninfo?id_token=' + encodeURIComponent(credential));
  if (!res.ok) return fail('not_granted', 'Login Google tidak valid. Coba lagi.', 401);
  const info = await res.json();
  const email = String(info.email || '').toLowerCase();
  const issuerOk = info.iss === 'accounts.google.com' || info.iss === 'https://accounts.google.com';
  if (info.aud !== env.GOOGLE_CLIENT_ID || !issuerOk || String(info.email_verified) !== 'true' || Number(info.exp) * 1000 < Date.now())
    return fail('not_granted', 'Login Google tidak valid. Coba lagi.', 401);
  if (!allowed(env).includes(email)) return fail('not_allowed', `Email ${email} belum terdaftar sebagai petugas.`, 403);
  return json({ token: await staffToken(env), email });
}
