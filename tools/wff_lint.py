"""Checks for Watch Face Format files that the XSD schema can't express.

Usage:
    python tools/wff_lint.py <watchface.xml> <res folder>

Reports:
  - a configuration (List/Boolean/Color) used inside another configuration's option
    (WFF before v5: "configuration options cannot be nested"; on a watch the
    Customise screen closes when that setting is changed)
  - scene configurations that aren't declared in <UserConfigurations>, or are declared as another type
  - [CONFIGURATION.x.n] colour references to anything other than a ColorConfiguration
  - resource="..." with no matching drawable, and drawables nothing uses
  - displayName strings missing from res/values/strings.xml
Exits with status 1 if anything is reported.
"""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

CFG = {"ListConfiguration", "BooleanConfiguration", "ColorConfiguration"}


def lint(xml, res):
    root = ET.parse(xml).getroot()
    uc = root.find("UserConfigurations")
    declared = {c.get("id"): c.tag for c in (uc if uc is not None else [])}
    problems = []

    def walk(el, inside_option):
        for k in el:
            if k.tag in CFG:
                if inside_option:
                    problems.append(f"nested configuration '{k.get('id')}' inside option '{inside_option}'")
                if declared.get(k.get("id")) != k.tag:
                    problems.append(f"scene uses {k.tag} '{k.get('id')}' that isn't declared as one")
                for opt in k:
                    walk(opt, f"{k.get('id')}/{opt.get('id')}")
            else:
                walk(k, inside_option)

    walk(root.find("Scene"), None)
    text = open(xml, encoding="utf-8").read()
    for ref in sorted(set(re.findall(r"\[CONFIGURATION\.([A-Za-z0-9_]+)\.\d+\]", text))):
        if declared.get(ref) != "ColorConfiguration":
            problems.append(f"[CONFIGURATION.{ref}.n] used but '{ref}' isn't a ColorConfiguration")

    drawables = {os.path.splitext(os.path.basename(f))[0]
                 for f in glob.glob(os.path.join(res, "drawable*", "*")) if os.path.isfile(f)}
    refs = set(re.findall(r'resource="([A-Za-z0-9_]+)"', text))
    info = os.path.join(res, "xml", "watch_face_info.xml")
    meta_refs = set(re.findall(r'@drawable/([A-Za-z0-9_]+)', open(info, encoding="utf-8").read())) if os.path.isfile(info) else set()
    problems += [f"missing drawable '{r}'" for r in sorted((refs | meta_refs) - drawables)]
    problems += [f"unused drawable '{d}'" for d in sorted(drawables - refs - meta_refs)]

    strings_file = os.path.join(res, "values", "strings.xml")
    strings = set(re.findall(r'<string name="([A-Za-z0-9_]+)"', open(strings_file, encoding="utf-8").read())) \
        if os.path.isfile(strings_file) else set()
    names = set(re.findall(r'(?:displayName|screenReaderText)="([A-Za-z0-9_]+)"', text))
    problems += [f"missing string '{s}'" for s in sorted(names - strings)]
    return problems


if __name__ == "__main__":
    found = lint(sys.argv[1], sys.argv[2])
    print("\n".join(found) or "lint: no problems")
    sys.exit(1 if found else 0)
