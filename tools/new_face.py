"""Start a new watch face from templates/analog (Google's SimpleAnalog sample, WFF v1).

Usage (from the repository root):
    python tools/new_face.py moon-phase "Moon Phase"
    python tools/new_face.py moon-phase "Moon Phase" --package io.github.henderjj.watchface.moonphase

Creates faces/<slug>/ as a self-contained Android Studio project with its own
applicationId, so it installs alongside your other faces.
"""
import argparse
import os
import re
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_PREFIX = "io.github.henderjj.watchface"   # change to a domain you control if you publish


def edit(path, pairs):
    with open(path, encoding="utf-8") as f:
        s = f.read()
    for old, new in pairs:
        if old not in s:
            sys.exit(f"Template changed: '{old}' not found in {path}")
        s = s.replace(old, new)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="folder name, lower-case with hyphens, e.g. moon-phase")
    ap.add_argument("name", help="name shown on the watch, e.g. 'Moon Phase'")
    ap.add_argument("--package", help="applicationId (default: %s.<slug without hyphens>)" % PACKAGE_PREFIX)
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z][a-z0-9-]*", a.slug):
        sys.exit("slug must be lower-case letters, digits and hyphens, starting with a letter")
    pkg = a.package or f"{PACKAGE_PREFIX}.{a.slug.replace('-', '')}"
    if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", pkg):
        sys.exit(f"invalid package name: {pkg}")
    dest = os.path.join(REPO, "faces", a.slug)
    if os.path.exists(dest):
        sys.exit(f"{dest} already exists")

    shutil.copytree(os.path.join(REPO, "templates", "analog"), dest)
    project = "".join(w.capitalize() for w in a.slug.split("-"))
    edit(os.path.join(dest, "settings.gradle.kts"), [('rootProject.name = "SimpleAnalog"', f'rootProject.name = "{project}"')])
    edit(os.path.join(dest, "watchface", "build.gradle.kts"), [("com.example.simpleanalog", pkg)])
    xml_name = a.name.replace("&", "&amp;").replace("<", "&lt;")
    edit(os.path.join(dest, "watchface", "src", "main", "res", "values", "strings.xml"),
         [('<string name="watch_face_name">Simple Analog</string>', f'<string name="watch_face_name">{xml_name}</string>')])
    with open(os.path.join(dest, "README.md"), "w", encoding="utf-8") as f:
        f.write(f"""# {a.name}

*Work in progress, started from `templates/analog` (Google's SimpleAnalog sample).*

- **Package:** `{pkg}`
- **Watch Face Format:** version 1 (Wear OS 4 and later)

## Install
Open this folder (`faces/{a.slug}`) in Android Studio, then follow
[docs/install-on-galaxy-watch.md](../../docs/install-on-galaxy-watch.md).

## Checklist
- [ ] Describe the idea here
- [ ] Generate artwork and `watchface.xml` from scripts in `tools/`
- [ ] `python ../../tools/validate_wff.py watchface/src/main/res/raw/watchface.xml`
- [ ] `python ../../tools/wff_lint.py watchface/src/main/res/raw/watchface.xml watchface/src/main/res`
- [ ] Preview with `../../tools/wff_sim.py`
- [ ] Test on the watch, including Customise
- [ ] Add the face to the table in the repository README
""")
    print(f"Created faces/{a.slug} ({pkg}). Open it in Android Studio.")


if __name__ == "__main__":
    main()
