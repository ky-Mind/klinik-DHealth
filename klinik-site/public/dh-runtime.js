// DHealth runtime for the self-hosted site (klinik.xianzing.my.id).
// The pages were written against the artifact runtime (window.claude.use(...)); this file provides the same small
// surface they use — sample (assistant), db, user, downloads — backed by the site's own Pages Functions.
(function () {
  const get = (k) => { try { return localStorage.getItem(k); } catch (_) { return null; } };
  const put = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (_) {} };

  // A signed-in patient's records live under the id the server derives from their Google email (dh-patient-me.pid),
  // so they follow the account to any device. Before signing in, a random id per browser stands in.
  const readMe = () => { try { return JSON.parse(get('dh-patient-me') || 'null'); } catch (_) { return null; } };
  let device = get('dh-device');
  if (!device) { device = 'd_' + crypto.randomUUID().replace(/-/g, ''); put('dh-device', device); }
  if (get('dh-patient') && readMe()?.pid) device = readMe().pid;
  const staffToken = () => get('dh-staff');
  const patientToken = () => get('dh-patient');

  async function api(path, opts = {}) {
    const headers = { 'content-type': 'application/json', 'x-device': device };
    const t = staffToken(); if (t) headers['x-staff-token'] = t;
    const pt = patientToken(); if (pt) headers['x-patient-token'] = pt;
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

  // Patients: booking, demo requests and bug reports need a Google sign-in plus a WhatsApp number (page /masuk).
  // Opening one of those dialogs while signed out goes to /masuk, which comes back here afterwards.
  let pticket = null;
  const keepPatient = (out) => { put('dh-patient', out.token); put('dh-patient-me', JSON.stringify(out.me)); device = out.me.pid; return out.me; };
  window.dhPatient = {
    signedIn: () => !!patientToken() && !!readMe(),
    me: readMe,
    methods: () => api('/api/patient').catch(() => ({ clientId: null, devLogin: false, me: null })),
    async google(credential) { return this._first(await api('/api/patient', { method: 'POST', body: JSON.stringify({ credential }) })); },
    async devLogin(email) { return this._first(await api('/api/patient', { method: 'POST', body: JSON.stringify({ devEmail: email }) })); },
    _first(out) { if (out.token) return { done: true, me: keepPatient(out) }; pticket = out.ticket; return { done: false, email: out.email, name: out.name }; },
    finish: async (wa) => keepPatient(await api('/api/patient', { method: 'POST', body: JSON.stringify({ ticket: pticket, wa }) })),
    async setWa(wa) { const out = await api('/api/patient', { method: 'PUT', body: JSON.stringify({ wa }) }); put('dh-patient-me', JSON.stringify(out.me)); return out.me; },
    logout() { pticket = null; put('dh-patient', null); put('dh-patient-me', null); device = get('dh-device'); },
    loginUrl: (next) => '/masuk?next=' + encodeURIComponent(next || location.pathname + location.search + location.hash),
  };
  const GATED = { bookDlg: 1, demoDlg: 1, bugDlg: 1, apptDlg: 1 };
  const showWa = (wa) => (wa || '').replace(/^62/, '0').replace(/(\d{4})(\d{4})(\d+)/, '$1-$2-$3');
  // prefill the form's sample name and number with the account's, unless the visitor already typed something
  const fill = (sel, value) => { const el = document.querySelector(sel); if (el && value && el.value === el.defaultValue) el.value = value; };
  const showModal = HTMLDialogElement.prototype.showModal;
  HTMLDialogElement.prototype.showModal = function () {
    if (GATED[this.id] && !window.dhPatient.signedIn()) { location.href = window.dhPatient.loginUrl(); return; }
    const me = readMe();
    if (me && GATED[this.id]) {
      fill('#bName', me.name); fill('#bPhone', showWa(me.wa)); fill('#dWa', showWa(me.wa)); fill('#bugMail', me.email);
      if (this.id === 'apptDlg' && !this.querySelector('.pt-bar')) {
        this.querySelector('.dlg-h')?.insertAdjacentHTML('afterend', '<p class="pt-bar" style="margin:0;padding:8px 20px;font-size:13px;color:var(--muted);border-bottom:1px solid var(--line)"></p>');
      }
      const bar = this.querySelector('.pt-bar');
      if (bar) { bar.textContent = 'Masuk sebagai ' + me.email + ' · '; const a = document.createElement('a'); a.href = '/masuk'; a.textContent = 'Kelola akun'; a.style.fontWeight = '700'; bar.append(a); }
    }
    return showModal.call(this);
  };
})();
