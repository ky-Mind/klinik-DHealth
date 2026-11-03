// /api/patient — patient sign-in, required before booking, requesting a demo or filing a bug report.
//   GET                       which sign-in methods are set up, and the signed-in patient (x-patient-token) if any
//   POST { credential }       Google ID token (or { devEmail } in local testing only). A patient with a WhatsApp number
//                             on file gets a session at once; a new one gets a 10-minute ticket to add the number.
//   POST { ticket, wa }       finish a new sign-in with the WhatsApp number, returns a session
//   PUT  { wa }               change the WhatsApp number of the signed-in patient
import { json, fail, overLimit, signToken, readToken, devLoginAllowed, googleIdentity, patientId, patientSessionFor, patientSession, normalizeWa } from '../_lib/util.js';

const BAD_WA = 'Nomor WhatsApp tidak valid. Contoh: 0812-3456-7890.';
const me = async (env, rec) => ({ email: rec.email, name: rec.name, wa: rec.wa, pid: await patientId(env, rec.email) });
const signedIn = async (env, rec) => json({ token: await patientSessionFor(env, rec), me: await me(env, rec) });

export async function onRequestGet({ request, env }) {
  const p = await patientSession(request, env);
  return json({ clientId: env.GOOGLE_CLIENT_ID || null, devLogin: devLoginAllowed(request, env), me: p });
}

export async function onRequestPost({ request, env }) {
  if (!env.DH_KV || !(env.SESSION_SECRET || env.STAFF_PASSWORD)) return fail('unavailable', 'Login belum dikonfigurasi.', 503);
  if (await overLimit(env, request, 'patient', 20)) return fail('rate_limited', 'Terlalu banyak percobaan. Coba lagi sebentar lagi.', 429);
  let body;
  try { body = await request.json(); } catch (_) { return fail('bad_request', 'Permintaan tidak valid.', 400); }

  if (body.ticket != null) {
    const t = await readToken(env, body.ticket, 'pticket');
    if (!t) return fail('expired', 'Sesi login habis. Masuk dengan Google lagi.', 401);
    const wa = normalizeWa(body.wa);
    if (!wa) return fail('bad_wa', BAD_WA, 400);
    const old = (await env.DH_KV.get('patient/' + t.email, 'json')) || { email: t.email, name: t.name, createdAt: new Date().toISOString() };
    const rec = { ...old, name: old.name || t.name, wa };
    await env.DH_KV.put('patient/' + rec.email, JSON.stringify(rec));
    return signedIn(env, rec);
  }

  let who;
  if (body.devEmail != null) {
    if (!devLoginAllowed(request, env)) return fail('not_granted', 'Mode uji lokal tidak aktif.', 403);
    const email = String(body.devEmail).trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return fail('bad_request', 'Email tidak valid.', 400);
    who = { email, name: email.split('@')[0] };
  } else {
    if (!env.GOOGLE_CLIENT_ID) return fail('unavailable', 'Login Google belum dikonfigurasi.', 503);
    who = await googleIdentity(env, body.credential);
    if (!who) return fail('not_granted', 'Login Google tidak valid. Coba lagi.', 401);
  }

  const rec = await env.DH_KV.get('patient/' + who.email, 'json');
  if (rec && rec.wa) return signedIn(env, rec);
  const ticket = await signToken(env, { kind: 'pticket', email: who.email, name: who.name, exp: Date.now() + 10 * 60e3 });
  return json({ ticket, needWa: true, email: who.email, name: who.name });
}

export async function onRequestPut({ request, env }) {
  const p = await patientSession(request, env);
  if (!p) return fail('not_granted', 'Masuk dulu dengan Google.', 401);
  let body;
  try { body = await request.json(); } catch (_) { return fail('bad_request', 'Permintaan tidak valid.', 400); }
  const wa = normalizeWa(body.wa);
  if (!wa) return fail('bad_wa', BAD_WA, 400);
  const rec = { ...(await env.DH_KV.get('patient/' + p.email, 'json')), wa };
  await env.DH_KV.put('patient/' + rec.email, JSON.stringify(rec));
  return json({ me: await me(env, rec) });
}
