"""Render hand artwork in three layers per hand so colour can come from a ColorConfiguration
(tintColor) without nesting one setting inside another:

  halo_<kind>_<style>    black soft shadow (never tinted)
  body_<kind>_<style>    pure white silhouette (tinted with the chosen metal colour)
  detail_<kind>_<style>  facet shading + lume insert (never tinted)

Because the tinted layer is pure white, the result is identical whether the watch's
tint is a multiply or a colour replace.

Usage: python3 -I hands.py <out_drawable_dir>
Writes hands.json with {image_name: [width, height, pivotY_fraction]}.
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "generated")

import json
import sys

from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if __name__ == "__main__" else None
SS = 4  # supersampling

METALS = {  # option id: (display name, colour)
    "0": ("White", "#FFFFFFFF"),
    "1": ("Steel", "#FFD6DBE2"),
    "2": ("Gold", "#FFF0CD78"),
    "3": ("Rose gold", "#FFF0B6A0"),
}
ACCENTS = {
    "0": ("Orange", "#FFFF7A28"),
    "1": ("Red", "#FFE82C2C"),
    "2": ("Yellow", "#FFFFCE28"),
    "3": ("Blue", "#FF409CFF"),
    "4": ("White", "#FFF5F5F5"),
}
STYLES = {"dauphine": "Dauphine", "sword": "Sword", "baton": "Baton", "skeleton": "Skeleton"}
LUME = (232, 240, 220, 255)
INK = (20, 22, 26, 255)
SHADE = (0, 0, 0, 66)      # darkens the right-hand facet by ~26% whatever the metal colour
CLEAR = (0, 0, 0, 0)
WHITE = (255, 255, 255, 255)

# Hand geometry: length (pivot to tip), tail (pivot to back end), max width
GEOM = {"hour": (112, 20, 16), "minute": (172, 22, 13)}
HALO = 5

meta = {}


class Canvas:
    """Supersampled drawing surface in hand-local units: x across, y=0 at the pivot, -y towards the tip."""

    def __init__(self, length, tail, width):
        self.W = int(round((width + 2 * HALO + 2) * SS))
        self.H = int(round((length + tail + 2 * HALO) * SS))
        self.cx = self.W / 2
        self.py = (HALO + length) * SS
        self.img = Image.new("RGBA", (self.W, self.H), CLEAR)
        self.d = ImageDraw.Draw(self.img)
        self.frac = (HALO + length) / (length + tail + 2 * HALO)

    def p(self, pts):
        return [(self.cx + x * SS, self.py + y * SS) for x, y in pts]

    def poly(self, pts, fill, outline=None, width=0):
        self.d.polygon(self.p(pts), fill=fill, outline=outline, width=width)

    def erase(self, pts):
        self.d.polygon(self.p(pts), fill=CLEAR)

    def circle(self, x, y, r, fill):
        self.d.ellipse([self.cx + (x - r) * SS, self.py + (y - r) * SS, self.cx + (x + r) * SS, self.py + (y + r) * SS], fill=fill)

    def save(self, img, name):
        w, h = round(self.W / SS), round(self.H / SS)
        img.resize((w, h), Image.LANCZOS).save(f"{OUT}/{name}.png", optimize=True)
        meta[name] = [w, h, self.frac]

    def save_halo(self, name, strength=0.78):
        a = self.img.split()[3]
        halo = a.filter(ImageFilter.MaxFilter(2 * SS + 1)).filter(ImageFilter.GaussianBlur(HALO * SS / 2.4))
        shadow = Image.new("RGBA", self.img.size, CLEAR)
        shadow.putalpha(halo.point(lambda v: int(v * strength)))
        self.save(shadow, name)


def mirror(right):
    """Right-half outline (top to bottom) -> full polygon."""
    return right + [(-x, y) for x, y in reversed(right)]


def two_tone(c, right, P):
    c.poly(mirror(right), P["light"])
    c.poly([(0, right[0][1])] + right + [(0, right[-1][1])], P["dark"])


def dauphine(c, L, T, w, P):
    two_tone(c, [(0, -L), (w / 2, -0.20 * L), (w * 0.30, T)], P)


def sword(c, L, T, w, P):
    two_tone(c, [(0, -L), (w * 0.50, -0.80 * L), (w * 0.42, -0.30 * L), (w * 0.20, 0), (w * 0.20, T)], P)
    k = [(0, -0.92 * L), (w * 0.36, -0.78 * L), (w * 0.30, -0.32 * L), (w * 0.10, -0.14 * L)]
    c.poly(mirror(k), P["lume"], outline=P["ink"], width=int(1.1 * SS))
    c.circle(0, 0, w * 0.34, P["light"])


def baton(c, L, T, w, P):
    hw = w * 0.36
    two_tone(c, [(0, -L), (hw * 0.55, -L + 0.4), (hw, -L + 3), (hw, T)], P)
    c.circle(0, 0, w * 0.42, P["light"])


def skeleton(c, L, T, w, P):
    c.poly(mirror([(0, -L), (w * 0.50, -0.62 * L), (w * 0.24, -0.10 * L), (w * 0.20, T)]), P["light"])
    c.erase(mirror([(0, -L + 9), (w * 0.50 - 2.6, -0.62 * L), (w * 0.24 - 2.4, -0.10 * L - 6)]))
    c.circle(0, 0, w * 0.34, P["light"])


DRAW = {"dauphine": dauphine, "sword": sword, "baton": baton, "skeleton": skeleton}
BODY = {"light": WHITE, "dark": WHITE, "lume": WHITE, "ink": WHITE}
DETAIL = {"light": CLEAR, "dark": SHADE, "lume": LUME, "ink": INK}


def render_hands():
    for style, fn in DRAW.items():
        for kind, (L, T, w) in GEOM.items():
            w = w if kind == "hour" else w * 0.85
            body = Canvas(L, T, GEOM[kind][2])
            fn(body, L, T, w, BODY)
            body.save(body.img, f"body_{kind}_{style}")
            body.save_halo(f"halo_{kind}_{style}")
            det = Canvas(L, T, GEOM[kind][2])
            fn(det, L, T, w, DETAIL)
            det.save(det.img, f"detail_{kind}_{style}")


def render_seconds():
    L, T = 188, 36
    c = Canvas(L, T, 10)
    c.poly([(-0.8, -L), (0.8, -L), (1.3, T - 8), (-1.3, T - 8)], WHITE)
    c.circle(0, T - 8, 4.2, WHITE)
    c.circle(0, 0, 3.0, WHITE)
    c.save(c.img, "body_second")
    c.save_halo("halo_second", strength=0.6)


def disc(size, items, name):
    s = size * SS
    img = Image.new("RGBA", (s, s), CLEAR)
    d = ImageDraw.Draw(img)
    for r, fill, width in items:
        box = [(size / 2 - r) * SS, (size / 2 - r) * SS, (size / 2 + r) * SS, (size / 2 + r) * SS]
        if width:
            d.ellipse(box, outline=fill, width=int(width * SS))
        else:
            d.ellipse(box, fill=fill)
    img.resize((size, size), Image.LANCZOS).save(f"{OUT}/{name}.png", optimize=True)


def render_caps():
    disc(28, [(13, (0, 0, 0, 110), 0)], "cap_base")            # shadow under the cap (untinted)
    disc(28, [(8, WHITE, 0)], "cap_top")                         # tinted with the hand colour
    disc(28, [(8, (0, 0, 0, 80), 0.9)], "cap_ring")              # bevel edge (untinted)
    disc(28, [(5, WHITE, 0)], "pin_ring")                        # tinted with the seconds colour
    disc(28, [(2, (28, 28, 30, 255), 0)], "pin_dot")             # jewel (untinted)


if __name__ == "__main__":
    render_hands()
    render_seconds()
    render_caps()
    json.dump(meta, open(os.path.join(GEN, "hands.json"), "w"), indent=1)
    print(len(meta), "hand images")
