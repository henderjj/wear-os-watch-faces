"""Check that a face's committed generated files match what its scripts produce.

Run this after a face's tools/build.py has regenerated its files in place:
    python tools/check_generated.py faces/<face>

Compares every changed or new file under faces/<face>/watchface/ with the committed
version (git HEAD). PNGs are compared by pixels, allowing tiny differences
(default 2/255 per channel) so that different zlib or numpy builds don't cause
false failures. All other files must match exactly.
Exits with status 1 and lists the files if anything differs, which usually means
someone edited a generated file by hand, or changed a script without rebuilding.
"""
import argparse
import io
import os
import subprocess
import sys

import numpy as np
from PIL import Image


def git(*args, binary=False):
    r = subprocess.run(["git", *args], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode()


def pixels(data):
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"), dtype=np.int16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("face", help="path to the face folder, e.g. faces/earth-day-night")
    ap.add_argument("--tolerance", type=int, default=2, help="max per-channel PNG difference (0-255)")
    a = ap.parse_args()
    target = os.path.join(a.face, "watchface")

    changed = [l[3:] for l in git("status", "--porcelain", "--untracked-files=all", "--", target).splitlines()]
    problems = []
    for path in changed:
        status = git("status", "--porcelain", "--", path)[:2]
        if "?" in status:
            problems.append(f"{path}: generated but not committed")
            continue
        if "D" in status:
            problems.append(f"{path}: committed but no longer generated")
            continue
        new = open(path, "rb").read()
        old = git("show", f"HEAD:{path}", binary=True)
        if path.endswith(".png"):
            p_new, p_old = pixels(new), pixels(old)
            if p_new.shape != p_old.shape:
                problems.append(f"{path}: size changed {p_old.shape[1]}x{p_old.shape[0]} -> {p_new.shape[1]}x{p_new.shape[0]}")
                continue
            diff = int(np.abs(p_new - p_old).max())
            if diff > a.tolerance:
                problems.append(f"{path}: pixels differ (max difference {diff})")
        elif new.replace(b"\r\n", b"\n") != old.replace(b"\r\n", b"\n"):
            problems.append(f"{path}: content differs")

    if problems:
        print("Generated files don't match the committed ones:")
        print("\n".join("  " + p for p in problems))
        print("Rebuild with the face's tools/build.py and commit the results (don't edit generated files by hand).")
        sys.exit(1)
    extra = f" ({len(changed)} images re-encoded with identical pixels)" if changed else ""
    print(f"{a.face}: committed files match a fresh build{extra}")


if __name__ == "__main__":
    main()
