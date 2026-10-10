"""Render date-window frames and the words/digits shown inside them.

Usage: python3 -I date_assets.py <font.ttf> <out_drawable_dir>
Writes date_layout.json with the element positions used by make_xml.py / simulate.py.
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "generated")

import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT, OUT = sys.argv[1], sys.argv[2]
SS = 4
H = 30            # window height
SIZE = 20         # font size (canvas px)
TRACK = 1.3       # letter spacing (canvas px)
TEXT = (242, 242, 238)
DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]          # DAY_OF_WEEK 1..7
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

font = ImageFont.truetype(FONT, SIZE * SS)
cap_top, cap_bot = font.getbbox("H")[1], font.getbbox("H")[3]


def text_width(s):
    return (sum(font.getlength(ch) for ch in s) + TRACK * SS * (len(s) - 1)) / SS


def text_img(s, w, align="center"):
    img = Image.new("RGBA", (w * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    tw = text_width(s) * SS
    x = {"center": (w * SS - tw) / 2, "left": 0, "right": w * SS - tw}[align]
    y = (H * SS - (cap_bot - cap_top)) / 2 - cap_top
    for ch in s:
        d.text((x, y), ch, font=font, fill=TEXT + (255,))
        x += font.getlength(ch) + TRACK * SS
    return img.resize((w, H), Image.LANCZOS)


def rrect_alpha(w, h, r, inset=0.0):
    """Antialiased rounded-rectangle coverage at supersampled resolution."""
    W, Hh = int(w * SS), int(h * SS)
    yy, xx = np.mgrid[0:Hh, 0:W]
    x = (xx + 0.5) / SS; y = (yy + 0.5) / SS
    r2 = r - inset
    dx = np.maximum(np.abs(x - w / 2) - (w / 2 - inset - r2), 0)
    dy = np.maximum(np.abs(y - h / 2) - (h / 2 - inset - r2), 0)
    dist = np.hypot(dx, dy) - r2
    return np.clip(0.5 - dist * SS / 1.0, 0, 1), y


def frame(name, w):
    outer, y = rrect_alpha(w, H, 6)
    inner, _ = rrect_alpha(w, H, 6, inset=1.8)
    t = y / H
    metal = (225 - 120 * t)[..., None] * np.ones(3)          # bevelled steel: light top, dark bottom
    glass = np.zeros_like(metal) + np.array([6, 9, 16])
    # soft inner shadow under the top edge
    shade = np.clip(1 - (y - 1.8) / 7, 0, 1)[..., None]
    glass_a = 0.66 + 0.22 * shade[..., 0]
    rgb = metal * (outer - inner)[..., None] + glass * inner[..., None]
    a = (outer - inner) + inner * glass_a
    rgb = np.where(a[..., None] > 0, rgb / np.maximum((outer - inner) + inner, 1e-6)[..., None], 0)
    img = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.clip(a * 255, 0, 255)]).astype(np.uint8), "RGBA")
    img.resize((w, H), Image.LANCZOS).save(f"{OUT}/{name}.png", optimize=True)


def save(img, name):
    img.save(f"{OUT}/{name}.png", optimize=True)


if __name__ == "__main__":
    C = 225
    day_w = max(round(text_width(s)) for s in DAYS)            # widest weekday
    mon_w = max(round(text_width(s)) for s in MONTHS)
    dig_w = round(max(text_width(str(i)) for i in range(10)) + TRACK)
    pad, gap = 10, 6

    # weekday (centred for its own window, right-aligned for the combined window)
    for i, s in enumerate(DAYS, start=1):
        save(text_img(s, day_w + 2 * pad), f"day_{i}")
        save(text_img(s, day_w, "right"), f"dayr_{i}")
    for i, s in enumerate(MONTHS, start=1):
        save(text_img(s, mon_w, "left"), f"mon_{i}")
    for i in range(10):
        save(text_img(str(i), dig_w), f"dig_{i}")

    # --- split layout: weekday window at 9 o'clock, date window at 3 o'clock
    edge = 184                                            # outer edges sit this far from the centre
    dw = day_w + 2 * pad
    date_w = 2 * dig_w + gap + mon_w + 2 * pad - 2
    frame("frame_day", dw)
    frame("frame_date", date_w)
    split = {
        "day_frame": [C - edge, C - H // 2, dw, H],
        "day_text": [C - edge, C - H // 2, dw, H],
        "date_frame": [C + edge - date_w, C - H // 2, date_w, H],
    }
    x0 = C + edge - date_w + pad
    split["tens"] = [x0, C - H // 2, dig_w, H]
    split["units"] = [x0 + dig_w, C - H // 2, dig_w, H]
    split["month"] = [x0 + 2 * dig_w + gap, C - H // 2, mon_w, H]

    # --- single window at 6 o'clock: WED 08 OCT
    full_w = day_w + gap + 2 + 2 * dig_w + gap + mon_w + 2 * pad - 2
    frame("frame_full", full_w)
    yc = C + 147 - H // 2
    xf = C - full_w // 2
    single = {"frame": [xf, yc, full_w, H]}
    x = xf + pad
    single["day"] = [x, yc, day_w, H]; x += day_w + gap + 2
    single["tens"] = [x, yc, dig_w, H]; x += dig_w
    single["units"] = [x, yc, dig_w, H]; x += dig_w + gap
    single["month"] = [x, yc, mon_w, H]
    json.dump({"split": split, "single": single, "H": H}, open(os.path.join(GEN, "date_layout.json"), "w"), indent=1)
    print(json.dumps({"split": split, "single": single}))
