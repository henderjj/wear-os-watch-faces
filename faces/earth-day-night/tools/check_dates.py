"""Check the date Conditions for every day of 2026-2028 in both layouts."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "generated")
SHARED = os.path.normpath(os.path.join(HERE, "..", "..", "..", "tools"))  # repo-level shared tools

import datetime as dt
import sys
import numpy as np
sys.path.insert(0, HERE)
sys.path.insert(0, SHARED)
import wff_sim

XML, D = sys.argv[1], sys.argv[2]
DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
names = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
months = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
bad = 0
d = dt.date(2026, 1, 1)
while d < dt.date(2029, 1, 1):
    for style, pre in (("split", "day"), ("single", "dayr")):
        s = wff_sim.Sim(XML, D, dt.datetime(d.year, d.month, d.day, 12), 0, {"dateStyle": style}, False)
        el = next(e for e in s.root.find("Scene") if e.tag == "ListConfiguration" and e.get("id") == "dateStyle")
        s.element(el, np.zeros((450, 450, 4), np.float32))
        got = [r for r in s.drawn if not r.startswith("frame")]
        dow = names.index(d.strftime("%a").upper())
        want = [f"{pre}_{dow + 1}", f"dig_{d.day // 10}", f"dig_{d.day % 10}", f"mon_{d.month}"]
        if got != want:
            bad += 1
            print("MISMATCH", d, style, got, want)
    d += dt.timedelta(days=1)
print("checked 3 years x 2 layouts, mismatches:", bad)
sys.exit(1 if bad else 0)
