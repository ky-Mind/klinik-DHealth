// POST /api/staff — step 2 of staff sign-in: the Google ticket from step 1 plus the person's own password.
// The account (admin, or a specific doctor) decides what the dashboard shows.
import { json, fail, overLimit, readToken, getAccount, hashPassword, sameText, sessionFor, publicAccount } from '../_lib/util.js';

export async function onRequestPost({ request, env }) {
  if (!env.DH_KV) return fail('unavailable', 'Login petugas belum dikonfigurasi.', 503);
  if (await overLimit(env, request, 'staff', 5)) return fail('rate_limited', 'Terlalu banyak percobaan.', 429);
  let ticket, password;
  try { ({ ticket, password } = await request.json()); } catch (_) { return fail('bad_request', 'Permintaan tidak valid.', 400); }
  const t = await readToken(env, ticket, 'ticket');
  if (!t) return fail('expired', 'Sesi Google sudah habis. Masuk dengan Google lagi.', 401);
  if (await overLimit(env, request, 'staff-acc', 5, t.email)) return fail('rate_limited', 'Terlalu banyak percobaan.', 429);

  const acc = await getAccount(env, t.email);
  if (!acc) return fail('not_allowed', 'Akun ini sudah tidak terdaftar sebagai petugas.', 403);
  if (!acc.hash) return fail('no_password', 'Akun ini belum punya kata sandi. Buat kata sandi dulu.', 409);
  const { hash } = await hashPassword(String(password || ''), acc.salt);
  if (!sameText(hash, acc.hash)) return fail('not_granted', 'Kata sandi salah.', 401);
  return json({ token: await sessionFor(env, acc), account: publicAccount(acc) });
}
