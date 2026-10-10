"""Generate res/raw/watchface.xml and res/values/strings.xml for the Earth watch face."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.join(HERE, "generated")

import json
import sys
from xml.sax.saxutils import escape, quoteattr

sys.path.insert(0, HERE)
import wff_expr as W  # noqa: E402
from hands import ACCENTS, METALS, STYLES  # noqa: E402
from params import CANVAS, EARTH_R, EARTH_X, LAT0, LON0, MASK_COUNT, MASK_STEP_DEG  # noqa: E402

XML_OUT, STRINGS_OUT = sys.argv[1], sys.argv[2]
hands = json.load(open(os.path.join(GEN, "hands.json")))
layout = json.load(open(os.path.join(GEN, "date_layout.json")))
D = 2 * EARTH_R
C = CANVAS / 2

DEFAULTS = {"handStyle": "dauphine", "handTint": "0", "accentTint": "0", "seconds": "TRUE", "dateStyle": "split"}
DATE_STYLES = {"split": "Day and date apart", "single": "One window at 6", "off": "Off"}

strings = {
    "watch_face_name": "Earth Day &amp; Night",
    "cfg_hand_style": "Hand style",
    "cfg_hand_color": "Hand colour",
    "cfg_accent": "Seconds hand colour",
    "cfg_seconds": "Seconds hand",
    "cfg_date": "Date",
}
for k, v in STYLES.items():
    strings[f"style_{k}"] = v
for k, (v, _) in METALS.items():
    strings[f"metal_{k}"] = v
for k, (v, _) in ACCENTS.items():
    strings[f"accent_{k}"] = v
for k, v in DATE_STYLES.items():
    strings[f"date_{k}"] = escape(v)


def ind(text, n):
    return "\n".join((" " * n + line) if line else line for line in text.splitlines())


def hand_el(tag, res, extra=""):
    w, h, py = hands[res]
    x = round(C - w / 2)
    y = round(C - h * py)
    return (f'<{tag} resource="{res}" x="{x}" y="{y}" width="{w}" height="{h}" '
            f'pivotX="{(C - x) / w:.5f}" pivotY="{(C - y) / h:.5f}">{extra}</{tag}>')


def image(res, r, extra=""):
    x, y, w, h = r
    return f'<PartImage x="{x}" y="{y}" width="{w}" height="{h}">{extra}\n  <Image resource="{res}" />\n</PartImage>'


def condition(cases, default):
    """cases: [(expression, element_xml)], default: element_xml"""
    exprs = "\n".join(f'    <Expression name="c{i}">{escape(e)}</Expression>' for i, (e, _) in enumerate(cases))
    comps = "\n".join(f'  <Compare expression="c{i}">\n{ind(el, 4)}\n  </Compare>' for i, (_, el) in enumerate(cases))
    return f"<Condition>\n  <Expressions>\n{exprs}\n  </Expressions>\n{comps}\n  <Default>\n{ind(default, 4)}\n  </Default>\n</Condition>"


def date_parts(L, day_res):
    weekday = condition([(f"[DAY_OF_WEEK] == {i}", image(f"{day_res}_{i}", L["day"])) for i in range(1, 7)],
                        image(f"{day_res}_7", L["day"]))
    tens = condition([(f"[DAY] < {10 * (i + 1)}", image(f"dig_{i}", L["tens"])) for i in range(3)],
                     image("dig_3", L["tens"]))
    units = condition([(f"[DAY] % 10 == {i}", image(f"dig_{i}", L["units"])) for i in range(9)],
                      image("dig_9", L["units"]))
    month = condition([(f"[MONTH] == {i}", image(f"mon_{i}", L["month"])) for i in range(1, 12)],
                      image("mon_12", L["month"]))
    return weekday, tens, units, month


def date_group(name, frames, parts):
    body = "\n".join(frames + list(parts))
    return (f'<Group name="{name}" x="0" y="0" width="{CANVAS}" height="{CANVAS}">\n'
            f'  <Variant mode="AMBIENT" target="alpha" value="190" />\n{ind(body, 2)}\n</Group>')


s = layout["split"]
split = date_group("date_split", [image("frame_day", s["day_frame"]), image("frame_date", s["date_frame"])],
                   date_parts({"day": s["day_text"], **s}, "day"))
g = layout["single"]
single = date_group("date_single", [image("frame_full", g["frame"])], date_parts(g, "dayr"))

# ---- hands. No configuration is nested inside another (WFF: "configuration options
# cannot be nested in their use"). Style is a ListConfiguration; colours are
# ColorConfigurations applied with tintColor to pure-white artwork.
HAND_TINT = "[CONFIGURATION.handTint.0]"
ACCENT_TINT = "[CONFIGURATION.accentTint.0]"


def clock(tag, res, tint=None, extra=""):
    t = f' tintColor="{tint}"' if tint else ""
    el = hand_el(tag, res, extra).replace(f'resource="{res}"', f'resource="{res}"{t}', 1)
    return f'<AnalogClock x="0" y="0" width="{CANVAS}" height="{CANVAS}">\n  {el}\n</AnalogClock>'


style_opts = []
for st in STYLES:
    layers = []
    for kind, tag in (("hour", "HourHand"), ("minute", "MinuteHand")):
        layers += [clock(tag, f"halo_{kind}_{st}"),
                   clock(tag, f"body_{kind}_{st}", HAND_TINT),
                   clock(tag, f"detail_{kind}_{st}")]
    style_opts.append(f'  <ListOption id="{st}">\n'
                      f'    <Group name="hands_{st}" x="0" y="0" width="{CANVAS}" height="{CANVAS}">\n'
                      f'{ind(chr(10).join(layers), 6)}\n'
                      f'    </Group>\n  </ListOption>')
hands_xml = '<ListConfiguration id="handStyle">\n' + "\n".join(style_opts) + "\n</ListConfiguration>"

CAP = [int(C) - 14, int(C) - 14, 28, 28]


def tinted_image(res, r, tint):
    return image(res, r).replace("<PartImage ", f'<PartImage tintColor="{tint}" ', 1)


caps_xml = "\n".join([image("cap_base", CAP), tinted_image("cap_top", CAP, HAND_TINT), image("cap_ring", CAP)])

sweep = chr(10) + '    <Sweep frequency="15" />' + chr(10) + "  "
seconds_body = "\n".join([
    clock("SecondHand", "halo_second", extra=sweep),
    clock("SecondHand", "body_second", ACCENT_TINT, extra=sweep),
    tinted_image("pin_ring", CAP, ACCENT_TINT),
    image("pin_dot", CAP),
])
seconds_xml = (f'<BooleanConfiguration id="seconds">\n  <BooleanOption id="TRUE">\n'
               f'    <Group name="seconds" x="0" y="0" width="{CANVAS}" height="{CANVAS}">\n'
               f'      <Variant mode="AMBIENT" target="alpha" value="0" />\n'
               f'{ind(seconds_body, 6)}\n'
               f'    </Group>\n  </BooleanOption>\n</BooleanConfiguration>')

date_xml = (f'<ListConfiguration id="dateStyle">\n'
            f'  <ListOption id="split">\n{ind(split, 4)}\n  </ListOption>\n'
            f'  <ListOption id="single">\n{ind(single, 4)}\n  </ListOption>\n'
            f'</ListConfiguration>')


def list_cfg(cid, label, opts, prefix):
    o = "\n".join(f'      <ListOption id="{k}" displayName="{prefix}_{k}" />' for k in opts)
    return (f'    <ListConfiguration id="{cid}" displayName="{label}" screenReaderText="{label}" '
            f'defaultValue="{DEFAULTS[cid]}">\n{o}\n    </ListConfiguration>')


def color_cfg(cid, label, opts, prefix):
    o = "\n".join(f'      <ColorOption id="{k}" displayName="{prefix}_{k}" colors="{c}" />' for k, (_, c) in opts.items())
    return (f'    <ColorConfiguration id="{cid}" displayName="{label}" screenReaderText="{label}" '
            f'defaultValue="{DEFAULTS[cid]}">\n{o}\n    </ColorConfiguration>')


user_cfg = "\n".join([
    list_cfg("handStyle", "cfg_hand_style", STYLES, "style"),
    color_cfg("handTint", "cfg_hand_color", METALS, "metal"),
    color_cfg("accentTint", "cfg_accent", ACCENTS, "accent"),
    '    <BooleanConfiguration id="seconds" displayName="cfg_seconds" screenReaderText="cfg_seconds" defaultValue="TRUE" />',
    list_cfg("dateStyle", "cfg_date", DATE_STYLES, "date"),
])

masks = "\n".join(
    f'          <PartImage x="0" y="0" width="{D}" height="{D}">\n'
    f'            <Transform target="alpha" value={quoteattr(W.mask_alpha(j))} />\n'
    f'            <Image resource="mask_{j:02d}" />\n'
    f'          </PartImage>'
    for j in range(MASK_COUNT))

xml = f'''<?xml version="1.0" encoding="utf-8"?>
<!--
  Earth Day & Night - an analogue watch face for Wear OS (Watch Face Format v1).

  The Earth is shown as seen from space above {LAT0:g} N, {LON0:g} E (the equator at
  Greenwich). Two pre-rendered views are stacked: the night side (city lights) underneath
  and the sunlit side on top. The sunlit layer is clipped by a soft mask that
  marks where the Sun is up. The mask's shape depends only on how far the Sun
  is from the viewing direction, so {MASK_COUNT} shapes are pre-rendered
  ({MASK_STEP_DEG:g} degrees apart); the two nearest are blended and the whole
  mask is rotated to point at the Sun.

  The Sun's position is computed from UTC time and the day of the year:
  declination (season) plus the equation of time.

  Customisation (long-press the face > Customise): hand style, hand colour,
  seconds hand colour, seconds hand on/off, and date layout.

  Imagery: NASA Blue Marble and NASA Earth at Night (public domain).
  Date lettering: Barlow Condensed (SIL Open Font License), pre-rendered.
-->
<WatchFace width="{CANVAS}" height="{CANVAS}">
  <Metadata key="CLOCK_TYPE" value="ANALOG" />
  <Metadata key="PREVIEW_TIME" value="10:08:32" />
  <UserConfigurations>
{user_cfg}
  </UserConfigurations>
  <Scene backgroundColor="#000000">

    <!-- Starfield -->
    <PartImage x="0" y="0" width="{CANVAS}" height="{CANVAS}">
      <Variant mode="AMBIENT" target="alpha" value="0" />
      <Image resource="space" />
    </PartImage>

    <!-- Thin atmosphere glow around the limb -->
    <PartImage x="0" y="0" width="{CANVAS}" height="{CANVAS}">
      <Variant mode="AMBIENT" target="alpha" value="64" />
      <Image resource="atmosphere" />
    </PartImage>

    <!-- Night side: always drawn; the day side covers it where the Sun is up -->
    <PartImage x="{EARTH_X}" y="{EARTH_X}" width="{D}" height="{D}">
      <Variant mode="AMBIENT" target="alpha" value="140" />
      <Image resource="earth_night" />
    </PartImage>

    <!-- Day side, clipped by the terminator mask -->
    <Group name="daylight" x="{EARTH_X}" y="{EARTH_X}" width="{D}" height="{D}">
      <Variant mode="AMBIENT" target="alpha" value="0" />
      <PartImage x="0" y="0" width="{D}" height="{D}">
        <Image resource="earth_day" />
      </PartImage>
      <Group name="terminator" x="0" y="0" width="{D}" height="{D}" pivotX="0.5" pivotY="0.5" renderMode="MASK">
        <!-- Rotate the mask so its bright side faces the Sun (clockwise from 3 o'clock) -->
        <Transform target="angle" value={quoteattr(W.ROT)} />
{masks}
      </Group>
    </Group>

    <!-- Minute track -->
    <PartImage x="0" y="0" width="{CANVAS}" height="{CANVAS}">
      <Variant mode="AMBIENT" target="alpha" value="150" />
      <Image resource="dial" />
    </PartImage>

    <!-- Day and date windows (chosen by number, so always English capitals) -->
{ind(date_xml, 4)}

    <!-- Hour and minute hands: style x colour -->
{ind(hands_xml, 4)}

    <!-- Centre cap in the hand colour -->
{ind(caps_xml, 4)}

    <!-- Seconds hand and its centre pin, in the accent colour -->
{ind(seconds_xml, 4)}
  </Scene>
</WatchFace>
'''
open(XML_OUT, "w").write(xml)

res = "\n".join(f'  <string name="{k}">{v}</string>' for k, v in strings.items())
open(STRINGS_OUT, "w").write(f'<?xml version="1.0" encoding="utf-8"?>\n<resources>\n{res}\n</resources>\n')
print(len(xml), "bytes")
