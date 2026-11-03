// POST /api/staff — exchange the clinic staff password for a token the browser keeps.
import { json, fail, staffToken, sameText, overLimit } from '../_lib/util.js';

export async function onRequestPost({ request, env }) {
  if (!env.STAFF_PASSWORD) return fail('unavailable', 'Login petugas belum dikonfigurasi.', 503);
  if (await overLimit(env, request, 'staff', 5)) return fail('rate_limited', 'Terlalu banyak percobaan.', 429);
  let password;
  try { ({ password } = await request.json()); } catch (_) { return fail('bad_request', 'Permintaan tidak valid.', 400); }
  if (!sameText(password || '', env.STAFF_PASSWORD)) return fail('not_granted', 'Kata sandi salah.', 401);
  return json({ token: await staffToken(env) });
}
