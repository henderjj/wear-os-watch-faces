"""Shared constants for the Earth watch face."""
import numpy as np

CANVAS = 450            # WFF canvas size
CENTER = CANVAS / 2
EARTH_R = 196           # Earth disk radius in canvas px
EARTH_X = int(CENTER - EARTH_R)
LAT0 = 0.0              # view centred on the equator
LON0 = 0.0 
MASK_STEP_DEG = 5.0     # sun-elevation step between precomputed terminator masks
MASK_COUNT = int(180 / MASK_STEP_DEG) + 1
MASK_RES = EARTH_R      # masks are drawn at half resolution and scaled 2x (they are soft)

LO, HI = -0.10, 0.26    # cos(solar zenith) range of the day/night blend (twilight to ~15 deg sun)


def mask_profile(illum):
    t = np.clip((illum - LO) / (HI - LO), 0, 1)
    return t * t * (3 - 2 * t)
