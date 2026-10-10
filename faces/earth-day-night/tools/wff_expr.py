"""Builds the WFF arithmetic expressions for the sun position and an evaluator
that runs the *same strings* in Python, so the maths can be checked offline."""
import math
import re

from params import LAT0, LON0, MASK_STEP_DEG

SP = f"{math.sin(math.radians(LAT0)):.6f}"
CP = f"{math.cos(math.radians(LAT0)):.6f}"

# UTC hours of day (integer modulo is exact in WFF)
T = "(([UTC_TIMESTAMP] % 86400000) / 3600000.0)"
# Fractional-year angle measured from the March equinox (~day 81)
B = "rad(0.9863014 * ([DAY_OF_YEAR] - 81))"
# Equation of time in minutes
EOT = f"(9.87 * sin(2 * {B}) - 7.53 * cos({B}) - 1.5 * sin({B}))"
# Local hour angle of the sun at the view-centre longitude (radians)
H = f"rad(15 * ({T} - 12) + {EOT} / 4 + ({LON0}))"
# Solar declination (radians)
DEC = f"rad(23.44 * sin({B}))"

SX = f"(0 - cos({DEC}) * sin({H}))"                              # east
SY = f"(sin({DEC}) * {CP} - cos({DEC}) * {SP} * cos({H}))"        # north
SZ = f"(sin({DEC}) * {SP} + cos({DEC}) * {CP} * cos({H}))"        # towards viewer

# Angle between the sun and the viewing direction, in mask steps
IDX = f"(deg(acos(clamp({SZ}, -1, 1))) / {MASK_STEP_DEG:g})"
# Screen rotation of the sun direction, clockwise from 3 o'clock (y points down on screen)
ROT = (f"(deg(acos(clamp({SX} / (sqrt({SX} * {SX} + {SY} * {SY}) + 0.000001), -1, 1)))"
       f" * ((0 - {SY}) / (abs({SY}) + 0.000000001)))")


def mask_alpha(j):
    d = f"({IDX} - {j})"
    return f"255 * clamp(1 - {d}, 0, 1) * clamp(({d} + 1) * 1000, 0, 1)"


# ---------------------------------------------------------------- evaluator
_NS = {
    "sin": math.sin, "cos": math.cos, "acos": math.acos, "sqrt": math.sqrt, "abs": abs,
    "rad": math.radians, "deg": math.degrees, "floor": math.floor,
    "fract": lambda x: x - math.floor(x),
    "clamp": lambda x, a, b: min(max(float(x), float(a)), float(b)),
}


def evaluate(expr, utc_ms, day_of_year):
    py = expr.replace("[UTC_TIMESTAMP]", str(int(utc_ms))).replace("[DAY_OF_YEAR]", str(int(day_of_year)))
    assert "[" not in py, py
    assert not re.search(r"[?:]", py)
    return eval(py, {"__builtins__": {}}, _NS)
