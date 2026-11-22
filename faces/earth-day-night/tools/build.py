"""Regenerate every image and the watch face XML, then run the checks.

Usage (from faces/earth-day-night):
    python tools/build.py

The default inputs are in inputs/ (NASA textures and the Barlow Condensed font).
Needs Python 3.9+ with numpy and Pillow (pip install numpy pillow).
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
RES = os.path.join(PROJECT, "watchface", "src", "main", "res")
DRAWABLE = os.path.join(RES, "drawable-nodpi")
GEN = os.path.join(HERE, "generated")
SHARED = os.path.normpath(os.path.join(PROJECT, "..", "..", "tools"))  # repo-level shared tools
INPUTS = os.path.join(PROJECT, "inputs")
ASSETS = os.path.join(GEN, "drawable")


def run(script, *args, where=HERE):
    print(f"> {script} {' '.join(args)}")
    subprocess.run([sys.executable, os.path.join(where, script), *args], check=True, cwd=HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=os.path.join(INPUTS, "earth-blue-marble.jpg"),
                    help="equirectangular daytime Earth texture (NASA Blue Marble)")
    ap.add_argument("--night", default=os.path.join(INPUTS, "earth-night.jpg"),
                    help="equirectangular night-lights texture (NASA Earth at Night)")
    ap.add_argument("--font", default=os.path.join(INPUTS, "BarlowCondensed-SemiBold.ttf"),
                    help="TTF used for the date lettering")
    ap.add_argument("--skip-checks", action="store_true")
    a = ap.parse_args()

    shutil.rmtree(GEN, ignore_errors=True)
    os.makedirs(ASSETS)
    run("render_assets.py", os.path.abspath(a.day), os.path.abspath(a.night), ASSETS)
    run("hands.py", ASSETS)
    run("date_assets.py", os.path.abspath(a.font), ASSETS)

    for f in glob.glob(os.path.join(DRAWABLE, "*.png")):
        os.remove(f)
    for f in glob.glob(os.path.join(ASSETS, "*.png")):
        shutil.copy(f, DRAWABLE)

    xml = os.path.join(RES, "raw", "watchface.xml")
    run("make_xml.py", xml, os.path.join(RES, "values", "strings.xml"))

    # Preview shown in the watch-face picker: default settings at 10:08:32
    sys.path.insert(0, SHARED)
    import wff_sim
    from PIL import Image, ImageDraw
    img, _ = wff_sim.run(xml, DRAWABLE, "2026-10-08T10:08:32", 1)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, img.width - 1, img.height - 1], fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    out.save(os.path.join(DRAWABLE, "preview.png"), optimize=True)

    run("wff_lint.py", xml, RES, where=SHARED)
    if not a.skip_checks:
        run("check_dates.py", xml, DRAWABLE)
        os.makedirs(os.path.join(GEN, "previews"), exist_ok=True)
        run("check_faces.py", xml, DRAWABLE, os.path.join(GEN, "previews"))
    print("Done. Validate with:  python ../../tools/validate_wff.py watchface/src/main/res/raw/watchface.xml --version 1")


if __name__ == "__main__":
    main()
