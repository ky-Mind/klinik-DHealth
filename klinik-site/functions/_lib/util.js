// Shared helpers for the Pages Functions.

export const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });

export const fail = (code, message, status) => json({ code, message }, status);

// The staff token is an HMAC of a fixed label with STAFF_PASSWORD: changing the password signs everyone out.
export async function staffToken(env) {
  if (!env.STAFF_PASSWORD) return null;
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(env.STAFF_PASSWORD), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode('devhealth-staff-v1'));
  return [...new Uint8Array(sig)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export function sameText(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function isStaff(request, env) {
  const expected = await staffToken(env);
  return !!expected && sameText(request.headers.get('x-staff-token') || '', expected);
}

// Fixed-window limit per client IP, kept in KV (approximate, which is enough to stop abuse).
export async function overLimit(env, request, name, perMinute) {
  if (!env.DH_KV) return false;
  const ip = request.headers.get('cf-connecting-ip') || 'unknown';
  const key = `rl:${name}:${ip}:${Math.floor(Date.now() / 60000)}`;
  const used = Number((await env.DH_KV.get(key)) || 0);
  if (used >= perMinute) return true;
  await env.DH_KV.put(key, String(used + 1), { expirationTtl: 120 });
  return false;
}
