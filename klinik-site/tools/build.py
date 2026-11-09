"""Copy the Vidia Medika pages from the artifact sources (one folder up) into public/ for Cloudflare Pages.

Run from klinik-site/:  python3 tools/build.py
Each page gets a normal document head and loads dh-runtime.js before its own scripts.
"""
import pathlib, shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT.parent
OUT = ROOT / 'public'
RUNTIME = '<script src="/dh-runtime.js"></script>'
# tab icon and home-screen icon for every page (made from the logo by tools/make_icons.py)
ICONS = ('<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">'
         '<link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">')
RESET = ('<style>:root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);'
         'padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>')

home = (SRC / 'devhealth.html').read_text()
(OUT / 'index.html').write_text(
    '<!doctype html>\n<html lang="id"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    + RESET + ICONS + RUNTIME + '</head><body>\n' + home + '\n</body></html>\n')

for name in ('artikel.html', 'dokter.html', 'admin.html', 'masuk.html', 'privasi.html'):
    page = (SRC / name).read_text()
    assert '<head>' in page, name
    (OUT / name).write_text(page.replace('<head>', '<head>\n' + ICONS + RUNTIME, 1))

for asset in ('hero-doctor.webp', 'vidia-logo.svg', 'favicon.ico', 'favicon-32.png', 'favicon-192.png', 'apple-touch-icon.png'):
    shutil.copy(SRC / asset, OUT / asset)
print('built:', ', '.join(sorted(p.name for p in OUT.iterdir())))
