#!/usr/bin/env python3
"""make.fun entry for news-image-20261117.

The competition asks for one image that sums up the world's news of Tuesday
17 November 2026, written to /output/entry.png by a program that runs with no
network. The rules allow the simplest form of entry: a repository that holds the
image, with a program that copies it to the output directory. That is what this
is.

The image is art/entry.png, rendered offline by art/render_image.py (see
art/README.md for the design and the checks it passed). Rendering happens at
build time, never here, so this program needs nothing beyond the standard
library, makes no network call, and writes byte-identical output on every run --
copying the same file twice yields the same bytes, which is what the two-run
reproducibility gate requires.

Usage:
    MAKEFUN_OUTPUT_DIR=out python3 main.py        # then look at out/entry.png
    python3 main.py                               # defaults to /output
"""

from __future__ import annotations

import os
import shutil
import sys

# the rendered image, committed beside this file
SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "art", "entry.png")

# the competition names the file exactly; keep it even though the format is PNG
OUTPUT_NAME = "entry.png"

DEFAULT_OUT_DIR = "/output"

MAX_BYTES = 1048576          # the gate rejects anything larger
MAX_SIDE = 1024              # and anything wider or taller than this


def fail(message):
    """Report a real problem on stderr and exit non-zero, never pass silently."""
    print(f"main.py: {message}", file=sys.stderr)
    return 1


def png_size(path):
    """Read width and height from the PNG IHDR chunk without any dependency."""
    with open(path, "rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    # signature 8 bytes, then chunk length 4 and type 4, so IHDR data starts at 16
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def main():
    if not os.path.isfile(SOURCE):
        return fail(f"missing source image: {SOURCE}")

    size = os.path.getsize(SOURCE)
    if size > MAX_BYTES:
        return fail(f"source is {size} bytes, over the {MAX_BYTES} byte limit")

    try:
        width, height = png_size(SOURCE)
    except ValueError as exc:
        return fail(f"source is not a readable PNG ({exc})")
    if width > MAX_SIDE or height > MAX_SIDE:
        return fail(f"source is {width}x{height}, over the {MAX_SIDE}px limit")

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or DEFAULT_OUT_DIR
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        return fail(f"cannot create output directory {out_dir}: {exc}")

    dest = os.path.join(out_dir, OUTPUT_NAME)
    try:
        shutil.copyfile(SOURCE, dest)
    except OSError as exc:
        return fail(f"cannot write {dest}: {exc}")

    written = os.path.getsize(dest)
    if written != size:
        return fail(f"{dest} is {written} bytes, expected {size}")

    print(f"wrote {dest} ({written} bytes, {width}x{height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
