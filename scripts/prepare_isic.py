#!/usr/bin/env python3
"""Prepare ISIC 2018 Task 1 (or any image+mask corpus) into the working layout.

ISIC 2018 Task 1 is the dossier's primary corpus: 2,594 dermoscopic JPEGs with
binary lesion masks. The official archives are:

    ISIC2018_Task1-2_Training_Input.zip       images  ISIC_<id>.jpg
    ISIC2018_Task1_Training_GroundTruth.zip   masks   ISIC_<id>_segmentation.png

Both are gated behind a registration click, so this script does not download
anything. It takes whatever you extracted and normalises it.

Usage, either shape:

    # official zips already extracted
    python scripts/prepare_isic.py --images ~/ISIC2018/images \
                                   --masks  ~/ISIC2018/masks \
                                   --out datasets/isic2018

    # PH2-style, masks named <id>_lesion.bmp
    python scripts/prepare_isic.py --images <repo>/Data/Train/Original \
                                   --masks  <repo>/Data/Train/GT \
                                   --out datasets/ph2_train

The mask file is found by trying, in order:
    <id>_segmentation.png, <id>_segmentation.jpg, <id>.png, <id>.jpg,
    <id>_lesion.bmp, <id>_mask.png
and finally by a prefix scan, so a mask whose name merely starts with the image
stem is still matched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

SIZE = 512
IMAGE_RESAMPLE = Image.BICUBIC      # pinned, dossier §10
MASK_RESAMPLE = Image.NEAREST       # Trap 28
JPEG_QUALITY = 95
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
MASK_SUFFIXES = ("_segmentation", "_lesion", "_mask", "_gt")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_mask_index(mask_dir: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for p in sorted(mask_dir.iterdir()):
        if p.suffix.lower() not in IMAGE_EXTS:
            continue
        stem = p.stem
        for suffix in MASK_SUFFIXES:
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        index.setdefault(stem, p)
    return index


def find_mask(ident: str, mask_dir: Path, index: dict[str, Path]) -> Path | None:
    for suffix in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"):
        for name in (f"{ident}_segmentation{suffix}", f"{ident}{suffix}",
                     f"{ident}_lesion{suffix}", f"{ident}_mask{suffix}"):
            p = mask_dir / name
            if p.exists():
                return p
    return index.get(ident)


def dhash(gray: np.ndarray, size: int = 8) -> str:
    im = Image.fromarray(gray).resize((size + 1, size), Image.BILINEAR)
    a = np.asarray(im, dtype=np.int16)
    return "".join("1" if b else "0" for b in (a[:, 1:] > a[:, :-1]).flatten())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--masks", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0,
                    help="only prepare the first N matched pairs")
    ap.add_argument("--dataset", default="ISIC 2018 Task 1")
    args = ap.parse_args()

    img_dir, mask_dir = Path(args.images), Path(args.masks)
    out = Path(args.out)
    for d in (img_dir, mask_dir):
        if not d.is_dir():
            print(f"not a directory: {d}", file=sys.stderr)
            return 2

    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "masks").mkdir(parents=True, exist_ok=True)

    index = build_mask_index(mask_dir)
    entries, missing = [], []
    images = [p for p in sorted(img_dir.iterdir()) if p.suffix.lower() in IMAGE_EXTS]

    for img_path in images:
        if args.limit and len(entries) >= args.limit:
            break
        ident = img_path.stem
        mask_path = find_mask(ident, mask_dir, index)
        if mask_path is None:
            missing.append(ident)
            continue

        im = Image.open(img_path).convert("RGB")
        mk = Image.open(mask_path).convert("L")
        if mk.size != im.size:
            mk = mk.resize(im.size, MASK_RESAMPLE)

        im_r = im.resize((SIZE, SIZE), IMAGE_RESAMPLE)
        mask = np.asarray(mk.resize((SIZE, SIZE), MASK_RESAMPLE)) > 127

        im_out = out / "images" / f"{ident}.jpg"
        mk_out = out / "masks" / f"{ident}.png"
        im_r.save(im_out, "JPEG", quality=JPEG_QUALITY, subsampling=0, optimize=True)
        Image.fromarray((mask * 255).astype(np.uint8), "L").save(mk_out, "PNG", compress_level=6)

        entries.append({
            "id": ident,
            "source_image": img_path.name,
            "source_mask": mask_path.name,
            "source_image_sha256": sha256(img_path),
            "source_mask_sha256": sha256(mask_path),
            "derived_image_sha256": sha256(im_out),
            "lesion_fraction": round(float(mask.mean()), 6),
            "dhash": dhash(np.asarray(im_r.convert("L"))),
        })

    if not entries:
        print("no image/mask pairs matched", file=sys.stderr)
        if missing:
            print(f"  {len(missing)} images had no mask, e.g. {missing[:3]}", file=sys.stderr)
        return 1

    total = sum(p.stat().st_size for p in (out / "images").glob("*.jpg")) + \
        sum(p.stat().st_size for p in (out / "masks").glob("*.png"))

    fracs = sorted(e["lesion_fraction"] for e in entries)
    receipt = {
        "dataset": args.dataset,
        "role": "primary corpus, dossier §16",
        "prepared_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "preparation": {
            "image_size": SIZE,
            "image_resample": "PIL BICUBIC",
            "mask_resample": "PIL NEAREST",
            "image_encoding": f"JPEG q{JPEG_QUALITY}, 4:4:4",
            "mask_encoding": "PNG lossless, 0/255",
            "pillow": Image.__version__,
            "numpy": np.__version__,
        },
        "counts": {
            "images_in_source": len(images),
            "pairs_prepared": len(entries),
            "images_without_mask": len(missing),
            "bytes_after_convert": total,
        },
        "lesion_fraction": {"min": fracs[0], "median": fracs[len(fracs) // 2], "max": fracs[-1]},
        "missing_mask_sample": missing[:20],
        "files": entries,
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2))

    print(f"prepared {len(entries)} pairs -> {out}")
    print(f"  source images: {len(images)}, without mask: {len(missing)}")
    print(f"  size on disk: {total/1e6:.1f} MB")
    print(f"  lesion fraction: min {fracs[0]:.3f} median {fracs[len(fracs)//2]:.3f} max {fracs[-1]:.3f}")
    if missing:
        print(f"  WARNING: {len(missing)} images had no mask and were skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
