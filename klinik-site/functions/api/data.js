// /api/data — records from the site's forms, stored in Workers KV.
//   GET  ?path=<collection>/<id>   read one record: its owner (x-device) or staff
//   PUT  ?path=<collection>/<id>   replace one record: its owner (x-device) or staff
//   GET  ?collection=<collection>  list all records: staff only
import { json, fail, isStaff, overLimit } from '../_lib/util.js';

const COLLECTIONS = new Set(['appts', 'bugs', 'demos']);
const MAX_BYTES = 64 * 1024;

function parsePath(path) {
  const m = /^([a-z]+)\/(d_[a-f0-9]{32})$/.exec(path || '');
  return m && COLLECTIONS.has(m[1]) ? { collection: m[1], id: m[2] } : null;
}

async function canTouch(request, env, id) {
  return request.headers.get('x-device') === id || (await isStaff(request, env));
}

export async function onRequestGet({ request, env }) {
  if (!env.DH_KV) return fail('unavailable', 'Penyimpanan belum dikonfigurasi.', 503);
  const url = new URL(request.url);

  const collection = url.searchParams.get('collection');
  if (collection) {
    if (!COLLECTIONS.has(collection)) return fail('bad_request', 'Koleksi tidak dikenal.', 400);
    if (!(await isStaff(request, env))) return fail('not_granted', 'Khusus petugas klinik.', 403);
    const docs = [];
    let cursor;
    do {
      const page = await env.DH_KV.list({ prefix: collection + '/', cursor });
      const values = await Promise.all(page.keys.map((k) => env.DH_KV.get(k.name, 'json')));
      page.keys.forEach((k, i) => values[i] && docs.push({ id: k.name.slice(collection.length + 1), data: values[i] }));
      cursor = page.list_complete ? null : page.cursor;
    } while (cursor);
    return json({ docs });
  }

  const p = parsePath(url.searchParams.get('path'));
  if (!p) return fail('bad_request', 'Alamat data tidak valid.', 400);
  if (!(await canTouch(request, env, p.id))) return fail('not_granted', 'Tidak punya akses.', 403);
  return json({ data: await env.DH_KV.get(`${p.collection}/${p.id}`, 'json') });
}

export async function onRequestPut({ request, env }) {
  if (!env.DH_KV) return fail('unavailable', 'Penyimpanan belum dikonfigurasi.', 503);
  if (await overLimit(env, request, 'data', 30)) return fail('rate_limited', 'Terlalu banyak permintaan.', 429);
  const p = parsePath(new URL(request.url).searchParams.get('path'));
  if (!p) return fail('bad_request', 'Alamat data tidak valid.', 400);
  if (!(await canTouch(request, env, p.id))) return fail('not_granted', 'Tidak punya akses.', 403);

  const raw = await request.text();
  if (raw.length > MAX_BYTES) return fail('bad_request', 'Data terlalu besar.', 400);
  let data;
  try { data = JSON.parse(raw); } catch (_) { return fail('bad_request', 'Data tidak valid.', 400); }
  if (!data || typeof data !== 'object' || Array.isArray(data)) return fail('bad_request', 'Data tidak valid.', 400);

  await env.DH_KV.put(`${p.collection}/${p.id}`, JSON.stringify(data));
  return json({ ok: true });
}
