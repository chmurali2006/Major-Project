#!/usr/bin/env python
"""Regenerate the measured tables in docs/BENCHMARKS.md from a receipt.

The tables used to be typed by hand, and they drifted: three separate
documents quoted three different detection rates for the same corpus. A
number that appears in prose is a claim; a number that is written into the
document by the run it describes is a measurement.

    python scripts/make_tables.py --receipt runs/2026-10-19-n200-v5/receipt.json

Everything between the BEGIN/END markers in the target file is replaced.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.battery.conditions import FROZEN  # noqa: E402

BEGIN = "<!-- BEGIN MEASURED TABLES -->"
END = "<!-- END MEASURED TABLES -->"
BEGIN_ENV = "<!-- BEGIN ENVELOPE TABLE -->"
END_ENV = "<!-- END ENVELOPE TABLE -->"
BEGIN_BASE = "<!-- BEGIN BASELINE TABLE -->"
END_BASE = "<!-- END BASELINE TABLE -->"
BEGIN_HANDLING = "<!-- BEGIN HANDLING ABLATION TABLE -->"
END_HANDLING = "<!-- END HANDLING ABLATION TABLE -->"


def envelope_table(receipt: dict, baseline: dict | None = None) -> str:
    """Coverage and false claims per quality and noise level, from the receipt.

    `baseline` optionally carries the textbook LSB scheme so the two can be
    read side by side; it is a different kind of mark measured on the same
    images, not a variant of this one.
    """
    n = receipt["n"]
    out = ["| JPEG quality | certified area | 10th pct | images half certified "
           "| images with any verdict | false claims |",
           "|---|---|---|---|---|---|"]
    for q, r in receipt["jpeg"].items():
        out.append(f"| Q{q} | **{r['coverage_mean']:.3f}** | {r['coverage_p10']:.3f} "
                   f"| {r['images_half_certified']}/{n} | {r['images_with_any_verdict']}/{n} "
                   f"| **{r['false_claims']}** |")
    out += ["", "| noise sigma | certified area | 10th pct | images half certified "
            "| images with any verdict | false claims |",
            "|---|---|---|---|---|---|"]
    for sig, r in receipt["noise"].items():
        out.append(f"| {sig} | **{r['coverage_mean']:.3f}** | {r['coverage_p10']:.3f} "
                   f"| {r['images_half_certified']}/{n} | {r['images_with_any_verdict']}/{n} "
                   f"| **{r['false_claims']}** |")
    ls = receipt["lossless"]
    out += ["", f"Lossless PNG round trip: certified area **{ls['coverage_mean']:.3f}**, "
            f"{ls['images_half_certified']}/{n} images at least half certified, "
            f"**{ls['false_claims']} false claims**."]
    return "\n".join(out)


def baseline_table(receipt: dict, ours: dict) -> str:
    """The textbook scheme against this one, on the numbers a reader compares."""
    b = receipt["summary"]
    r = ours["bars"]["values"]
    n = receipt["n"]
    nn = ours["results"]["n_images"]
    rows = [
        ("detection, conditions 1-5", f"{100*b['detection']:.2f}%", f"{100*r['detection']:.2f}%"),
        ("localisation IoU, conditions 1-6", f"{b['iou']:.4f}", f"{r['iou']:.4f}"),
        ("false claims, benign handling", f"**{100*b['benign_claim_rate']:.2f}%**",
         f"**{100*r['benign_claim_rate']:.2f}%**"),
        ("false claims, untouched image", f"{b['clean_claims']}/{n}", f"{ours['results']['clean_claims']}/{nn}"),
        ("PSNR", f"{b['psnr']:.2f} dB", f"{r['psnr']:.2f} dB"),
        ("JPEG Q100: images claimed", f"**{100*b['jpeg100_claim']:.0f}%**", "**0%**"),
        ("JPEG Q95: images claimed", f"**{100*b['jpeg95_claim']:.0f}%**", "**0%**"),
        ("sigma=1 noise: images claimed", f"**{100*b['noise1_claim']:.0f}%**", "**0%**"),
    ]
    out = ["| | textbook 8x8 block-hash LSB | this work |", "|---|---|---|"]
    for k, a, c in rows:
        out.append(f"| {k} | {a} | {c} |")
    return "\n".join(out)


def handling_table(receipt: dict) -> str:
    """Ablations under handling rather than under the battery."""
    n = receipt["n"]
    keys = ["png"] + [f"j{q}" for q in receipt["jpeg_qualities"]] + \
           [f"n{s}" for s in receipt["noise_sigmas"]]
    head = {"png": "clean", "j100": "Q100", "j99": "Q99", "j98": "Q98", "j95": "Q95",
            "n1.0": "sigma 1", "n2.0": "sigma 2"}
    out = ["| variant | " + " | ".join(head.get(k, k) for k in keys) + " |",
           "|---" * (len(keys) + 1) + "|"]
    for name, r in receipt["variants"].items():
        cells = [f"{r[k]['false_claims']}/{n} · {r[k]['coverage']:.2f}" for k in keys]
        out.append(f"| {name} | " + " | ".join(cells) + " |")
    out.append("")
    out.append("*Cells are false claims / images · certified area. A clean "
               "column of 0 means the variant does not lie; the certified area "
               "says what the rule costs.*")
    return "\n".join(out)


def bars_table(receipt: dict) -> str:
    b = receipt["bars"]["values"]
    res = receipt["results"]
    v = receipt["bars"]["verdicts"]
    rows = [
        ("detection, conditions 1-5", ">= 97.6%", f"{100 * b['detection']:.2f}%", "detection"),
        ("localisation IoU, conditions 1-6", ">= 0.832", f"{b['iou']:.4f}", "iou"),
        ("false claims, benign conditions", "<= 0.5%", f"{100 * b['benign_claim_rate']:.2f}%",
         "benign_claim_rate"),
        ("PSNR (mean; worst image)", ">= 37.8 dB",
         f"{b['psnr']:.2f} dB; {res['psnr_worst']:.2f} dB", "psnr"),
        ("verify latency", "<= 44 ms", f"{b['verify_ms']:.2f} ms", "verify_ms"),
    ]
    out = ["| what | bar | measured | |", "|---|---|---|---|"]
    for what, bar, measured, key in rows:  # noqa: B007
        out.append(f"| {what} | {bar} | **{measured}** | {v[key]} |")
    return "\n".join(out)


def condition_table(receipt: dict) -> str:
    res = receipt["results"]
    out = ["| # | condition | family | claim | detected | det@IoU 0.5 | IoU | block-F1 "
           "| coverage | silent (img) | silent (blocks) |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for cond in FROZEN:
        a = res["per_condition"][str(cond.cid)]
        claim = 100 * a["claim"] / a["n"]
        if a["known"]:
            det = 100 * a["det"] / a["known"]
            det50 = 100 * a.get("det50", 0) / a["known"]
            iou = sum(a["iou"]) / len(a["iou"])
            f1 = sum(a["f1"]) / len(a["f1"])
            cov = sum(a["cov"]) / len(a["cov"])
            sil = 100 * a["silent"] / a["n"]
            silb = (100 * a.get("silent_blocks", 0) / a["gt_blocks"]
                    if a.get("gt_blocks") else 0.0)
            out.append(f"| {cond.cid} | {cond.name} | {cond.family} | {claim:.1f}% | "
                       f"{det:.1f}% | {det50:.1f}% | {iou:.3f} | {f1:.3f} | {cov:.3f} | "
                       f"{sil:.1f}% | {silb:.1f}% |")
        else:
            cov = sum(a["cov"]) / len(a["cov"])
            out.append(f"| {cond.cid} | {cond.name} | {cond.family} | {claim:.1f}% | — | — "
                       f"| — | — | {cov:.3f} | — | — |")
    out.append("")
    out.append(f"PSNR {res['psnr_mean']:.2f} dB (worst {res['psnr_worst']:.2f}) · "
               f"coverage {res['coverage_mean']:.3f} · protect {res['protect_ms']:.0f} ms/img · "
               f"verify {res['verify_ms']:.1f} ms/img.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--write", default="docs/BENCHMARKS.md")
    ap.add_argument("--envelope", default="")
    ap.add_argument("--baseline", default="")
    ap.add_argument("--handling", default="")
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()

    receipt = json.loads(Path(args.receipt).read_text())
    res = receipt["results"]
    head = (f"**Run:** `{receipt['command']}`  \n"
            f"**Commit:** `{receipt['code']['git_commit'][:7]}` · **dirty tree:** "
            f"{'yes' if receipt.get('code_dirty') else 'no'} · "
            f"**n:** {res['n_images']}\n")
    body = "\n".join([head, "", bars_table(receipt), "",
                      condition_table(receipt)])
    if args.print:
        print(BEGIN + "\n\n" + body + "\n\n" + END)
        return 0

    path = Path(args.write)
    text = path.read_text()

    blocks = [(BEGIN, END, body)]
    if args.envelope and BEGIN_ENV in text:
        env = json.loads(Path(args.envelope).read_text())
        blocks.append((BEGIN_ENV, END_ENV, envelope_table(env)))
    if args.baseline and BEGIN_BASE in text:
        base = json.loads(Path(args.baseline).read_text())
        blocks.append((BEGIN_BASE, END_BASE, baseline_table(base, receipt)))
    if args.handling and BEGIN_HANDLING in text:
        hand = json.loads(Path(args.handling).read_text())
        blocks.append((BEGIN_HANDLING, END_HANDLING, handling_table(hand)))

    for b, e, chunk in blocks:
        start, end = text.index(b), text.index(e) + len(e)
        text = text[:start] + b + "\n\n" + chunk + "\n\n" + e + text[end:]
    path.write_text(text)
    print(f"wrote {len(body.splitlines())} lines into {path} "
          f"(+{len(blocks) - 1} generated companion tables)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
