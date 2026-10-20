#!/usr/bin/env python
"""The textbook fragile watermark, measured on the same battery.

Every review asks it: *why not just put a hash in the LSBs?* It is the obvious
design, it is what the word "fragile" usually means, and no amount of argument
settles whether it is better here. So it is implemented and measured.

The scheme (Wong-style block hash, the standard construction):

  * the image is cut into the same 8x8 grid this project uses, so localisation
    resolution is identical and the comparison is about the *rule*, not the grid;
  * the LSB of one pixel per block position is set to zero, the block is hashed
    with a keyed BLAKE2b over its address and content, and 64 hash bits are
    written back into the 64 LSBs of the block;
  * verification zeroes those LSBs, recomputes the hash and compares.

It detects any pixel change exactly, so its detection and localisation should be
excellent. It has no way to tell a codec from a scalpel, so it should also call
every JPEG re-encode tampering. Both are measured rather than asserted.

    python scripts/baseline_lsb.py --data /tmp/ph2mirror --limit 200 \
                                   --receipt runs/<run>/receipt.json
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from bench import detected, git_commit, iou, load_dataset   # noqa: E402
from src.battery.conditions import FROZEN                    # noqa: E402

KEY = b"lsb-baseline-key"
BLOCK = 8
CHANNEL = 1          # green: least perceptual weight of the three
PASTE = (1, 2, 3, 4, 5)
BENIGN = (7, 8, 9, 10, 11)


def _hash(block_zeroed: np.ndarray, address: int) -> int:
    h = hashlib.blake2b(key=KEY, digest_size=8)
    h.update(address.to_bytes(4, "little"))
    h.update(np.ascontiguousarray(block_zeroed, dtype=np.uint8).tobytes())
    return int.from_bytes(h.digest(), "little")


def embed(rgb: np.ndarray) -> np.ndarray:
    out = rgb.copy()
    plane = out[..., CHANNEL]
    ny, nx = plane.shape[0] // BLOCK, plane.shape[1] // BLOCK
    for by in range(ny):
        for bx in range(nx):
            y0, x0 = by * BLOCK, bx * BLOCK
            block = plane[y0:y0 + BLOCK, x0:x0 + BLOCK]
            zeroed = block & 0xFE
            bits = _hash(zeroed, by * nx + bx)
            pat = np.array([(bits >> i) & 1 for i in range(BLOCK * BLOCK)],
                           dtype=np.uint8).reshape(BLOCK, BLOCK)
            plane[y0:y0 + BLOCK, x0:x0 + BLOCK] = zeroed | pat
    return out


def detect(rgb: np.ndarray) -> np.ndarray:
    """Per-block mismatch map on the same 64x64 grid the project reports on."""
    plane = rgb[..., CHANNEL]
    ny, nx = plane.shape[0] // BLOCK, plane.shape[1] // BLOCK
    bad = np.zeros((ny, nx), dtype=bool)
    for by in range(ny):
        for bx in range(nx):
            y0, x0 = by * BLOCK, bx * BLOCK
            block = plane[y0:y0 + BLOCK, x0:x0 + BLOCK]
            zeroed = block & 0xFE
            bits = _hash(zeroed, by * nx + bx)
            pat = np.array([(bits >> i) & 1 for i in range(BLOCK * BLOCK)],
                           dtype=np.uint8).reshape(BLOCK, BLOCK)
            bad[by, bx] = bool((block & 1 != pat).any())
    return bad


def jpeg(data: bytes, quality: int) -> bytes:
    rgb = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "JPEG", quality=quality, subsampling=0)
    back = np.array(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
    from src.container import png_bytes, png_text
    return png_bytes(back, text=png_text(data))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--receipt", default="")
    args = ap.parse_args()

    images = load_dataset(args.data, args.limit)
    per = {c.cid: {"n": 0, "claim": 0, "det": 0, "iou": [], "f1": []} for c in FROZEN}
    psnrs, clean_claims = [], 0
    j100_claim = j95_claim = j90_claim = 0
    n1_claim = 0

    for i, (rgb, mask, _ident) in enumerate(images):
        marked = embed(rgb)
        mse = float(np.mean((marked.astype(float) - rgb.astype(float)) ** 2))
        psnrs.append(99.0 if mse == 0 else 10 * np.log10(255.0 ** 2 / mse))

        clean_claims += int(detect(marked).any())

        buf = io.BytesIO()
        Image.fromarray(marked).save(buf, "PNG")
        png = buf.getvalue()

        for q in (100, 95, 90):
            d = detect(np.array(Image.open(io.BytesIO(jpeg(png, q))).convert("RGB")))
            if q == 100:
                j100_claim += int(d.any())
            elif q == 95:
                j95_claim += int(d.any())
            else:
                j90_claim += int(d.any())

        noisy = np.clip(np.rint(marked.astype(float)
                               + np.random.default_rng(i).normal(0, 1.0, marked.shape)),
                        0, 255).astype(np.uint8)
        d = detect(noisy)
        n1_claim += int(d.any())

        for cond in FROZEN:
            data, gt = cond(png)
            res = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
            pred = detect(res)
            a = per[cond.cid]
            a["n"] += 1
            a["claim"] += int(pred.any())
            if gt is not None and gt.shape == pred.shape:
                a["iou"].append(float(iou(pred, gt)))
                a["det"] += int(detected(pred, gt, 0.10))
                tp = float((pred & gt).sum())
                prec = tp / max(pred.sum(), 1)
                rec = tp / max(gt.sum(), 1)
                a["f1"].append(0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec))

    n = len(images)

    def mean(v):
        return float(np.mean(v)) if v else float("nan")

    print(f"\n{args.data}  n={n}\n")
    print(f"{'#':>2} {'condition':28} {'claim%':>7} {'detect%':>8} {'IoU':>6} {'blkF1':>6}")
    for cond in FROZEN:
        a = per[cond.cid]
        print(f"{cond.cid:>2} {cond.name[:28]:28} {100*a['claim']/a['n']:7.1f} "
              f"{100*a['det']/a['n']:8.1f} {mean(a['iou']):6.3f} {mean(a['f1']):6.3f}")

    det = mean([per[c]["det"] / per[c]["n"] for c in PASTE])
    ious = mean([np.mean(per[c]["iou"]) for c in range(1, 7)])
    benign = mean([per[c]["claim"] / per[c]["n"] for c in BENIGN])
    print(f"\ndetection c1-c5 {det:.4f}   IoU c1-c6 {ious:.4f}   "
          f"benign claim {benign:.4f}   clean claims {clean_claims}/{n}   "
          f"PSNR {mean(psnrs):.2f} dB")
    print(f"JPEG Q100 {j100_claim}/{n} claimed   Q95 {j95_claim}/{n}   "
          f"Q90 {j90_claim}/{n}   noise sigma1 {n1_claim}/{n}")

    if args.receipt:
        out = Path(args.receipt)
        if str(args.receipt).endswith("/"):
            out = out / "receipt.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "kind": "baseline_lsb",
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "command": " ".join(sys.argv),
            "dataset": str(args.data),
            "n": n,
            "scheme": "Wong-style 8x8 block hash in the LSB plane",
            "code": {"git_commit": git_commit()},
            "environment": {"python": platform.python_version(),
                            "platform": platform.platform()},
            "summary": {
                "detection": det, "iou": ious, "benign_claim_rate": benign,
                "clean_claims": clean_claims, "psnr": mean(psnrs),
                "jpeg100_claim": j100_claim / n, "jpeg95_claim": j95_claim / n,
                "jpeg90_claim": j90_claim / n, "noise1_claim": n1_claim / n,
            },
            "per_condition": {
                str(c.cid): {"n": per[c.cid]["n"], "claim": per[c.cid]["claim"],
                             "det": per[c.cid]["det"],
                             "iou_mean": mean(per[c.cid]["iou"]),
                             "f1_mean": mean(per[c.cid]["f1"])}
                for c in FROZEN},
        }, indent=1))
        print(f"receipt written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
