#!/usr/bin/env python
"""Per-image coverage and image quality — the distribution behind the means.

The battery receipt reports coverage averaged over conditions. That average
hides the case a reviewer cares about: the image on which the tool could only
commit to a fifth of the frame, because the mark would not fit. This prints
that distribution, worst first, so the claim "it abstains where it cannot read
the mark" can be checked image by image.

    python scripts/probe_coverage.py --data datasets/ph2 --limit 200 \
                                     --out runs/<run>/coverage.json

With no --data it runs on the synthetic phantoms, which are fixtures and not
results; the header of the output says so.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from bench import load_dataset                      # noqa: E402
from src.config import DEFAULT                      # noqa: E402
from src.fixtures import phantom_batch              # noqa: E402
from src.pipeline import System                     # noqa: E402

KEY = b"coverage-probe"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--phantoms", type=int, default=6)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if args.data:
        images = load_dataset(args.data, args.limit)
        label = args.data
    else:
        images = [(rgb, mask, f"phantom{i}") for i, (rgb, mask)
                  in enumerate(phantom_batch(args.phantoms))]
        label = "SYNTHETIC PHANTOMS — fixtures, not results"

    sysm = System(KEY, DEFAULT)
    rows = []
    for i, (rgb, mask, ident) in enumerate(images):
        p = sysm.protect(rgb, mask, image_id=1000 + i)
        clean = sysm.verify(p.png)
        mse = float(np.mean((p.rgb.astype(float) - rgb.astype(float)) ** 2))
        psnr = 99.0 if mse == 0 else 10 * np.log10(255.0 ** 2 / mse)
        rows.append({
            "image": str(ident),
            "coverage": float(clean.coverage),
            "psnr": float(psnr),
            "unmarked_blocks": int(p.refused.sum()),
            "blocks": int(p.refused.size),
        })

    rows.sort(key=lambda r: r["coverage"])
    cov = np.array([r["coverage"] for r in rows])
    psnr = np.array([r["psnr"] for r in rows])
    print(f"{label}  n={len(rows)}")
    print(f"coverage  min {cov.min():.3f}  p10 {np.percentile(cov, 10):.3f}  "
          f"median {np.median(cov):.3f}  mean {cov.mean():.3f}")
    print(f"psnr      min {psnr.min():.2f}  p10 {np.percentile(psnr, 10):.2f}  "
          f"median {np.median(psnr):.2f}  mean {psnr.mean():.2f}")
    print("\nworst ten by coverage:")
    print(f"  {'image':>16} {'coverage':>8} {'psnr':>7} {'unmarked blocks':>15}")
    for r in rows[:10]:
        print(f"  {r['image']:>16} {r['coverage']:>8.3f} {r['psnr']:>7.2f} "
              f"{r['unmarked_blocks']:>15d}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"dataset": label, "n": len(rows),
                                   "config": DEFAULT.__dict__, "rows": rows}, indent=1))
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
