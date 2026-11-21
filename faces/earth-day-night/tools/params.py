"""Shared constants for the Earth watch face."""
import numpy as np

CANVAS = 450            # WFF canvas size
CENTER = CANVAS / 2
EARTH_R = 196           # Earth disk radius in canvas px
EARTH_X = int(CENTER - EARTH_R)
# Views of the globe, offered by the "View" setting. Each one needs its own pair of
# Earth images (about 385 KB of PNG); the day/night masks are shared by every view.
# id: (name shown in Customise, latitude of the centre, longitude of the centre)
VIEWS = {
    "equator": ("Equator", 0.0, 0.0),
    "cancer": ("Tropic of Cancer", 23.44, 0.0),
}
DEFAULT_VIEW = "equator"
MASK_STEP_DEG = 5.0     # sun-elevation step between precomputed terminator masks
MASK_COUNT = int(180 / MASK_STEP_DEG) + 1
MASK_RES = EARTH_R      # masks are drawn at half resolution and scaled 2x (they are soft)

LO, HI = -0.10, 0.26    # cos(solar zenith) range of the day/night blend (twilight to ~15 deg sun)


def mask_profile(illum):
    t = np.clip((illum - LO) / (HI - LO), 0, 1)
    return t * t * (3 - 2 * t)
