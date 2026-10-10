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
from solar import truth_mask
from params import EARTH_R

XML, D, OUTDIR = sys.argv[1], sys.argv[2], sys.argv[3]
# Limits for the day/night mask versus a precise solar calculation (fraction of full opacity).
# v1.2 measures at most 0.011 mean and 0.146 at the 99th percentile; these leave headroom.
MAX_MEAN, MAX_P99 = 0.02, 0.25
failures = 0
cases = [  # local time, utc offset
    ("2026-10-08T08:00:00", 1), ("2026-10-08T13:00:00", 1), ("2026-10-08T18:30:00", 1),
    ("2026-10-08T23:02:00", 1), ("2026-06-21T12:00:00", 1), ("2026-06-21T23:59:00", 1),
    ("2026-12-21T09:00:00", 0), ("2026-12-21T16:00:00", 0), ("2026-03-20T06:10:00", 0),
]
for iso, off in cases:
    img, s = wff_sim.run(XML, D, iso, off)
    img.save(f"{OUTDIR}/{iso[:16].replace(':', '-')}.png")
    utc = dt.datetime.fromisoformat(iso).replace(tzinfo=dt.timezone.utc) - dt.timedelta(hours=off)
    truth, inside = truth_mask(utc, 2 * EARTH_R)
    got = wff_sim.captured["terminator"][..., 3]
    err = np.abs(truth - got)[inside]
    mean, p99 = err.mean(), np.percentile(err, 99)
    ok = mean <= MAX_MEAN and p99 <= MAX_P99
    failures += not ok
    print(f"{iso} mean_err={mean:.3f} p99={p99:.3f}{'' if ok else '  <-- TOO FAR FROM TRUE SUN POSITION'}")
sys.exit(1 if failures else 0)
