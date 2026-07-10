#!/usr/bin/env python3
"""Generate .webp siblings for raster images. Idempotent: skips when the
.webp is newer than the source.

    python scripts/optimize_images.py static/blog/images
    python scripts/optimize_images.py static/images/tools --max-width 1200
"""
import argparse
import sys
from pathlib import Path

from PIL import Image


def convert_dir(
    target: Path, max_width: int | None, quality: int
) -> list[tuple[Path, int, int]]:
    done = []
    for src in sorted(target.rglob("*")):
        if src.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        dst = src.with_suffix(".webp")
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            continue
        img = Image.open(src)
        if max_width and img.width > max_width:
            img.thumbnail((max_width, max_width * 10), Image.LANCZOS)
        img.save(dst, "WEBP", quality=quality, method=6)
        done.append((dst, src.stat().st_size, dst.stat().st_size))
    return done


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path)
    ap.add_argument("--max-width", type=int, default=None)
    ap.add_argument("--quality", type=int, default=80)
    a = ap.parse_args()
    results = convert_dir(a.target, a.max_width, a.quality)
    for dst, before, after in results:
        print(f"{dst}  {before // 1024}K -> {after // 1024}K")
    # runnable check: every produced webp must be smaller than its source
    bad = [d for d, b, a2 in results if a2 >= b]
    if bad:
        sys.exit(f"webp not smaller: {bad}")
    print(f"OK: {len(results)} converted")
