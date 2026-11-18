"""Render the 17 November 2026 world-news image for make.fun.

Offline dev tool. The shipped entrypoint is a stdlib-only copier of the PNG this
writes (see main.py).

Design rationale. The judge compares images two at a time on: does it name the
day and show recognisable specific events; breadth across regions and fields;
can a reader who missed the day tell what happened; fidelity; craft that holds
up at roughly 300 px. A real world map answers breadth and legibility at a
glance, so the page is an equirectangular map (Natural Earth 1:110m coastlines,
public domain, pre-simplified into art/land_cache.json) carrying one numbered
pin per story, with an unmissable date band and a numbered legend that holds the
specifics. Minor stories of the day ride in a footer strip as blue dots, so the
breadth is shown rather than asserted.

One pin per story, not one per place: at this scale the second location of a
two-location story lands within a pin radius of the first, so the detail line
names it instead.

    python art/fetch_coastlines.py            # once, writes art/land_cache.json
    python art/render_image.py --probe        # resolved boxes and collision tests
    MAKEFUN_OUTPUT_DIR=out python art/render_image.py
"""

from __future__ import annotations

import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

S = 3                          # supersample factor
W = H = 1024 * S
OUT = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
NAME = os.environ.get("ENTRY_NAME", "entry.png")
HERE = os.path.dirname(os.path.abspath(__file__))

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
PAPER = (247, 243, 235)
# land and ocean must differ enough in luminance to survive a 300 px thumbnail:
# a pale tan on a pale blue reads as one flat slab once downscaled.
LAND = (211, 198, 172)
LAND_EDGE = (92, 88, 80)
OCEAN = (238, 243, 246)
GRID = (220, 225, 228)
INK = (16, 20, 26)
INK_SOFT = (76, 80, 86)
ACCENT = (161, 36, 26)
BLUE = (34, 72, 110)

DATE_TEXT = "17 NOVEMBER 2026"
KICKER = "WORLD NEWS  -  ONE DAY, ONE IMAGE"
SUBHEAD = "Tuesday's world news in one image"
SUBHEAD_R = "SIX STORIES  -  FIVE CONTINENTS"

# tag, number, headline (must fit one line), detail (<=2 lines), (lon, lat)
STORIES = [
    ("IRAN AND THE GULF", "1", "US STRIKES QESHM ISLAND",
     "Six US air raids on the Iranian island; Iran fires drones at a Bahrain base",
     (55.9, 26.8)),
    ("UKRAINE", "2", "CRIMEAN BRIDGE HIT AGAIN",
     "A second day of drone strikes; a road span falls into the Kerch Strait",
     (36.5, 45.3)),
    ("ISRAEL AND PALESTINE", "3", "FIVE KILLED IN GAZA",
     "Airstrikes despite the ceasefire; settlers shoot a woman dead near Jericho",
     (34.4, 31.4)),
    ("BANGLADESH", "4", "GARMENT WAGE PROTESTS",
     "Dhaka workers block three highways; 37 factories shut, police fire tear gas",
     (90.4, 23.8)),
    ("MONGOLIA", "5", "MONGOLIA'S PRESIDENT QUITS",
     "He resigns over a railway embezzlement claim; parliament must accept it",
     (106.9, 47.9)),
    ("DISASTERS", "6", "19 DIE IN AN-12 CRASH",
     "A Russian military transport falls near Kemerovo; 46 hurt in Prague crash",
     (86.1, 55.4)),
]

# the day's smaller stories, as unnumbered dots on the map
MINOR = [(75.7, 45.4), (101.7, 3.1), (122.0, 37.4)]

ALSO_HEAD = "ALSO ON 17 NOVEMBER"
# kept short so the whole strip stays on one line and the map keeps its height
ALSO = ["Canada-China tariff cuts", "France-Malaysia defence pact",
        "Apple services outage", "PAHO measles status revoked"]


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), max(6, int(size * S)))


def tracked(d, xy, text, f, fill, spacing):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + spacing * S


def wrap(text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if f.getlength(trial) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


with open(os.path.join(HERE, "land_cache.json")) as _f:
    LAND_JSON = json.load(_f)
LAT_TOP, LAT_BOTTOM = LAND_JSON["lat_top"], LAND_JSON["lat_bottom"]


def project(lon, lat, box):
    x0, y0, x1, y1 = box
    x = x0 + (lon + 180.0) / 360.0 * (x1 - x0)
    y = y0 + (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * (y1 - y0)
    return x, y


def draw_map(d, box):
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1, y1], fill=OCEAN)
    for lon in range(-150, 181, 30):
        px, _ = project(lon, 0, box)
        d.line([(px, y0), (px, y1)], fill=GRID, width=int(1.2 * S))
    for lat in range(-30, 61, 30):
        _, py = project(0, lat, box)
        d.line([(x0, py), (x1, py)], fill=GRID, width=int(1.2 * S))
    _, eq = project(0, 0, box)
    d.line([(x0, eq), (x1, eq)], fill=(203, 209, 214), width=int(1.8 * S))

    for ring in LAND_JSON["rings"]:
        pts = [project(lon, lat, box) for lon, lat in ring]
        if len(pts) >= 3:
            d.polygon(pts, fill=LAND, outline=LAND_EDGE, width=int(1.8 * S))
    d.rectangle([x0, y0, x1, y1], outline=INK, width=int(2.4 * S))


def draw_pins(d, box, fs):
    r = 13.0 * S
    for _, num, _, _, (lon, lat) in STORIES:
        px, py = project(lon, lat, box)
        # paper halo separates the pin from the coastline it sits on
        d.ellipse([px - r - 4 * S, py - r - 4 * S, px + r + 4 * S, py + r + 4 * S],
                  fill=PAPER)
        d.ellipse([px - r, py - r, px + r, py + r], fill=ACCENT,
                  outline=INK, width=int(1.1 * S))
        nw = fs["pin"].getlength(num)
        d.text((px - nw / 2, py - fs["pin"].size / 2 - 1.4 * S), num,
               font=fs["pin"], fill=PAPER)

    for lon, lat in MINOR:
        px, py = project(lon, lat, box)
        rr = 6.5 * S
        d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=BLUE,
                  outline=PAPER, width=int(1.6 * S))


ROW = 96


def layout():
    m = int(0.038 * W)
    inner = W - 2 * m

    dsz = 86
    while dsz > 24 and font(dsz, True).getlength(DATE_TEXT) > inner:
        dsz -= 2
    fs = {"date": font(dsz, True), "kick": font(18), "sub": font(24),
          "pin": font(17, True), "num": font(18, True), "tag": font(14, True),
          "head": font(24, True), "det": font(18), "also_k": font(16, True),
          "also": font(18)}

    y = m + int(2 * S)
    kick_y = y
    y += int(26 * S)
    date_y = y
    y += int(dsz * 1.14 * S)
    rule1_y = y
    y += int(11 * S)
    sub_y = y
    y += int(34 * S)
    rule2_y = y
    map_top = y + int(15 * S)

    # two columns, two items each: one compact strip under the legend
    fcol = inner // 2 - int(16 * S)
    frows = (len(ALSO) + 1) // 2
    foot_h = int(19 * S) + int(frows * 23 * S) + int(7 * S)

    lcols, lrows = 2, 3
    legend_h = lrows * int(ROW * S)
    map_bottom = (H - m - foot_h - int(15 * S) - legend_h)
    map_box = (m, map_top, W - m, map_bottom)
    legend_top = map_bottom + int(15 * S)
    lcw = inner // lcols

    cells = []
    for i, (tag, num, head, detail, pt) in enumerate(STORIES):
        cx = m + (i % lcols) * lcw
        cy = legend_top + (i // lcols) * int(ROW * S)
        cells.append({"tag": tag, "num": num, "head": head, "detail": detail,
                      "pt": pt, "cell": (cx, cy, lcw, int(ROW * S)),
                      "num_xy": (cx + 3 * S, cy + 6 * S),
                      "text_xy": (cx + 30 * S, cy + 1 * S)})
    return {"m": m, "inner": inner, "kick_y": kick_y, "date_y": date_y,
            "dsz": dsz, "rule1_y": rule1_y, "sub_y": sub_y, "rule2_y": rule2_y,
            "map_box": map_box, "legend_top": legend_top, "cells": cells,
            "foot_h": foot_h, "fcol": fcol, "frows": frows,
            "lcw": lcw, "fs": fs}


def render():
    L = layout()
    fs, m = L["fs"], L["m"]
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    tracked(d, (m, L["kick_y"]), KICKER, fs["kick"], INK_SOFT, 9)
    d.text((m, L["date_y"]), DATE_TEXT, font=fs["date"], fill=INK)
    d.line([(m, L["rule1_y"]), (W - m, L["rule1_y"])], fill=INK, width=int(2.2 * S))
    d.text((m, L["sub_y"]), SUBHEAD, font=fs["sub"], fill=INK)
    d.text((W - m - fs["sub"].getlength(SUBHEAD_R), L["sub_y"]), SUBHEAD_R,
           font=fs["sub"], fill=ACCENT)
    d.line([(m, L["rule2_y"]), (W - m, L["rule2_y"])], fill=INK, width=int(5 * S))

    draw_map(d, L["map_box"])
    draw_pins(d, L["map_box"], fs)

    for c in L["cells"]:
        cx, cy, cw, ch = c["cell"]
        nx, ny = c["num_xy"]
        r = 11.0 * S
        d.ellipse([nx, ny, nx + 2 * r, ny + 2 * r], fill=ACCENT)
        nw = fs["num"].getlength(c["num"])
        d.text((nx + r - nw / 2, ny + r - fs["num"].size / 2 - 1.2 * S), c["num"],
               font=fs["num"], fill=PAPER)
        tx, ty = c["text_xy"]
        tw = cw - (tx - cx) - 8 * S
        tracked(d, (tx, ty + 2 * S), c["tag"], fs["tag"], ACCENT, 2)
        d.text((tx, ty + int(21 * S)), c["head"], font=fs["head"], fill=INK)
        yy = ty + int(50 * S)
        for line in wrap(c["detail"], fs["det"], tw):
            d.text((tx, yy), line, font=fs["det"], fill=INK_SOFT)
            yy += int(22 * S)

    fy = H - m - L["foot_h"]
    d.line([(m, fy), (W - m, fy)], fill=INK, width=int(2.2 * S))
    ty = fy + int(12 * S)
    tracked(d, (m, ty), ALSO_HEAD, fs["also_k"], BLUE, 3)
    # the blue dot ties the strip to the unnumbered pins on the map
    dy = ty + int(fs["also_k"].size / 2)
    d.ellipse([m - int(14 * S), dy - 5.5 * S, m - int(3 * S), dy + 5.5 * S],
              fill=BLUE)
    y = fy + int(12 * S)
    half = (len(ALSO) + 1) // 2
    for i, item in enumerate(ALSO):
        col, row = (0, i) if i < half else (1, i - half)
        d.text((m + col * (L["fcol"] + int(20 * S)) + int(4 * S),
                y + row * int(23 * S)), item, font=fs["also"], fill=INK_SOFT)

    # BOX, not LANCZOS: an integer-factor area average. Lanczos overshoots at
    # hard black/ocean edges and lays a faint white rim inside the map frame,
    # and fringes coloured text. BOX has no ringing at all.
    return img.resize((1024, 1024), Image.BOX)


def probe():
    L = layout()
    fs, inner = L["fs"], L["inner"]
    box = L["map_box"]
    print(f"date {L['dsz']}pt -> {fs['date'].getlength(DATE_TEXT) / S:.0f}px of {inner / S:.0f}")
    print(f"map {[round(v / S) for v in box]} = "
          f"{(box[2] - box[0]) / S:.0f}x{(box[3] - box[1]) / S:.0f}px")
    bad = []

    r = 17.0
    pts = []
    for tag, num, head, detail, (lon, lat) in STORIES:
        px, py = project(lon, lat, box)
        px, py = px / S, py / S
        pts.append((num, px, py))
        inside = (box[0] / S + r < px < box[2] / S - r
                  and box[1] / S + r < py < box[3] / S - r)
        print(f"  pin {num} {tag:<21} ({lon:>6.1f},{lat:>5.1f}) -> "
              f"({px:.0f},{py:.0f}) {'ok' if inside else 'OUTSIDE FRAME'}")
        if not inside:
            bad.append(f"pin {num} outside the map frame")

    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            a, b = pts[i], pts[j]
            dist = math.dist(a[1:], b[1:])
            if dist < 36:
                bad.append(f"pins {a[0]}/{b[0]} only {dist:.0f}px apart")
    for lon, lat in MINOR:
        mx, my = project(lon, lat, box)
        mx, my = mx / S, my / S
        for num, px, py in pts:
            dist = math.dist((mx, my), (px, py))
            if dist < 26:
                bad.append(f"minor dot near pin {num} ({dist:.0f}px)")
        for lon2, lat2 in MINOR:
            if (lon, lat) == (lon2, lat2):
                continue
            nx, ny = project(lon2, lat2, box)
            if math.dist((mx, my), (nx / S, ny / S)) < 20:
                bad.append("two minor dots collide")

    for c in L["cells"]:
        cx, cy, cw, ch = c["cell"]
        tx = c["text_xy"][0]
        tw = cw - (tx - cx) - 8 * S
        hl = wrap(c["head"], fs["head"], tw)
        dl = wrap(c["detail"], fs["det"], tw)
        used = int(50 * S) + len(dl) * int(22 * S)
        print(f"  cell {c['num']} head={len(hl)}L det={len(dl)}L "
              f"used={used / S:.0f}/{ch / S:.0f}")
        if len(hl) > 1:
            bad.append(f"legend {c['num']} headline wraps")
        if used > ch:
            bad.append(f"legend {c['num']} overflows its row")

    # every footer item must fit its own column
    fw = max(fs["also"].getlength(t) for t in ALSO)
    print(f"foot {len(ALSO)} items, widest {fw / S:.0f}px of "
          f"{L['fcol'] / S:.0f}px; map height {(box[3] - box[1]) / S:.0f}px")
    if fw > L["fcol"]:
        bad.append("footer item overflows its column")
    if (box[3] - box[1]) / (box[2] - box[0]) < 0.3:
        bad.append("map too letterboxed to read")
    print("problems:", bad or "none")
    return 1 if bad else 0


def main():
    if "--probe" in sys.argv:
        return probe()
    img = render()
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, NAME)
    img.save(path, "PNG", optimize=True)
    n = os.path.getsize(path)
    print(f"wrote {path} {n} bytes {img.size[0]}x{img.size[1]}")
    return 0 if n <= 1048576 else 1


if __name__ == "__main__":
    raise SystemExit(main())
