"""Shared constants for the Earth watch face."""
import numpy as np

CANVAS = 450            # WFF canvas size
CENTER = CANVAS / 2
EARTH_R = 196           # Earth disk radius in canvas px
EARTH_X = int(CENTER - EARTH_R)
# Views of the globe, offered by the "View" setting. Each one needs its own pair of
# Earth images (about 400 KB of PNG); the day/night masks are shared by every view.
# Every view is centred on the Tropic of Cancer, the equator or the Tropic of Capricorn;
# the longitude picks the region. Listed in the order shown in Customise.
# id: (name shown in Customise, latitude of the centre, longitude of the centre)
# "equator" and "cancer" keep their 1.3 ids so a saved choice survives the upgrade.
CANCER, EQUATOR, CAPRICORN = 23.44, 0.0, -23.44
VIEWS = {
    "cancer_120w": ("US West Coast", CANCER, -120.0),
    "cancer_97w": ("Central US & C. America", CANCER, -97.0),
    "cancer_77w": ("US East Coast", CANCER, -77.0),
    "cancer": ("Europe & N. Africa", CANCER, 0.0),
    "cancer_40e": ("E. Europe & Middle East", CANCER, 40.0),
    "cancer_78e": ("Russia & Central Asia", CANCER, 78.0),
    "cancer_115e": ("East Asia", CANCER, 115.0),
    "equator_60w": ("Amazon", EQUATOR, -60.0),
    "equator": ("West & Central Africa", EQUATOR, 0.0),
    "equator_37e": ("East Africa", EQUATOR, 37.0),
    "equator_78e": ("Southern Asia", EQUATOR, 78.0),
    "equator_110e": ("South-East Asia", EQUATOR, 110.0),
    "capricorn_60w": ("South America", CAPRICORN, -60.0),
    "capricorn_20e": ("Southern Africa", CAPRICORN, 20.0),
    "capricorn_152e": ("Australia & NZ", CAPRICORN, 152.0),
}
DEFAULT_VIEW = "equator"
MASK_STEP_DEG = 5.0     # sun-elevation step between precomputed terminator masks
MASK_COUNT = int(180 / MASK_STEP_DEG) + 1
MASK_RES = EARTH_R      # masks are drawn at half resolution and scaled 2x (they are soft)

LO, HI = -0.10, 0.26    # cos(solar zenith) range of the day/night blend (twilight to ~15 deg sun)


def mask_profile(illum):
    t = np.clip((illum - LO) / (HI - LO), 0, 1)
    return t * t * (3 - 2 * t)
