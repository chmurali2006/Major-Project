"""Turn receipts into the tables chapter 5 needs.

    python3 scripts/report_tables.py runs/ph2-v1
    python3 scripts/report_tables.py runs/ph2-v1 --out docs/results/

Reads every `<config>.json` receipt in a directory and emits markdown. The point
is that a table in the report is generated from receipts, never typed by hand --
typing is how a number acquires a digit it never had.

Three tables:

  1. the configuration matrix, with `not run` for anything absent
  2. the stratified detail for one configuration (per diagnosis, per area bucket)
  3. the provenance block, which carries the commit hash and the dirty flag

A receipt is printed only if it is usable. Unusable receipts are listed
separately with the reason, because suppressing them would be the same
dishonesty in the other direction.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ORDER = ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7",
         "C8", "C9", "C10", "C11"]


def load(path: Path) -> dict[str, dict]:
    out = {}
    for p in sorted(path.glob("*.json")):
        try:
            r = json.loads(p.read_text())
        except Exception as exc:                      # noqa: BLE001
            print(f"  ! {p.name}: unreadable ({exc})")
            continue
        if isinstance(r, dict) and "config" in r:
            out[r["config"]] = r
    return out


def f(x, nd=4):
    return "—" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def matrix_table(receipts: dict[str, dict]) -> str:
    lines = [
        "| cfg | configuration | detection | IoU | false claims | params (M) | status |",
        "|---|---|---|---|---|---|---|",
    ]
    for cid in ORDER:
        r = receipts.get(cid)
        if r is None:
            lines.append(f"| {cid} | — | — | — | — | — | `not run` |")
            continue
        status = "ok" if r.get("usable") else "**unusable**"
        det = f"{r['detection']:.4f} ({r['detection_denominator']})"
        claims = f"{r['false_claims']} / {r['n_intact_denominator']}"
        lines.append(f"| {cid} | {r['name']} | {det} | {r['iou_mean']:.4f} | "
                     f"{claims} | {f(r.get('params_m'), 3)} | {status} |")
    return "\n".join(lines)


def strata_table(r: dict) -> str:
    out = [f"### {r['config']} — {r['name']}", ""]
    by_area = r.get("by_area") or []
    if by_area:
        out += ["| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |",
                "|---|---|---|---|---|---|"]
        for row in by_area:
            head = row["ceiling"] - row["iou"] if row.get("ceiling") else None
            tag = " *(small n)*" if row.get("small_n") else ""
            out.append(f"| {row['bucket']}{tag} | {row['n']} | "
                       f"{f(row.get('median_radius_px'), 1)} | {f(row['iou'], 3)} | "
                       f"{f(row.get('ceiling'), 3)} | {f(head, 3)} |")
        out.append("")
    by_dx = r.get("by_diagnosis") or []
    by_dx = [x for x in by_dx if x.get("n") and x.get("dx") != "UNKNOWN"]
    if by_dx:
        out += ["| diagnosis | n | IoU |", "|---|---|---|"]
        for row in by_dx:
            tag = " *(small n)*" if row.get("small_n") else ""
            out.append(f"| {row['dx']}{tag} | {row['n']} | {f(row.get('iou'), 3)} |")
        out.append("")
    if not by_area and not by_dx:
        out.append("_no stratification in this receipt_")
    return "\n".join(out)


def provenance_table(r: dict) -> str:
    p = r.get("provenance", {})
    return "\n".join([
        "| field | value |",
        "|---|---|",
        f"| config | {r['config']} — {r['name']} |",
        f"| isolates | {r.get('isolates', '—')} |",
        f"| n | {r.get('n')} (tampered {r.get('n_tampered')}, intact {r.get('n_intact')}) |",
        f"| commit | `{p.get('commit', '—')}` |",
        f"| code_dirty | {p.get('code_dirty')} |",
        f"| usable | {r.get('usable')} |",
        f"| threshold | {f(r.get('tau'), 2)} (chosen on validation) |",
        f"| wall clock | {r.get('seconds', '—')} s |",
        f"| smoke | {r.get('smoke')} |",
    ])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", type=Path)
    ap.add_argument("--out", type=Path, default=None,
                    help="write markdown here instead of stdout")
    args = ap.parse_args()

    receipts = load(args.dir)
    if not receipts:
        print(f"no receipts in {args.dir}")
        return 1

    usable = {k: v for k, v in receipts.items() if v.get("usable")}
    unusable = {k: v for k, v in receipts.items() if not v.get("usable")}

    parts = ["## The configuration matrix", "",
             matrix_table(receipts), ""]
    if unusable:
        parts += ["**Unusable receipts, and why:**", ""]
        for cid, r in sorted(unusable.items()):
            why = "; ".join(r.get("problems") or ["unspecified"])
            parts.append(f"- `{cid}` — {why}")
        parts.append("")
    for cid in ORDER:
        if cid in usable:
            parts += [strata_table(usable[cid]), ""]
    if usable:
        first = usable[sorted(usable)[0]]
        parts += ["## Provenance", "", provenance_table(first), ""]

    text = "\n".join(parts)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "tables.md").write_text(text)
        print(f"wrote {args.out / 'tables.md'}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
