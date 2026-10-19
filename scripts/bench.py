#!/usr/bin/env python3
"""Benchmark harness on synthetic phantoms.

    python scripts/bench.py --images 3 --beta 12

Every number is labelled SYNTHETIC: these phantoms are fixtures, not data, and
nothing produced here enters the thesis. The point is the harness: the same
code path will run on ISIC 2018 when the images are available.
"""
import argparse, sys, time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.battery.conditions import FROZEN
from src.config import DEFAULT, DELTA_F, BETA0
from src.fixtures import phantom
from src.metrics import block_f1, detected, iou
from src.pipeline import System
from src.ladder import TAMPERED, CANNOT_SAY, INTACT


def load_dataset(path: str, limit: int = 0):
    root = Path(path)
    img_dir, mask_dir = root / "images", root / "masks"
    if not img_dir.is_dir() or not mask_dir.is_dir():
        raise SystemExit(f"{path} needs images/ and masks/")
    out = []
    for img_path in sorted(img_dir.iterdir()):
        if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        mask_path = mask_dir / f"{img_path.stem}.png"
        if not mask_path.exists():
            continue
        rgb = np.array(Image.open(img_path).convert("RGB"))
        mask = np.array(Image.open(mask_path).convert("L")) > 127
        if rgb.shape[:2] != (512, 512):
            continue
        out.append((rgb, mask, img_path.stem))
        if limit and len(out) >= limit:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=int, default=3)
    ap.add_argument("--beta", type=float, default=BETA0)
    ap.add_argument("--delta", type=float, default=DELTA_F)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--gate", action="store_true", default=None,
                    help="force the texture gate on")
    ap.add_argument("--no-gate", action="store_true", help="falsification check 3")
    ap.add_argument("--data", type=str, default=None,
                    help="dataset dir with images/ and masks/ (e.g. datasets/ph2)")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    gate = DEFAULT.gate_enabled
    if args.gate:
        gate = True
    if args.no_gate:
        gate = False
    cfg = DEFAULT.with_(beta0=args.beta, delta_f=args.delta, gate_enabled=gate)
    sysm = System(b"bench-key", cfg)
    keys = [c.cid for c in FROZEN]

    agg = {cid: {"n": 0, "claim": 0, "iou": [], "f1": [], "cov": [], "det": 0,
                 "known": 0} for cid in keys}
    tp_t = tr_t = 0.0
    psnrs = []
    dataset = load_dataset(args.data, args.limit) if args.data else None
    n_images = len(dataset) if dataset else args.images
    for i in range(n_images):
        if dataset:
            rgb, mask, ident = dataset[i]
        else:
            rgb, mask = phantom(seed=args.seed0 + i)
            ident = i
        t0 = time.perf_counter()
        p = sysm.protect(rgb, mask, image_id=1000 + i)
        tp_t += time.perf_counter() - t0
        t0 = time.perf_counter()
        sysm.verify(p.png)
        tr_t += time.perf_counter() - t0
        mse = np.mean((p.rgb.astype(float) - rgb.astype(float)) ** 2)
        psnrs.append(99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse))
        for cond in FROZEN:
            data, gt = cond(p.png)
            res = sysm.verify(data)
            pred = res.ladder.verdict == TAMPERED
            a = agg[cond.cid]
            a["n"] += 1
            a["claim"] += int(pred.any())
            a["cov"].append(res.coverage)
            if gt is not None:
                a["known"] += 1
                a["iou"].append(iou(pred, gt))
                a["det"] += int(detected(pred, gt, cfg.iou_detect))
                a["f1"].append(block_f1(pred, gt, answered=res.ladder.verdict != CANNOT_SAY).value)
    n = n_images
    source = args.data if args.data else "SYNTHETIC PHANTOMS (fixtures, not results)"
    print(f"\n{source}  n={n}, beta={args.beta}, delta={args.delta}, gate={cfg.gate_enabled}")
    print(f"{'#':>2} {'condition':28} {'family':7} {'claim%':>7} {'detect%':>8} {'IoU':>6} {'blkF1':>6} {'cov':>6}")
    for cond in FROZEN:
        a = agg[cond.cid]
        claim = 100 * a["claim"] / a["n"]
        if a["known"]:
            det = 100 * a["det"] / a["known"]
            iou_m = float(np.mean(a["iou"]))
            f1_m = float(np.mean(a["f1"]))
            print(f"{cond.cid:>2} {cond.name:28} {cond.family:7} {claim:>7.1f} {det:>8.1f} "
                  f"{iou_m:>6.3f} {f1_m:>6.3f} {np.mean(a['cov']):>6.3f}")
        else:
            flag = "  <-- VIOLATION" if claim > 0 else ""
            print(f"{cond.cid:>2} {cond.name:28} {cond.family:7} {claim:>7.1f} {'-':>8} "
                  f"{'-':>6} {'-':>6} {np.mean(a['cov']):>6.3f}{flag}")
    print(f"\nPSNR {np.mean(psnrs):.2f} dB (worst {np.min(psnrs):.2f})   "
          f"protect {1000*tp_t/n:.0f} ms/img   verify {1000*tr_t/n:.0f} ms/img")


if __name__ == "__main__":
    main()
