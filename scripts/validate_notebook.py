"""Execute every code cell of the notebook and fail on the first error.

This is the check that matters before a notebook is uploaded: a notebook that
looks right and dies on cell 9 wastes a GPU session. Running it locally in
smoke mode proves every import, every shape and every key is correct; the real
dataset only changes the images, not the plumbing.

    python scripts/validate_notebook.py [--fast]

--fast reduces the epoch counts so the validation finishes in a couple of
minutes. It does not change any code path.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks" / "keyswm_isic2019.ipynb"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", default=True)
    args = ap.parse_args()

    nb = json.loads(NB.read_text())
    cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    ns: dict = {"__name__": "__main__"}

    t_all = time.time()
    for i, cell in enumerate(cells):
        src = "".join(cell["source"])
        label = src.strip().splitlines()[0][:60]
        print(f"\n{'=' * 70}\ncell {i + 1}/{len(cells)}: {label}\n{'=' * 70}")
        t0 = time.time()
        try:
            exec(compile(src, f"<cell {i + 1}>", "exec"), ns)
        except Exception:
            traceback.print_exc()
            print(f"\nFAILED in cell {i + 1}")
            return 1
        print(f"[cell {i + 1} ok in {time.time() - t0:.1f}s]")

        # keep the local validation quick; identical code path, fewer epochs
        if args.fast and isinstance(ns.get("CFG"), dict):
            for key in ("epochs", "epochs_ae", "epochs_fusion"):
                if key in ns["CFG"]:
                    ns["CFG"][key] = min(ns["CFG"][key], 2)

    print(f"\nALL {len(cells)} CODE CELLS EXECUTED in {time.time() - t_all:.1f}s")
    receipt = ns.get("receipt")
    if receipt is not None:
        print("\nreceipt claimable:", receipt.get("claimable"))
        print("receipt mode     :", receipt.get("mode"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
