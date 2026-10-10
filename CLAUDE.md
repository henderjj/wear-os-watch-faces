# CLAUDE.md

Guidance for Claude when working in this repository of Wear OS watch faces. The owner tests on a **Galaxy Watch 6** and installs from **Android Studio on Windows**.

## Layout
- `faces/<slug>/` holds one self-contained Android Studio project per face. The README describes the face; a GUIDE.md, if present, explains how it works; `tools/` holds the scripts that generate it.
- `tools/` holds shared scripts: `validate_wff.py` (official schema), `wff_lint.py` (semantic checks), `wff_sim.py` (renders a face from its XML), `new_face.py` (starts a face from `templates/analog`).
- `docs/` holds the general guides. Read `docs/agentic-wear-os-watch-faces.md` before starting a new face.

## Rules
- **Watch Face Format v1** unless the owner asks otherwise. It runs on Wear OS 4+, so it's safe on the Galaxy Watch 6. Check the schema in `external/watchface/third_party/wff/specification/documents/<version>/` (fetched by `validate_wff.py`) rather than relying on memory.
- **Never nest a configuration inside another configuration's option** (List, Boolean or Color inside a `ListOption`/`BooleanOption`). Before v5 this makes the watch's Customise screen close. Combine settings with top-level configurations and `tintColor="[CONFIGURATION.<color>.0]"` instead.
- **Tinted artwork must be pure white.** Put shading and lume in a separate untinted layer above it, because how tinting blends isn't documented.
- **Prefer numeric data sources** (`[DAY_OF_WEEK]`, `[DAY]`, `[MONTH]`) over locale-dependent strings. Use ranges or integer `%` rather than `==` on floats.
- **Generate, don't hand-edit.** Change a face's scripts and run its `tools/build.py`, never the generated XML, strings or PNGs.
- **Before handing over a build:**
  1. `python tools/validate_wff.py <xml> --version 1`
  2. `python tools/wff_lint.py <xml> <res>`
  3. render previews with `tools/wff_sim.py` and look at them
  4. increase `versionCode` and `versionName`
  5. update the face's README and GUIDE, including the version history
- Extend `wff_sim.py` when a face uses an element it doesn't support yet. It raises an error on unknown elements by design.
- Sandboxes usually can't reach Gradle or Maven, so the owner builds and installs. Ask for `logcat` output (see `docs/install-on-galaxy-watch.md`) when something fails on the watch.

## Adding a face
1. Run `python tools/new_face.py <slug> "<Name>"`.
2. Build it out with its own `tools/` scripts.
3. Add a row to the faces table in `README.md`, with its preview image.
