"""Render an icon for each View option: the region's globe, dimmed, with its name on top.

Usage: python3 -I icons.py <font.ttf> <out_drawable_dir>
Run after render_assets.py, which writes the earth_day_<view>.png images this reads.
The watch's Customise screen shows these icons, so the name is readable there; the
dial itself doesn't change.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from params import VIEWS  # noqa: E402

FONT, OUT = sys.argv[1], sys.argv[2]
SIZE = 160          # icon size in px
SS = 4              # supersampling for the lettering
TEXT_W = 118        # widest line, so the words stay inside a circular crop
TRACK = 1.2
DIM = 0.45          # how much of the globe's brightness to keep behind the words


def lines_for(name, font):
    """Split the upper-case name into at most three lines no wider than TEXT_W."""
    words, lines = name.upper().split(), []
    for w in words:
        if lines and width(lines[-1] + " " + w, font) <= TEXT_W:
            lines[-1] += " " + w
        else:
            lines.append(w)
    return lines


def width(s, font):
    return (sum(font.getlength(ch) for ch in s) + TRACK * SS * (len(s) - 1)) / SS


def icon(view, name):
    globe = Image.open(os.path.join(OUT, f"earth_day_{view}.png")).convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
    arr = np.asarray(globe).astype(np.float32)
    arr[..., :3] *= DIM
    base = Image.fromarray(arr.astype(np.uint8), "RGBA")
    bg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(bg).ellipse([0, 0, SIZE - 1, SIZE - 1], fill=(8, 12, 22, 255))
    bg.alpha_composite(base)

    for size in (26, 24, 22, 20):
        font = ImageFont.truetype(FONT, size * SS)
        lines = lines_for(name, font)
        if len(lines) <= 3 and all(width(l, font) <= TEXT_W for l in lines):
            break
    top, bot = font.getbbox("H")[1], font.getbbox("H")[3]
    cap, gap = (bot - top), size * 0.32 * SS
    block = len(lines) * cap + (len(lines) - 1) * gap
    text = Image.new("L", (SIZE * SS, SIZE * SS), 0)
    d = ImageDraw.Draw(text)
    y = (SIZE * SS - block) / 2 - top
    for line in lines:
        x = (SIZE * SS - width(line, font) * SS) / 2
        for ch in line:
            d.text((x, y), ch, font=font, fill=255)
            x += font.getlength(ch) + TRACK * SS
        y += cap + gap
    text = text.resize((SIZE, SIZE), Image.LANCZOS)
    halo = text.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(2.5))
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow.putalpha(halo.point(lambda v: int(v * 0.8)))
    bg.alpha_composite(shadow)
    white = Image.new("RGBA", (SIZE, SIZE), (245, 245, 240, 255))
    white.putalpha(text)
    bg.alpha_composite(white)
    bg.save(os.path.join(OUT, f"icon_{view}.png"), optimize=True)


if __name__ == "__main__":
    for k, (name, _, _) in VIEWS.items():
        icon(k, name)
    print(len(VIEWS), "view icons")
