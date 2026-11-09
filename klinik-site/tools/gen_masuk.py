"""Generate masuk.html (patient sign-in: Google, then a WhatsApp number) from devhealth.html.

Run from klinik-site/:  python3 tools/gen_masuk.py
Booking, demo requests and bug reports send signed-out visitors here (window.dhPatient in dh-runtime.js);
after signing in they go back to the page they came from (?next=).
"""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT.parent
home = (SRC / 'devhealth.html').read_text()


def grab(pattern):
    m = re.search(pattern, home, re.S | re.M)
    assert m, pattern
    return m.group(0)


head = grab(r'\A.*?(?=<style>)')
head = head.replace('<title>Vidia Medika</title>', '<title>Masuk · Vidia Medika</title>')
head = re.sub(r'<meta name="description"[^>]*>', '<meta name="robots" content="noindex">', head)
style = grab(r'^<style>.*?^</style>')
sprite = grab(r'^<svg width="0".*?^</svg>')
logo = grab(r'<span class="logo-mark">.*?</span>')

CSS = '''<style>
.pt{padding-block:32px 72px;min-height:calc(100vh - 71px)}
.pt-card{max-width:440px;width:100%;box-sizing:border-box;margin:6vh auto 0;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:28px;display:grid;gap:14px;grid-template-columns:minmax(0,1fr);box-shadow:var(--shadow)}
.pt-card>*{min-width:0}
.pt-card h1{font-size:clamp(1.5rem,3vw,2.1rem);font-weight:800}
.pt-card p{color:var(--muted);font-size:15px}
.pt-card .field input{width:100%;box-sizing:border-box}
.pt-card .btn{justify-self:start}
#ptGoogle{min-height:44px;display:flex;justify-content:center}
.pt-dev{display:grid;gap:10px;padding:14px;border:1px dashed var(--line);border-radius:14px}
.pt-who{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:14px;background:var(--bg);border:1px solid var(--line)}
.pt-who>div{min-width:0}
.pt-who b{display:block;font-size:14.5px}
.pt-who small{display:block;color:var(--faint);font-size:12.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pt-who .btn-link{margin-left:auto;white-space:nowrap;flex:none}
.pt-av{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:var(--primary);color:#fff;font-weight:800;flex:none}
.btn-link{background:none;border:0;padding:4px 0;color:var(--primary);font-weight:700;font-size:14px;cursor:pointer;justify-self:start}
.btn-link:hover{text-decoration:underline}
.pt-acts{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.pt-note{font-size:13px!important;color:var(--faint)!important}
</style>'''

BODY = f'''<header class="nav" id="nav">
  <div class="wrap nav-in">
    <a class="logo" href="/" aria-label="Vidia Medika beranda">{logo}<span>Vidia <b>Medika</b></span></a>
    <div style="margin-left:auto"><a class="btn btn-line btn-sm" href="/">Beranda</a></div>
  </div>
</header>

<main class="pt"><div class="wrap">
  <section class="pt-card" id="ptLoad"><p>Memuat…</p></section>

  <section class="pt-card" id="stepGoogle" hidden>
    <span class="eyebrow">Masuk · langkah 1 dari 2</span>
    <h1>Masuk untuk membuat janji</h1>
    <p>Masuk dengan akun Google, lalu isi nomor WhatsApp. Nomor ini kami pakai untuk konfirmasi janji dan pengingat antrean.</p>
    <div id="ptGoogle"></div>
    <form id="devForm" class="pt-dev" hidden>
      <div class="field"><label for="devEmail">Email (mode uji lokal)</label><input id="devEmail" type="email" autocomplete="email" placeholder="nama@gmail.com" required></div>
      <button class="btn btn-line" type="submit">Lanjut tanpa Google</button>
    </form>
    <p class="err" id="googleFail" hidden>Tombol Google tidak termuat. Biasanya karena ekstensi pemblokir iklan atau privasi, atau koneksi lambat. Izinkan accounts.google.com untuk situs ini, lalu <a href="">muat ulang halaman</a>.</p>
    <p class="err" id="googleNone" hidden>Login Google belum dikonfigurasi di situs ini. Hubungi klinik lewat WhatsApp 0895-0613-8191.</p>
    <p class="pt-note">Kami hanya menerima nama dan email dari akun Google Anda. <a href="/privasi" style="color:var(--primary);font-weight:700">Kebijakan privasi</a></p>
  </section>

  <section class="pt-card" id="stepWa" hidden>
    <span class="eyebrow" id="waLbl">Masuk · langkah 2 dari 2</span>
    <h1 id="waTitle">Nomor WhatsApp Anda</h1>
    <div class="pt-who"><span class="pt-av" id="waAv">A</span><div><b id="waName"></b><small id="waMail"></small></div><button class="btn-link" type="button" data-restart>Ganti akun</button></div>
    <form id="waForm" style="display:grid;gap:14px">
      <div class="field"><label for="waNum">No. WhatsApp</label><input id="waNum" type="tel" inputmode="tel" autocomplete="tel" placeholder="0812-3456-7890" required></div>
      <p class="pt-note">Pastikan nomor aktif di WhatsApp. Konfirmasi janji dan pengingat antrean dikirim ke nomor ini.</p>
      <button class="btn btn-accent" type="submit" id="waBtn">Simpan &amp; lanjut</button>
    </form>
  </section>

  <section class="pt-card" id="stepDone" hidden>
    <span class="eyebrow">Akun pasien</span>
    <h1>Anda sudah masuk</h1>
    <div class="pt-who"><span class="pt-av" id="doneAv">A</span><div><b id="doneName"></b><small id="doneMail"></small></div></div>
    <p>WhatsApp: <b id="doneWa"></b> · <button class="btn-link" type="button" id="toWa">Ubah nomor</button></p>
    <div class="pt-acts"><a class="btn btn-accent" id="doneNext" href="/">Lanjut</a><button class="btn btn-line" type="button" id="ptOut">Keluar / ganti akun</button></div>
  </section>

  <p class="err pt-card" id="ptErr" hidden style="box-shadow:none"></p>
</div></main>'''

SCRIPT = '''<script>
(function(){
  const $=s=>document.querySelector(s);
  // only same-site paths may be the destination after signing in
  const nextRaw=new URLSearchParams(location.search).get('next')||'/';
  const next=/^\\/(?!\\/)/.test(nextRaw)?nextRaw:'/';
  const P=window.dhPatient;
  const steps=['ptLoad','stepGoogle','stepWa','stepDone'];
  const step=id=>steps.forEach(s=>{$('#'+s).hidden=s!==id;});
  const oops=t=>{$('#ptErr').textContent=t;$('#ptErr').hidden=!t;};
  const showWa=wa=>(wa||'').replace(/^62/,'0').replace(/(\\d{4})(\\d{4})(\\d+)/,'$1-$2-$3');
  const who=(pre,name,email)=>{$('#'+pre+'Av').textContent=(name||email||'?').trim()[0].toUpperCase();$('#'+pre+'Name').textContent=name||email;$('#'+pre+'Mail').textContent=email;};
  let editing=false;
  const done=me=>{
    if(new URLSearchParams(location.search).has('next')&&!editing){location.replace(next);return;}
    editing=false;who('done',me.name,me.email);$('#doneWa').textContent=showWa(me.wa);$('#doneNext').href=next;step('stepDone');
  };
  const askWa=(name,email,edit)=>{
    editing=!!edit;who('wa',name,email);
    $('#waLbl').textContent=edit?'Akun pasien':'Masuk · langkah 2 dari 2';$('#waTitle').textContent=edit?'Ubah nomor WhatsApp':'Nomor WhatsApp Anda';
    $('#waNum').value=edit?showWa(P.me().wa):'';step('stepWa');$('#waNum').focus();
  };
  const first=r=>{oops('');if(r.done)done(r.me);else askWa(r.name,r.email,false);};
  const msg=ex=>ex.message||'Terjadi kesalahan. Coba lagi.';
  if(!P){step('stepGoogle');$('#googleNone').hidden=false;return;}

  $('#waForm').addEventListener('submit',async e=>{e.preventDefault();const b=$('#waBtn');b.disabled=true;oops('');
    try{done(editing?await P.setWa($('#waNum').value):await P.finish($('#waNum').value));}
    catch(ex){oops(msg(ex));if(ex.code==='expired')step('stepGoogle');}
    b.disabled=false;});
  $('#toWa').addEventListener('click',()=>{const me=P.me();askWa(me.name,me.email,true);});
  document.querySelector('[data-restart]').addEventListener('click',()=>{if(editing){editing=false;done(P.me());return;}P.logout();step('stepGoogle');});
  $('#ptOut').addEventListener('click',()=>{P.logout();try{google.accounts.id.disableAutoSelect();}catch(_){}step('stepGoogle');});
  $('#devForm').addEventListener('submit',async e=>{e.preventDefault();
    try{first(await P.devLogin($('#devEmail').value));}catch(ex){oops(msg(ex));}});

  P.methods().then(m=>{
    if(P.signedIn()&&m.me){done(m.me);}
    else{if(P.signedIn())P.logout();step('stepGoogle');}
    if(m.devLogin)$('#devForm').hidden=false;
    if(!m.clientId){if(!m.devLogin)$('#googleNone').hidden=false;return;}
    const s=document.createElement('script');s.src='https://accounts.google.com/gsi/client';s.async=true;
    const fail=()=>{if(!$('#ptGoogle').querySelector('iframe')&&!$('#stepGoogle').hidden)$('#googleFail').hidden=false;};
    s.onerror=fail;setTimeout(fail,8000);
    s.onload=()=>{
      google.accounts.id.initialize({client_id:m.clientId,ux_mode:'popup',callback:async r=>{oops('');
        try{first(await P.google(r.credential));}catch(ex){oops(ex.code==='rate_limited'?msg(ex):'Login Google gagal. Coba lagi.');}}});
      google.accounts.id.renderButton($('#ptGoogle'),{theme:'outline',size:'large',shape:'pill',text:'signin_with',locale:'id',width:Math.min(384,$('#stepGoogle').clientWidth||320)});
    };
    document.head.appendChild(s);
  });
})();
</script>'''

DOC = ('<!doctype html>\n<html lang="id"><head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n')
(SRC / 'masuk.html').write_text(DOC + head + style + '\n' + CSS + '\n</head><body>\n' + sprite + '\n\n' + BODY + '\n' + SCRIPT + '\n</body></html>\n')
print('wrote', SRC / 'masuk.html')

# the privacy policy that the Google sign-in screen links to
PRIVACY = f'''<header class="nav" id="nav">
  <div class="wrap nav-in">
    <a class="logo" href="/" aria-label="Vidia Medika beranda">{logo}<span>Vidia <b>Medika</b></span></a>
    <div style="margin-left:auto"><a class="btn btn-line btn-sm" href="/">Beranda</a></div>
  </div>
</header>
<main class="pt"><div class="wrap"><article class="pt-card pt-doc">
  <span class="eyebrow">Kebijakan privasi</span>
  <h1>Data pasien di Vidia Medika</h1>
  <p>Berlaku sejak 3 November 2026 untuk situs klinik.xianzing.my.id.</p>
  <h2>Data yang kami simpan</h2>
  <ul>
    <li>Dari akun Google Anda: nama dan alamat email. Kami tidak menerima kata sandi Google, kontak, atau data lain.</li>
    <li>Nomor WhatsApp yang Anda isi saat masuk.</li>
    <li>Isi formulir yang Anda kirim: janji temu (dokter, jadwal, nama pasien, keluhan singkat), permintaan demo, dan laporan bug.</li>
  </ul>
  <h2>Untuk apa</h2>
  <ul>
    <li>Membuat dan menampilkan janji temu Anda di "Janji Saya".</li>
    <li>Mengirim konfirmasi janji dan pengingat antrean lewat WhatsApp.</li>
    <li>Memberi petugas klinik (admin dan dokter yang Anda pilih) data yang dibutuhkan untuk melayani Anda.</li>
  </ul>
  <h2>Siapa yang bisa melihat</h2>
  <p>Anda sendiri, admin klinik, dan dokter tujuan janji Anda. Kami tidak menjual atau membagikan data Anda ke pihak lain. Data disimpan di layanan Cloudflare yang dipakai situs ini.</p>
  <h2>Mengubah atau menghapus data</h2>
  <p>Nomor WhatsApp bisa diubah kapan saja di halaman <a href="/masuk">Akun pasien</a>. Untuk menghapus akun dan seluruh data Anda, kirim permintaan ke <a href="mailto:admin@xianzing.my.id">admin@xianzing.my.id</a> atau WhatsApp <a href="https://wa.me/6289506138191">0895-0613-8191</a>.</p>
</article></div></main>'''
PRIVACY_CSS = '<style>.pt-doc{max-width:720px}.pt-doc h2{font-size:1.1rem;font-weight:800;margin-top:6px}.pt-doc ul{margin:0;padding-left:20px;display:grid;gap:6px;color:var(--muted);font-size:15px}.pt-doc a{color:var(--primary);font-weight:700}</style>'
(SRC / 'privasi.html').write_text(DOC + head.replace('<title>Masuk · Vidia Medika</title>', '<title>Kebijakan Privasi · Vidia Medika</title>').replace('<meta name="robots" content="noindex">', '')
                                  + style + '\n' + CSS + '\n' + PRIVACY_CSS + '\n</head><body>\n' + sprite + '\n\n' + PRIVACY + '\n</body></html>\n')
print('wrote', SRC / 'privasi.html')
