#!/usr/bin/env python3
"""
preprocess.py  —  prepare funeral slideshow assets

Reads from ./photos, writes web-ready files to ./photos_ready, and emits
./photos_ready/manifest.json describing every item for the slideshow.

  - .heic/.heif        -> .jpg   (decoded via pillow-heif)
  - .jpg/.jpeg/.png    -> .jpg   (EXIF orientation baked in -> no sideways photos)
  - .mov/.mp4/.m4v     -> copied (browser plays natively; sound is ON in the player)

Run:
  pip install pillow pillow-heif      # one time
  python3 preprocess.py
"""

import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()

SRC = Path("./photos")
OUT = Path("./photos_ready")

IMAGE_EXT = {".jpg", ".jpeg", ".heic", ".heif", ".png", ".webp"}
VIDEO_EXT = {".mov", ".mp4", ".m4v", ".webm"}

OUT.mkdir(parents=True, exist_ok=True)


def exif_date(im):
    """Capture date as ISO 'YYYY-MM-DD' from EXIF, or None if absent/invalid."""
    try:
        ex = im.getexif()
        raw = ex.get_ifd(0x8769).get(36867) or ex.get(306)  # DateTimeOriginal, then DateTime
        if not raw:
            return None
        d = str(raw)[:10].replace(":", "-")
        y, m, day = (int(x) for x in d.split("-"))
        if 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= day <= 31:
            return d
    except Exception:
        pass
    return None


def bar(done, total, width=30):
    r = done / total if total else 0
    filled = round(r * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def main():
    if not SRC.is_dir():
        sys.exit(f"Source dir {SRC} not found.")

    files = sorted(p for p in SRC.iterdir() if p.is_file() and not p.name.startswith("."))
    if not files:
        sys.exit(f"No files in {SRC}.")

    print(f"Processing {len(files)} files from {SRC}/\n")

    manifest = []
    img_ok = vid_ok = fail = 0

    for i, p in enumerate(files):
        ext = p.suffix.lower()
        stem = p.stem
        try:
            if ext in IMAGE_EXT:
                out_name = f"{stem}.jpg"
                im = Image.open(p)
                date = exif_date(im)                     # read before transpose strips EXIF
                im = ImageOps.exif_transpose(im)        # bake in rotation
                im = im.convert("RGB")
                im.save(OUT / out_name, "JPEG", quality=90)
                entry = {"file": out_name, "type": "image"}
                if date:
                    entry["date"] = date
                manifest.append(entry)
                img_ok += 1
                status = f"✓ image  {p.name} -> {out_name}"
            elif ext in VIDEO_EXT:
                shutil.copy2(p, OUT / p.name)
                manifest.append({"file": p.name, "type": "video"})
                vid_ok += 1
                status = f"✓ video  {p.name} (copied)"
            else:
                status = f"· skip   {p.name} (unknown type)"
        except Exception as e:
            fail += 1
            status = f"✗ FAIL   {p.name} — {e}"

        done = i + 1
        pct = f"{done / len(files) * 100:5.1f}"
        print(f"{bar(done, len(files))} {pct}%  {status}")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\nDone. {img_ok} images, {vid_ok} video(s), {fail} failed.")
    print(f"Wrote {OUT}/manifest.json with {len(manifest)} items.")
    if fail:
        print("\n⚠ Some files failed. Re-run after checking them, or remove and proceed.")


if __name__ == "__main__":
    main()
