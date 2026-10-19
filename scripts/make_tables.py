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
    ap.add_argument("--print", action="store_true")
    args = ap.parse_args()

    receipt = json.loads(Path(args.receipt).read_text())
    res = receipt["results"]
    head = (f"**Run:** `{receipt['command']}`  \n"
            f"**Commit:** `{receipt['code']['git_commit'][:7]}` · **dirty tree:** "
            f"{'yes' if receipt.get('code_dirty') else 'no'} · "
            f"**n:** {res['n_images']}\n")
    body = "\n".join([BEGIN, head, "", bars_table(receipt), "",
                      condition_table(receipt), END])
    if args.print:
        print(body)
        return 0

    path = Path(args.write)
    text = path.read_text()
    start, end = text.index(BEGIN), text.index(END) + len(END)
    path.write_text(text[:start] + body + text[end:])
    print(f"wrote {len(body.splitlines())} lines into {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
