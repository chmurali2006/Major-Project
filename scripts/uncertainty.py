#!/usr/bin/env python
"""How sure is each headline number? Bootstrap intervals over images.

Every rate in this project is a mean over 200 images, and a mean over 200
images has an uncertainty that a panel is entitled to see. This resamples the
per-image results that the receipt already stores, so no re-run is needed.

    python scripts/uncertainty.py --receipt runs/2026-10-20-n200-v7/receipt.json

Two things are reported for each metric: the point estimate and a 95%
percentile bootstrap interval over images. The interval is over *images*, which
is the unit a reviewer generalises from ("another 200 dermoscopy images"),
not over blocks (which would produce absurdly narrow intervals because blocks
within an image are strongly dependent).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

N_BOOT = 4000
SEED = 20261020
PASTE = (1, 2, 3, 4, 5)


def boot(values: np.ndarray, stat=np.mean, n: int = N_BOOT, seed: int = SEED):
    rng = np.random.default_rng(seed)
    v = np.asarray(values, float)
    if v.size == 0:
        return float("nan"), float("nan"), float("nan")
    draws = rng.choice(v, size=(n, v.size), replace=True)
    stats = stat(draws, axis=1)
    return (float(stat(v)), float(np.quantile(stats, 0.025)),
            float(np.quantile(stats, 0.975)))


def detection_matrix(receipt: dict, cids) -> np.ndarray:
    """(conditions x images) indicator: was this image detected on this one?

    The receipt stores the per-image IoU of every condition, and the detection
    rule is a fixed threshold on it, so the indicator is recoverable exactly -
    the mean over the whole matrix is the number `bench.py` prints.
    """
    iou_detect = receipt["config"]["iou_detect"]
    per = [np.asarray(receipt["results"]["per_condition"][str(c)]["iou"], float)
           for c in cids]
    return (np.vstack(per) >= iou_detect).astype(float)


def boot_matrix(m: np.ndarray, n: int = N_BOOT, seed: int = SEED):
    """Bootstrap over images (columns) of the mean over the whole matrix."""
    rng = np.random.default_rng(seed)
    cols = m.shape[1]
    draws = rng.integers(0, cols, size=(n, cols))
    stats = np.array([m[:, d].mean() for d in draws])
    return float(m.mean()), float(np.quantile(stats, 0.025)), float(np.quantile(stats, 0.975))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", required=True)
    args = ap.parse_args()

    receipt = json.loads(Path(args.receipt).read_text())
    res = receipt["results"]
    pc = res["per_condition"]

    print(f"\n{args.receipt}  n={res['n_images']}")
    print("95% percentile bootstrap over images, "
          f"{N_BOOT} resamples\n")
    print(f"{'metric':34} {'estimate':>10} {'95% CI':>20}")

    det = detection_matrix(receipt, PASTE)
    est, lo, hi = boot_matrix(det)
    print(f"{'detection, conditions 1-5':34} {100*est:9.1f}% "
          f"  [{100*lo:.1f}, {100*hi:.1f}]")
    for c in PASTE:
        est, lo, hi = boot_matrix(det[[c - 1]])
        print(f"{'  detection, condition ' + str(c):34} {100*est:9.1f}% "
              f"  [{100*lo:.1f}, {100*hi:.1f}]")

    ious = np.concatenate([np.asarray(pc[str(c)]["iou"], float)
                           for c in range(1, 7)])
    est, lo, hi = boot(ious)
    print(f"{'IoU, conditions 1-6 (pooled)':34} {est:10.4f} "
          f"  [{lo:.4f}, {hi:.4f}]")

    for c in range(1, 7):
        a = pc[str(c)]
        est, lo, hi = boot(np.asarray(a["iou"], float))
        print(f"{'  IoU, condition ' + str(c):34} {est:10.4f} "
              f"  [{lo:.4f}, {hi:.4f}]")

    # per-image benign claims are not stored, so the exact count is quoted
    total = sum(pc[str(c)]["claim"] for c in (7, 8, 9, 10, 11))
    trials = sum(pc[str(c)]["n"] for c in (7, 8, 9, 10, 11))
    print(f"{'benign false claims (exact)':34} {total:>10d} / {trials}   "
          f"rule of three upper bound {3/trials*100:.2f}%")

    clean = res.get("clean_claims")
    if clean is not None:
        print(f"{'false claims, untouched image':34} {clean:>10d} / "
              f"{res['n_images']}   rule of three upper bound "
              f"{300/res['n_images']:.2f}%")

    cov = [np.asarray(pc[str(c)]["cov"], float) for c in range(1, 7)]
    est, lo, hi = boot(np.concatenate(cov))
    print(f"{'coverage, conditions 1-6 (pooled)':34} {est:10.4f} "
          f"  [{lo:.4f}, {hi:.4f}]")

    print(f"{'PSNR (mean over images)':34} {res['psnr_mean']:10.2f} dB")

    print("\nA zero count is not a zero rate. With 0 events in n trials the")
    print("one-sided 95% upper bound is 3/n (rule of three), which is what is")
    print("quoted above; claiming 0.000% exactly would overstate the evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
