#!/usr/bin/env python3
"""Prepare the PH2 corpus into the working layout, with a full receipt.

PH2 (ADDI project, Mendonca et al.) is 200 dermoscopic images with expert
lesion masks, distributed as 767x576 BMP. It is a real, peer-reviewed
dermoscopy corpus and is used here for Phase One instrument validation.

**PH2 is not the dossier's primary dataset.** ISIC 2018 Task 1 remains the
primary corpus for every reported number; PH2 exists because the sandbox
cannot reach the ISIC archive and instrument validation on synthetic phantoms
was not evidence. Every table that uses PH2 says so.

Usage:
    python scripts/prepare_ph2.py --src /tmp/hunt/AniketP04... --out datasets/ph2
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
IMAGE_RESAMPLE = Image.BICUBIC      # pinned: dossier §10, one rule for all images
MASK_RESAMPLE = Image.NEAREST       # Trap 28: masks are binary, never interpolated


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dhash(gray: np.ndarray, size: int = 8) -> str:
    """Difference hash for near-duplicate detection (Trap 27)."""
    im = Image.fromarray(gray).resize((size + 1, size), Image.BILINEAR)
    a = np.asarray(im, dtype=np.int16)
    bits = (a[:, 1:] > a[:, :-1]).flatten()
    return "".join("1" if b else "0" for b in bits)


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="cloned repo root containing Data/")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    src = Path(args.src) / "Data"
    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "masks").mkdir(parents=True, exist_ok=True)

    pairs: list[tuple[str, Path, Path]] = []
    for split in ("Train", "Test"):
        img_dir, gt_dir = src / split / "Original", src / split / "GT"
        if not img_dir.is_dir():
            continue
        for img_path in sorted(img_dir.glob("*.bmp")):
            lesion = img_path.stem
            mask_path = gt_dir / f"{lesion}_lesion.bmp"
            if not mask_path.exists():
                print(f"  missing mask for {lesion}", file=sys.stderr)
                continue
            pairs.append((split, img_path, mask_path))

    if not pairs:
        print("no pairs found", file=sys.stderr)
        return 1

    entries, hashes = [], []
    for split, img_path, mask_path in pairs:
        ident = img_path.stem
        im = Image.open(img_path).convert("RGB")
        mk = Image.open(mask_path).convert("L")
        if mk.size != im.size:
            print(f"  size mismatch {ident}: {im.size} vs {mk.size}", file=sys.stderr)
            mk = mk.resize(im.size, MASK_RESAMPLE)

        im_r = im.resize((SIZE, SIZE), IMAGE_RESAMPLE)
        mk_r = mk.resize((SIZE, SIZE), MASK_RESAMPLE)
        mask = (np.asarray(mk_r) > 127)

        if mask.sum() < 0.01 * SIZE * SIZE:
            print(f"  empty mask {ident} ({mask.mean():.4f})", file=sys.stderr)

        # The corpus is stored as JPEG q95, 4:4:4, because that is how the
        # target corpus (ISIC 2018) is distributed. Storing lossless PNG would
        # give the system an easier image than any real deployment sees.
        im_out = out / "images" / f"{ident}.jpg"
        mk_out = out / "masks" / f"{ident}.png"
        im_r.save(im_out, "JPEG", quality=95, subsampling=0, optimize=True)
        Image.fromarray((mask * 255).astype(np.uint8), "L").save(mk_out, "PNG", compress_level=6)

        dh = dhash(np.asarray(im_r.convert("L")))
        hashes.append((ident, dh))
        entries.append({
            "id": ident,
            "source_split": split,
            "source_image": str(img_path.relative_to(Path(args.src))),
            "source_mask": str(mask_path.relative_to(Path(args.src))),
            "source_image_sha256": sha256(img_path),
            "source_mask_sha256": sha256(mask_path),
            "derived_image_sha256": sha256(im_out),
            "derived_mask_sha256": sha256(mk_out),
            "lesion_fraction": round(float(mask.mean()), 6),
            "dhash": dh,
        })

    # near-duplicate clusters across the corpus (Trap 27)
    dupes = []
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            d = hamming(hashes[i][1], hashes[j][1])
            if d <= 4:
                dupes.append({"a": hashes[i][0], "b": hashes[j][0], "hamming": d})

    total = sum(p.stat().st_size for p in (out / "images").glob("*.jpg")) + \
        sum(p.stat().st_size for p in (out / "masks").glob("*.png"))

    receipt = {
        "dataset": "PH2",
        "role": "Phase One instrument validation; ISIC 2018 remains primary",
        "provenance": {
            "source_repo": "https://github.com/AniketP04/Skin-Cancer-Lesion-Segmentation",
            "source_path": "Data/{Train,Test}/{Original,GT}",
            "original_format": "BMP 767x576 RGB, masks mode-1 binary",
            "note": "third-party mirror of the ADDI PH2 distribution; not the official download",
        },
        "licence": {
            "name": "PH2 / ADDI research use",
            "terms": "free for research; redistribution of pixels not permitted",
            "reference": "Mendonca et al., PH2: a dermoscopic image database, 2013",
        },
        "prepared_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "preparation": {
            "image_size": SIZE,
            "image_resample": "PIL BICUBIC",
            "image_encoding": "JPEG quality 95, subsampling 4:4:4 (matches ISIC storage)",
            "mask_resample": "PIL NEAREST",
            "output_format": "images JPEG q95, masks PNG lossless",
            "pillow": Image.__version__,
            "numpy": np.__version__,
        },
        "counts": {"images": len(entries), "bytes_after_convert": total},
        "near_duplicates": dupes,
        "files": entries,
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2))

    print(f"prepared {len(entries)} pairs -> {out}")
    print(f"  size on disk: {total/1e6:.1f} MB")
    print(f"  near-duplicate pairs (dhash<=4): {len(dupes)}")
    print(f"  lesion fraction: min {min(e['lesion_fraction'] for e in entries):.3f} "
          f"median {sorted(e['lesion_fraction'] for e in entries)[len(entries)//2]:.3f} "
          f"max {max(e['lesion_fraction'] for e in entries):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
