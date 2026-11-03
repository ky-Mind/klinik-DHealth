// /api/staff-google — step 1 of staff sign-in: prove who you are with Google.
// GET tells /admin which sign-in methods are set up. POST checks a Google ID token (or, in local testing only, a typed
// email), looks the email up among staff accounts, and returns a 10-minute ticket for step 2 (password, or setting one).
import { json, fail, overLimit, signToken, getAccount, publicAccount, devLoginAllowed, googleIdentity } from '../_lib/util.js';

export async function onRequestGet({ request, env }) {
  return json({ clientId: env.GOOGLE_CLIENT_ID || null, devLogin: devLoginAllowed(request, env) });
}

export async function onRequestPost({ request, env }) {
  if (!env.DH_KV || !(env.SESSION_SECRET || env.STAFF_PASSWORD)) return fail('unavailable', 'Login petugas belum dikonfigurasi.', 503);
  if (await overLimit(env, request, 'staff-google', 10)) return fail('rate_limited', 'Terlalu banyak percobaan.', 429);
  let body;
  try { body = await request.json(); } catch (_) { return fail('bad_request', 'Permintaan tidak valid.', 400); }

  let email;
  if (body.devEmail != null) {
    if (!devLoginAllowed(request, env)) return fail('not_granted', 'Mode uji lokal tidak aktif.', 403);
    email = String(body.devEmail).trim().toLowerCase();
  } else {
    if (!env.GOOGLE_CLIENT_ID) return fail('unavailable', 'Login Google belum dikonfigurasi.', 503);
    const who = await googleIdentity(env, body.credential);
    if (!who) return fail('not_granted', 'Login Google tidak valid. Coba lagi.', 401);
    email = who.email;
  }

  const acc = await getAccount(env, email);
  if (!acc) return fail('not_allowed', `Email ${email} belum terdaftar sebagai petugas.`, 403);
  const ticket = await signToken(env, { kind: 'ticket', email: acc.email, exp: Date.now() + 10 * 60e3 });
  return json({ ticket, account: publicAccount(acc) });
}
