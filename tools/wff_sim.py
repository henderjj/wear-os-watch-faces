"""A small renderer for the subset of Watch Face Format used by this watch face.

It reads the generated watchface.xml directly, so previews exercise the real file:
UserConfigurations (List/Boolean), Condition/Compare/Default, Transform (alpha, angle),
Variant (AMBIENT), renderMode MASK clipping, PartImage and AnalogClock hands.

Usage: python3 -I wff_sim.py <watchface.xml> <drawable_dir> <out.png> <ISO local time> <utc offset h> [key=value ...] [ambient]
"""
import datetime as dt
import math
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw

_cache = {}
captured = {}


def load(d, res, w, h):
    key = (res, w, h)
    if key not in _cache:
        im = Image.open(f"{d}/{res}.png").convert("RGBA")
        if im.size != (w, h):
            im = im.resize((w, h), Image.BILINEAR)
        _cache[key] = np.asarray(im, np.float32) / 255.0
    return _cache[key]


def over(dst, src, x, y, alpha=1.0):
    H, W = dst.shape[:2]
    h, w = src.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    r = dst[y0:y1, x0:x1]
    a = s[..., 3:4] * alpha
    out_a = a + r[..., 3:4] * (1 - a)
    rgb = (s[..., :3] * a + r[..., :3] * r[..., 3:4] * (1 - a)) / np.maximum(out_a, 1e-6)
    r[..., :3] = rgb
    r[..., 3:4] = out_a


def rotate(layer, angle, px, py):
    """Rotate clockwise by angle degrees about (px, py), premultiplied to avoid fringes."""
    pm = layer.copy()
    pm[..., :3] *= pm[..., 3:4]
    im = Image.fromarray((pm * 255).astype(np.uint8), "RGBA").rotate(-angle, Image.BICUBIC, center=(px, py))
    out = np.asarray(im, np.float32) / 255.0
    out = out.copy()
    out[..., :3] /= np.maximum(out[..., 3:4], 1e-6)
    return np.clip(out, 0, 1)


class Sim:
    def __init__(self, xml, drawable, local, offset_h, config, ambient):
        self.root = ET.parse(xml).getroot()
        self.d = drawable
        self.local = local
        self.utc = local - dt.timedelta(hours=offset_h)
        self.ambient = ambient
        self.drawn = []
        # defaults from UserConfigurations, then overrides
        self.cfg = {}
        for c in self.root.find("UserConfigurations"):
            self.cfg[c.get("id")] = c.get("defaultValue")
            if c.tag == "ListConfiguration":
                ids = [o.get("id") for o in c]
                for k, v in config.items():
                    if k == c.get("id"):
                        assert v in ids, f"{k}={v} not in {ids}"
        self.cfg.update(config)
        self.colors = {c.get("id"): {o.get("id"): o.get("colors").split() for o in c}
                       for c in self.root.find("UserConfigurations") if c.tag == "ColorConfiguration"}
        self.sources = {
            "UTC_TIMESTAMP": int(self.utc.replace(tzinfo=dt.timezone.utc).timestamp() * 1000),
            "DAY_OF_YEAR": local.timetuple().tm_yday,
            "DAY_OF_WEEK": local.isoweekday() % 7 + 1,  # Sunday = 1
            "DAY": local.day,
            "MONTH": local.month,
        }

    # --- expressions
    def ev(self, expr):
        def sub(m):
            return str(self.sources[m.group(1)])
        py = re.sub(r"\[([A-Z_0-9]+)\]", sub, expr).replace("&&", " and ").replace("||", " or ")
        ns = {"sin": math.sin, "cos": math.cos, "acos": math.acos, "sqrt": math.sqrt, "abs": abs,
              "rad": math.radians, "deg": math.degrees, "floor": math.floor,
              "clamp": lambda x, a, b: min(max(float(x), a), b)}
        return eval(py, {"__builtins__": {}}, ns)

    def tint(self, el, img):
        t = el.get("tintColor")
        if not t:
            return img
        m = re.fullmatch(r"\[CONFIGURATION\.(\w+)\.(\d+)\]", t)
        if m:
            t = self.colors[m.group(1)][self.cfg[m.group(1)]][int(m.group(2))]
        t = t.lstrip("#")
        rgb = np.array([int(t[i:i + 2], 16) for i in range(len(t) - 6, len(t), 2)], np.float32) / 255
        out = img.copy()
        out[..., :3] *= rgb  # multiply (identical to colour-replace on pure-white artwork)
        return out

    def attr_alpha(self, el):
        a = float(el.get("alpha", 255))
        for t in el.findall("Transform"):
            if t.get("target") == "alpha":
                a = self.ev(t.get("value"))
        if self.ambient:
            for v in el.findall("Variant"):
                if v.get("mode") == "AMBIENT" and v.get("target") == "alpha":
                    a = float(v.get("value"))
        return max(0.0, min(255.0, a)) / 255.0

    # --- rendering
    def render(self):
        W, H = int(self.root.get("width")), int(self.root.get("height"))
        canvas = np.zeros((H, W, 4), np.float32)
        canvas[..., 3] = 1
        self.children(self.root.find("Scene"), canvas)
        return canvas

    def children(self, parent, layer):
        """Draw parent's children into layer, applying MASK children as a clip."""
        kids = list(parent)
        masks = [k for k in kids if k.get("renderMode") in ("MASK", "ALL")]
        if not masks:
            for k in kids:
                self.element(k, layer)
            return
        src = np.zeros_like(layer)
        for k in kids:
            if k.get("renderMode", "SOURCE") in ("SOURCE", "ALL"):
                self.element(k, src)
        mask = np.zeros_like(layer)
        for k in masks:
            self.element(k, mask, force=True)
        src[..., 3] *= mask[..., 3]
        over(layer, src, 0, 0)

    def element(self, el, layer, force=False):
        tag = el.tag
        if tag == "PartImage":
            x, y, w, h = (int(el.get(k)) for k in ("x", "y", "width", "height"))
            res = el.find("Image").get("resource")
            self.drawn.append(res)
            img = self.tint(el, load(self.d, res, w, h))
            over(layer, img, x, y, self.attr_alpha(el))
        elif tag == "Group":
            x, y, w, h = (int(el.get(k)) for k in ("x", "y", "width", "height"))
            sub = np.zeros((h, w, 4), np.float32)
            self.children(el, sub)
            ang = float(el.get("angle", 0))
            for t in el.findall("Transform"):
                if t.get("target") == "angle":
                    ang = self.ev(t.get("value"))
            if ang:
                sub = rotate(sub, ang, float(el.get("pivotX", 0.5)) * w, float(el.get("pivotY", 0.5)) * h)
            captured[el.get("name")] = sub
            over(layer, sub, x, y, self.attr_alpha(el))
        elif tag == "ListConfiguration" or tag == "BooleanConfiguration":
            want = self.cfg[el.get("id")]
            for opt in el:
                if opt.get("id") == want:
                    self.children(opt, layer)
        elif tag == "Condition":
            for comp in el.findall("Compare"):
                name = comp.get("expression")
                expr = next(e.text for e in el.find("Expressions") if e.get("name") == name)
                if self.ev(expr):
                    self.children(comp, layer)
                    return
            if el.find("Default") is not None:
                self.children(el.find("Default"), layer)
        elif tag == "AnalogClock":
            if self.attr_alpha(el) == 0:
                return
            t = self.local
            angles = {"HourHand": (t.hour % 12 + t.minute / 60 + t.second / 3600) * 30,
                      "MinuteHand": (t.minute + t.second / 60) * 6, "SecondHand": t.second * 6}
            for hnd in el:
                if hnd.tag not in angles:
                    continue
                a = self.attr_alpha(hnd)
                if a == 0:
                    continue
                x, y, w, h = (int(hnd.get(k)) for k in ("x", "y", "width", "height"))
                img = self.tint(hnd, load(self.d, hnd.get("resource"), w, h))
                tmp = np.zeros_like(layer)
                over(tmp, img, x, y)
                px, py = x + float(hnd.get("pivotX", 0.5)) * w, y + float(hnd.get("pivotY", 0.5)) * h
                over(layer, rotate(tmp, angles[hnd.tag], px, py), 0, 0, a)
        elif tag in ("Variant", "Transform", "Metadata"):
            pass
        else:
            raise ValueError(f"unsupported element {tag}")


def to_image(canvas):
    img = Image.fromarray((np.clip(canvas, 0, 1) * 255).astype(np.uint8), "RGBA")
    n = img.width
    circ = Image.new("L", img.size, 0)
    ImageDraw.Draw(circ).ellipse([0, 0, n - 1, n - 1], fill=255)
    bg = Image.new("RGBA", img.size, (24, 24, 28, 255))
    bg.paste(img, (0, 0), circ)
    return bg


def run(xml, d, iso, off, config=None, ambient=False):
    local = dt.datetime.fromisoformat(iso)
    s = Sim(xml, d, local, off, config or {}, ambient)
    return to_image(s.render()), s


if __name__ == "__main__":
    xml, d, out, iso, off = sys.argv[1:6]
    cfg = dict(a.split("=", 1) for a in sys.argv[6:] if "=" in a)
    img, _ = run(xml, d, iso, float(off), cfg, "ambient" in sys.argv[6:])
    img.save(out)
