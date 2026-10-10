# Building Wear OS watch faces with an AI agent

A practical guide to developing Wear OS watch faces with an agent such as Claude, based on building the [*Earth Day & Night*](../faces/earth-day-night/) face for a Galaxy Watch 6. It covers how to split the work between you and the agent, how the agent can check its own work when it can't reach a watch, and the format details that cause trouble.

---

## 1. The division of labour

The agent can write the watch face, but in a typical cloud setup it can't touch your watch. It often can't build an Android app either, because sandboxes usually block Google's Maven and Gradle servers. Plan for this split:

| The agent does | You do |
|---|---|
| Research the format and read the official schema and samples | Describe what you want, and judge how it looks |
| Generate all artwork in code (Python, Pillow, NumPy) | Install Android Studio once |
| Generate the watch face XML from scripts | Pair the watch over Wi-Fi debugging |
| Validate against the official schema | Press **Run ▶** to build and install |
| Run its own checks: lint, a simulated render, maths checks | Try it on your wrist, especially the customise screen |
| Package an Android Studio project with a README | Paste back errors from `logcat` |

Your part is small but essential: the watch is the only real test. A face can pass every check and still behave differently on the watch, as section 6 shows.

---

## 2. Choose the route

Since **January 2026, every watch face installed on a Wear OS device must use the Watch Face Format (WFF)**. WFF is a declarative XML format: you supply images and an XML scene, and the system's renderer draws it. Your package contains no code (`android:hasCode="false"`). There are three ways to make one:

| Route | Best for | How an agent helps |
|---|---|---|
| **Watch Face Studio** (Samsung, no code) | Designers who want to drag and drop | Makes artwork, suggests layouts, writes tag expressions |
| **Watch Face Designer** (Figma plugin) | Figma users | Makes artwork and copy |
| **Hand-written or generated WFF XML** in Android Studio | Anything driven by maths or data, many variants, exact control | Writes everything: assets, XML, checks and project |

The third route suits an agent best. The XML is plain text and the schema is public, so the agent can generate both the XML and the artwork from parameters and check them mechanically. For example, the Earth face has 37 day/night mask images, four hand styles, and date windows built from Conditions. Doing that by hand in a visual tool would be slow.

---

## 3. Platform facts the agent must work within

- **No custom code runs.** Anything dynamic is either an *expression* or a choice between pre-made images:
  - Expressions use data sources such as `[UTC_TIMESTAMP]`, `[DAY_OF_YEAR]` and `[HOUR_0_23_MINUTE]`, with maths like `sin`, `acos`, `clamp` and `?:`. They drive `Transform`s (alpha, angle, position) and `Condition`s.
  - Complex effects come from **pre-rendering images and selecting or blending them with expressions**.
- **Format versions.** Pick the lowest version that has what you need. **Version 1 runs on Wear OS 4 and later**, which includes the Galaxy Watch 6 even before its software updates. Later versions add features such as Flavors (v2) and nested settings (v5). Check the *Available features* page before using anything new.
- **The trig functions work in radians.** `deg()` and `rad()` convert.
- **Some data sources are strings.** In v1, `TIMEZONE_OFFSET` and the `*_S`/`*_F` day and month names are strings, and the names depend on the watch's locale. Prefer numeric sources such as `[DAY_OF_WEEK]` (1 = Sunday), `[DAY]` and `[MONTH]` where you can.
- **Integer and float comparisons have odd rules.** The documentation says that comparing an integer with its floating-point equivalent using `<` is `false`, and using `<=` is `true`. Avoid comparing the result of division or `floor()` with `==`. Use ranges (`[DAY] < 10`) or integer modulo (`[DAY] % 10 == 3`).
- **Masks (`renderMode="MASK"`)** apply only within their parent `Group`. Order doesn't matter there: all `SOURCE` children are drawn, then clipped by the combined `MASK` children. Soft-edged masks work, which allows smooth transitions.
- **Customisation** is declared in `<UserConfigurations>` (`ListConfiguration`, `BooleanConfiguration`, `ColorConfiguration`) and used in the scene.
  - **Settings can't be nested before v5.** Never put one setting's `ListConfiguration` inside another's `ListOption`. The schema validator accepts it, but on a real watch the customise screen closes when you change that setting.
  - Reading a **colour** setting inside a list option is fine. Use `tintColor="[CONFIGURATION.myColour.0]"`, as Google's own v1 samples do.
  - An option you don't include in the scene simply draws nothing. That's a convenient way to make an "Off" choice.
  - Set `<Editable value="true" />` in `watch_face_info.xml`, or the Customise button won't appear.
- **How tinting blends isn't documented.** If you tint an image, draw the part to be tinted in **pure white**, and put shading on a separate untinted layer above it. Then the result is the same whether the watch multiplies or replaces the colour.
- **An `AnalogClock` can hold at most two of each hand type.** For more layers per hand, stack several `AnalogClock`s.
- **Always-on display:** use `<Variant mode="AMBIENT" target="alpha" .../>` to dim or hide parts. Keep the always-on view dark and sparse.
- **`Condition`** picks the **first** `Compare` that is true, otherwise `Default`. Every `ListOption` and `Compare` needs exactly one child, so wrap several elements in a `Group`.

---

## 4. The development loop

```
 brief ─► research spec + samples ─► generate assets (code) ─► generate XML (code)
   ▲                                                                │
   │                                                                ▼
 feedback ◄─ you test on the watch ◄─ package project ◄─ validate ─► lint ─► simulate
 (logcat, photos,
  "it drops out of…")
```

### 4.1 Give the agent the primary sources
Point it at, or let it clone:
- **[google/watchface](https://github.com/google/watchface).** The XSD schemas for every WFF version, a Java validator, a memory-footprint checker, and an optimiser.
- **[android/wear-os-samples → WatchFaceFormat](https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat).** Working Gradle projects to copy the build setup from (SimpleAnalog, Flavors, Weather and others).
- **The WFF reference on developer.android.com.** The XML reference, data sources, expressions and settings.

Ask the agent to quote the schema or docs when a rule matters, rather than relying on memory.

### 4.2 Generate, don't hand-write
Keep one parameters file (canvas size, positions, lengths, colours) and have scripts generate:
- every image (render at 2–4× size and scale down, for clean edges)
- the XML, including long repetitive blocks such as one image per mask, per weekday or per colour
- `strings.xml` for the option names in the customise screen

When you want a change ("move the date", "add a gold option"), the agent edits a parameter and rebuilds. It doesn't need to edit hundreds of XML lines by hand.

### 4.3 Validate against the official schema
**In this repository**, run `python tools/validate_wff.py <watchface.xml> --version 1`. It fetches, compiles and runs Google's validator, and finds the Java bundled with Android Studio. By hand, the steps are:

```bash
git clone --depth 1 https://github.com/google/watchface
cd watchface/third_party/wff/specification
javac -d classes -cp "validator/libs/*" $(find validator/src -name "*.java")
(cd documents && zip -qr ../classes/docs.zip .)
java -cp "classes:validator/libs/*" com.samsung.watchface.DWFValidationApplication 1 /path/to/watchface.xml
```

The `1` is the format version. Check that the validator really catches errors: break an attribute on purpose and confirm it fails. Android Studio also checks WFF syntax as you edit.

### 4.4 Lint for what the schema can't express
A schema checks structure, not meaning. In this repository, `tools/wff_lint.py <watchface.xml> <res folder>` checks that:
- no setting is nested inside another setting's option
- every `[CONFIGURATION.x]` reference points to a declared setting of the right type
- every `resource=` has a matching drawable, and no drawable is unused
- every `displayName` has a string resource

Test the lint against a known-bad file to show it catches the problem.

### 4.5 Simulate before you install
Use, or have the agent extend, a **small renderer that reads the generated XML** (in this repository: `tools/wff_sim.py`) and draws it with given settings, times and dates. It needs to handle settings, Conditions, Transforms, Variants, masks and hands. The renderer is a few hundred lines of Python, and it lets the agent:
- show you previews of option combinations and times of day before you install anything
- check logic exhaustively. For example, render the date for every day over several years, and check every combination of settings.
- compare against an independent truth, such as a precise solar-position formula for a day/night line

The simulator is the agent's interpretation of the format, not the real renderer. Use it to catch logic and layout mistakes, and expect the watch to differ on things the documentation leaves vague.

### 4.6 Let CI repeat the checks
Run the same checks automatically on every pull request. In this repository, `.github/workflows/checks.yml` lints and validates every face and rebuilds the ones that have scripts. It then fails if the committed files don't match the rebuild (`tools/check_generated.py`).

That last check enforces "generate, don't hand-edit". It also catches a script change that was committed without rebuilding. Make the workflow a required status check on `main`, and nothing broken can be merged, whether you or the agent wrote it.

### 4.7 Package and hand over
In this repository, `python tools/new_face.py <slug> "<Name>"` starts a new face from `templates/analog`, a copy of Google's SimpleAnalog sample. Otherwise, copy the build setup from a Google sample: `hasCode="false"`, the `com.google.wear.watchface.format.version` property, `res/raw/watchface.xml`, `res/xml/watch_face_info.xml` with a `preview` drawable, and `drawable-nodpi/` for images. Increase `versionCode` with each release. Include a README with install steps written for your operating system.

### 4.8 Close the loop with real errors
When something goes wrong on the watch, a description helps ("it drops out of customise mode"), but the runtime's own log is better:

```
adb logcat --pid=$(adb shell pidof -s com.google.wear.watchface.runtime)
```

Paste that output to the agent. Expression errors and missing resources show up there.

---

## 5. Briefing the agent

A good first brief covers:

1. **The idea in one sentence.** For example, "The Earth as it looks right now, day and night, with an analogue dial over it."
2. **The device and its software.** For example, "Galaxy Watch 6, round, Wear OS 4 or later." This decides the format version.
3. **Must-haves and nice-to-haves:** the date, settings, always-on behaviour, battery concerns.
4. **Your setup:** "Windows PC, happy to install Android Studio." The agent can then write install steps for your system.
5. **How you want to review:** "Show me previews before I install," "show me a few options."

Then work in small rounds. Ask for one coherent change per release (for example "date + recentre + hand styles") and test each on the watch before stacking more changes.

---

## 6. Lessons from the Earth Day & Night project

| What happened | Takeaway |
|---|---|
| The sandbox couldn't reach Gradle or Maven, so the agent couldn't build the APK | Expect it. The agent delivers a validated project; you build in Android Studio. |
| Raw file downloads were blocked, but `git clone` from GitHub worked | Look for assets and schemas in public Git repos, such as the NASA imagery and fonts. |
| A day/night line needed trigonometry in XML | Work the maths out in Python first, then generate the XML expression strings from the same code so the two can't drift apart. |
| Day and month names are locale-dependent strings | Select images by `[DAY_OF_WEEK]` and `[MONTH]` numbers instead. The date is then always capitals in your chosen style. |
| Hand colours: tint or pre-coloured images? | Pre-coloured images looked right but led to nesting (below). White artwork with an untinted shading layer above gives the same look without nesting. |
| **Changing hand style closed the customise screen** | Hand colour was a setting nested inside each hand-style option. The docs say settings can't be nested, but the schema allows it. The fix was flattening the settings, plus a lint rule so it can't happen again. |
| The simulator agreed with a precise solar formula to within about 1% | Independent checks earn trust. Hold back deep visual tweaks until the logic is proven. |

---

## 7. References

- [Watch Face Format overview](https://developer.android.com/training/wearables/wff), Android Developers
- [Build watch faces](https://developer.android.com/training/wearables/watch-faces): the routes, including Watch Face Studio and Watch Face Designer
- [Define user configurations](https://developer.android.com/training/wearables/wff/personalization/user-configurations)
- [ListConfiguration reference](https://developer.android.com/reference/wear-os/wff/user-configuration/list-configuration)
- [WFF release notes](https://developer.android.com/training/wearables/wff/release-notes)
- [Data sources reference](https://developer.android.com/reference/wear-os/wff/common/attributes/source-type)
- [google/watchface](https://github.com/google/watchface): schemas, validator, memory-footprint tool
- [android/wear-os-samples – WatchFaceFormat](https://github.com/android/wear-os-samples/tree/main/WatchFaceFormat)
- [Watch Face Studio release notes](https://developer.samsung.com/watch-face-studio/release-note.html), Samsung
