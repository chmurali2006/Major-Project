#!/usr/bin/env python
"""Falsification checks: break one mechanism, watch the claim it supports fail.

Dossier §19. Each ablation changes the **embedder** as well as the verifier -
an ablation that only changes the reader proves nothing, because the mark it
is reading was written by the unablated encoder.

A falsification check passes when removing a mechanism makes the battery fail
in the way the design predicts. It fails when the removal changes nothing:
that would mean the mechanism is decoration.

    python scripts/ablate.py --data datasets/ph2 --limit 6
"""

from __future__ import annotations

import argparse
import io
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from bench import detected, iou, load_dataset          # noqa: E402
from src.battery.conditions import FROZEN              # noqa: E402
from src.config import DEFAULT                         # noqa: E402
from src.pipeline import System                        # noqa: E402
from src.container import field_mask, png_bytes, png_text, recover_luma  # noqa: E402

KEY = b"falsification-key"


def jpeg(data: bytes, quality: int) -> bytes:
    """Re-encode at a fixed quality and read back into the same container.

    This is not one of the frozen 22. It is here because the battery's JPEG
    conditions are all Q <= 90, where the mark dies everywhere and the
    attenuation rule abstains; a high-quality re-encode breaks only a few per
    cent of blocks and used to be reported as tampering on 196 of 200 images.
    A mechanism that fixes that has to be falsifiable, so the probe lives in
    the falsification harness rather than in a one-off script (A-031).
    """
    from PIL import Image
    rgb = np.array(Image.open(io.BytesIO(data)).convert("RGB"))
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "JPEG", quality=quality, subsampling=0)
    back = np.array(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
    return png_bytes(back, text=png_text(data))

PASTE = (1, 2, 3, 4, 5)
BENIGN = (7, 8, 9, 10, 11)  # sample-preserving handling; sigma=1 included
                            # because A-021 makes the tool abstain on it


def run_variant(rgb, mask, image_id, overrides, conds):
    """Protect once, then run the requested conditions. Returns metrics."""
    overrides = {k: v for k, v in overrides.items() if not k.startswith("_")}
    cfg = DEFAULT.with_(**overrides)
    sysm = System(KEY, cfg)
    p = sysm.protect(rgb, mask, image_id=image_id)

    mse = float(np.mean((p.rgb.astype(float) - rgb.astype(float)) ** 2))
    psnr = 99.0 if mse == 0 else 10 * np.log10(255.0 ** 2 / mse)
    clean = sysm.verify(p.png)

    # Integrity assertions about blocks that carry no mark at all. This is the
    # honesty metric: a white surround block can never be authenticated, so
    # any verdict other than CANNOT_SAY there is a claim the tool cannot back.
    true_field = field_mask(recover_luma(p.rgb))
    decided_field = (clean.ladder.verdict != 2) & true_field

    out = {"clean_claim": int(clean.ladder.verdict.max() == 1),
           "clean_coverage": clean.coverage,
           "surround_verdicts": float(decided_field.mean()),
           "psnr": psnr,
           "refusal": p.refusal_rate}

    reencoded = sysm.verify(jpeg(p.png, 100))
    out["jpeg100_claim"] = int((reencoded.ladder.verdict == 1).any())
    out["jpeg100_coverage"] = reencoded.coverage

    for cond in FROZEN:
        if cond.cid not in conds:
            continue
        data, gt = cond(p.png)
        res = sysm.verify(data)
        pred = res.ladder.verdict == 1
        row = {"claim": int(pred.any()), "coverage": res.coverage}
        if gt is not None:
            row["iou"] = float(iou(pred, gt))
            row["det"] = int(detected(pred, gt, cfg.iou_detect))
        out[cond.cid] = row
    return out


def summarise(rows, conds):
    agg = {}
    paste = [cid for cid in PASTE if cid in conds]
    if paste:
        agg["det"] = float(np.mean([r[cid]["det"] for r in rows for cid in paste]))
        agg["iou"] = float(np.mean([r[cid]["iou"] for r in rows for cid in paste]))
        agg["paste_claim"] = float(np.mean([r[cid]["claim"] for r in rows for cid in paste]))
    benign = [cid for cid in BENIGN if cid in conds]
    if benign:
        agg["benign_claim"] = float(np.mean([r[cid]["claim"] for r in rows for cid in benign]))
    if 6 in conds:
        agg["cond6_claim"] = float(np.mean([r[6]["claim"] for r in rows]))
    if 11 in conds:
        agg["resize_claim"] = float(np.mean([r[11]["claim"] for r in rows]))
    if 21 in conds:
        agg["cond21_iou"] = float(np.mean([r[21]["iou"] for r in rows]))
    agg["jpeg100_claim"] = float(np.mean([r["jpeg100_claim"] for r in rows]))
    agg["jpeg100_coverage"] = float(np.mean([r["jpeg100_coverage"] for r in rows]))
    agg["clean_claim"] = float(np.mean([r["clean_claim"] for r in rows]))
    agg["psnr"] = float(np.mean([r["psnr"] for r in rows]))
    agg["coverage"] = float(np.mean([r["clean_coverage"] for r in rows]))
    agg["surround_verdicts"] = float(np.mean([r["surround_verdicts"] for r in rows]))
    agg["refusal"] = float(np.mean([r["refusal"] for r in rows]))
    return agg


# Each entry: name, overrides, the metric it must move, the direction, and the
# sentence the design would be wrong about if the metric does not move.
ABLATIONS = [
    ("A1 binding cut", {"bind_address": False}, "det", "drop",
     "If copy-move detection survives without the address in the tag, position "
     "binding is not what defeats copy-move and contribution one is false."),
    ("A2 corroboration cut", {"use_robust": False}, "cond6_claim", "change",
     "If removing Carrier B changes nothing, the semi-robust reference is "
     "decoration and the two-carrier rule is one bit wearing a second hat."),
    ("A3 capacity refusal removed", {"field_excuse": False, "window_min": 0.0,
                                     "_eps": 0.001}, "surround_verdicts", "rise",
     "If the tool still refuses to judge blocks it never marked, the capacity "
     "refusal is not doing any work."),
    ("A4 tilt restored", {"lam": 1.0}, "psnr", "drop",
     "If restoring region weighting costs no measurable image quality, the "
     "decision to remove it (A-018) was not buying anything either."),
    ("A6 global attenuation cut", {"use_attenuation": False}, "resize_claim", "rise",
     "If a 90% resize of a smooth image still does not produce a false claim "
     "without the attenuation rule, the rule is not what fixes condition 11."),
    ("A5 ladder collapsed", {"tau_area": 1.0}, "benign_claim", "rise",
     "If a single threshold with no abstention is equally quiet on benign "
     "handling, the ladder earns its complexity nowhere."),
    ("A7 mean binding cut", {"dc_bind": False}, "cond21_iou", "drop",
     "If burned-in text localises just as well without the block mean in the "
     "tag, the detail coefficients were enough and A-030 buys nothing."),
    ("A9 scatter rule cut", {"scatter_min_components": 10 ** 9}, "jpeg100_claim",
     "rise",
     "If a Q100 re-encode is still not claimed without the scatter rule, the "
     "rule is not what separates a codec's damage from surgery and A-031 is "
     "decoration."),
    ("A8 both global rules cut", {"use_attenuation": False, "tau_area": 1.0},
     "resize_claim", "rise",
     "A6 and A5 are individually redundant now that the mean binding makes a "
     "resample break every block rather than a few edge blocks. If removing "
     "BOTH still produces no false claim, there is no global-transform rule "
     "left and condition 11 is passing for an unstated reason."),
]

CONDS = (1, 2, 3, 4, 5, 6) + BENIGN + (21, 22)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--receipt", type=str, default=None)
    ap.add_argument("--smooth", type=float, default=0.0, metavar="SIGMA",
                    help="blur each image before protecting. Models ISIC-2018's "
                         "flatter images, where a benign resize breaks only a "
                         "few edge blocks and the extent rule cannot help.")
    args = ap.parse_args()

    images = load_dataset(args.data, args.limit)
    if args.smooth > 0:
        from PIL import Image, ImageFilter


        images = [(np.array(Image.fromarray(rgb).filter(
            ImageFilter.GaussianBlur(args.smooth))), mask, name)
            for rgb, mask, name in images]
    print(f"\n{args.data}  n={len(images)}  conditions {list(CONDS)}")

    results = {}
    base_rows = [run_variant(rgb, mask, 1000 + i, {}, CONDS)
                 for i, (rgb, mask, _) in enumerate(images)]
    base = summarise(base_rows, CONDS)
    results["baseline"] = base

    for name, overrides, metric, direction, claim in ABLATIONS:
        rows = [run_variant(rgb, mask, 1000 + i, overrides, CONDS)
                for i, (rgb, mask, _) in enumerate(images)]
        agg = summarise(rows, CONDS)
        results[name] = {"metrics": agg, "predicted_metric": metric,
                         "predicted_direction": direction, "claim": claim}

    hdr = (f"{'variant':30} {'det':>6} {'IoU':>6} {'paste':>6} {'benign':>7} "
           f"{'c6':>6} {'r11':>6} {'c21IoU':>7} {'j100':>6} {'clean':>6} "
           f"{'inField':>8} {'PSNR':>6} {'cov':>6}")
    print("\n" + hdr)
    print("-" * len(hdr))
    for key in ["baseline"] + [a[0] for a in ABLATIONS]:
        m = results[key]["metrics"] if key != "baseline" else results[key]
        print(f"{key:30} {m['det']:6.3f} {m['iou']:6.3f} {m['paste_claim']:6.3f} "
              f"{m['benign_claim']:7.3f} {m.get('cond6_claim', float('nan')):6.3f} "
              f"{m.get('resize_claim', float('nan')):6.3f} "
              f"{m.get('cond21_iou', float('nan')):7.3f} "
              f"{m.get('jpeg100_claim', float('nan')):6.2f} "
              f"{m['clean_claim']:6.3f} {m['surround_verdicts']:8.4f} "
              f"{m['psnr']:6.2f} {m['coverage']:6.3f}")

    print("\nFalsification verdicts")
    print("-" * 72)
    ok = 0
    for name, overrides, metric, direction, claim in ABLATIONS:
        m = results[name]["metrics"]
        b = base[metric]
        v = m[metric]
        eps = overrides.get("_eps", 0.02)
        if direction == "drop":
            moved = v < b - eps
        elif direction == "rise":
            moved = v > b + eps
        else:
            moved = abs(v - b) > eps
        ok += int(moved)
        print(f"  {name:30} {metric} {b:.4f} -> {v:.4f}  "
              f"{'MECHANISM IS LOAD-BEARING' if moved else 'NO EFFECT - finding, not failure'}")
        if not moved:
            print(f"      {claim}")
            print("      => the mechanism does not earn its place; drop it or "
                  "rewrite the claim.")
    print(f"\n  {ok}/{len(ABLATIONS)} ablations changed the battery as predicted.")

    if args.receipt:
        out = Path(args.receipt)
        if str(args.receipt).endswith("/"):
            out = out / "receipt.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                    cwd=ROOT, capture_output=True, text=True
                                    ).stdout.strip()
        except Exception:
            commit = "unknown"
        out.write_text(json.dumps({
            "kind": "falsification",
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "command": " ".join(sys.argv),
            "dataset": str(args.data),
            "n": len(images),
            "conditions": list(CONDS),
            "git_commit": commit,
            "python": platform.python_version(),
            "results": results,
            "predicted_breaks": ok,
            "ablations": len(ABLATIONS),
        }, indent=2, default=float))
        print(f"receipt written: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
