"""Draw images/views.png: every view at 14:30 local solar time, one row per latitude.

Run from faces/earth-day-night after tools/build.py:
    python tools/view_sheet.py
This picture is for the README and GUIDE only; build.py doesn't make it and the
watch face doesn't use it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(PROJECT, "..", "..", "tools")))

import wff_sim  # noqa: E402
from params import CANCER, CAPRICORN, EQUATOR, VIEWS  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

RES = os.path.join(PROJECT, "watchface", "src", "main", "res")
XML = os.path.join(RES, "raw", "watchface.xml")
DRAWABLE = os.path.join(RES, "drawable-nodpi")
FONT = os.path.join(PROJECT, "inputs", "BarlowCondensed-SemiBold.ttf")
DATE = "2026-11-21T14:30:00"
ROWS = [("Tropic of Cancer · 23.44°N", CANCER), ("Equator · 0°", EQUATOR),
        ("Tropic of Capricorn · 23.44°S", CAPRICORN)]
C, G, LBL, HEAD, TOP = 240, 20, 54, 44, 30


def main():
    f, fs, fh = (ImageFont.truetype(FONT, n) for n in (22, 17, 30))
    cols = max(sum(v[1] == lat for v in VIEWS.values()) for _, lat in ROWS)
    out = Image.new("RGB", (cols * C + (cols + 1) * G, len(ROWS) * (HEAD + C + LBL + G) + G + TOP), (18, 18, 22))
    d = ImageDraw.Draw(out)
    d.text((G, G - 6), "West to east. Each face at 14:30 local solar time on 21 November 2026",
           font=fs, fill=(150, 150, 160))
    y = G + TOP
    for title, lat in ROWS:
        d.text((G, y), title, font=fh, fill=(235, 235, 240))
        y += HEAD
        ids = sorted((k for k, v in VIEWS.items() if v[1] == lat), key=lambda k: VIEWS[k][2])
        for i, k in enumerate(ids):
            name, _, lon = VIEWS[k]
            img, _ = wff_sim.run(XML, DRAWABLE, DATE, lon / 15, {"view": k})
            img = img.resize((C, C), Image.LANCZOS)
            disk = Image.new("L", (C, C), 0)
            ImageDraw.Draw(disk).ellipse([0, 0, C - 1, C - 1], fill=255)
            x = G + i * (C + G)
            out.paste(img, (x, y), disk)
            d.text((x + C / 2, y + C + 6), name, font=f, fill=(235, 235, 240), anchor="ma")
            d.text((x + C / 2, y + C + 31), f"{abs(lon):g}°{'E' if lon >= 0 else 'W'}",
                   font=fs, fill=(150, 150, 160), anchor="ma")
        y += C + LBL + G
    out.save(os.path.join(PROJECT, "images", "views.png"), optimize=True)


if __name__ == "__main__":
    main()
