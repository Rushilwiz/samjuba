#!/usr/bin/env python3
"""
dedup.py — detect (and optionally remove) duplicate photos in ./photos.

Hashes the source images directly (EXIF-corrected so rotation differences don't
cause false misses; HEIC/HEIF supported). Groups duplicates, then on --apply
deletes the redundant source files from ./photos (image + its .xmp sidecar).

Two kinds of duplicates:
  1. identical   — byte-identical OR perceptually identical (dHash distance 0)
  2. perceptual  — visually the same but not pixel-perfect (distance 1..THRESHOLD).
                   These are the only ones that might rarely be distinct burst
                   frames, so they are rendered to review_dupes.html (with JPEG
                   thumbnails, so HEIC displays) for eyeballing before deletion.

Within each group the lexicographically-first stem is kept.

Usage:
  python3 dedup.py              # detect, print report, write review_dupes.html
  python3 dedup.py --apply      # delete redundant source files from ./photos
  python3 dedup.py --threshold N

After --apply, run preprocess.py to (re)build ./photos_ready + manifest.json.
Nothing is deleted unless you pass --apply.
"""

import argparse
import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

SRC = Path("./photos")
REVIEW = Path("./review_dupes.html")
THUMBS = Path("./review_thumbs")
IMAGE_EXT = {".jpg", ".jpeg", ".heic", ".heif", ".png", ".webp"}
THRESHOLD = 5  # max Hamming distance (of 64 bits) to treat as the same image


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return ImageOps.exif_transpose(Image.open(path))


def dhash(im, size=8):
    g = im.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(g.getdata())
    bits = 0
    for row in range(size):
        base = row * (size + 1)
        for col in range(size):
            bits = (bits << 1) | (1 if px[base + col] > px[base + col + 1] else 0)
    return bits


def hamming(a, b):
    return bin(a ^ b).count("1")


def source_files(stem):
    """All files in ./photos for a stem (image + .xmp sidecar)."""
    return [p for p in SRC.iterdir() if p.is_file() and p.name.startswith(stem + ".")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="delete redundant source files from ./photos")
    ap.add_argument("--threshold", type=int, default=THRESHOLD)
    args = ap.parse_args()

    if not SRC.is_dir():
        sys.exit(f"{SRC} not found — run from the slideshow/ directory.")

    imgs = sorted(p for p in SRC.iterdir()
                  if p.is_file() and p.suffix.lower() in IMAGE_EXT)
    if not imgs:
        sys.exit(f"No images in {SRC}.")

    print(f"Hashing {len(imgs)} source images...\n")
    info = {}  # path -> (md5, dhash)
    for p in imgs:
        try:
            info[p] = (md5(p), dhash(load(p)))
        except Exception as e:
            print(f"  ! could not hash {p.name}: {e}")

    # Union-find: merge on identical md5 OR perceptual closeness.
    parent = {p: p for p in info}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    items = list(info.items())
    by_md5 = {}
    for p, (m, _) in items:
        by_md5.setdefault(m, []).append(p)
    for g in by_md5.values():
        for other in g[1:]:
            union(g[0], other)
    for i in range(len(items)):
        pi, (_, hi) = items[i]
        for j in range(i + 1, len(items)):
            pj, (_, hj) = items[j]
            if hamming(hi, hj) <= args.threshold:
                union(pi, pj)

    clusters = {}
    for p in info:
        clusters.setdefault(find(p), []).append(p)
    groups = sorted(([sorted(g)[0]] + sorted(g)[1:] for g in clusters.values() if len(g) > 1),
                    key=lambda g: g[0].name)

    if not groups:
        print("No duplicates found.")
        return

    def max_dist(g):
        return max(hamming(info[g[0]][1], info[x][1]) for x in g[1:])

    perceptual = [g for g in groups if max_dist(g) >= 1]
    redundant = sum(len(g) - 1 for g in groups)

    print(f"{len(groups)} duplicate group(s), {redundant} redundant file(s) "
          f"({len(perceptual)} non-identical — see review_dupes.html):\n")
    for g in groups:
        kind = "perceptual" if max_dist(g) >= 1 else "identical"
        print(f"  [{kind}] keep {g[0].name}")
        for extra in g[1:]:
            print(f"             drop {extra.name}  (dist {hamming(info[g[0]][1], info[extra][1])})")

    # Render non-identical groups (with JPEG thumbnails so HEIC displays).
    if perceptual:
        THUMBS.mkdir(exist_ok=True)

        def thumb(path):
            out = THUMBS / (path.stem + ".jpg")
            if not out.exists():
                im = load(path).convert("RGB")
                im.thumbnail((400, 400))
                im.save(out, "JPEG", quality=80)
            return out.as_posix()

        cards = []
        for g in perceptual:
            cells = [f'<figure class="keep"><img src="{thumb(g[0])}">'
                     f'<figcaption>KEEP · {g[0].name}</figcaption></figure>']
            for extra in g[1:]:
                d = hamming(info[g[0]][1], info[extra][1])
                cells.append(f'<figure class="drop"><img src="{thumb(extra)}">'
                             f'<figcaption>drop · dist {d} · {extra.name}</figcaption></figure>')
            cards.append('<div class="group">' + "".join(cells) + "</div>")
        REVIEW.write_text(
            "<!doctype html><meta charset=utf-8><title>Duplicate review</title>"
            "<style>body{background:#111;color:#ddd;font:14px system-ui;margin:0;padding:24px}"
            "h1{font-weight:500}.group{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start;"
            "padding:16px;border-bottom:1px solid #333}figure{margin:0;max-width:280px}"
            "img{max-width:280px;max-height:280px;display:block;border:3px solid #444}"
            ".keep img{border-color:#3a7}.drop img{border-color:#a44}"
            "figcaption{font:11px monospace;color:#999;margin-top:4px;word-break:break-all}</style>"
            f"<h1>{len(perceptual)} non-identical duplicate group(s) to verify</h1>"
            "<p>Green = kept, red = will be deleted. Check the red ones are truly the same shot.</p>"
            + "".join(cards)
        )
        print(f"\nWrote {REVIEW} ({len(perceptual)} group(s)) — open it to verify before --apply.")

    if not args.apply:
        print(f"\nDetection only. Re-run with --apply to delete {redundant} source file(s) from {SRC}.")
        return

    deleted = 0
    missing = []
    for g in groups:
        for extra in g[1:]:
            srcs = source_files(extra.stem)
            if not srcs:
                missing.append(extra.stem)
            for f in srcs:
                f.unlink()
                deleted += 1
    print(f"\nDeleted {deleted} source file(s) from {SRC} "
          f"({redundant} duplicate images + their .xmp sidecars).")
    if missing:
        print(f"  ! no source found for: {', '.join(missing[:5])}")
    print("Now run preprocess.py to rebuild photos_ready/ and manifest.json.")


if __name__ == "__main__":
    main()
