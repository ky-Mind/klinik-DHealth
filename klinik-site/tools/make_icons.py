"""Make the transparent logo and the tab icons from the original logo on black (Dhealth.png, one folder up).

Run from klinik-site/:  python3 tools/make_icons.py
The black is removed by brightness: solid parts keep their colour, the glow fades out with its full-brightness hue,
so the logo sits cleanly on light and dark pages.
"""
import pathlib
import numpy as np
from PIL import Image

SRC = pathlib.Path(__file__).resolve().parent.parent.parent
im = np.asarray(Image.open(SRC / 'Dhealth.png').convert('RGB')).astype(np.float32)
m = im.max(axis=2)
lo, hi = 10.0, 140.0
t = np.clip((m - lo) / (hi - lo), 0, 1)
bright = im * 255 / np.maximum(m, 1)[..., None]
rgb = bright * (1 - t[..., None]) + im * t[..., None]
img = Image.fromarray(np.dstack([rgb, t * 255]).clip(0, 255).astype(np.uint8), 'RGBA')
img = img.crop(img.getbbox())
w, h = img.size
side = max(w, h)
sq = Image.new('RGBA', (side, side), (0, 0, 0, 0))
sq.paste(img, ((side - w) // 2, (side - h) // 2))
sq.save(SRC / 'dhealth-logo-full.png')
sq.resize((256, 256), Image.LANCZOS).save(SRC / 'dhealth-logo.png', optimize=True)
for name, size in (('favicon-32.png', 32), ('favicon-192.png', 192), ('apple-touch-icon.png', 180)):
    sq.resize((size, size), Image.LANCZOS).save(SRC / name, optimize=True)
sq.save(SRC / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
print('icons written to', SRC)
