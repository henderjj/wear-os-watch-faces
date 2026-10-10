"""Validate watch face XML against Google's official Watch Face Format schema.

Usage (from anywhere in the repository):
    python tools/validate_wff.py faces/<face>/watchface/src/main/res/raw/watchface.xml [--version 1]

The first run clones https://github.com/google/watchface into external/ (ignored by git)
and compiles its validator. Needs git and a JDK; on Windows the JDK bundled with
Android Studio is found automatically.
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTERNAL = os.path.join(REPO, "external")
WF = os.path.join(EXTERNAL, "watchface")
SPEC = os.path.join(WF, "third_party", "wff", "specification")
CLASSES = os.path.join(EXTERNAL, "wff-validator-classes")


def find_jdk_tool(name):
    exe = name + (".exe" if os.name == "nt" else "")
    candidates = [shutil.which(name)]
    if os.environ.get("JAVA_HOME"):
        candidates.append(os.path.join(os.environ["JAVA_HOME"], "bin", exe))
    candidates += [  # JDK bundled with Android Studio
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Android", "Android Studio", "jbr", "bin", exe),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Android Studio", "jbr", "bin", exe),
        f"/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/{name}",
        os.path.expanduser(f"~/android-studio/jbr/bin/{name}"),
        f"/opt/android-studio/jbr/bin/{name}",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    sys.exit(f"Couldn't find '{name}'. Install Android Studio or a JDK, or set JAVA_HOME.")


def ensure_validator():
    if not os.path.isdir(SPEC):
        os.makedirs(EXTERNAL, exist_ok=True)
        print("Cloning google/watchface (first run only)...")
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/google/watchface.git", WF], check=True)
    marker = os.path.join(CLASSES, "docs.zip")
    if os.path.isfile(marker):
        return
    print("Compiling the validator (first run only)...")
    os.makedirs(CLASSES, exist_ok=True)
    libs = os.path.join(SPEC, "validator", "libs", "*")
    sources = glob.glob(os.path.join(SPEC, "validator", "src", "**", "*.java"), recursive=True)
    subprocess.run([find_jdk_tool("javac"), "-nowarn", "-d", CLASSES, "-cp", libs, *sources], check=True)
    docs = os.path.join(SPEC, "documents")
    with zipfile.ZipFile(marker, "w", zipfile.ZIP_DEFLATED) as z:  # the validator loads the XSDs from /docs.zip
        for root, _, files in os.walk(docs):
            for f in files:
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, docs))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # Windows consoles may not be UTF-8
    ap = argparse.ArgumentParser()
    ap.add_argument("xml", nargs="+")
    ap.add_argument("--version", default="1", help="Watch Face Format version declared in the manifest")
    a = ap.parse_args()
    ensure_validator()
    cp = os.pathsep.join([CLASSES, os.path.join(SPEC, "validator", "libs", "*")])
    ok = True
    for x in a.xml:
        r = subprocess.run([find_jdk_tool("java"), "-cp", cp, "com.samsung.watchface.DWFValidationApplication",
                            a.version, os.path.abspath(x)], capture_output=True, text=True, errors="replace")
        out = "\n".join(l for l in (r.stdout + r.stderr).splitlines()
                        if "JAVA_TOOL_OPTIONS" not in l and "Validation Application Version" not in l)
        print(out.replace("\u2705", "").replace("\u274c", "").strip())
        ok = ok and "PASSED" in out and "FAILED" not in out
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
