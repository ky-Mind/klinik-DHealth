// DEVHEALTH runtime for the self-hosted site (klinik.xianzing.my.id).
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

  // viewer: staff are whoever signed in on #staf with the clinic password
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

  // Staff sign-in opens only when someone presses a "Dasbor Klinik" link ([data-dh-login]) while signed out;
  // visitors never see a password prompt otherwise. Signed-in staff go straight to the dashboard.
  function staffDialog() {
    const d = document.createElement('dialog');
    d.className = 'dh-staff-login';
    d.innerHTML = `<form method="dialog" class="dlg-b" style="min-width:min(380px,calc(100vw - 48px))">
      <h3 style="margin:0;font-size:1.2rem">Masuk petugas klinik</h3>
      <p style="margin:0;font-size:14px;color:var(--muted)">Untuk membuka Dasbor Klinik: janji pasien, permintaan demo, dan laporan bug.</p>
      <div class="field"><label for="dhPw">Kata sandi petugas</label><input id="dhPw" type="password" autocomplete="current-password" required></div>
      <p class="err" id="dhPwErr" hidden></p>
      <div style="display:flex;gap:8px;justify-content:flex-end"><button class="btn btn-line" value="cancel" type="button" id="dhPwCancel">Batal</button><button class="btn btn-primary" type="submit">Masuk</button></div>
    </form>`;
    document.body.appendChild(d);
    d.querySelector('#dhPwCancel').addEventListener('click', () => { d.close(); d.remove(); });
    d.querySelector('form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const err = d.querySelector('#dhPwErr'); err.hidden = true;
      try {
        const out = await api('/api/staff', { method: 'POST', body: JSON.stringify({ password: d.querySelector('#dhPw').value }) });
        put('dh-staff', out.token);
        location.replace(location.pathname + '#dasbor'); location.reload();
      } catch (ex) {
        err.textContent = ex.code === 'rate_limited' ? 'Terlalu banyak percobaan. Coba lagi beberapa menit lagi.' : 'Kata sandi salah.';
        err.hidden = false;
      }
    });
    d.showModal();
  }
  document.addEventListener('click', (e) => {
    const login = e.target.closest('[data-dh-login]');
    if (login && !staffToken()) { e.preventDefault(); e.stopImmediatePropagation(); staffDialog(); return; }
    const logout = e.target.closest('[data-dh-logout]');
    if (logout) { e.preventDefault(); put('dh-staff', null); location.replace(location.pathname); }
  }, true);
  // signed-in staff get a sign-out link beside the footer's dashboard link
  function staffFooter() {
    const link = document.querySelector('footer [data-dh-login]');
    if (!link || !staffToken()) return;
    const out = document.createElement('a');
    out.href = '#'; out.setAttribute('data-dh-logout', ''); out.textContent = 'Keluar dari akun petugas';
    link.closest('li')?.insertAdjacentHTML('afterend', '<li></li>');
    link.closest('li')?.nextElementSibling?.appendChild(out);
  }
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', staffFooter) : staffFooter();
})();
