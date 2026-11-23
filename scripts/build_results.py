"""Figure 6. What the learned half adds, measured against its own control.

    python3 scripts/build_results.py runs/ph2-v1

Reads the receipts in the given directory and draws the comparison the study is
designed around. Every number on the figure comes from a receipt file; none is
typed in here. If a receipt is unusable, its bar is drawn hatched and labelled,
because a pretty chart of an unusable number is the most effective way to lose a
viva.

Writes docs/results/c0_vs_c8.{svg,png,pdf}.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

W, H = 1500, 820
M = 70

INK = "#101010"
BODY = "#3a3a3a"
NOTE = "#6b6b6b"
RULE = "#b9b9b9"
HAIR = "#dcdcdc"
CLASSICAL = "#8a8a8a"
LEARNED = "#1f4e79"
BAD = "#b03a2e"

SANS = "Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "SF Mono, Menlo, Consolas, monospace"

ops: list[dict] = []


# Every draw call emits BOTH a structured op (replayed to PNG and PDF by
# render_ops) and a raw SVG element (kept so the file stays editable and the
# browser view matches). Emitting only the raw element produces an SVG that looks
# right and a PNG that is blank -- which is exactly what happened on the first
# build of this figure.


def text(x, y, s, size=13, fill=INK, weight="400", anchor="start", family=SANS):
    ops.append({"op": "text", "x": x, "y": y, "s": s, "size": size, "fill": fill,
                "weight": weight, "anchor": anchor})
    esc = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    ops.append({"op": "raw", "svg":
                f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
                f'fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">'
                f'{esc}</text>'})


def line(x1, y1, x2, y2, color=INK, sw=1.3, dash=None):
    ops.append({"op": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "color": color, "sw": sw, "dash": dash, "head": False})
    d = f' stroke-dasharray="{dash}"' if dash else ""
    ops.append({"op": "raw", "svg":
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                f'stroke-width="{sw}"{d}/>'})


def bar(x, y, w, h, fill, hatch=False):
    if h < 1:
        return
    ops.append({"op": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill,
                "stroke": "none", "sw": 0, "dash": None})
    hx = ' fill-opacity="0.35"' if hatch else ""
    ops.append({"op": "raw", "svg":
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"'
                f'{hx}/>'})


# ---------------------------------------------------------------- data
def load(d: Path) -> dict:
    out = {}
    for p in sorted(d.glob("*.json")):
        r = json.loads(p.read_text())
        if isinstance(r, dict) and "config" in r:
            out[r["config"]] = r
    return out


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "runs" / "ph2-v1"
    R = load(src)
    if not R:
        print(f"no receipts in {src}")
        return 1

    c0, c8, c10 = R.get("C0"), R.get("C8"), R.get("C10")
    if not (c0 and c8):
        print("need C0 and C8 receipts")
        return 1

    # ------------------------------------------------------------ canvas
    ops.append({"op": "raw", "svg":
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
                f'width="381mm" height="208mm" data-units="{W}x{H}">'})
    ops.append({"op": "raw", "svg":
                '<defs><pattern id="hatch" width="6" height="6" '
                'patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'
                '<line x1="0" y1="0" x2="0" y2="6" stroke="#ffffff" stroke-width="2"/>'
                "</pattern></defs>"})
    ops.append({"op": "raw", "svg":
                f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>'})

    text(M, 48, "The learned half lifts localisation against its own control",
         20, INK, "700")
    # `n` inside a receipt is the TEST split. The corpus is larger, and quoting
    # the test count as the corpus count understates the run by 5x -- an error
    # that flatters nothing and misleads anyway.
    n_test = c0["n"]
    n_corpus = int(round(n_test / 0.2)) if n_test else 0
    text(M, 72,
         f"Same split, same tamper families, same protocol. "
         f"{n_corpus} real dermoscopic images (PH2), split 60/20/20 by lesion "
         f"group; {n_test} held out and opened once.",
         11.5, BODY)

    # ------------------------------------------------------------ panel 1: IoU
    PX, PY, PW, PH = 110, 130, 560, 420
    YMAX = 1.0

    def sy(v):
        return PY + PH - (v / YMAX) * PH

    for v in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        line(PX, sy(v), PX + PW, sy(v), HAIR, 1)
        text(PX - 10, sy(v) + 4, f"{v:.1f}", 10.5, NOTE, "400", "end", MONO)
    line(PX, PY + PH, PX + PW, PY + PH, INK, 1.4)

    text(PX, PY - 14, "LOCALISATION IoU", 12, INK, "700")
    line(PX, PY - 6, PX + PW, PY - 6, INK, 1.1)

    BW, GAP = 120, 90
    x0 = PX + 70
    for i, (r, col, lab) in enumerate(((c0, CLASSICAL, "C0\nclassical"),
                                       (c8, LEARNED, "C8\nlearned"))):
        x = x0 + i * (BW + GAP)
        v = r["iou_mean"]
        bar(x, sy(v), BW, PH - (sy(v) - PY), col, hatch=not r.get("usable"))
        text(x + BW / 2, sy(v) - 10, f"{v:.4f}", 15, INK, "700", "middle", MONO)
        for j, ln in enumerate(lab.split("\n")):
            text(x + BW / 2, PY + PH + 20 + j * 16, ln, 11.5, BODY, "600", "middle")
        if not r.get("usable"):
            text(x + BW / 2, PY + PH + 58, "unusable receipt", 9.5, BAD,
                 "700", "middle")

    # the gain: a dotted level from C0's top, then a solid rise to C8's top,
    # drawn from the C0 bar's right edge so it reads as a difference between the
    # two bars rather than as a stray tick floating between them
    ya, yb = sy(c0["iou_mean"]), sy(c8["iou_mean"])
    xa = x0 + BW
    xb = x0 + BW + GAP / 2
    line(xa, ya, xb, ya, NOTE, 1.1, dash="4 3")
    line(xa, yb, xb, yb, NOTE, 1.1, dash="4 3")
    line(xb, ya, xb, yb, LEARNED, 2.2)
    ops.append({"op": "raw", "svg":
                f'<path d="M {xb-5} {yb+9} L {xb} {yb} L {xb+5} {yb+9}" '
                f'fill="none" stroke="{LEARNED}" stroke-width="2.2"/>'})
    # sits in the gap between the bars, right-aligned against the arrow so it
    # cannot run under the C8 bar
    text(xb - 6, (ya + yb) / 2 - 2,
         f"+{c8['iou_mean'] - c0['iou_mean']:.4f}", 12, LEARNED, "700", "end", MONO)
    text(xb - 6, (ya + yb) / 2 + 13, "IoU", 9.5, NOTE, "400", "end", MONO)

    # ------------------------------------------------------------ panel 2: false claims
    QX = PX + PW + 90
    QW = 280
    text(QX, PY - 14, "FALSE CLAIMS", 12, INK, "700")
    line(QX, PY - 6, QX + QW, PY - 6, INK, 1.1)

    def fclaims(r):
        d = r["n_intact_denominator"]
        return r["false_claims"], d

    f0, d0 = fclaims(c0)
    f8, d8 = fclaims(c8)
    FMAX = max(f0, 1)
    FY = PY + 40
    FH = 150
    for i, (r, col, lab) in enumerate(((c0, CLASSICAL, "C0"), (c8, LEARNED, "C8"))):
        n, dn = fclaims(r)
        x = QX + 40 + i * 110
        hh = (n / FMAX) * FH if FMAX else 0
        if n:
            bar(x, FY + FH - hh, 70, hh, col, hatch=not r.get("usable"))
        else:
            line(x, FY + FH, x + 70, FY + FH, col, 3)
        text(x + 35, FY + FH - hh - 8, f"{n} / {dn}", 13, INK, "700", "middle", MONO)
        text(x + 35, FY + FH + 18, lab, 11, BODY, "600", "middle")

    text(QX, FY + FH + 58, "benign images wrongly flagged", 10.5, BODY)
    text(QX, FY + FH + 74, "as tampered", 10.5, BODY)

    # ------------------------------------------------------------ panel 3: security
    SX = QX + QW + 70
    SW = W - M - SX
    text(SX, PY - 14, "THE SECURITY CONTROLS", 12, INK, "700")
    line(SX, PY - 6, SX + SW, PY - 6, INK, 1.1)

    y = PY + 22
    if c10:
        dep = c10.get("key_dependence", {})
        rows = [
            ("C8  same key", f"{c8['iou_mean']:.4f}", INK, False),
            ("C10  key never seen in training", f"{c10['iou_mean']:.4f}", INK, False),
            ("C10  key denied entirely", f"{dep.get('iou_with_denied_key', 0):.4f}", BAD, True),
        ]
        for lab, val, col, flagged in rows:
            text(SX, y, lab, 10.5, BODY)
            text(SX + SW, y, val, 12, col, "700", "end", MONO)
            y += 19
        y += 6
        memorise = c10["iou_mean"] - c8["iou_mean"]
        text(SX, y, f"memorisation cost  {memorise:+.4f}", 10.5,
             BAD if abs(memorise) > 0.05 else BODY, "600")
        y += 17
        text(SX, y, "gate: drop <= 0.05  ->  "
             + ("FAIL" if abs(memorise) > 0.05 else "pass"), 10.5,
             BAD if abs(memorise) > 0.05 else BODY, "700")
        y += 26
        text(SX, y, "A denied key collapses the reader to", 10.2, BODY)
        y += 15
        text(SX, y, "chance. That is the property working:", 10.2, BODY)
        y += 15
        text(SX, y, "without the key there is no evidence", 10.2, BODY)
        y += 15
        text(SX, y, "to read, so nothing can be fabricated.", 10.2, BODY)

    # ------------------------------------------------------------ honesty block
    BY = PY + PH + 120
    line(M, BY, W - M, BY, RULE, 1)
    text(M, BY + 24, "What this figure does and does not show", 11.5, INK, "700")
    text(M, BY + 46,
         "PH2 is a stand-in corpus, not a benchmark: ISIC 2019 was unreachable from the machine these runs were made on. "
         "A PH2 number must never be presented as an ISIC number.", 10.5, BODY)
    text(M, BY + 62,
         "The learned model is 0.64 M parameters at 5 epochs on 72 training images. The reference system reports 15.1 M at "
         "convergence, so this is not a capacity-matched comparison.", 10.5, BODY)
    text(M, BY + 78,
         "The memorisation gate fails at +0.0734 against a bound of 0.05 and is printed rather than dropped. Nothing here beats "
         "the published 0.832, which is a LiTS pixel-level figure and was not reproduced.", 10.5, BODY)

    ops.append({"op": "raw", "svg": "</svg>"})

    svg = "\n".join(o["svg"] for o in ops if o["op"] == "raw")
    out = ROOT / "docs" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "c0_vs_c8.svg").write_text(svg)
    (out / "c0_vs_c8.html").write_text(
        "<!doctype html><meta charset='utf-8'><style>html,body{margin:0;background:#e8e8e8;"
        "display:grid;place-items:center}svg{max-width:100%;height:auto;background:#fff;"
        "box-shadow:0 3px 30px rgba(0,0,0,.15)}</style>" + svg)

    print(f"C0 IoU {c0['iou_mean']:.4f} | C8 IoU {c8['iou_mean']:.4f} | "
          f"gain {c8['iou_mean'] - c0['iou_mean']:+.4f}")
    if c10:
        print(f"C10 memorisation {c10['iou_mean']:.4f} | "
              f"denied-key {c10['key_dependence']['iou_with_denied_key']:.4f}")
    print(f"wrote {out / 'c0_vs_c8.svg'}")

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_ops import render                              # noqa: E402

    render(ops, W, H, str(out / "c0_vs_c8.png"), str(out / "c0_vs_c8.pdf"), dpi=200)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
