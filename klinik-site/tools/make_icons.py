"""Draw the Vidia Medika logo mark and write the header logo and the tab icons (one folder up).

Run from klinik-site/:  python3 tools/make_icons.py
The mark is a "V" of two rounded strokes (bright and deep blue) with a medical cross in its notch; the same geometry
is in vidia-logo.svg, which the page headers use. Raster copies are drawn large and scaled down for clean edges.
"""
import pathlib
from PIL import Image, ImageDraw

SRC = pathlib.Path(__file__).resolve().parent.parent.parent
SIZE = 1024
K = SIZE / 64  # the SVG viewBox is 64 units wide


def stroke(draw, a, b, width, colour):
    draw.line([(a[0] * K, a[1] * K), (b[0] * K, b[1] * K)], fill=colour, width=int(width * K))
    r = width * K / 2
    for x, y in (a, b):
        draw.ellipse([x * K - r, y * K - r, x * K + r, y * K + r], fill=colour)


mark = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(mark)
stroke(d, (13, 15), (32, 51), 11, '#0778C8')
stroke(d, (51, 15), (32, 51), 11, '#0A5BB0')
stroke(d, (32, 9), (32, 23), 5.5, '#18A9E6')
stroke(d, (25, 16), (39, 16), 5.5, '#18A9E6')

mark.save(SRC / 'vidia-logo-1024.png')
for name, size in (('favicon-32.png', 32), ('favicon-192.png', 192), ('apple-touch-icon.png', 180)):
    mark.resize((size, size), Image.LANCZOS).save(SRC / name, optimize=True)
mark.save(SRC / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
print('icons written to', SRC)
