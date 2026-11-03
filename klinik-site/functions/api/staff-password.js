// POST /api/staff-password — create a password (first sign-in) or replace a forgotten one.
// It needs a fresh Google ticket from step 1, so only the owner of the registered Google account can do it.
// Setting a password signs that account out everywhere else.
import { json, fail, overLimit, readToken, getAccount, putAccount, hashPassword, sessionFor, publicAccount } from '../_lib/util.js';

export async function onRequestPost({ request, env }) {
  if (!env.DH_KV) return fail('unavailable', 'Login petugas belum dikonfigurasi.', 503);
  if (await overLimit(env, request, 'staff-pw', 5)) return fail('rate_limited', 'Terlalu banyak percobaan.', 429);
  let ticket, password;
  try { ({ ticket, password } = await request.json()); } catch (_) { return fail('bad_request', 'Permintaan tidak valid.', 400); }
  const t = await readToken(env, ticket, 'ticket');
  if (!t) return fail('expired', 'Sesi Google sudah habis. Masuk dengan Google lagi.', 401);
  password = String(password || '');
  if (password.length < 8 || password.length > 128) return fail('weak', 'Kata sandi minimal 8 karakter.', 400);

  const acc = await getAccount(env, t.email);
  if (!acc) return fail('not_allowed', 'Akun ini sudah tidak terdaftar sebagai petugas.', 403);
  const { salt, hash } = await hashPassword(password);
  const next = { ...acc, salt, hash, pwv: (acc.pwv || 0) + 1, pwAt: new Date().toISOString() };
  await putAccount(env, next);
  return json({ token: await sessionFor(env, next), account: publicAccount(next) });
}
