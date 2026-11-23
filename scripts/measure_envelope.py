#!/usr/bin/env python
"""The tool's validity envelope: how much handling it survives before it abstains.

The battery reports that no benign condition produces a false claim. That is
true, and on its own it is a weak statement: a tool that abstains on everything
also never lies. This script measures the thing the battery's claim column
hides — **how much of the image the tool can still certify after a given amount
of ordinary handling**, and where that capacity reaches zero.

Two axes, both measured on the protected image itself, no tampering:

  * JPEG quality, re-encoded from the protected PNG and read back.
  * Additive Gaussian noise, sigma in luma levels.

and one control: the lossless PNG round trip, which must be 1.000 or nothing
downstream means anything.

    python scripts/measure_envelope.py --data datasets/ph2 --limit 200 \
                                       --receipt runs/<run>/receipt.json

The output is a curve, and the receipt carries every per-image point, so a
reviewer can recompute the curve rather than trust the figure.
"""

from __future__ import annotations

import argparse
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

from bench import git_commit, load_dataset          # noqa: E402
from src.config import DEFAULT                      # noqa: E402
from src.pipeline import System                     # noqa: E402

KEY = b"envelope-key"
JPEG_QUALITIES = (100, 99, 98, 97, 96, 95, 92, 90, 85, 80, 70, 50)
NOISE_SIGMAS = (0.0, 0.5, 1.0, 1.5, 2.0, 4.0, 8.0)


def to_jpeg(png: bytes, quality: int) -> bytes:
    rgb = np.array(Image.open(io.BytesIO(png)).convert("RGB"))
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "JPEG", quality=quality, subsampling=0)
    # Read back into the same PNG container the verifier expects; the damage
    # is the JPEG quantisation, not the file format.
    back = np.array(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
    from src.container import png_bytes, png_text
    return png_bytes(back, text=png_text(png))


def add_noise(png: bytes, sigma: float, seed: int) -> bytes:
    rgb = np.array(Image.open(io.BytesIO(png)).convert("RGB")).astype(np.float64)
    rng = np.random.default_rng(seed)
    noisy = np.clip(np.rint(rgb + rng.normal(0.0, sigma, rgb.shape)), 0, 255).astype(np.uint8)
    from src.container import png_bytes, png_text
    return png_bytes(noisy, text=png_text(png))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--receipt", default="")
    args = ap.parse_args()

    images = load_dataset(args.data, args.limit)
    sysm = System(KEY, DEFAULT)

    jpeg_rows = {q: {"coverage": [], "claim": 0, "evidence": []} for q in JPEG_QUALITIES}
    noise_rows = {s: {"coverage": [], "claim": 0, "evidence": []} for s in NOISE_SIGMAS}
    png_cov, png_claim = [], 0

    for i, (rgb, mask, _ident) in enumerate(images):
        p = sysm.protect(rgb, mask, image_id=1000 + i)

        clean = sysm.verify(p.png)
        png_cov.append(clean.coverage)
        png_claim += int((clean.ladder.verdict == 1).any())

        for q in JPEG_QUALITIES:
            res = sysm.verify(to_jpeg(p.png, q))
            jpeg_rows[q]["coverage"].append(res.coverage)
            jpeg_rows[q]["claim"] += int((res.ladder.verdict == 1).any())
            jpeg_rows[q]["evidence"].append(float(np.median(res.delta_f)))

        for s in NOISE_SIGMAS:
            data = p.png if s == 0.0 else add_noise(p.png, s, seed=i)
            res = sysm.verify(data)
            noise_rows[s]["coverage"].append(res.coverage)
            noise_rows[s]["claim"] += int((res.ladder.verdict == 1).any())
            noise_rows[s]["evidence"].append(float(np.median(res.delta_f)))

    n = len(images)

    def summarise(rows):
        return {str(k): {
            "coverage_mean": float(np.mean(v["coverage"])),
            "coverage_p10": float(np.percentile(v["coverage"], 10)),
            "images_with_any_verdict": int(sum(c > 0 for c in v["coverage"])),
            "images_half_certified": int(sum(c > 0.5 for c in v["coverage"])),
            "false_claims": int(v["claim"]),
            "median_delta_f": float(np.mean(v["evidence"])),
        } for k, v in rows.items()}

    jpeg_sum = summarise(jpeg_rows)
    noise_sum = summarise(noise_rows)

    print(f"\n{args.data}  n={n}\n")
    print(f"{'JPEG quality':>12} {'coverage':>9} {'p10':>6} {'>=50% cert':>10} "
          f"{'any verdict':>12} {'false claims':>13} {'median df':>10}")
    for q in JPEG_QUALITIES:
        r = jpeg_sum[str(q)]
        print(f"{q:>12} {r['coverage_mean']:9.3f} {r['coverage_p10']:6.3f} "
              f"{r['images_half_certified']:>4}/{n:<5} {r['images_with_any_verdict']:>6}/{n:<5} "
              f"{r['false_claims']:>13} {r['median_delta_f']:10.3f}")

    print(f"\n{'noise sigma':>12} {'coverage':>9} {'p10':>6} {'certified':>10} "
          f"{'any verdict':>12} {'false claims':>13} {'median df':>10}")
    for s in NOISE_SIGMAS:
        r = noise_sum[str(s)]
        print(f"{s:>12.1f} {r['coverage_mean']:9.3f} {r['coverage_p10']:6.3f} "
              f"{r['images_half_certified']:>4}/{n:<5} {r['images_with_any_verdict']:>6}/{n:<5} "
              f"{r['false_claims']:>13} {r['median_delta_f']:10.3f}")

    print(f"\nlossless PNG round trip: coverage {np.mean(png_cov):.3f}, "
          f"at least half certified {sum(c > 0.5 for c in png_cov)}/{n}, "
          f"false claims {png_claim}")

    if args.receipt:
        out = Path(args.receipt)
        if str(args.receipt).endswith("/") or out.suffix != ".json":
            out = out / "receipt.json" if out.suffix != ".json" else out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "kind": "envelope",
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "command": " ".join(sys.argv),
            "dataset": str(args.data),
            "n": n,
            "config": DEFAULT.__dict__,
            "code": {"git_commit": git_commit()},
            "environment": {"python": platform.python_version(),
                            "platform": platform.platform()},
            "lossless": {"coverage_mean": float(np.mean(png_cov)),
                         "images_half_certified": int(sum(c > 0.5 for c in png_cov)),
                         "false_claims": int(png_claim)},
            "jpeg": jpeg_sum,
            "noise": noise_sum,
        }, indent=1))
        print(f"receipt written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
