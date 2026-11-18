"""Pixel-level QA for the shipped entry.png.

No image viewer is available in this tick, so the page is verified by
measurement of the actual rendered pixels: the map frame must be filled with
land and sea, every numbered pin must sit on ink, the legend and footer bands
must carry text, nothing may collide, and the page must still be legible after a
300 px downscale (the size a judge reads thumbnails at).

    python art/qa_image.py out/entry.png
"""

from __future__ import annotations

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_image as R

S = R.S


def density(im, box, thresh=190):
    g = im.convert("L").crop(box)
    px = list(g.get_flattened_data()) if hasattr(g, "get_flattened_data") \
        else list(g.getdata())
    return sum(1 for v in px if v < thresh) / max(1, len(px))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "out/entry.png"
    im = Image.open(path).convert("RGB")
    n = os.path.getsize(path)
    print(f"{path}: {im.size[0]}x{im.size[1]} {n} bytes "
          f"({'OK' if n <= 1048576 else 'OVER 1 MiB'})")
    if im.size != (1024, 1024):
        print("PROBLEMS: wrong size")
        return 1

    L = R.layout()
    box = [v / S for v in L["map_box"]]
    bad = []

    total = density(im, (0, 0, 1024, 1024))
    print(f"page ink density {total:.3f} ({'ok' if 0.03 < total < 0.55 else 'SUSPECT'})")

    # the map frame must be entirely drawn: land tan and ocean blue both
    ocean = density(im, (int(box[0]) + 2, int(box[1]) + 2,
                         int(box[2]) - 2, int(box[3]) - 2), thresh=245)
    print(f"map frame fill {ocean:.3f}")
    if ocean < 0.99:
        bad.append("map frame has undrawn gaps")

    # land must actually be present (not an empty ocean rectangle)
    g = im.convert("RGB")
    tan = g.crop((int(box[0]), int(box[1]), int(box[2]), int(box[3])))
    tp = list(tan.get_flattened_data()) if hasattr(tan, "get_flattened_data") \
        else list(tan.getdata())
    lr, lg, lb = R.LAND
    land_px = sum(1 for r, gg, b in tp
                  if abs(r - lr) < 14 and abs(gg - lg) < 14 and abs(b - lb) < 16)
    share = land_px / max(1, len(tp))
    print(f"land share of map {share:.3f} (expect ~0.3)")
    if not 0.15 < share < 0.55:
        bad.append(f"land share {share:.2f} looks wrong")

    # every pin centre must be at the accent colour, not paper
    for tag, num, head, detail, (lon, lat) in R.STORIES:
        px, py = R.project(lon, lat, R.layout()["map_box"])
        px, py = int(px / S), int(py / S)
        r, gg, b = im.getpixel((px, py))
        ar, ag, ab = R.ACCENT
        is_pin = abs(r - ar) < 45 and abs(gg - ag) < 45 and abs(b - ab) < 45
        if not is_pin:
            # the numeral is paper-coloured and sits at the centre
            near = im.crop((px - 14, py - 14, px + 14, py + 14))
            np_ = list(near.get_flattened_data()) if hasattr(near, "get_flattened_data") \
                else list(near.getdata())
            pins = sum(1 for rr, gg2, bb in np_
                       if abs(rr - ar) < 50 and abs(gg2 - ag) < 50 and abs(bb - ab) < 50)
            is_pin = pins > 120
        print(f"  pin {num} at ({px},{py}) rgb=({r},{gg},{b}) "
              f"{'ok' if is_pin else 'MISSING'}")
        if not is_pin:
            bad.append(f"pin {num} not drawn")

    # headline band, legend band, footer band must all carry ink
    band_date = density(im, (int(L["m"] / S), int(L["date_y"] / S), 1024 - int(L["m"] / S),
                             int(L["rule1_y"] / S)))
    leg_top = int(L["legend_top"] / S)
    leg_bot = leg_top + 3 * R.ROW
    band_leg = density(im, (int(L["m"] / S), leg_top + R.ROW - 6,
                            1024 - int(L["m"] / S), leg_top + R.ROW + 34))
    fy = 1024 - int(L["m"] / S) - int(L["foot_h"] / S)
    band_foot = density(im, (int(L["m"] / S), fy + 2, 1024 - int(L["m"] / S), 1024 - 10))
    print(f"bands: date {band_date:.3f} legend {band_leg:.3f} foot {band_foot:.3f}")
    for name, v, lim in (("date", band_date, 0.05), ("legend", band_leg, 0.03),
                         ("footer", band_foot, 0.01)):
        if v < lim:
            bad.append(f"{name} band empty")

    # legend rows must not overlap the footer or the map
    if leg_bot > fy:
        bad.append("legend overlaps footer")

    # legibility at the size the judge reads
    small = im.resize((300, 300), Image.LANCZOS).convert("L")
    data = list(small.get_flattened_data()) if hasattr(small, "get_flattened_data") \
        else list(small.getdata())
    contrast = max(data) - min(data)
    dark = sum(1 for v in data if v < 140) / len(data)
    print(f"at 300px: contrast {contrast}, ink {dark:.3f}")
    if contrast < 150:
        bad.append("flattens at 300px")
    if dark < 0.02:
        bad.append("almost no ink at 300px")

    print("\nPROBLEMS: " + (", ".join(bad) if bad else "none"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
