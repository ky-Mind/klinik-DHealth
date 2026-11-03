// DHealth runtime for the self-hosted site (klinik.xianzing.my.id).
// The pages were written against the artifact runtime (window.claude.use(...)); this file provides the same small
// surface they use — sample (assistant), db, user, downloads — backed by the site's own Pages Functions.
(function () {
  const get = (k) => { try { return localStorage.getItem(k); } catch (_) { return null; } };
  const put = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (_) {} };

  // A random id per browser stands in for a signed-in account: each visitor reads and writes only their own records.
  let device = get('dh-device');
  if (!device) { device = 'd_' + crypto.randomUUID().replace(/-/g, ''); put('dh-device', device); }
  const staffToken = () => get('dh-staff');

  async function api(path, opts = {}) {
    const headers = { 'content-type': 'application/json', 'x-device': device };
    const t = staffToken(); if (t) headers['x-staff-token'] = t;
    const res = await fetch(path, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) { const e = new Error(body.message || res.statusText); e.code = body.code || 'unavailable'; throw e; }
    return body;
  }

  // assistant: same call shape as the artifact runtime's sample(); the answer arrives whole
  async function sample(input, opts = {}) {
    const text = typeof input === 'string' ? input : input.map((m) => m.content).join('\n\n');
    const out = await api('/api/chat', { method: 'POST', body: JSON.stringify({ input: text }), signal: opts.signal });
    opts.onText?.({ text: out.text, delta: out.text });
    return { text: out.text, truncated: false };
  }

  // database: documents live at "<collection>/<id>"; snapshots poll because Pages has no live connection
  const POLL_MS = 20000;
  const docSnap = (id, data) => ({ id, exists: data != null, data: () => (data == null ? undefined : data), metadata: { fromCache: false } });
  function docRef(path) {
    const id = path.split('/').pop();
    const listeners = new Set();
    const read = async () => docSnap(id, (await api('/api/data?path=' + encodeURIComponent(path))).data);
    return {
      id, path, get: read,
      async set(data) {
        await api('/api/data?path=' + encodeURIComponent(path), { method: 'PUT', body: JSON.stringify(data) });
        const s = docSnap(id, data); listeners.forEach((f) => f(s));
      },
      onSnapshot(next, error) {
        listeners.add(next);
        read().then(next, (e) => error && error(e));
        const timer = setInterval(() => read().then(next, () => {}), POLL_MS);
        return () => { listeners.delete(next); clearInterval(timer); };
      },
    };
  }
  function collectionRef(name) {
    const read = async () => {
      const out = await api('/api/data?collection=' + encodeURIComponent(name));
      const docs = out.docs.map((d) => docSnap(d.id, d.data));
      return { docs, size: docs.length, empty: !docs.length, metadata: { fromCache: false } };
    };
    return {
      get: read,
      doc: (id) => docRef(name + '/' + id),
      onSnapshot(next, error) {
        let first = true;
        const tick = () => read().then(next, (e) => { if (first && error) error(e); });
        tick().finally(() => { first = false; });
        const timer = setInterval(tick, POLL_MS);
        return () => clearInterval(timer);
      },
    };
  }
  const db = { doc: docRef, collection: collectionRef };

  // viewer: staff are whoever signed in on /admin (Google, then their own password)
  const user = {
    id: async () => device,
    me: async () => ({ id: device, name: '' }),
    isOwner: () => !!staffToken(),
    canEdit: () => !!staffToken(),
    can: () => null,
    profiles: async () => ({}),
  };

  // file save: a normal browser download on the real site
  const downloads = {
    async save({ filename, data }) {
      const blob = data instanceof Blob ? data : new Blob([data]);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = filename;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      return { status: 'saved' };
    },
  };

  const caps = { sample, db, user, downloads };
  window.claude = { use: async (name) => caps[name] || null };

  // Staff sign-in lives only on /admin (admin.html); public pages never show a password prompt or staff links.
  // Two steps: Google proves who you are (a 10-minute ticket), then your own password opens your account
  // (admin, or one doctor). A forgotten password is replaced with the same Google ticket.
  let ticket = null;
  const keep = (out) => { put('dh-staff', out.token); return out.account; };
  window.dhStaff = {
    signedIn: () => !!staffToken(),
    methods: () => api('/api/staff-google').catch(() => ({ clientId: null, devLogin: false })),
    async google(credential) { const out = await api('/api/staff-google', { method: 'POST', body: JSON.stringify({ credential }) }); ticket = out.ticket; return out.account; },
    async devLogin(email) { const out = await api('/api/staff-google', { method: 'POST', body: JSON.stringify({ devEmail: email }) }); ticket = out.ticket; return out.account; },
    password: async (password) => keep(await api('/api/staff', { method: 'POST', body: JSON.stringify({ ticket, password }) })),
    setPassword: async (password) => keep(await api('/api/staff-password', { method: 'POST', body: JSON.stringify({ ticket, password }) })),
    accounts: () => api('/api/staff-accounts'),
    saveAccount: (acc) => api('/api/staff-accounts', { method: 'PUT', body: JSON.stringify(acc) }),
    resetAccount: (email) => api('/api/staff-accounts', { method: 'POST', body: JSON.stringify({ email, action: 'reset' }) }),
    removeAccount: (email) => api('/api/staff-accounts?email=' + encodeURIComponent(email), { method: 'DELETE' }),
    logout: () => { ticket = null; put('dh-staff', null); },
  };
})();
