"""Figures for the review: the battery at a glance, and what a verdict looks like.

Both are generated from artefacts that already exist - a bench receipt and the
dataset - so no number in a figure can drift from a number in a receipt.

    python scripts/make_figures.py --receipt runs/<run>/receipt.json \\
                                   --data /path/to/ph2 --out docs/figures
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from src.battery.conditions import BY_ID, FROZEN
from src.config import DEFAULT
from src.pipeline import System
from src.ladder import CANNOT_SAY, TAMPERED

BARS = {"detection": 0.976, "iou": 0.832}

FAMILY_COLOUR = {"paste": "#2f6f4e", "structure": "#8a5a12",
                 "benign": "#8a8a8a", "degrade": "#8a8a8a"}


def summarise(receipt: dict):
    res = receipt["results"]
    rows = []
    for cond in FROZEN:
        a = res["per_condition"][str(cond.cid)]
        row = {"cid": cond.cid, "name": cond.name, "family": cond.family,
               "claim": a["claim"] / a["n"], "coverage": float(np.mean(a["cov"]))}
        if a["known"]:
            row["detection"] = a["det"] / a["known"]
            row["iou"] = float(np.mean(a["iou"]))
            row["silent"] = a["silent"] / a["n"]
        rows.append(row)
    return res, rows


def battery_figure(receipt: dict, out: Path):
    res, rows = summarise(receipt)
    scored = [r for r in rows if "detection" in r]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 6.2),
                             gridspec_kw={"width_ratios": [2.1, 1.0, 0.9]})
    y = np.arange(len(scored))[::-1]

    ax = axes[0]
    vals = [100 * r["detection"] for r in scored]
    ax.barh(y, vals, color=[FAMILY_COLOUR[r["family"]] for r in scored], height=0.62)
    ax.axvline(100 * BARS["detection"], color="#b02020", lw=1.4, ls="--")
    ax.text(100 * BARS["detection"] - 1.5, y[0] + 1.15, "bar 97.6%", ha="right",
            va="bottom", color="#b02020", fontsize=8)
    ax.set_yticks(y, [f'{r["cid"]:>2}  {r["name"]}' for r in scored], fontsize=7.5)
    ax.set_xlim(0, 105)
    ax.set_xlabel("images detected (IoU $\\geq$ 0.10), %")
    ax.set_title("Detection", fontsize=10, loc="left")
    ax.grid(axis="x", alpha=0.25)

    ax = axes[1]
    ax.barh(y, [r["iou"] for r in scored],
            color=[FAMILY_COLOUR[r["family"]] for r in scored], height=0.62)
    ax.axvline(BARS["iou"], color="#b02020", lw=1.4, ls="--")
    ax.set_yticks([]);
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("IoU")
    ax.set_title("Localisation", fontsize=10, loc="left")
    ax.grid(axis="x", alpha=0.25)

    ax = axes[2]
    ax.scatter([r["coverage"] for r in scored], y, s=16,
               color=[FAMILY_COLOUR[r["family"]] for r in scored])
    ax.set_yticks([]);
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("coverage")
    ax.set_title("Answers, not abstentions", fontsize=10, loc="left")
    ax.grid(axis="x", alpha=0.25)

    b = receipt["bars"]["values"]
    fig.suptitle(
        f"PH2 n={res['n_images']} · 22 frozen conditions · "
        f"detection {100*b['detection']:.1f}% (bar 97.6) · IoU {b['iou']:.3f} (bar 0.832) · "
        f"benign claims {100*b['benign_claim_rate']:.2f}% (bar 0.5) · "
        f"PSNR {b['psnr']:.2f} dB · verify {b['verify_ms']:.1f} ms",
        fontsize=9.5, y=0.985)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.savefig(out, dpi=170)
    plt.close(fig)


def localisation_figure(data: Path, out: Path, image_names: list[str], cid: int,
                        key: bytes, image_id0: int = 5000):
    sysm = System(key, DEFAULT)
    n = len(image_names)
    fig, axes = plt.subplots(n, 3, figsize=(9.6, 3.25 * n))
    if n == 1:
        axes = axes[None, :]
    for row, name in enumerate(image_names):
        rgb = np.array(Image.open(data / "images" / f"{name}.jpg").convert("RGB"))
        mask = np.array(Image.open(data / "masks" / f"{name}.png").convert("L")) > 127
        p = sysm.protect(rgb, mask, image_id=image_id0 + row)
        forged, gt = BY_ID[cid](p.png)
        res = sysm.verify(forged)
        shown = np.array(Image.open(__import__("io").BytesIO(forged)).convert("RGB"))
        overlay = shown.copy()
        tam = res.ladder.verdict == TAMPERED
        abst = res.ladder.verdict == CANNOT_SAY
        # The ladder works on the block grid; the picture is per pixel.
        def to_pixels(mask):
            b = shown.shape[0] // mask.shape[0]
            return np.repeat(np.repeat(mask, b, axis=0), b, axis=1)
        tam_px, abst_px = to_pixels(tam), to_pixels(abst)
        overlay[tam_px] = (0.55 * overlay[tam_px] + 0.45 * np.array([220, 30, 30])).astype(np.uint8)
        overlay[abst_px] = (0.75 * overlay[abst_px] + 0.25 * np.array([170, 170, 170])).astype(np.uint8)
        panels = [(shown, "protected + condition %d" % cid),
                  (overlay, f"verdict: {int(tam.sum())} tampered, {int(abst.sum())} abstain"),
                  (to_pixels(gt)[..., None].repeat(3, axis=2) * np.uint8(255), "ground truth")]
        for col, (img, title) in enumerate(panels):
            axes[row, col].imshow(img)
            axes[row, col].set_xticks([]);
            axes[row, col].set_yticks([])
            if row == 0:
                axes[row, col].set_title(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--data", default="")
    ap.add_argument("--out", default="docs/figures")
    ap.add_argument("--images", default="IMD002,IMD003")
    ap.add_argument("--condition", type=int, default=22)
    ap.add_argument("--key", default="figure-key")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    receipt = json.loads(Path(args.receipt).read_text())
    battery_figure(receipt, out / "battery.png")
    print("wrote", out / "battery.png")
    if args.data:
        localisation_figure(Path(args.data), out / "localisation.png",
                            args.images.split(","), args.condition,
                            args.key.encode())
        print("wrote", out / "localisation.png")


if __name__ == "__main__":
    main()
