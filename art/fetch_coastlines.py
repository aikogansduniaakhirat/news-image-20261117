"""Fetch and pre-simplify the world coastlines used by the map page.

Natural Earth 1:110m land polygons are public domain. They are fetched once,
projected to equirectangular, clipped to the latitudes the page shows, and
written as a compact JSON of integer coordinates so the renderer stays fast and
its drawings never depend on a network call at build time.
"""

from __future__ import annotations

import json
import os
import urllib.request

SRC = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
       "master/geojson/ne_110m_land.geojson")
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "land_cache.json")

LAT_TOP, LAT_BOTTOM = 84.0, -58.0      # what the page shows
DP_TOL = 0.18                          # degrees; keeps coastlines readable, small


def perp(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    px, py = x1 + t * dx, y1 + t * dy
    return ((x - px) ** 2 + (y - py) ** 2) ** 0.5


def simplify(pts, tol):
    """Douglas-Peucker, iterative so a huge ring cannot blow the stack."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        best, idx = 0.0, -1
        for k in range(i + 1, j):
            d = perp(pts[k], pts[i], pts[j])
            if d > best:
                best, idx = d, k
        if best > tol and idx > 0:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    return [p for p, k in zip(pts, keep) if k]


def ring_area(pts):
    s = 0.0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def main():
    with urllib.request.urlopen(SRC, timeout=60) as r:
        gj = json.load(r)

    rings = []
    for feat in gj["features"]:
        geom = feat["geometry"]
        polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
                 else [geom["coordinates"]])
        for poly in polys:
            for ring in poly:
                if ring_area(ring) < 3.0:      # drop specks that vanish at 1024px
                    continue
                clipped = []
                for lon, lat in ring:
                    clipped.append((round(lon, 2),
                                    round(max(LAT_BOTTOM, min(LAT_TOP, lat)), 2)))
                simp = simplify(clipped, DP_TOL)
                if len(simp) >= 4:
                    rings.append([[round(x, 2), round(y, 2)] for x, y in simp])

    rings.sort(key=len, reverse=True)
    with open(CACHE, "w") as f:
        json.dump({"lat_top": LAT_TOP, "lat_bottom": LAT_BOTTOM, "rings": rings},
                  f, separators=(",", ":"))
    pts = sum(len(r) for r in rings)
    print(f"{len(rings)} rings, {pts} points -> {CACHE} "
          f"({os.path.getsize(CACHE)} bytes)")


if __name__ == "__main__":
    main()
