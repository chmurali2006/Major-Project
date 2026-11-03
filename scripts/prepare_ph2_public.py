#!/usr/bin/env python3
"""Prepare the public PH2 mirror into the working layout, with a receipt.

PH2 (ADDI project, Mendonca et al.) is 200 dermoscopic images with expert
lesion masks. The distribution with masks is a registration download; a public
mirror of the *images* is on GitHub:

    git clone https://github.com/vikaschouhan/PH2-dataset /tmp/ph2src

That mirror ships 200 JPEGs and no masks. This script is honest about both:
it records the per-file SHA-256 of every source image, and it writes a
placeholder mask that is **not** expert data. The placeholder is safe for
every configuration in this repository because the mask multiplies region
weighting, and region weighting is off (`lam = 0`, A-018) with the texture gate
also off (A-007): `beta = beta0 * (1 + lam*region)` is constant in `region`.
`scripts/bench.py` never reads the mask it loads, only `sysm.protect` does.

If you have the official distribution with `_lesion.bmp` masks, use
`scripts/prepare_ph2.py` instead - it checks the masks, records their hashes,
and flags empty ones.

    python scripts/prepare_ph2_public.py --src /tmp/ph2src --out datasets/ph2
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
IMAGE_RESAMPLE = Image.BICUBIC      # dossier §10: one resize rule for all images


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True,
                    help="root of the cloned mirror (contains images/)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    src = Path(args.src) / "images"
    if not src.is_dir():
        print(f"{src} does not exist", file=sys.stderr)
        return 1
    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "masks").mkdir(parents=True, exist_ok=True)

    entries = []
    for img_path in sorted(src.glob("*.jpg")):
        ident = img_path.stem
        im = Image.open(img_path).convert("RGB")
        im_r = im.resize((SIZE, SIZE), IMAGE_RESAMPLE)
        im_out = out / "images" / f"{ident}.jpg"
        # Stored as JPEG q95 4:4:4, the same rule prepare_ph2.py uses, so this
        # corpus is not easier than the one every other table was measured on.
        im_r.save(im_out, "JPEG", quality=95, subsampling=0, optimize=True)

        mask = np.zeros((SIZE, SIZE), bool)
        mask[112:400, 136:424] = True          # placeholder, not expert data
        mk_out = out / "masks" / f"{ident}.png"
        Image.fromarray((mask * 255).astype(np.uint8), "L").save(mk_out, "PNG")

        entries.append({
            "id": ident,
            "source": img_path.name,
            "source_size": list(im.size),
            "source_sha256": sha256(img_path),
            "derived_sha256": sha256(im_out),
            "mask": "placeholder (not expert data; unused at lam=0, gate off)",
        })

    if not entries:
        print(f"no jpg files under {src}", file=sys.stderr)
        return 1

    receipt = {
        "kind": "prepare",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(args.src),
        "source_kind": "public GitHub mirror, images only",
        "target_size": SIZE,
        "resample": "BICUBIC (images), placeholder masks",
        "stored_as": "JPEG quality=95, subsampling=0",
        "mask_caveat": (
            "The mirror has no expert masks. Region weighting is off in every "
            "reported configuration (A-018: lam=0), and the texture gate is off "
            "(A-007), so the mask has no effect on any number in docs/. It is "
            "written only because scripts/bench.py requires a mask file to exist."
        ),
        "n": len(entries),
        "files": entries,
    }
    (out / "prepare_receipt.json").write_text(json.dumps(receipt, indent=1))
    print(f"wrote {len(entries)} pairs to {out}")
    print(f"receipt: {out / 'prepare_receipt.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
