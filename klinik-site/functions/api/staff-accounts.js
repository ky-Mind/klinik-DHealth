// /api/staff-accounts — who may sign in to /admin and as what (admins only).
//   GET               the signed-in account (any staff) and, for admins, every account
//   PUT    {email, name, role, doc}   add or update an account; role 'admin' or 'dokter' (doc = the doctor's name)
//   POST   {email, action:'reset'}     clear a password: the person sets a new one after signing in with Google
//   DELETE ?email=    remove an account (not your own)
import { json, fail, staffSession, getAccount, putAccount, publicAccount, adminEmails } from '../_lib/util.js';

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

async function listAll(env) {
  const out = new Map();
  let cursor;
  do {
    const page = await env.DH_KV.list({ prefix: 'staff/', cursor });
    const vals = await Promise.all(page.keys.map((k) => env.DH_KV.get(k.name, 'json')));
    vals.forEach((v) => v && out.set(v.email, publicAccount(v)));
    cursor = page.list_complete ? null : page.cursor;
  } while (cursor);
  adminEmails(env).forEach((e) => out.has(e) || out.set(e, { email: e, name: e, role: 'admin', doc: '', hasPassword: false }));
  return [...out.values()].sort((a, b) => a.role.localeCompare(b.role) || a.email.localeCompare(b.email));
}

async function admin(request, env) {
  const me = await staffSession(request, env);
  return me && me.role === 'admin' ? me : null;
}

export async function onRequestGet({ request, env }) {
  const me = await staffSession(request, env);
  if (!me) return fail('not_granted', 'Silakan masuk lagi.', 401);
  return json({ me: publicAccount(me), accounts: me.role === 'admin' ? await listAll(env) : [] });
}

export async function onRequestPut({ request, env }) {
  const me = await admin(request, env);
  if (!me) return fail('not_granted', 'Khusus admin.', 403);
  let b; try { b = await request.json(); } catch (_) { return fail('bad_request', 'Permintaan tidak valid.', 400); }
  const email = String(b.email || '').trim().toLowerCase();
  if (!EMAIL.test(email)) return fail('bad_request', 'Email tidak valid.', 400);
  const role = b.role === 'admin' ? 'admin' : 'dokter';
  const doc = role === 'dokter' ? String(b.doc || '').slice(0, 120) : '';
  if (role === 'dokter' && !doc) return fail('bad_request', 'Pilih dokter untuk akun ini.', 400);
  if (email === me.email && role !== 'admin') return fail('bad_request', 'Anda tidak bisa menurunkan peran akun Anda sendiri.', 400);
  const prev = (await env.DH_KV.get('staff/' + email, 'json')) || { email, pwv: 0 };
  const acc = { ...prev, email, name: String(b.name || email).slice(0, 80), role, doc };
  await putAccount(env, acc);
  return json({ account: publicAccount(acc) });
}

export async function onRequestPost({ request, env }) {
  const me = await admin(request, env);
  if (!me) return fail('not_granted', 'Khusus admin.', 403);
  let b; try { b = await request.json(); } catch (_) { return fail('bad_request', 'Permintaan tidak valid.', 400); }
  if (b.action !== 'reset') return fail('bad_request', 'Aksi tidak dikenal.', 400);
  const acc = await getAccount(env, b.email);
  if (!acc) return fail('not_found', 'Akun tidak ditemukan.', 404);
  const next = { ...acc, salt: undefined, hash: undefined, pwv: (acc.pwv || 0) + 1 };
  await putAccount(env, next);
  return json({ account: publicAccount(next) });
}

export async function onRequestDelete({ request, env }) {
  const me = await admin(request, env);
  if (!me) return fail('not_granted', 'Khusus admin.', 403);
  const email = String(new URL(request.url).searchParams.get('email') || '').toLowerCase();
  if (email === me.email) return fail('bad_request', 'Anda tidak bisa menghapus akun Anda sendiri.', 400);
  if (adminEmails(env).includes(email)) return fail('bad_request', 'Akun ini terdaftar di ADMIN_EMAILS. Hapus dari pengaturan Cloudflare.', 400);
  await env.DH_KV.delete('staff/' + email);
  return json({ ok: true });
}
