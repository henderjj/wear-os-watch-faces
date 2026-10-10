"""Independent, precise Sun position (NOAA-style) used to check the watch face's day/night line."""
import math

import numpy as np

from params import LAT0, LON0, mask_profile


def precise_sun(t):
    """NOAA solar position: returns (declination rad, subsolar longitude deg)."""
    jd = t.timestamp() / 86400.0 + 2440587.5
    n = jd - 2451545.0
    L = math.radians((280.460 + 0.9856474 * n) % 360)
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = L + math.radians(1.915) * math.sin(g) + math.radians(0.020) * math.sin(2 * g)
    eps = math.radians(23.439 - 0.0000004 * n)
    dec = math.asin(math.sin(eps) * math.sin(lam))
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    gmst = (280.46061837 + 360.98564736629 * n) % 360
    sublon = (math.degrees(ra) - gmst + 540) % 360 - 180
    return dec, sublon


def truth_mask(t, size):
    dec, sublon = precise_sun(t)
    p0, l0 = math.radians(LAT0), math.radians(LON0)
    ls = math.radians(sublon)
    s = np.array([math.cos(dec) * math.cos(ls), math.cos(dec) * math.sin(ls), math.sin(dec)])
    e = np.array([-math.sin(l0), math.cos(l0), 0.0])
    n = np.array([-math.sin(p0) * math.cos(l0), -math.sin(p0) * math.sin(l0), math.cos(p0)])
    c = np.array([math.cos(p0) * math.cos(l0), math.cos(p0) * math.sin(l0), math.sin(p0)])
    sx, sy, sz = s @ e, s @ n, s @ c
    cc = (size - 1) / 2
    yy, xx = np.mgrid[0:size, 0:size]
    u = (xx - cc) / (size / 2); v = -(yy - cc) / (size / 2)
    z = np.sqrt(np.clip(1 - u * u - v * v, 0, 1))
    return mask_profile(u * sx + v * sy + z * sz), (u * u + v * v) <= 1
