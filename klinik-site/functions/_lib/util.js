// Shared helpers for the Pages Functions.

export const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });

export const fail = (code, message, status) => json({ code, message }, status);

export function sameText(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

const enc = new TextEncoder();
const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
const b64u = (s) => btoa(unescape(encodeURIComponent(s))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const unb64u = (s) => decodeURIComponent(escape(atob(s.replace(/-/g, '+').replace(/_/g, '/'))));

// Tokens are signed with SESSION_SECRET (falling back to STAFF_PASSWORD on older deployments).
const signingKey = (env) => env.SESSION_SECRET || env.STAFF_PASSWORD || null;

async function hmac(key, msg) {
  const k = await crypto.subtle.importKey('raw', enc.encode(key), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return hex(await crypto.subtle.sign('HMAC', k, enc.encode(msg)));
}

export async function signToken(env, payload) {
  const key = signingKey(env); if (!key) return null;
  const body = b64u(JSON.stringify(payload));
  return body + '.' + (await hmac(key, body));
}

export async function readToken(env, token, kind) {
  const key = signingKey(env);
  if (!key || typeof token !== 'string' || token.length > 2048) return null;
  const [body, sig] = token.split('.');
  if (!body || !sig || !sameText(sig, await hmac(key, body))) return null;
  let p; try { p = JSON.parse(unb64u(body)); } catch (_) { return null; }
  return p && p.kind === kind && p.exp > Date.now() ? p : null;
}

// Staff passwords: PBKDF2-SHA256 with a random salt per account (100k rounds is the Workers maximum).
export async function hashPassword(password, saltHex) {
  const salt = saltHex || hex(crypto.getRandomValues(new Uint8Array(16)));
  const base = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: enc.encode(salt), iterations: 100000 }, base, 256);
  return { salt, hash: hex(bits) };
}

// Staff accounts live in KV at staff/<email>: { email, name, role: 'admin'|'dokter', doc, salt, hash, pwv }.
// Emails in ADMIN_EMAILS are admins even before they have a stored record, so a new site can be set up.
export const adminEmails = (env) => (env.ADMIN_EMAILS || '').split(',').map((e) => e.trim().toLowerCase()).filter(Boolean);

export async function getAccount(env, email) {
  email = String(email || '').toLowerCase();
  if (!email || !env.DH_KV) return null;
  const rec = await env.DH_KV.get('staff/' + email, 'json');
  if (rec) return rec;
  return adminEmails(env).includes(email) ? { email, name: email, role: 'admin', doc: '', pwv: 0 } : null;
}

export const putAccount = (env, acc) => env.DH_KV.put('staff/' + acc.email, JSON.stringify(acc));

export const publicAccount = (a) => ({ email: a.email, name: a.name, role: a.role, doc: a.doc || '', hasPassword: !!a.hash });

export async function sessionFor(env, acc) {
  return signToken(env, { kind: 'session', email: acc.email, pwv: acc.pwv || 0, exp: Date.now() + 12 * 3600e3 });
}

// The signed-in staff member for this request, read fresh from KV so role changes and password resets apply at once.
export async function staffSession(request, env) {
  const p = await readToken(env, request.headers.get('x-staff-token') || '', 'session');
  if (!p) return null;
  const acc = await getAccount(env, p.email);
  if (!acc || (acc.pwv || 0) !== p.pwv || !acc.hash) return null;
  return acc;
}

// Local testing without a Google client: only with DEV_LOGIN=1 in .dev.vars and only on localhost.
export function devLoginAllowed(request, env) {
  const host = new URL(request.url).hostname;
  return env.DEV_LOGIN === '1' && (host === 'localhost' || host === '127.0.0.1');
}

// Fixed-window limit per client IP (or any key), kept in KV (approximate, which is enough to stop abuse).
export async function overLimit(env, request, name, perMinute, extraKey = '') {
  if (!env.DH_KV) return false;
  const ip = request.headers.get('cf-connecting-ip') || 'unknown';
  const key = `rl:${name}:${extraKey || ip}:${Math.floor(Date.now() / 60000)}`;
  const used = Number((await env.DH_KV.get(key)) || 0);
  if (used >= perMinute) return true;
  await env.DH_KV.put(key, String(used + 1), { expirationTtl: 120 });
  return false;
}
