"""Generate admin.html (the clinic dashboard for admins and doctors) from devhealth.html.

Run from klinik-site/:  python3 tools/gen_admin.py
The page reuses the home page's stylesheet, icon sprite and doctor list, so it always matches the public site.
On the self-hosted site it signs staff in with the clinic password (window.dhStaff from dh-runtime.js);
inside the claude.ai artifact it opens for the page's owner and editors.
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
head = head.replace('<title>Vidia Medika</title>', '<title>Admin Vidia Medika</title>')
head = re.sub(r'<meta name="description"[^>]*>', '<meta name="robots" content="noindex,nofollow">', head)
style = grab(r'^<style>.*?^</style>')
sprite = grab(r'^<svg width="0".*?^</svg>')
logo = grab(r'<span class="logo-mark">.*?</span>')
helpers = '\n'.join(grab(p) for p in (
    r'^  const iso=.*?$',
    r'^  const docs=\[.*?^  \];',
    r'^  const spLabel=.*?$',
    r'^  const setPressed=.*?$',
    r'^  const apptBadge=.*?Dibatalkan</span>\';',
    r'^  const esc=.*?$',
))

ADMIN_CSS = '''<style>
/* admin page: an app-style top bar, then either the sign-in card or the full-width dashboard */
.adm-nav .nav-in{gap:12px}
.adm-act{margin-left:auto;display:flex;gap:8px;align-items:center}
.adm{padding-block:32px 72px;min-height:calc(100vh - 71px)}
.adm-card{max-width:440px;margin:6vh auto 0;background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:28px;display:grid;gap:14px;box-shadow:var(--shadow)}
.adm-card h1,.adm-head h1{font-size:clamp(1.5rem,3vw,2.1rem);font-weight:800}
.adm-card p{color:var(--muted);font-size:15px}
.adm-card .btn{justify-self:start}
#admDash{display:grid;gap:18px}
.adm-panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:20px;display:grid;gap:14px}
.adm .appts{max-height:none;overflow:visible}
@supports (corner-shape:squircle){.adm-card,.adm-panel{corner-shape:squircle}}
.adm-or{display:flex;align-items:center;gap:12px;color:var(--faint);font-size:13px}
.adm-or::before,.adm-or::after{content:"";flex:1;height:1px;background:var(--line)}
.adm-google{display:grid;gap:14px}
#admGoogle{min-height:44px;display:flex;justify-content:center}
#otherAcc{justify-self:center;font-size:14px}
.adm-card .adm-help{font-size:13.5px;color:var(--faint)}
@media (max-width:520px){.adm-nav .chip{display:none}.adm-panel{padding:14px}}
/* the sign-in card never grows past its width: every grid level may shrink, long emails are clipped */
.adm-card{grid-template-columns:minmax(0,1fr);width:100%;box-sizing:border-box}
.adm-card>*,.adm-step,.adm-step>*,.adm-step .field{min-width:0}
.adm-step{display:grid;gap:14px;grid-template-columns:minmax(0,1fr)}
.adm-step .field input{width:100%;box-sizing:border-box}
.adm-dev{display:grid;gap:10px;padding:14px;border:1px dashed var(--line);border-radius:14px}
.adm-who{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:14px;background:var(--bg);border:1px solid var(--line)}
.adm-who b{display:block;font-size:14.5px}
.adm-who small{color:var(--faint);font-size:12.5px}
.adm-who .btn-link{margin-left:auto;white-space:nowrap;flex:none}
.adm-who>div{min-width:0}
.adm-who small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.adm-av{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;background:var(--primary);color:#fff;font-weight:800;flex:none}
.btn-link{background:none;border:0;padding:4px 0;color:var(--primary);font-weight:700;font-size:14px;cursor:pointer;justify-self:start}
.btn-link:hover{text-decoration:underline}
.pw-box{position:relative}
.pw-box input{padding-right:64px}
.pw-eye{position:absolute;right:6px;top:50%;transform:translateY(-50%);border:0;background:var(--surface);color:var(--primary);font-weight:700;font-size:12.5px;padding:6px 10px;border-radius:8px;cursor:pointer}
.adm-me{font-size:13px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:240px}
.adm-me b{color:var(--ink)}
.acc-form{display:grid;grid-template-columns:1.3fr 1fr .7fr 1.2fr auto;gap:10px;align-items:end}
@media (max-width:900px){.acc-form{grid-template-columns:1fr 1fr}.acc-form .btn{grid-column:1/-1}}
@media (max-width:520px){.acc-form{grid-template-columns:1fr}.adm-me{display:none}}
.acc-row{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between}
.acc-row .appt-acts{margin-left:auto}
</style>'''

BODY = f'''<header class="nav adm-nav" id="nav">
  <div class="wrap nav-in">
    <a class="logo" href="index.html" aria-label="Vidia Medika beranda">{logo}<span>Vidia <b>Medika</b></span></a>
    <span class="chip">Admin &amp; dokter</span>
    <div class="adm-act"><span class="adm-me" id="admMe" hidden></span><a class="btn btn-line btn-sm" href="index.html">Lihat situs</a><button class="btn btn-soft btn-sm" type="button" id="admOut" hidden>Keluar</button></div>
  </div>
</header>

<main class="adm"><div class="wrap">
  <section id="admLoad" class="adm-card"><p>Memuat…</p></section>

  <section id="admLogin" class="adm-card" hidden>
    <span class="eyebrow" id="admStepLbl">Khusus petugas · langkah 1 dari 2</span>

    <div id="stepGoogle" class="adm-step">
      <h1>Masuk Dasbor Klinik</h1>
      <p>Untuk admin dan dokter Vidia Medika. Masuk dulu dengan akun Google yang terdaftar di klinik, lalu isi kata sandi Anda.</p>
      <div id="admGoogle"></div>
      <button class="btn-link" type="button" id="otherAcc" hidden>Pakai akun Google lain</button>
      <form id="devForm" class="adm-dev" hidden>
        <div class="field"><label for="devEmail">Email petugas (mode uji lokal)</label><input id="devEmail" type="email" autocomplete="email" placeholder="nama@dhealth.id" required></div>
        <button class="btn btn-line" type="submit">Lanjut tanpa Google</button>
        <p class="adm-help">Mode ini hanya muncul di komputer pengembang (localhost) untuk menguji login.</p>
      </form>
      <p class="err" id="googleFail" hidden>Tombol Google tidak termuat. Biasanya karena ekstensi pemblokir iklan atau privasi, atau koneksi lambat. Izinkan accounts.google.com untuk situs ini, lalu <a href="">muat ulang halaman</a>.</p>
      <p class="err" id="googleNone" hidden>Login Google belum dikonfigurasi di situs ini. Hubungi pengelola situs.</p>
    </div>

    <form id="stepPw" class="adm-step" hidden>
      <div class="adm-who"><span class="adm-av" id="pwAv">A</span><div><b id="pwName"></b><small id="pwMeta"></small></div><button class="btn-link" type="button" data-restart>Ganti akun</button></div>
      <h1>Kata sandi Anda</h1>
      <p>Kata sandi menentukan akun yang dibuka: admin, atau jadwal dokter Anda sendiri.</p>
      <div class="field"><label for="admPw">Kata sandi</label><div class="pw-box"><input id="admPw" type="password" autocomplete="current-password" required><button class="pw-eye" type="button" data-eye="admPw" aria-label="Tampilkan kata sandi">Lihat</button></div></div>
      <button class="btn btn-primary" type="submit">Masuk</button>
      <button class="btn-link" type="button" id="toForgot">Lupa kata sandi? Ganti di sini</button>
    </form>

    <form id="stepNew" class="adm-step" hidden>
      <div class="adm-who"><span class="adm-av" id="newAv">A</span><div><b id="newName"></b><small id="newMeta"></small></div><button class="btn-link" type="button" data-restart>Ganti akun</button></div>
      <h1 id="newTitle">Buat kata sandi baru</h1>
      <p id="newLead">Identitas Anda sudah dipastikan lewat Google, jadi Anda bisa langsung membuat kata sandi baru. Sesi di perangkat lain akan otomatis keluar.</p>
      <div class="field"><label for="newPw">Kata sandi baru</label><div class="pw-box"><input id="newPw" type="password" autocomplete="new-password" minlength="8" required><button class="pw-eye" type="button" data-eye="newPw" aria-label="Tampilkan kata sandi">Lihat</button></div><small class="adm-help" id="pwRule">Minimal 8 karakter. Gabungkan huruf dan angka.</small></div>
      <div class="field"><label for="newPw2">Ulangi kata sandi baru</label><div class="pw-box"><input id="newPw2" type="password" autocomplete="new-password" required><button class="pw-eye" type="button" data-eye="newPw2" aria-label="Tampilkan kata sandi">Lihat</button></div></div>
      <button class="btn btn-primary" type="submit">Simpan &amp; masuk</button>
      <button class="btn-link" type="button" id="backPw">Kembali ke kata sandi</button>
    </form>

    <p class="err" id="admErr" hidden></p>
  </section>

  <section id="admDenied" class="adm-card" hidden>
    <span class="eyebrow">Khusus petugas</span>
    <h1>Halaman ini untuk admin dan dokter</h1>
    <p>Akun Anda tidak punya akses ke Dasbor Klinik. Untuk membuat atau melihat janji temu Anda sendiri, buka beranda.</p>
    <a class="btn btn-primary" href="index.html">Ke beranda</a>
  </section>

  <section id="admDash" hidden>
    <div class="adm-head"><span class="eyebrow" id="dashEyebrow">Dasbor Klinik</span><h1 id="dashTitle">Janji temu pasien</h1><p class="st-sub">Data diperbarui otomatis. Tidak terlihat oleh pasien.</p></div>
    <div class="st-stats" id="stStats"></div>
    <div class="adm-panel">
      <div class="search-tabs" id="stTabs" role="tablist"><button type="button" role="tab" aria-selected="true" data-tab="all">Semua janji pasien</button><button type="button" role="tab" aria-selected="false" data-tab="doc">Jadwal per dokter</button><button type="button" role="tab" aria-selected="false" data-tab="inbox" data-admin>Demo &amp; laporan bug</button><button type="button" role="tab" aria-selected="false" data-tab="staff" data-admin hidden>Akun petugas</button></div>
      <div id="stAllWrap" class="st-wrap">
        <div class="filters" id="stStatus" role="group" aria-label="Status janji"><button type="button" aria-pressed="true" data-st="all">Semua</button><button type="button" aria-pressed="false" data-st="aktif">Terjadwal</button><button type="button" aria-pressed="false" data-st="batal">Dibatalkan</button></div>
        <div class="appts" id="stAll"></div>
      </div>
      <div id="stDocWrap" class="st-wrap" hidden>
        <div class="field" id="stDocField"><label for="stDocSel">Dokter</label><select id="stDocSel"></select></div>
        <p class="appt-policy" id="stDocInfo"></p>
        <div class="appts" id="stDoc"></div>
      </div>
      <div id="stInboxWrap" class="st-wrap" hidden>
        <h4 class="st-h">Permintaan demo SIMKlinik</h4>
        <div class="appts" id="stDemos"><p class="appt-policy">Memuat…</p></div>
        <h4 class="st-h">Laporan bug</h4>
        <div class="appts" id="stBugs"><p class="appt-policy">Memuat…</p></div>
      </div>
      <div id="stStaffWrap" class="st-wrap" hidden>
        <p class="appt-policy">Setiap petugas masuk dengan akun Google-nya, lalu kata sandinya sendiri. Akun dokter hanya melihat jadwal dan pasien dokter itu.</p>
        <form id="accForm" class="acc-form">
          <div class="field"><label for="accEmail">Email Google</label><input id="accEmail" type="email" required placeholder="nama@gmail.com"></div>
          <div class="field"><label for="accName">Nama</label><input id="accName" type="text" placeholder="dr. Nadia Prameswari"></div>
          <div class="field"><label for="accRole">Peran</label><select id="accRole"><option value="dokter">Dokter</option><option value="admin">Admin</option></select></div>
          <div class="field" id="accDocF"><label for="accDoc">Dokter</label><select id="accDoc"></select></div>
          <button class="btn btn-primary" type="submit">Simpan akun</button>
        </form>
        <p class="err" id="accErr" hidden></p>
        <div class="appts" id="accList"></div>
      </div>
    </div>
  </section>
</div></main>
'''

SCRIPT = '''<script>
(function(){
  const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
''' + helpers + r'''
  const show=id=>['admLoad','admLogin','admDenied','admDash'].forEach(x=>{$('#'+x).hidden=x!==id;});

  // who may enter: on the self-hosted site, staff who pass Google + their own password; in the artifact, its owner and editors
  let me={role:'admin',name:'',email:'',doc:''};
  (async()=>{
    const [db,user]=await Promise.all([window.claude?.use?.('db'),window.claude?.use?.('user')].map(p=>Promise.resolve(p).catch(()=>null)));
    if(window.dhStaff){
      $('#admOut').addEventListener('click',()=>{dhStaff.logout();location.reload();});
      if(dhStaff.signedIn()){
        try{me=(await dhStaff.accounts()).me;}catch(_){dhStaff.logout();}
      }
      if(!dhStaff.signedIn()){signIn();return;}
      $('#admOut').hidden=false;
      $('#admMe').innerHTML=`<b>${esc(me.name)}</b> · ${me.role==='admin'?'Admin':'Dokter'}`;$('#admMe').hidden=false;
    }else if(!db||!user||!user.canEdit()){show('admDenied');return;}
    show('admDash');dashboard(db);
  })();

  // step 1 Google (or the local test form), step 2 the person's own password, or a new password when it is the
  // first sign-in or they forgot it
  function signIn(){
    show('admLogin');
    const err=$('#admErr'), oops=m=>{err.textContent=m;err.hidden=false;}, clear=()=>{err.hidden=true;};
    const msg=ex=>({rate_limited:'Terlalu banyak percobaan. Tunggu 1 menit, lalu coba lagi.',expired:ex.message,not_allowed:ex.message+' Minta admin klinik menambahkannya.',weak:ex.message,no_password:ex.message})[ex.code]||(ex.code==='not_granted'?ex.message:'Tidak bisa terhubung. Periksa koneksi lalu coba lagi.');
    let acc=null;
    const step=id=>{['stepGoogle','stepPw','stepNew'].forEach(x=>$('#'+x).hidden=x!==id);$('#admStepLbl').textContent='Khusus petugas · langkah '+(id==='stepGoogle'?'1':'2')+' dari 2';clear();};
    const who=(pre)=>{const r=acc.role==='admin'?'Admin':'Dokter'+(acc.doc?' · '+acc.doc:'');$('#'+pre+'Av').textContent=(acc.name||acc.email)[0].toUpperCase();$('#'+pre+'Name').textContent=acc.name||acc.email;$('#'+pre+'Meta').textContent=acc.email+' · '+r;};
    const afterId=a=>{acc=a;if(a.hasPassword){who('pw');step('stepPw');$('#admPw').value='';$('#admPw').focus();}else newPw(true);};
    const newPw=first=>{who('new');step('stepNew');$('#newTitle').textContent=first?'Buat kata sandi':'Ganti kata sandi';
      $('#newLead').textContent=first?'Ini login pertama Anda. Buat kata sandi untuk akun ini; berikutnya Anda masuk dengan Google lalu kata sandi ini.':'Identitas Anda sudah dipastikan lewat Google, jadi Anda bisa langsung membuat kata sandi baru. Sesi di perangkat lain akan otomatis keluar.';
      $('#backPw').hidden=first;$('#newPw').value='';$('#newPw2').value='';$('#newPw').focus();};
    $$('[data-restart]').forEach(b=>b.addEventListener('click',()=>{dhStaff.logout();step('stepGoogle');}));
    $$('[data-eye]').forEach(b=>b.addEventListener('click',()=>{const i=$('#'+b.dataset.eye);const v=i.type==='password';i.type=v?'text':'password';b.textContent=v?'Sembunyi':'Lihat';b.setAttribute('aria-label',v?'Sembunyikan kata sandi':'Tampilkan kata sandi');}));
    $('#toForgot').addEventListener('click',()=>newPw(false));
    $('#backPw').addEventListener('click',()=>{who('pw');step('stepPw');});
    const busy=(f,on)=>f.querySelectorAll('button').forEach(b=>b.disabled=on);
    $('#stepPw').addEventListener('submit',async e=>{e.preventDefault();busy(e.target,true);
      try{await dhStaff.password($('#admPw').value);location.reload();}
      catch(ex){oops(msg(ex));if(ex.code==='expired')step('stepGoogle');busy(e.target,false);}});
    $('#stepNew').addEventListener('submit',async e=>{e.preventDefault();clear();
      const a=$('#newPw').value,b=$('#newPw2').value;
      if(a.length<8)return oops('Kata sandi minimal 8 karakter.');
      if(a!==b)return oops('Kedua kata sandi belum sama. Ketik ulang.');
      busy(e.target,true);
      try{await dhStaff.setPassword(a);location.reload();}
      catch(ex){oops(msg(ex));if(ex.code==='expired')step('stepGoogle');busy(e.target,false);}});
    $('#devForm').addEventListener('submit',async e=>{e.preventDefault();busy(e.target,true);
      try{afterId(await dhStaff.devLogin($('#devEmail').value));}catch(ex){oops(msg(ex));}busy(e.target,false);});
    step('stepGoogle');
    // "another account": a full-page Google sign-in with the account chooser forced open, which comes back to /admin
    // with an ID token in the URL hash; state and nonce tie the answer to this browser
    const back=location.origin+'/admin';
    const hash=new URLSearchParams(location.hash.slice(1));
    if(hash.has('id_token')||hash.has('error')){
      history.replaceState(null,'',location.pathname+location.search);
      let want={};try{want=JSON.parse(sessionStorage.getItem('dh-gsel')||'{}');sessionStorage.removeItem('dh-gsel');}catch{}
      const tok=hash.get('id_token');let nonce='';
      try{nonce=JSON.parse(atob(tok.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))).nonce;}catch{}
      if(!tok)oops('Login Google dibatalkan.');
      else if(!want.state||hash.get('state')!==want.state||nonce!==want.nonce)oops('Login Google gagal. Coba lagi.');
      else dhStaff.google(tok).then(afterId,ex=>oops(ex.code==='not_allowed'||ex.code==='rate_limited'?msg(ex):'Login Google gagal. Coba lagi.'));
    }
    const pickAccount=clientId=>{
      const rnd=()=>Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');
      const want={state:rnd(),nonce:rnd()};try{sessionStorage.setItem('dh-gsel',JSON.stringify(want));}catch{}
      location.href='https://accounts.google.com/o/oauth2/v2/auth?'+new URLSearchParams({client_id:clientId,redirect_uri:back,
        response_type:'id_token',scope:'openid email profile',prompt:'select_account',state:want.state,nonce:want.nonce});
    };
    dhStaff.methods().then(m=>{
      if(m.devLogin)$('#devForm').hidden=false;
      if(!m.clientId){if(!m.devLogin)$('#googleNone').hidden=false;return;}
      $('#otherAcc').hidden=false;$('#otherAcc').addEventListener('click',()=>pickAccount(m.clientId));
      const s=document.createElement('script');s.src='https://accounts.google.com/gsi/client';s.async=true;
      const fail=()=>{if(!$('#admGoogle').querySelector('iframe'))$('#googleFail').hidden=false;};
      s.onerror=fail;setTimeout(fail,8000);
      s.onload=()=>{
        google.accounts.id.initialize({client_id:m.clientId,ux_mode:'popup',callback:async r=>{clear();
          try{afterId(await dhStaff.google(r.credential));}catch(ex){oops(ex.code==='not_allowed'||ex.code==='rate_limited'?msg(ex):'Login Google gagal. Coba lagi.');}}});
        google.accounts.id.renderButton($('#admGoogle'),{theme:'outline',size:'large',shape:'pill',text:'signin_with',locale:'id',width:Math.min(384,$('#stepGoogle').clientWidth||320)});
      };
      document.head.appendChild(s);
    });
  }

  function dashboard(db){
    const allBox=$('#stAll'), docBox=$('#stDoc'), docSel=$('#stDocSel');
    docSel.innerHTML=docs.map((d,i)=>`<option value="${i}">${esc(d.n)} · ${esc(spLabel(d))}</option>`).join('');
    let rows=[], status='all', tab='all';
    const isDoc=me.role==='dokter';
    if(isDoc){
      // a doctor's account: only their own schedule (the server already sends only their patients)
      const i=docs.findIndex(d=>d.n===me.doc); if(i>=0)docSel.value=i;
      $('#stDocField').hidden=true;$$('[data-admin]').forEach(b=>b.hidden=true);
      $('#dashEyebrow').textContent='Jadwal dokter';$('#dashTitle').textContent='Jadwal '+(me.name||me.doc);
      const t=$$('#stTabs button');t[0].textContent='Semua pasien saya';t[1].textContent='Jadwal saya';
      tab='doc';t.forEach(x=>x.setAttribute('aria-selected',String(x.dataset.tab==='doc')));$('#stAllWrap').hidden=true;$('#stDocWrap').hidden=false;
    }else if(window.dhStaff&&me.role==='admin'){$('[data-tab="staff"]').hidden=false;}
    const todayIso=iso(new Date());
    const slotOf=a=>a.slot||(a.when.match(/(\d{2}\.\d{2}) WIB/)||[])[1]||'';
    const isVideo=a=>a.type==='video'||/Video call/.test(a.loc);
    const row=a=>`<article class="appt ${a.status==='aktif'?'':'off'}">
      <div class="appt-top"><div><div class="appt-num">${esc(a.num)}</div><div class="st-time">${esc(slotOf(a))} WIB${a.date===todayIso?' · <b>Hari ini</b>':''}</div></div>${apptBadge(a)}</div>
      <div><div class="appt-doc">${esc(a.name)}</div><div class="appt-meta"><span>${esc(a.doc)}</span><span>${esc(a.when)}</span><span>${isVideo(a)?'Video call':esc(a.loc)}</span>${a.wa?`<span>WA ${esc(a.wa)}</span>`:''}${a.acct?`<span>Akun ${esc(a.acct.email)} · WA akun ${esc(a.acct.wa)}</span>`:''}${a.note?`<span>Keluhan: ${esc(a.note)}</span>`:''}${a.reason?`<span>Alasan batal: ${esc(a.reason)}</span>`:''}</div></div></article>`;
    function draw(){
      const act=rows.filter(a=>a.status==='aktif');
      $('#stStats').innerHTML=`<div><b>${act.filter(a=>a.date===todayIso).length}</b><span>hari ini</span></div><div><b>${act.filter(a=>a.date>todayIso).length}</b><span>akan datang</span></div><div><b>${rows.length-act.length}</b><span>dibatalkan</span></div><div><b>${new Set(rows.map(a=>a.owner)).size}</b><span>pasien</span></div>`;
      if(tab==='all'){
        const list=rows.filter(a=>status==='all'||(status==='aktif'?a.status==='aktif':a.status!=='aktif'));
        allBox.innerHTML=list.length?list.map(row).join(''):'<div class="appt-empty"><p>Belum ada janji di kategori ini.</p></div>';
      }else if(tab==='doc'){
        const d=docs[docSel.value];
        const mine=rows.filter(a=>a.doc===d.n&&a.status==='aktif'&&a.date>=todayIso);
        const byDate={};mine.forEach(a=>(byDate[a.date]=byDate[a.date]||[]).push(a));
        const days=Object.keys(byDate).sort();
        $('#stDocInfo').innerHTML=`<b>${esc(d.n)}</b> · ${esc(d.loc)} · praktik ${Object.entries(d.sched).map(([k,v])=>k+' '+v).join(', ')}`;
        docBox.innerHTML=days.length?days.map(k=>`<section class="st-day"><h4>${new Date(k+'T00:00').toLocaleDateString('id-ID',{weekday:'long',day:'numeric',month:'long'})}${k===todayIso?' · Hari ini':''} <span>${byDate[k].length} pasien</span></h4>${byDate[k].sort((x,y)=>slotOf(x).localeCompare(slotOf(y))).map(row).join('')}</section>`).join('')
          :'<div class="appt-empty"><p>Belum ada pasien terjadwal untuk dokter ini.</p></div>';
      }
    }
    allBox.innerHTML='<p class="appt-policy">Memuat janji pasien…</p>';
    const t=setTimeout(()=>allBox.insertAdjacentHTML('afterbegin','<p class="err">Data janji belum bisa dimuat. Periksa koneksi.</p>'),10000);
    db.collection('appts').onSnapshot(q=>{
      if(!q.metadata.fromCache)clearTimeout(t);
      rows=[];q.docs.forEach(d=>(d.data().items||[]).forEach(a=>rows.push({...a,owner:d.id,acct:d.data().patient})));
      rows.sort((a,b)=>(a.date+slotOf(a)).localeCompare(b.date+slotOf(b)));
      draw();
    },()=>{clearTimeout(t);allBox.innerHTML='<p class="err">Akun ini tidak punya akses ke data janji pasien. Coba keluar lalu masuk lagi.</p>';});
    $('#stTabs').addEventListener('click',e=>{const b=e.target.closest('[data-tab]');if(!b)return;tab=b.dataset.tab;
      $$('#stTabs button').forEach(x=>x.setAttribute('aria-selected',String(x===b)));
      $('#stAllWrap').hidden=tab!=='all';$('#stDocWrap').hidden=tab!=='doc';$('#stInboxWrap').hidden=tab!=='inbox';$('#stStaffWrap').hidden=tab!=='staff';if(tab==='inbox')startInbox();if(tab==='staff')startStaff();draw();});
    // demo requests and bug reports sent from the forms (bugs/<id>, demos/<id>); newest first
    let inboxOn=false;
    function startInbox(){
      if(inboxOn)return;inboxOn=true;
      const watch=(col,box,card,empty)=>db.collection(col).onSnapshot(q=>{
        const items=[];q.docs.forEach(d=>(d.data().items||[]).forEach(x=>items.push(x)));
        items.sort((a,b)=>String(b.at).localeCompare(String(a.at)));
        box.innerHTML=items.length?items.map(card).join(''):`<div class="appt-empty"><p>${empty}</p></div>`;
      },()=>{box.innerHTML='<p class="err">Akun ini tidak punya akses ke data ini.</p>';});
      const when=t=>new Date(t).toLocaleString('id-ID',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
      watch('demos',$('#stDemos'),x=>`<article class="appt"><div class="appt-top"><div><div class="appt-num">${esc(x.clinic)}</div><div class="st-time">${esc(x.city)} · ${esc(x.size)}</div></div><span class="chip">${esc(x.id)}</span></div>
        <div class="appt-meta"><span>${esc(x.name)} · WA ${esc(x.wa)}</span><span>Demo ${esc(new Date(x.date+'T00:00').toLocaleDateString('id-ID',{weekday:'short',day:'numeric',month:'short'}))}, ${esc(x.time)} WIB</span><span>Modul: ${esc((x.modules||[]).join(', '))}</span><span>Dikirim ${esc(when(x.at))}</span></div></article>`,'Belum ada permintaan demo.');
      watch('bugs',$('#stBugs'),x=>`<article class="appt"><div class="appt-top"><div><div class="appt-num">${esc(x.type)}</div><div class="st-time">${esc(x.page)} · ${esc(when(x.at))}</div></div><span class="chip chip-muted">${esc(x.id)}</span></div>
        <div class="appt-meta"><span>${esc(x.desc)}</span>${x.email?`<span>Email: ${esc(x.email)}</span>`:''}</div></article>`,'Belum ada laporan bug.');
    }
    // admin: manage who may sign in and as which doctor
    let staffOn=false;
    function startStaff(){
      if(staffOn)return;staffOn=true;
      const err=$('#accErr'),list=$('#accList');
      $('#accDoc').innerHTML=docs.map(d=>`<option>${esc(d.n)}</option>`).join('');
      const roleSync=()=>{$('#accDocF').hidden=$('#accRole').value!=='dokter';};
      $('#accRole').addEventListener('change',roleSync);roleSync();
      $('#accDoc').addEventListener('change',()=>{if(!$('#accName').value)$('#accName').value=$('#accDoc').value;});
      const load=async()=>{
        try{const {accounts}=await dhStaff.accounts();
          list.innerHTML=accounts.map(a=>`<article class="appt" data-email="${esc(a.email)}"><div class="acc-row"><div><div class="appt-doc">${esc(a.name)}</div><div class="appt-meta"><span>${esc(a.email)}</span><span>${a.role==='admin'?'Admin':'Dokter · '+esc(a.doc)}</span><span>${a.hasPassword?'Kata sandi sudah dibuat':'Belum membuat kata sandi'}</span></div></div>
            <div class="appt-acts">${a.email===me.email?'<span class="chip">Akun Anda</span>':`<button class="btn btn-line btn-sm" type="button" data-acc="edit">Ubah</button>${a.hasPassword?'<button class="btn btn-line btn-sm" type="button" data-acc="reset">Reset kata sandi</button>':''}<button class="btn btn-danger-line btn-sm" type="button" data-acc="del">Hapus</button>`}</div></div></article>`).join('')||'<div class="appt-empty"><p>Belum ada akun petugas.</p></div>';
          list._accounts=accounts;
        }catch(ex){list.innerHTML='<p class="err">Daftar akun belum bisa dimuat.</p>';}
      };
      $('#accForm').addEventListener('submit',async e=>{e.preventDefault();err.hidden=true;
        try{await dhStaff.saveAccount({email:$('#accEmail').value,name:$('#accName').value,role:$('#accRole').value,doc:$('#accDoc').value});e.target.reset();roleSync();load();}
        catch(ex){err.textContent=ex.message;err.hidden=false;}});
      list.addEventListener('click',async e=>{
        const b=e.target.closest('[data-acc]');if(!b)return;const email=b.closest('[data-email]').dataset.email;
        const a=(list._accounts||[]).find(x=>x.email===email);err.hidden=true;
        if(b.dataset.acc==='edit'){$('#accEmail').value=a.email;$('#accName').value=a.name;$('#accRole').value=a.role;roleSync();if(a.doc)$('#accDoc').value=a.doc;$('#accEmail').focus();return;}
        if(b.dataset.ok!=='1'){b.dataset.ok='1';b.textContent=b.dataset.acc==='del'?'Yakin hapus?':'Yakin reset?';setTimeout(()=>{b.dataset.ok='';b.textContent=b.dataset.acc==='del'?'Hapus':'Reset kata sandi';},4000);return;}
        try{if(b.dataset.acc==='del')await dhStaff.removeAccount(email);else await dhStaff.resetAccount(email);load();}
        catch(ex){err.textContent=ex.message;err.hidden=false;}
      });
      load();
    }
    $('#stStatus').addEventListener('click',e=>{const b=e.target.closest('[data-st]');if(!b)return;status=b.dataset.st;setPressed('#stStatus button',b);draw();});
    docSel.addEventListener('change',draw);
  }
})();
</script>'''

# a complete document: the artifact serves extra pages as-is, and build.py adds the runtime after <head>
DOC = ('<!doctype html>\n<html lang="id"><head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n')
(SRC / 'admin.html').write_text(DOC + head + style + '\n' + ADMIN_CSS + '\n</head><body>\n' + sprite + '\n\n' + BODY + '\n' + SCRIPT + '\n</body></html>\n')
print('wrote', SRC / 'admin.html')
