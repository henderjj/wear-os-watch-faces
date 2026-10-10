"""Render all bitmap assets for the Earth day/night watch face.

Usage: python3 -I render_assets.py <day_texture> <night_texture> <out_drawable_dir>
"""
import math
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from params import (CANVAS, CENTER, EARTH_R, LAT0, LON0, MASK_STEP_DEG,
                    MASK_COUNT, MASK_RES, mask_profile)

DAY_TEX, NIGHT_TEX, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SS = 2  # supersampling


def save(arr, name):
    Image.fromarray(np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA").save(f"{OUT}/{name}.png", optimize=True)


def sample(tex, lat, lon):
    """Bilinear sample an equirectangular texture (float array HxWx3)."""
    h, w, _ = tex.shape
    x = (lon + 180.0) / 360.0 * w - 0.5
    y = (90.0 - lat) / 180.0 * h - 0.5
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    x1 = (x0 + 1) % w; x0 = x0 % w
    y0c = np.clip(y0, 0, h - 1); y1c = np.clip(y0 + 1, 0, h - 1)
    a = tex[y0c, x0] * (1 - fx) + tex[y0c, x1] * fx
    b = tex[y1c, x0] * (1 - fx) + tex[y1c, x1] * fx
    return a * (1 - fy) + b * fy


def ortho_grid(size):
    """Return u (east), v (north), z, inside-mask for a disk filling size x size."""
    c = (size - 1) / 2.0
    yy, xx = np.mgrid[0:size, 0:size]
    u = (xx - c) / (size / 2.0)
    v = -(yy - c) / (size / 2.0)
    r2 = u * u + v * v
    inside = r2 <= 1.0
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    return u, v, z, inside, np.sqrt(r2)


def earth_latlon(u, v, z):
    p0, l0 = math.radians(LAT0), math.radians(LON0)
    e = np.array([-math.sin(l0), math.cos(l0), 0.0])
    n = np.array([-math.sin(p0) * math.cos(l0), -math.sin(p0) * math.sin(l0), math.cos(p0)])
    c = np.array([math.cos(p0) * math.cos(l0), math.cos(p0) * math.sin(l0), math.sin(p0)])
    P = u[..., None] * e + v[..., None] * n + z[..., None] * c
    lat = np.degrees(np.arcsin(np.clip(P[..., 2], -1, 1)))
    lon = np.degrees(np.arctan2(P[..., 1], P[..., 0]))
    return lat, lon


def disk_alpha(r, size):
    # antialiased edge, 1 px wide at final resolution
    px = 1.0 / (size / 2.0)
    return np.clip((1.0 - r) / px + 0.5, 0, 1)


def render_earth():
    size = 2 * EARTH_R * SS
    u, v, z, inside, r = ortho_grid(size)
    lat, lon = earth_latlon(u, v, z)
    day_tex = np.asarray(Image.open(DAY_TEX).convert("RGB"), dtype=np.float32) / 255.0
    night_tex = np.asarray(Image.open(NIGHT_TEX).convert("RGB"), dtype=np.float32) / 255.0

    day = sample(day_tex, lat, lon)
    # gentle contrast / saturation lift
    grey = day.mean(axis=2, keepdims=True)
    day = np.clip(grey + (day - grey) * 1.12, 0, 1)
    day = np.clip((day - 0.02) * 1.15, 0, 1)
    # Rayleigh haze towards the limb
    haze = np.array([0.55, 0.72, 1.0])
    w = (0.5 * (1 - z) ** 2.5)[..., None]
    day = day * (1 - w) + haze * w

    night = sample(night_tex, lat, lon)
    lum = night.max(axis=2, keepdims=True)
    lights = np.clip((lum - 0.22) / 0.45, 0, 1) ** 1.3  # city lights are the bright pixels
    base = night * 0.62  # darker landmasses, still readable
    glow = np.array([1.0, 0.78, 0.45]) * lights * 0.95
    night = np.clip(base * (1 - lights) + glow + base * lights * 0.4, 0, 1)
    rim = (np.array([0.05, 0.10, 0.26]) * ((1 - z) ** 4)[..., None])
    night = np.clip(night + rim, 0, 1)

    a = disk_alpha(r, size)[..., None]
    for name, img in (("earth_day", day), ("earth_night", night)):
        rgba = np.concatenate([img, a], axis=2)
        im = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").resize(
            (2 * EARTH_R, 2 * EARTH_R), Image.LANCZOS)
        im.save(f"{OUT}/{name}.png", optimize=True)


def render_masks():
    """Mask k: sun at angle k*STEP from the viewing direction, pointing to +x (right)."""
    size = MASK_RES
    c = (size - 1) / 2.0
    yy, xx = np.mgrid[0:size, 0:size]
    uu = (xx - c) / (size / 2.0)
    vv = (yy - c) / (size / 2.0)
    r2 = uu * uu + vv * vv
    # outside the disk, continue as if on the limb so rotation never exposes an edge
    scale = np.where(r2 > 1, 1 / np.sqrt(np.maximum(r2, 1e-9)), 1.0)
    uu, r2 = uu * scale, np.minimum(r2, 1)
    zz = np.sqrt(1 - r2)
    for k in range(MASK_COUNT):
        a = math.radians(k * MASK_STEP_DEG)
        illum = math.sin(a) * uu + math.cos(a) * zz
        m = mask_profile(illum)
        rgba = np.dstack([np.ones_like(m)] * 3 + [m])
        save(rgba, f"mask_{k:02d}")


def render_background():
    s = CANVAS * SS
    yy, xx = np.mgrid[0:s, 0:s]
    r = np.hypot(xx - (s - 1) / 2, yy - (s - 1) / 2) / SS
    # Stars
    rnd = random.Random(7)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    placed = 0
    while placed < 140:
        x, y = rnd.uniform(0, s), rnd.uniform(0, s)
        rr = math.hypot(x - s / 2, y - s / 2) / SS
        if rr < EARTH_R + 4 or rr > CANVAS / 2:
            continue
        b = int(255 * rnd.uniform(0.2, 0.75))
        rad = rnd.uniform(0.5, 1.2) * SS
        tint = rnd.choice([(255, 255, 255), (220, 230, 255), (255, 240, 220)])
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=tuple(int(t * b / 255) for t in tint) + (255,))
        placed += 1
    img.resize((CANVAS, CANVAS), Image.LANCZOS).save(f"{OUT}/space.png", optimize=True)

    # Atmosphere glow ring (transparent image)
    g = np.exp(-np.clip(r - EARTH_R, 0, None) / 4.5) * (r >= EARTH_R - 2)
    g = g * 0.5
    col = np.array([0.40, 0.65, 1.0])
    rgba = np.dstack([np.broadcast_to(col, g.shape + (3,)).copy().reshape(g.shape + (3,)), g])
    im = Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").resize((CANVAS, CANVAS), Image.LANCZOS)
    im.save(f"{OUT}/atmosphere.png", optimize=True)


def render_dial():
    s = CANVAS * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img); ds = ImageDraw.Draw(shadow)
    cx = cy = s / 2
    outer = (CANVAS / 2 - 4) * SS
    for i in range(60):
        ang = math.radians(i * 6 - 90)
        hour = i % 5 == 0
        if i == 0:
            length, width, col = 18, 7, (255, 255, 255, 255)
        elif hour:
            length, width, col = 15, 4.5, (255, 255, 255, 240)
        else:
            length, width, col = 7, 2, (255, 255, 255, 150)
        r1, r2 = outer, outer - length * SS
        p1 = (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))
        p2 = (cx + r2 * math.cos(ang), cy + r2 * math.sin(ang))
        d.line([p1, p2], fill=col, width=int(width * SS))
        ds.line([p1, p2], fill=(0, 0, 0, 200), width=int((width + 4) * SS))
    shadow = shadow.filter(ImageFilter.GaussianBlur(2 * SS))
    out = Image.alpha_composite(shadow, img).resize((CANVAS, CANVAS), Image.LANCZOS)
    out.save(f"{OUT}/dial.png", optimize=True)


def hand(name, length, tail, w_base, w_tip, color, halo=5, shape="dauphine", counter_r=0):
    """Draw a hand pointing up. Returns pivot fraction (pivotY)."""
    W = int((max(w_base, counter_r * 2) + 2 * halo) * SS) + 2
    H = int((length + tail + 2 * halo) * SS)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = W / 2
    py = (halo + length) * SS  # pivot y
    top = halo * SS
    bot = py + tail * SS
    if shape == "dauphine":
        pts = [(cx, top), (cx + w_base / 2 * SS, py - length * 0.18 * SS), (cx + w_base * 0.32 * SS, bot),
               (cx - w_base * 0.32 * SS, bot), (cx - w_base / 2 * SS, py - length * 0.18 * SS)]
    else:  # baton / needle
        pts = [(cx - w_tip / 2 * SS, top), (cx + w_tip / 2 * SS, top), (cx + w_base / 2 * SS, bot), (cx - w_base / 2 * SS, bot)]
    halo_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dh = ImageDraw.Draw(halo_img)
    dh.polygon(pts, fill=(0, 0, 0, 255))
    if counter_r:
        dh.ellipse([cx - counter_r * SS, bot - counter_r * 2 * SS, cx + counter_r * SS, bot], fill=(0, 0, 0, 255))
    halo_img = halo_img.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(halo * SS / 2.2))
    halo_arr = np.asarray(halo_img).astype(np.float32)
    halo_arr[..., 3] *= 0.75
    halo_img = Image.fromarray(halo_arr.astype(np.uint8), "RGBA")
    d.polygon(pts, fill=color)
    if shape == "dauphine":
        # subtle facet: darker right half for a polished-metal look
        facet = [(cx, top), (cx + w_base / 2 * SS, py - length * 0.18 * SS), (cx + w_base * 0.32 * SS, bot), (cx, bot)]
        d.polygon(facet, fill=tuple(int(c * 0.82) for c in color[:3]) + (255,))
    if counter_r:
        d.ellipse([cx - counter_r * SS, bot - counter_r * 2 * SS, cx + counter_r * SS, bot], fill=color)
    out = Image.alpha_composite(halo_img, img)
    fw, fh = round(W / SS), round(H / SS)
    out = out.resize((fw, fh), Image.LANCZOS)
    out.save(f"{OUT}/{name}.png", optimize=True)
    return fw, fh, (halo + length) / (length + tail + 2 * halo)


def render_cap():
    s = 24 * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2 * SS, 2 * SS, 22 * SS, 22 * SS], fill=(0, 0, 0, 120))
    d.ellipse([5 * SS, 5 * SS, 19 * SS, 19 * SS], fill=(255, 255, 255, 255))
    d.ellipse([8 * SS, 8 * SS, 16 * SS, 16 * SS], fill=(255, 122, 40, 255))
    d.ellipse([10.5 * SS, 10.5 * SS, 13.5 * SS, 13.5 * SS], fill=(30, 30, 30, 255))
    img.resize((24, 24), Image.LANCZOS).save(f"{OUT}/cap.png", optimize=True)


if __name__ == "__main__":
    render_earth()
    render_masks()
    render_background()
    render_dial()
