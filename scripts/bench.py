#!/usr/bin/env python3
"""Benchmark harness: one command, one table, one receipt.

    python scripts/bench.py --data datasets/isic2018 --limit 40 --receipt runs/001/receipt.json
    python scripts/bench.py --images 10            # synthetic phantoms, fixtures only

Every number this prints is also written to the receipt file: the command, the
configuration, the dataset, the per-condition counts, the environment and the
git commit. A number without a receipt does not exist (dossier §18).

Synthetic phantoms are fixtures. They are useful for finding defects and are
worthless as results; every table printed from them says so.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.battery.conditions import FROZEN
from src.config import BETA0, DEFAULT, DELTA_F
from src.fixtures import phantom
from src.ladder import CANNOT_SAY, INTACT, TAMPERED
from src.metrics import block_f1, detected, iou
from src.pipeline import System

# The paper's operating point, for context only. Cross-paper comparison is
# forbidden (Trap 21); these are the levels we hold ourselves to.
BARS = {
    "detection": ("min", 0.976),
    "iou": ("min", 0.832),
    "benign_claim_rate": ("max", 0.005),
    "psnr": ("min", 37.8),
    "verify_ms": ("max", 44.0),
}


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
    if not out:
        raise SystemExit(f"no 512x512 image/mask pairs found under {path}")
    return out


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def run(dataset, sysm, cfg, seed0: int, n_synthetic: int):
    keys = [c.cid for c in FROZEN]
    agg = {cid: {"n": 0, "claim": 0, "iou": [], "f1": [], "cov": [], "det": 0,
                 "known": 0, "silent": 0, "reasons": {}} for cid in keys}
    protect_t = verify_t = 0.0
    psnrs, coverage = [], []

    images = dataset if dataset is not None else [
        (*phantom(seed=seed0 + i), i) for i in range(n_synthetic)
    ]
    for i, (rgb, mask, _ident) in enumerate(images):
        t0 = time.perf_counter()
        p = sysm.protect(rgb, mask, image_id=1000 + i)
        protect_t += time.perf_counter() - t0

        t0 = time.perf_counter()
        sysm.verify(p.png)
        verify_t += time.perf_counter() - t0

        mse = float(np.mean((p.rgb.astype(float) - rgb.astype(float)) ** 2))
        psnrs.append(99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse))
        coverage.append(sysm.verify(p.png).coverage)

        for cond in FROZEN:
            data, gt = cond(p.png)
            res = sysm.verify(data)
            pred = res.ladder.verdict == TAMPERED
            a = agg[cond.cid]
            a["n"] += 1
            a["claim"] += int(pred.any())
            a["cov"].append(res.coverage)
            for r in np.unique(res.ladder.reason):
                a["reasons"][int(r)] = a["reasons"].get(int(r), 0) + int((res.ladder.reason == r).sum())
            if gt is not None:
                a["known"] += 1
                a["iou"].append(float(iou(pred, gt)))
                a["det"] += int(detected(pred, gt, cfg.iou_detect))
                # The safety metric. A miss is only acceptable if it is an
                # abstention; a tampered block reported INTACT is the failure
                # mode a clinical reader would act on.
                a["silent"] += int(((res.ladder.verdict == INTACT) & gt).any())
                a["f1"].append(block_f1(pred, gt, answered=res.ladder.verdict != CANNOT_SAY).value)

    n = len(images)
    return {
        "n_images": n,
        "per_condition": agg,
        "psnr_mean": float(np.mean(psnrs)),
        "psnr_worst": float(np.min(psnrs)),
        "coverage_mean": float(np.mean(coverage)),
        "protect_ms": 1000 * protect_t / n,
        "verify_ms": 1000 * verify_t / n,
    }


def summarise(res, label: str) -> dict:
    print(f"\n{label}  n={res['n_images']}")
    print(f"{'#':>2} {'condition':28} {'family':7} {'claim%':>7} {'detect%':>8} "
          f"{'IoU':>6} {'blkF1':>6} {'cov':>6} {'silent%':>8}")
    rows, violations = [], []
    for cond in FROZEN:
        a = res["per_condition"][cond.cid]
        claim = 100 * a["claim"] / a["n"]
        row = {"cid": cond.cid, "name": cond.name, "family": cond.family,
               "claim_rate": claim / 100, "n": a["n"], "coverage": float(np.mean(a["cov"]))}
        if a["known"]:
            row.update({
                "detection": a["det"] / a["known"],
                "iou": float(np.mean(a["iou"])),
                "block_f1": float(np.mean(a["f1"])),
                "n_known": a["known"],
                "silent_intact": a["silent"] / a["n"],
            })
            print(f"{cond.cid:>2} {cond.name:28} {cond.family:7} {claim:>7.1f} "
                  f"{100*row['detection']:>8.1f} {row['iou']:>6.3f} "
                  f"{row['block_f1']:>6.3f} {row['coverage']:>6.3f} "
                  f"{100*row['silent_intact']:>8.1f}")
        else:
            flag = ""
            if cond.family == "benign" and row["claim_rate"] > 0:
                flag = "  <-- VIOLATION: benign condition claimed tampering"
                violations.append({"cid": cond.cid, "name": cond.name,
                                   "kind": "benign_false_claim",
                                   "rate": row["claim_rate"]})
            print(f"{cond.cid:>2} {cond.name:28} {cond.family:7} {claim:>7.1f} "
                  f"{'-':>8} {'-':>6} {'-':>6} {row['coverage']:>6.3f} {'-':>8}{flag}")
        rows.append(row)
    print(f"\nPSNR {res['psnr_mean']:.2f} dB (worst {res['psnr_worst']:.2f})   "
          f"coverage {res['coverage_mean']:.3f}   "
          f"protect {res['protect_ms']:.0f} ms/img   verify {res['verify_ms']:.0f} ms/img")
    return {"rows": rows, "violations": violations}


def vs_bars(res, rows) -> dict:
    pastes = [r for r in rows if r["family"] == "paste" and "detection" in r]
    big = [r for r in pastes if r["cid"] in (1, 2, 3, 4, 5)]
    benign = [r for r in rows if r["family"] == "benign"]
    out = {
        "detection": float(np.mean([r["detection"] for r in big])) if big else None,
        "iou": float(np.mean([r["iou"] for r in pastes])) if pastes else None,
        "benign_claim_rate": float(np.mean([r["claim_rate"] for r in benign])) if benign else None,
        "psnr": res["psnr_mean"],
        "verify_ms": res["verify_ms"],
    }
    verdicts = {}
    for key, (direction, bar) in BARS.items():
        v = out.get(key)
        if v is None:
            verdicts[key] = "no data"
            continue
        verdicts[key] = "met" if (v >= bar if direction == "min" else v <= bar) else "NOT MET"
    print("\nAgainst the operating point (levels only, not a cross-paper comparison):")
    for key, v in out.items():
        unit = " dB" if key == "psnr" else (" ms" if key == "verify_ms" else "")
        shown = "n/a" if v is None else f"{v:.4f}{unit}" if key not in ("psnr", "verify_ms") \
            else f"{v:.2f}{unit}"
        print(f"  {key:20} {shown:>12}   target {BARS[key][0]} {BARS[key][1]}   -> {verdicts[key]}")
    return {"values": out, "verdicts": verdicts}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=int, default=3, help="synthetic phantoms to use")
    ap.add_argument("--beta", type=float, default=BETA0)
    ap.add_argument("--delta", type=float, default=DELTA_F)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--no-gate", action="store_true")
    ap.add_argument("--data", type=str, default=None, help="dir with images/ and masks/")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--key", type=str, default="bench-key")
    ap.add_argument("--receipt", type=str, default=None, help="write a JSON receipt here")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a config field, repeatable (e.g. --set lam=0)")
    args = ap.parse_args()

    gate = DEFAULT.gate_enabled
    if args.gate:
        gate = True
    if args.no_gate:
        gate = False
    overrides = {"beta0": args.beta, "delta_f": args.delta, "gate_enabled": gate}
    for item in args.set:
        key, _, raw = item.partition("=")
        key, raw = key.strip(), raw.strip()
        if not hasattr(DEFAULT, key):
            ap.error(f"unknown config field: {key}")
        current = getattr(DEFAULT, key)
        if isinstance(current, bool):
            value = raw.lower() in ("1", "true", "yes", "on")
        elif isinstance(current, int) and not isinstance(current, bool):
            value = int(raw)
        elif isinstance(current, float):
            value = float(raw)
        else:
            value = raw
        overrides[key] = value
    cfg = DEFAULT.with_(**overrides)
    sysm = System(args.key.encode(), cfg)

    dataset = load_dataset(args.data, args.limit) if args.data else None
    label = f"{args.data}" if args.data else "SYNTHETIC PHANTOMS — fixtures, not results"

    t_start = time.perf_counter()
    raw = run(dataset, sysm, cfg, args.seed0, args.images)
    summary = summarise(raw, label)
    bars = vs_bars(raw, summary["rows"])
    elapsed = time.perf_counter() - t_start

    print(f"\ntotal wall clock {elapsed:.1f} s")

    if args.receipt:
        out = Path(args.receipt)
        if str(args.receipt).endswith("/"):
            out = out / "receipt.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        receipt = {
            "kind": "benchmark",
            "labelled_as": "synthetic_fixture" if dataset is None else "measured",
            "dataset": args.data,
            "dataset_is_primary": bool(args.data and "isic" in args.data.lower()),
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "command": " ".join(sys.argv),
            "config": cfg.__dict__,
            "code": {"git_commit": git_commit()},
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "numpy": np.__version__,
                "pillow": Image.__version__,
            },
            "results": {
                "n_images": raw["n_images"],
                "psnr_mean": raw["psnr_mean"],
                "psnr_worst": raw["psnr_worst"],
                "coverage_mean": raw["coverage_mean"],
                "protect_ms": raw["protect_ms"],
                "verify_ms": raw["verify_ms"],
                "per_condition": {str(c.cid): {k: v for k, v in raw["per_condition"][c.cid].items()
                                               if k != "reasons"} for c in FROZEN},
            },
            "bars": bars,
            "violations": summary["violations"],
            "wall_clock_s": elapsed,
        }
        out.write_text(json.dumps(receipt, indent=2))
        print(f"receipt written: {out}")

    return 0 if not summary["violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
