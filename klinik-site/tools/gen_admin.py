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
head = head.replace('<title>DHealth</title>', '<title>Admin DHealth</title>')
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
.adm-card .adm-help{font-size:13.5px;color:var(--faint)}
@media (max-width:520px){.adm-nav .chip{display:none}.adm-panel{padding:14px}}
</style>'''

BODY = f'''<header class="nav adm-nav" id="nav">
  <div class="wrap nav-in">
    <a class="logo" href="index.html" aria-label="DHealth beranda">{logo}<span>D<b>Health</b></span></a>
    <span class="chip">Admin &amp; dokter</span>
    <div class="adm-act"><a class="btn btn-line btn-sm" href="index.html">Lihat situs</a><button class="btn btn-soft btn-sm" type="button" id="admOut" hidden>Keluar</button></div>
  </div>
</header>

<main class="adm"><div class="wrap">
  <section id="admLoad" class="adm-card"><p>Memuat…</p></section>

  <section id="admLogin" class="adm-card" hidden>
    <span class="eyebrow">Khusus petugas</span>
    <h1>Masuk Dasbor Klinik</h1>
    <p>Untuk admin dan dokter DHealth: janji pasien, jadwal per dokter, permintaan demo, dan laporan bug.</p>
    <form id="admForm" style="display:grid;gap:14px">
      <div class="field"><label for="admPw">Kata sandi petugas</label><input id="admPw" type="password" autocomplete="current-password" required></div>
      <p class="err" id="admErr" hidden></p>
      <button class="btn btn-primary" type="submit">Masuk</button>
    </form>
    <div id="admGoogleWrap" class="adm-google" hidden>
      <div class="adm-or"><span>atau</span></div>
      <div id="admGoogle"></div>
    </div>
    <p class="adm-help" id="admHelp">Lupa kata sandi? Hubungi pengelola situs untuk menggantinya.</p>
  </section>

  <section id="admDenied" class="adm-card" hidden>
    <span class="eyebrow">Khusus petugas</span>
    <h1>Halaman ini untuk admin dan dokter</h1>
    <p>Akun Anda tidak punya akses ke Dasbor Klinik. Untuk membuat atau melihat janji temu Anda sendiri, buka beranda.</p>
    <a class="btn btn-primary" href="index.html">Ke beranda</a>
  </section>

  <section id="admDash" hidden>
    <div class="adm-head"><span class="eyebrow">Dasbor Klinik</span><h1>Janji temu pasien</h1><p class="st-sub">Data diperbarui otomatis. Tidak terlihat oleh pasien.</p></div>
    <div class="st-stats" id="stStats"></div>
    <div class="adm-panel">
      <div class="search-tabs" id="stTabs" role="tablist"><button type="button" role="tab" aria-selected="true" data-tab="all">Semua janji pasien</button><button type="button" role="tab" aria-selected="false" data-tab="doc">Jadwal per dokter</button><button type="button" role="tab" aria-selected="false" data-tab="inbox">Demo &amp; laporan bug</button></div>
      <div id="stAllWrap" class="st-wrap">
        <div class="filters" id="stStatus" role="group" aria-label="Status janji"><button type="button" aria-pressed="true" data-st="all">Semua</button><button type="button" aria-pressed="false" data-st="aktif">Terjadwal</button><button type="button" aria-pressed="false" data-st="batal">Dibatalkan</button></div>
        <div class="appts" id="stAll"></div>
      </div>
      <div id="stDocWrap" class="st-wrap" hidden>
        <div class="field"><label for="stDocSel">Dokter</label><select id="stDocSel"></select></div>
        <p class="appt-policy" id="stDocInfo"></p>
        <div class="appts" id="stDoc"></div>
      </div>
      <div id="stInboxWrap" class="st-wrap" hidden>
        <h4 class="st-h">Permintaan demo SIMKlinik</h4>
        <div class="appts" id="stDemos"><p class="appt-policy">Memuat…</p></div>
        <h4 class="st-h">Laporan bug</h4>
        <div class="appts" id="stBugs"><p class="appt-policy">Memuat…</p></div>
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

  // who may enter: on the self-hosted site, whoever signs in with the clinic password; in the artifact, its owner and editors
  (async()=>{
    const [db,user]=await Promise.all([window.claude?.use?.('db'),window.claude?.use?.('user')].map(p=>Promise.resolve(p).catch(()=>null)));
    if(window.dhStaff){
      $('#admForm').addEventListener('submit',async e=>{
        e.preventDefault();const err=$('#admErr');err.hidden=true;
        const btn=e.submitter||$('#admForm button');btn.disabled=true;
        try{await dhStaff.login($('#admPw').value);location.reload();}
        catch(ex){err.textContent=ex.code==='rate_limited'?'Terlalu banyak percobaan. Coba lagi beberapa menit lagi.':'Kata sandi salah.';err.hidden=false;btn.disabled=false;}
      });
      $('#admOut').addEventListener('click',()=>{dhStaff.logout();location.reload();});
      if(!dhStaff.signedIn())googleButton();
      if(!dhStaff.signedIn()){show('admLogin');$('#admPw').focus();return;}
      $('#admOut').hidden=false;
    }else if(!db||!user||!user.canEdit()){show('admDenied');return;}
    show('admDash');dashboard(db);
  })();

  // "Masuk dengan Google" for staff whose email is on the clinic's list; hidden until the site has a Google client
  async function googleButton(){
    const clientId=await dhStaff.googleClientId(); if(!clientId)return;
    const s=document.createElement('script');s.src='https://accounts.google.com/gsi/client';s.async=true;
    s.onload=()=>{
      google.accounts.id.initialize({client_id:clientId,ux_mode:'popup',callback:async r=>{
        const err=$('#admErr');err.hidden=true;
        try{await dhStaff.loginGoogle(r.credential);location.reload();}
        catch(ex){err.textContent=ex.code==='not_allowed'?ex.message+' Minta pengelola situs menambahkannya.':ex.code==='rate_limited'?'Terlalu banyak percobaan. Coba lagi beberapa menit lagi.':'Login Google gagal. Coba lagi.';err.hidden=false;}
      }});
      google.accounts.id.renderButton($('#admGoogle'),{theme:'outline',size:'large',shape:'pill',text:'signin_with',locale:'id',width:Math.min(384,$('#admForm').clientWidth||320)});
      $('#admGoogleWrap').hidden=false;
      $('#admHelp').textContent='Lupa kata sandi? Masuk dengan akun Google yang terdaftar, atau hubungi pengelola situs untuk menggantinya.';
    };
    document.head.appendChild(s);
  }

  function dashboard(db){
    const allBox=$('#stAll'), docBox=$('#stDoc'), docSel=$('#stDocSel');
    docSel.innerHTML=docs.map((d,i)=>`<option value="${i}">${esc(d.n)} · ${esc(spLabel(d))}</option>`).join('');
    let rows=[], status='all', tab='all';
    const todayIso=iso(new Date());
    const slotOf=a=>a.slot||(a.when.match(/(\d{2}\.\d{2}) WIB/)||[])[1]||'';
    const isVideo=a=>a.type==='video'||/Video call/.test(a.loc);
    const row=a=>`<article class="appt ${a.status==='aktif'?'':'off'}">
      <div class="appt-top"><div><div class="appt-num">${esc(a.num)}</div><div class="st-time">${esc(slotOf(a))} WIB${a.date===todayIso?' · <b>Hari ini</b>':''}</div></div>${apptBadge(a)}</div>
      <div><div class="appt-doc">${esc(a.name)}</div><div class="appt-meta"><span>${esc(a.doc)}</span><span>${esc(a.when)}</span><span>${isVideo(a)?'Video call':esc(a.loc)}</span>${a.wa?`<span>WA ${esc(a.wa)}</span>`:''}${a.note?`<span>Keluhan: ${esc(a.note)}</span>`:''}${a.reason?`<span>Alasan batal: ${esc(a.reason)}</span>`:''}</div></div></article>`;
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
      rows=[];q.docs.forEach(d=>(d.data().items||[]).forEach(a=>rows.push({...a,owner:d.id})));
      rows.sort((a,b)=>(a.date+slotOf(a)).localeCompare(b.date+slotOf(b)));
      draw();
    },()=>{clearTimeout(t);allBox.innerHTML='<p class="err">Akun ini tidak punya akses ke data janji pasien. Coba keluar lalu masuk lagi.</p>';});
    $('#stTabs').addEventListener('click',e=>{const b=e.target.closest('[data-tab]');if(!b)return;tab=b.dataset.tab;
      $$('#stTabs button').forEach(x=>x.setAttribute('aria-selected',String(x===b)));
      $('#stAllWrap').hidden=tab!=='all';$('#stDocWrap').hidden=tab!=='doc';$('#stInboxWrap').hidden=tab!=='inbox';if(tab==='inbox')startInbox();draw();});
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
