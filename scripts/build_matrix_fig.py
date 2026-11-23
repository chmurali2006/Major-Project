"""Figure 7. Which component is carrying the result.

    python3 scripts/build_matrix_fig.py runs/ph2-v1

A horizontal bar chart of C0-C11, sorted by nothing -- kept in protocol order so
a reader can follow the arrow of addition -- with the C0 floor drawn as a line
and the C8 ceiling marked. Every value is read from a receipt.

This is the figure the study exists to produce. The field reports one aggregate
per paper; this reports twelve configurations of one system on one protocol, and
makes it possible to say which part is doing the work.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

W, H = 1500, 890
M = 70

INK = "#101010"
BODY = "#3a3a3a"
NOTE = "#6b6b6b"
RULE = "#b9b9b9"
HAIR = "#e2e2e2"
DIM = "#b9b9b9"
FULL = "#1f4e79"
CTRL = "#8a8a8a"
BAD = "#b03a2e"

SANS = "Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "SF Mono, Menlo, Consolas, monospace"

ops: list[dict] = []


def text(x, y, s, size=13, fill=INK, weight="400", anchor="start", family=SANS):
    ops.append({"op": "text", "x": x, "y": y, "s": s, "size": size, "fill": fill,
                "weight": weight, "anchor": anchor})
    esc = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    ops.append({"op": "raw", "svg":
                f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
                f'fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{esc}</text>'})


def line(x1, y1, x2, y2, color=INK, sw=1.3, dash=None):
    ops.append({"op": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "color": color, "sw": sw, "dash": dash, "head": False})
    d = f' stroke-dasharray="{dash}"' if dash else ""
    ops.append({"op": "raw", "svg":
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                f'stroke-width="{sw}"{d}/>'})


def rect(x, y, w, h, fill, stroke="none", sw=0):
    ops.append({"op": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill,
                "stroke": stroke, "sw": sw, "dash": None})
    ops.append({"op": "raw", "svg":
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
                f'stroke="{stroke}" stroke-width="{sw}"/>'})


ORDER = ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7",
         "C8", "C9", "C10", "C11"]
SHORT = {"C0": "classical only", "C1": "+ one-class AE", "C2": "+ RefineNet",
         "C3": "+ AE + RefineNet", "C4": "+ attention",
         "C5": "+ degradation", "C6": "+ segmentation",
         "C7": "+ three-way head", "C8": "full synthesis",
         "C9": "C8 minus the key", "C10": "unseen key", "C11": "held-out family"}


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "runs" / "ph2-v1"
    R = {}
    for p in sorted(src.glob("*.json")):
        r = json.loads(p.read_text())
        if isinstance(r, dict) and "config" in r:
            R[r["config"]] = r
    if not R:
        print(f"no receipts in {src}")
        return 1

    rows = [c for c in ORDER if c in R]
    c0 = R.get("C0", {}).get("iou_mean", 0.0)
    c8 = R.get("C8", {}).get("iou_mean", max(R[c]["iou_mean"] for c in rows))

    # ------------------------------------------------------------ canvas
    ops.append({"op": "raw", "svg":
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
                f'width="381mm" height="254mm" data-units="{W}x{H}">'})
    ops.append({"op": "raw", "svg":
                f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>'})

    text(M, 48, "Twelve configurations, one protocol: which component carries the result",
         20, INK, "700")
    text(M, 72,
         "Localisation IoU per configuration, same split, same tamper families, same "
         "metrics. PH2 stand-in, n = 120, 5 epochs, width 16.", 11.5, BODY)

    # ------------------------------------------------------------ plot
    PX = 330
    PY = 120
    PW = 700
    RH = 46
    XMAX = 1.0

    def sx(v):
        return PX + v * PW

    for v in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        line(sx(v), PY - 6, sx(v), PY + len(rows) * RH, HAIR, 1)
        text(sx(v), PY + len(rows) * RH + 18, f"{v:.1f}", 10.5, NOTE, "400",
             "middle", MONO)
    text(PX + PW / 2, PY + len(rows) * RH + 40, "localisation IoU", 11.5, BODY,
         "400", "middle")

    for i, cid in enumerate(rows):
        y = PY + i * RH
        v = R[cid]["iou_mean"]
        usable = R[cid].get("usable", False)
        wide = cid in ("C0", "C8")
        col = CTRL if cid == "C0" else (FULL if wide else DIM)
        rect(PX, y + 8, max(2, sx(v) - PX), RH - 20, col)
        text(PX - 12, y + RH / 2 + 5, cid, 11.5, INK, "700", "end", MONO)
        text(PX - 54, y + RH / 2 + 5, SHORT[cid], 10.8,
             INK if wide else BODY, "600" if wide else "400", "end")
        text(sx(v) + 8, y + RH / 2 + 5, f"{v:.4f}", 11, INK, "700", "start", MONO)
        if not usable:
            text(sx(v) + 70, y + RH / 2 + 5, "unusable", 9.5, BAD, "700")

    # the C0 floor
    line(sx(c0), PY - 6, sx(c0), PY + len(rows) * RH, CTRL, 1.6, dash="5 4")
    text(sx(c0), PY - 14, f"C0 floor {c0:.4f}", 10, CTRL, "700", "middle", MONO)

    # ------------------------------------------------------------ annotation
    AX = PX + PW + 90
    AW = W - M - AX
    text(AX, PY + 4, "WHAT THE ORDERING SAYS", 12, INK, "700")
    line(AX, PY + 12, AX + AW, PY + 12, INK, 1.1)

    c1 = R.get("C1", {}).get("iou_mean", 0.0)
    gain_total = c8 - c0
    gain_ae = c1 - c0
    share = gain_ae / gain_total if gain_total else 0.0

    y = PY + 34
    text(AX, y, "the one-class AE alone", 11, INK, "700")
    y += 17
    text(AX, y, f"{gain_ae:+.4f} of the {gain_total:+.4f} total", 10.8, BODY)
    y += 15
    text(AX, y, f"= {share * 100:.0f}% of the whole gain,", 10.8, BODY)
    y += 15
    text(AX, y, "from one component.", 10.8, BODY)

    y += 28
    text(AX, y, "the other six together", 11, INK, "700")
    y += 17
    text(AX, y, f"{(c8 - c1):+.4f}", 10.8, BODY)

    y += 28
    text(AX, y, "the key costs", 11, INK, "700")
    y += 17
    c9 = R.get("C9", {}).get("iou_mean", 0.0)
    text(AX, y, f"{c8 - c9:.4f} IoU (C8 vs C9)", 10.8, BODY)

    y += 32
    text(AX, y, "Two rows sit below their predecessors:", 10.2, BODY)
    y += 15
    text(AX, y, "C5 below C3, C7 below C6. At 5 epochs", 10.2, BODY)
    y += 15
    text(AX, y, "on 72 training images the ordering is", 10.2, BODY)
    y += 15
    text(AX, y, "partly optimisation noise. The matrix", 10.2, BODY)
    y += 15
    text(AX, y, "ranks components at this scale and no", 10.2, BODY)
    y += 15
    text(AX, y, "further. Re-run at convergence before", 10.2, BODY)
    y += 15
    text(AX, y, "quoting the ordering as a law.", 10.2, BODY)

    # ------------------------------------------------------------ caption
    CY = PY + len(rows) * RH + 90
    line(M, CY, W - M, CY, RULE, 1)
    text(M, CY + 24,
         "Figure 7.  Per-configuration localisation IoU.", 11.5, INK, "700")
    text(M, CY + 46,
         "Two measurements from the classical control are drawn explicitly: the C0 floor, which every learned configuration must beat to have been worth "
         "building, and C9, which removes the key and so prices the security property.", 10.5, BODY)
    text(M, CY + 62,
         "The contribution this figure makes is not that C8 is highest. It is that twelve configurations of one system, on one frozen protocol, make the "
         "individual contribution of each component visible — which a single reported aggregate cannot.", 10.5, BODY)
    text(M, CY + 78,
         "Caveats that travel with it: PH2 is a stand-in corpus; 5 epochs and 72 training images is not convergence; and no configuration is compared "
         "against a published number, because the published corpora were not run.", 10.5, BODY)

    ops.append({"op": "raw", "svg": "</svg>"})

    svg = "\n".join(o["svg"] for o in ops if o["op"] == "raw")
    out = ROOT / "docs" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "matrix.svg").write_text(svg)
    (out / "matrix.html").write_text(
        "<!doctype html><meta charset='utf-8'><style>html,body{margin:0;background:#e8e8e8;"
        "display:grid;place-items:center}svg{max-width:100%;height:auto;background:#fff;"
        "box-shadow:0 3px 30px rgba(0,0,0,.15)}</style>" + svg)

    for cid in rows:
        print(f"  {cid:4s} {R[cid]['iou_mean']:.4f}")
    print(f"\nAE share of the gain: {share * 100:.0f}%")
    print(f"wrote {out / 'matrix.svg'}")

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_ops import render                              # noqa: E402

    render(ops, W, H, str(out / "matrix.png"), str(out / "matrix.pdf"), dpi=200)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
