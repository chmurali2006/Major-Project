#!/usr/bin/env python
"""Ablations measured under handling, not under the battery.

`ablate.py` asks whether a mechanism earns its place under the frozen 22. Four
of them do not: removing Carrier B, the capacity refusal, the ladder, or the
attenuation rule changes nothing the battery can see. The battery, though, only
contains conditions this project chose — and A-031 was found by measuring
outside it. So the same question is asked again where the battery is blind:
a sweep of high-quality re-encodes and small noise.

Either answer is a finding. If a mechanism that the battery calls decoration is
load-bearing here, the battery was too narrow and the mechanism stays. If it is
still decoration, it should be removed rather than defended.

    python scripts/ablate_envelope.py --data /tmp/ph2mirror --limit 40
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from bench import git_commit, load_dataset                       # noqa: E402
from measure_envelope import add_noise, to_jpeg                  # noqa: E402
from src.config import DEFAULT                                   # noqa: E402
from src.pipeline import System                                  # noqa: E402

KEY = b"envelope-key"
JPEGS = (100, 99, 98, 95)
SIGMAS = (1.0, 2.0)

VARIANTS = [
    ("baseline", {}),
    ("A2 no Carrier B", {"use_robust": False}),
    ("A3 no capacity refusal", {"field_excuse": False, "window_min": 0.0}),
    ("A5 no ladder", {"tau_area": 1.0}),
    ("A6 no attenuation", {"use_attenuation": False}),
    ("A8 neither global rule", {"use_attenuation": False, "tau_area": 1.0}),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--receipt", default="")
    args = ap.parse_args()

    images = load_dataset(args.data, args.limit)
    n = len(images)
    print(f"\n{args.data}  n={n}")

    col = {"png": None}
    for q in JPEGS:
        col[f"j{q}"] = None
    for s in SIGMAS:
        col[f"n{s}"] = None

    out = {}
    for name, overrides in VARIANTS:
        sysm = System(KEY, DEFAULT.with_(**overrides))
        stats = {k: {"claim": 0, "cov": []} for k in col}
        for i, (rgb, mask, _ident) in enumerate(images):
            p = sysm.protect(rgb, mask, image_id=1000 + i)
            cases = [("png", p.png)]
            cases += [(f"j{q}", to_jpeg(p.png, q)) for q in JPEGS]
            cases += [(f"n{s}", add_noise(p.png, s, seed=i)) for s in SIGMAS]
            for key, data in cases:
                res = sysm.verify(data)
                stats[key]["claim"] += int((res.ladder.verdict == 1).any())
                stats[key]["cov"].append(res.coverage)
        out[name] = {k: {"false_claims": v["claim"], "coverage": float(np.mean(v["cov"]))}
                     for k, v in stats.items()}
        print(f"  {name}")

    hdr = f"{'variant':26}" + "".join(f"{k:>12}" for k in col)
    print("\n" + hdr + "      (false claims / coverage)")
    print("-" * len(hdr))
    for name, _ in VARIANTS:
        row = f"{name:26}"
        for k in col:
            r = out[name][k]
            row += f"{r['false_claims']:>5}/{n:<4}{r['coverage']:4.2f}"
        print(row)

    print("\nRead as: a mechanism is load-bearing under handling if removing it "
          "turns a 0 into a claim rate at any quality or noise level. Coverage "
          "moving the other way is the cost of the rule.")

    if args.receipt:
        p = Path(args.receipt)
        if str(args.receipt).endswith("/"):
            p = p / "receipt.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "kind": "ablate_envelope",
            "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "command": " ".join(sys.argv),
            "dataset": str(args.data),
            "n": n,
            "jpeg_qualities": list(JPEGS),
            "noise_sigmas": list(SIGMAS),
            "code": {"git_commit": git_commit()},
            "environment": {"python": platform.python_version(),
                            "platform": platform.platform()},
            "variants": out,
        }, indent=1))
        print(f"receipt written: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
