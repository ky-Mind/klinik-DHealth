// /api/data — records from the site's forms, stored in Workers KV.
//   GET  ?path=<collection>/<id>   read one record: the signed-in patient it belongs to, or an admin
//   PUT  ?path=<collection>/<id>   replace one record: the signed-in patient it belongs to, or an admin
//   GET  ?collection=<collection>  list records: admins see everything; a doctor sees only bookings made with them
import { json, fail, staffSession, patientSession, overLimit } from '../_lib/util.js';

const COLLECTIONS = new Set(['appts', 'bugs', 'demos']);
const MAX_BYTES = 64 * 1024;

function parsePath(path) {
  const m = /^([a-z]+)\/(d_[a-f0-9]{32})$/.exec(path || '');
  return m && COLLECTIONS.has(m[1]) ? { collection: m[1], id: m[2] } : null;
}

// Patients must be signed in (Google + WhatsApp) to keep records; each patient owns the one id derived from their email.
// Returns who is acting ({ patient } or { admin }), or null.
async function actor(request, env, id) {
  const p = await patientSession(request, env);
  if (p && p.pid === id) return { patient: p };
  const s = await staffSession(request, env);
  return s && s.role === 'admin' ? { admin: s } : null;
}

export async function onRequestGet({ request, env }) {
  if (!env.DH_KV) return fail('unavailable', 'Penyimpanan belum dikonfigurasi.', 503);
  const url = new URL(request.url);

  const collection = url.searchParams.get('collection');
  if (collection) {
    if (!COLLECTIONS.has(collection)) return fail('bad_request', 'Koleksi tidak dikenal.', 400);
    const s = await staffSession(request, env);
    if (!s) return fail('not_granted', 'Khusus petugas klinik.', 403);
    if (s.role !== 'admin' && collection !== 'appts') return fail('not_granted', 'Khusus admin.', 403);
    const docs = [];
    let cursor;
    do {
      const page = await env.DH_KV.list({ prefix: collection + '/', cursor });
      const values = await Promise.all(page.keys.map((k) => env.DH_KV.get(k.name, 'json')));
      page.keys.forEach((k, i) => values[i] && docs.push({ id: k.name.slice(collection.length + 1), data: values[i] }));
      cursor = page.list_complete ? null : page.cursor;
    } while (cursor);
    if (s.role !== 'admin') {
      // doctors: keep only their own patients' bookings, and drop patients with none
      const mine = docs.map((d) => ({ id: d.id, data: { ...d.data, items: (d.data.items || []).filter((a) => a && a.doc === s.doc) } }))
        .filter((d) => d.data.items.length);
      return json({ docs: mine });
    }
    return json({ docs });
  }

  const p = parsePath(url.searchParams.get('path'));
  if (!p) return fail('bad_request', 'Alamat data tidak valid.', 400);
  // a visitor who has not signed in simply has no records yet
  if (!(await actor(request, env, p.id))) return json({ data: null });
  return json({ data: await env.DH_KV.get(`${p.collection}/${p.id}`, 'json') });
}

export async function onRequestPut({ request, env }) {
  if (!env.DH_KV) return fail('unavailable', 'Penyimpanan belum dikonfigurasi.', 503);
  if (await overLimit(env, request, 'data', 30)) return fail('rate_limited', 'Terlalu banyak permintaan.', 429);
  const p = parsePath(new URL(request.url).searchParams.get('path'));
  if (!p) return fail('bad_request', 'Alamat data tidak valid.', 400);
  const who = await actor(request, env, p.id);
  if (!who) return fail('login_required', 'Masuk dulu dengan Google dan nomor WhatsApp.', 401);

  const raw = await request.text();
  if (raw.length > MAX_BYTES) return fail('bad_request', 'Data terlalu besar.', 400);
  let data;
  try { data = JSON.parse(raw); } catch (_) { return fail('bad_request', 'Data tidak valid.', 400); }
  if (!data || typeof data !== 'object' || Array.isArray(data)) return fail('bad_request', 'Data tidak valid.', 400);

  // the account behind the record, for the clinic: set from the patient's session, kept when an admin edits
  const key = `${p.collection}/${p.id}`;
  if (who.patient) data.patient = { email: who.patient.email, name: who.patient.name, wa: who.patient.wa };
  else { const old = await env.DH_KV.get(key, 'json'); if (old && old.patient) data.patient = old.patient; else delete data.patient; }
  await env.DH_KV.put(key, JSON.stringify(data));
  return json({ ok: true });
}
