"""Figure 1. System architecture, drawn in the register of a paper figure.

    python3 scripts/build_architecture.py

Writes docs/poster/architecture.{svg,png,pdf,html}.

Design constraints, deliberately austere:

  * monochrome. One accent, used ONLY for the parts that do not exist yet.
  * hairline rules and square corners. No pastel panels, no rounded pills.
  * function names in monospace, prose in a humanist sans, sizes in three steps.
  * every block states its real call site and its real constants, read from
    src/ on origin/dev @ a794cef -- not restated from memory.
  * a figure caption at the foot, the way a journal figure carries one,
    including the limitations.

The established system is emphasised by being the only thing drawn in solid
black. The extension is grey, dashed and clearly secondary.
"""

from __future__ import annotations

import sys
from pathlib import Path

W, H = 2400, 1436
M = 60

INK = "#101010"
BODY = "#3a3a3a"
NOTE = "#6b6b6b"
RULE = "#b9b9b9"
HAIR = "#d8d8d8"
ACCENT = "#1f4e79"          # new work only
FILL_EST = "#ffffff"
FILL_NEW = "#f5f6f8"

SANS = "Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "SF Mono, Menlo, Consolas, monospace"

ops: list[dict] = []


def text(x, y, s, size=13, fill=INK, weight="400", anchor="start",
         family=SANS, spacing=None, italic=False):
    ops.append({"op": "text", "x": x, "y": y, "s": s, "size": size, "fill": fill,
                "weight": weight, "anchor": anchor, "italic": italic})
    esc = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    extra = ' font-style="italic"' if italic else ""
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    ops.append({"op": "raw", "svg":
                f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
                f'fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"'
                f'{ls}{extra}>{esc}</text>'})


def rect(x, y, w, h, fill, stroke, sw=1.4, dash=None, rx=0):
    ops.append({"op": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill,
                "stroke": stroke, "sw": sw, "dash": dash})
    d = f' stroke-dasharray="{dash}"' if dash else ""
    ops.append({"op": "raw", "svg":
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'})


def line(x1, y1, x2, y2, color=INK, sw=1.3, dash=None, head=False):
    ops.append({"op": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "color": color, "sw": sw, "dash": dash, "head": head})
    d = f' stroke-dasharray="{dash}"' if dash else ""
    mk = ' marker-end="url(#a)"' if head else ""
    ops.append({"op": "raw", "svg":
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
                f'stroke-width="{sw}"{mk}{d}/>'})


def block(x, y, w, h, title, call, lines, new=False, params=None):
    """A process block: bold step, monospace call site, prose detail, and the
    actual parameters along the foot. The parameters are the point -- a block
    diagram that does not say what the constants are is decoration."""
    stroke = ACCENT if new else INK
    rect(x, y, w, h, FILL_NEW if new else FILL_EST, stroke,
         sw=1.3, dash="6 4" if new else None)
    text(x + 12, y + 21, title, 13.5, INK, "700")
    text(x + w - 12, y + 21, call, 10.5, ACCENT if new else NOTE, "400", "end",
         family=MONO)
    line(x + 12, y + 30, x + w - 12, y + 30, HAIR, 0.9)
    for i, ln in enumerate(lines):
        text(x + 12, y + 48 + i * 16, ln, 11.2, BODY)
    if params:
        line(x + 12, y + h - 30, x + w - 12, y + h - 30, HAIR, 0.9)
        text(x + 12, y + h - 13, params, 10.2, NOTE, family=MONO)


def column_header(x, y, w, label, right=""):
    text(x, y, label, 12.5, INK, "700", spacing="1.3")
    if right:
        text(x + w, y, right, 10.5, NOTE, "400", "end", family=MONO)
    line(x, y + 8, x + w, y + 8, INK, 1.1)


# ============================================================ canvas
ops.append({"op": "raw", "svg":
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="594mm" height="406mm" data-units="{W}x{H}">'})
ops.append({"op": "raw", "svg":
            '<defs><marker id="a" viewBox="0 0 10 10" refX="8.5" refY="5" '
            'markerWidth="5.5" markerHeight="5.5" orient="auto-start-reverse">'
            f'<path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="{INK}"/></marker></defs>'})
rect(0, 0, W, H, "#ffffff", "none", sw=0)

# ============================================================ title
text(M, 56, "Keyed fragile watermarking for medical image tamper detection",
     23, INK, "700")
text(M, 80, "Left: the protection applied once at acquisition. Centre: the "
            "verification applied at every check. Right: the learned refinement, "
            "which does not yet exist.", 12.5, BODY)
line(M, 94, W - M, 94, INK, 1.6)

# ============================================================ geometry
TOP = 126
COL_W = 700
C1X = M
C2X = C1X + COL_W + 96
C3X = C2X + 760 + 96
C3W = W - M - C3X

column_header(C1X, TOP, COL_W, "PROTECT", "pipeline.protect()")
column_header(C2X, TOP, 760, "VERIFY", "pipeline.verify()")
column_header(C3X, TOP, C3W, "LEARNED REFINEMENT",
              "src/models.py")

# ============================================================ PROTECT
PY = TOP + 26
PH = 150
PG = 16
protect = [
    ("Colour transform", "split_rct()",
     ["RGB → luma, Cb, Cr; exactly invertible",
      "512 × 512 × 3 → 512 × 512 luma + 2 chroma planes"],
     "Δ = 512 · Cb, Cr at half resolution"),
    ("Semi-robust carrier", "RobustCarrier.write()",
     ["DCT band u + v ∈ [3, 6]; 22 coefficients per block",
      "address-keyed signs, β₀ = 8 · applied FIRST, so A is undisturbed"],
     "β₀ = 8 · λ_region = 0 (λ measured to buy nothing: A-018)"),
    ("Range fitting", "fit_block_luma()",
     ["legal gamut window per block; a block that cannot host the mark",
      "unshifted is refused and transmitted verbatim, never clipped"],
     "a refusal is recorded, and the verifier re-derives it from the pixels"),
    ("Tag binder", "Binder.tags()",
     ["tag = key ⊕ address ⊕ content signature ⊕ block mean",
      "60 bits per block, one per Haar detail slot"],
     "BLAKE2b(key, image_id, address) · 16-bit selector · 2^-59 per block"),
    ("Fragile carrier", "FragileCarrier.write()",
     ["QIM in Haar detail coefficients; Δ = 8, residual ±Δ/4",
      "60 slots per block · written LAST (amendment A-002)"],
     "integer Haar: the quantisation index is exactly recoverable after marking"),
    ("Container", "png_bytes()",
     ["PNG with metadata chunks: image id, key id, declared size",
      "the key id is what lets a mismatched key abstain"],
     "chunks: pff_imageid · pff_keyid · pff_size"),
]
pys = []
for i, (t, c, ls, pr) in enumerate(protect):
    y = PY + i * (PH + PG)
    pys.append(y)
    block(C1X, y, COL_W, PH, t, c, ls, params=pr)
    if i < len(protect) - 1:
        line(C1X + COL_W / 2, y + PH, C1X + COL_W / 2, y + PH + PG - 2, INK, 1.2, head=True)

# ============================================================ VERIFY
VW = 760
vy = PY
block(C2X, vy, VW, 96, "Metadata gate", "verify()",
      ["absent or mismatched key id → CANNOT SAY, reason key_mismatch",
       "a wrong key is never reported as tampering"])

v2 = vy + 96 + 18
block(C2X, v2, VW, 112, "Read both carriers", "FragileCarrier.read(), .score()",
      ["Carrier A → tag disagreement δf      Carrier B → semi-robust error δsr",
       "survival → fraction of the 60 slots still holding a readable residual"])
line(C2X + 40, vy + 96, C2X + 40, v2 - 2, INK, 1.2, head=True)

LY = v2 + 112 + 18
LH = 596
rect(C2X, LY, VW, LH, FILL_EST, INK, sw=1.3)
text(C2X + 12, LY + 22, "Decision ladder", 13.5, INK, "700")
text(C2X + VW - 12, LY + 22, "ladder.classify()", 10.5, NOTE, "400", "end", family=MONO)
text(C2X + 12, LY + 40, "4096 blocks, decided independently", 11.2, BODY)
line(C2X + 12, LY + 50, C2X + VW - 12, LY + 50, HAIR, 1)

rungs = [
    ("1", "trip table",
     "δf > τf ⇒ broken;  δf > τ_strong ⇒ decisive",
     "decisive evidence stands alone, or a single 8×8 paste is censored"),
    ("2", "neighbour corroboration",
     "weak evidence accepted only if neighbours agree",
     "applied to weak evidence only, so small edits still localise"),
    ("3", "texture context",
     "flat block ⇒ may have been refused at embed time",
     "such a block abstains (capacity_refusal) rather than being accused"),
    ("4", "erasure",
     "a normalised correlation still scores 1.0 on a deleted mark",
     "the survival test catches it; a lone erased block needs support"),
    ("5", "attenuation / scatter",
     "median tag evidence low ⇒ routine_handling",
     "≥ 12 three-by-three islands ⇒ routine_handling: a codec, not surgery"),
]
ry = LY + 62
rh = 92
for i, (n, t, a, b) in enumerate(rungs):
    y = ry + i * rh
    if i:
        line(C2X + 12, y - 8, C2X + VW - 12, y - 8, HAIR, 1)
    text(C2X + 14, y + 16, n, 10.5, NOTE, "700", family=MONO)
    text(C2X + 34, y + 16, t, 12.2, INK, "700")
    text(C2X + 34, y + 33, a, 10.8, BODY, family=MONO)
    text(C2X + 34, y + 48, b, 10.8, NOTE)

line(C2X + 12, LY + LH - 86, C2X + VW - 12, LY + LH - 86, HAIR, 1)
text(C2X + 12, LY + LH - 66, "reason codes", 10.5, INK, "700", spacing="0.6")
text(C2X + 12, LY + LH - 48,
     "routine_handling · capacity_refusal · geometry_change", 10.5, BODY, family=MONO)
text(C2X + 12, LY + LH - 32,
     "evidence_conflict · key_mismatch", 10.5, BODY, family=MONO)

VY = LY + LH + 18
block(C2X, VY, VW, 112, "Verdict", "LadderResult",
      ["per 8×8 block: INTACT · TAMPERED · CANNOT SAY",
       "each with a reason code — a verdict without a reason is a guess"])
line(C2X + 40, LY + LH, C2X + 40, VY - 2, INK, 1.2, head=True)

# ============================================================ LEARNED
ey = PY
ew = C3W
block(C3X, ey, ew, 104, "Evidence maps", "evidence.read_rich()",
      ["E, S and six per-band agreements",
       "→ 10 channels per 8×8 block"], new=True)
e2 = ey + 104 + 16
block(C3X, e2, ew, 104, "Context", "degradation.estimate()",
      ["four degradation scalars",
       "saliency head, Conv 3×3 / 5×5 / 7×7"], new=True)
e3 = e2 + 104 + 16
block(C3X, e3, ew, 104, "Refinement", "PixelRefineNet",
      ["512 → 256 → 128 → 64 → 512",
       "skips; evidence injected by nearest"], new=True)
e4 = e3 + 104 + 16
block(C3X, e4, ew, 104, "Heads", "total_loss()",
      ["pixel 512² · block 64² · three-way",
       "four terms, one objective"], new=True)
for a, b in ((ey + 104, e2), (e2 + 104, e3), (e3 + 104, e4)):
    line(C3X + ew / 2, a, C3X + ew / 2, b - 2, ACCENT, 1.1, dash="4 3", head=True)

e5 = e4 + 104 + 22
rect(C3X, e5, ew, 168, FILL_NEW, ACCENT, sw=1.1, dash="6 4")
text(C3X + 12, e5 + 22, "Why it is needed", 12, ACCENT, "700")
text(C3X + 12, e5 + 42, "A 64×64 output grid cannot express a", 11, BODY)
text(C3X + 12, e5 + 58, "boundary finer than 8 px. Measured", 11, BODY)
text(C3X + 12, e5 + 74, "ceiling on a radius-32 lesion:", 11, BODY)
text(C3X + 12, e5 + 94, "0.809 pixel IoU", 13, INK, "700", family=MONO)
text(C3X + 12, e5 + 114, "against a published bar of 0.832,", 11, BODY)
text(C3X + 12, e5 + 130, "at zero errors. The pixel head is the", 11, BODY)
text(C3X + 12, e5 + 146, "fix. No result yet.", 11, BODY)

# ---- the study matrix, in the gap beneath the refinement column
cy = e5 + 168 + 22
rect(C3X, cy, ew, 264, FILL_EST, RULE, sw=1.1)
text(C3X + 12, cy + 22, "The comparison", 12.5, INK, "700", spacing="0.8")
text(C3X + 12, cy + 38, "twelve configurations, protocol frozen before training",
     10.4, NOTE)
labels = [("C0", "classical"), ("C1", "+ AE"), ("C2", "+ RefineNet"),
          ("C3", "+ AE + Ref"),
          ("C4", "+ attention"), ("C5", "+ degradation"), ("C6", "+ segmentation"),
          ("C7", "+ 3-way head"),
          ("C8", "full synthesis"), ("C9", "key removed"), ("C10", "re-key"),
          ("C11", "held-out family")]
_cw, _cg = (ew - 24 - 3 * 6) / 4, 6
for i, (cid, lab) in enumerate(labels):
    x = C3X + 12 + (i % 4) * (_cw + _cg)
    y = cy + 52 + (i // 4) * 62
    full = cid == "C8"
    rect(x, y, _cw, 54, FILL_EST, ACCENT if full else RULE,
         sw=1.5 if full else 0.9)
    text(x + _cw / 2, y + 21, cid, 11.5, INK, "700", "middle", family=MONO)
    text(x + _cw / 2, y + 38, lab, 8.4, NOTE, "400", "middle")
text(C3X + 12, cy + 252,
     "C9 and C10 isolate whether the mark is genuinely keyed.", 10, NOTE)

# ============================================================ measured table
TY = TOP + 26 + 6 * (PH + PG) + 34
# ---- row 1: the established system, on its own corpus
text(M, TY, "MEASURED ON THE ESTABLISHED SYSTEM", 12.5, INK, "700", spacing="1.3")
text(W - M, TY, "runs/isic-full-v8/receipt.json · isic 2018 task 1 · n = 2 594 · "
                "code_dirty = false · commit 28e4e6e", 10.5, NOTE, "400", "end",
     family=MONO)
line(M, TY + 8, W - M, TY + 8, INK, 1.1)

cols = [
    ("detection", "0.99992", "12 969 / 12 970"),
    ("localisation IoU", "0.9936", "block level"),
    ("benign false claims", "0 / 12 970", "0.000"),
    ("PSNR", "40.47 dB", "mean over the run"),
    ("verify", "58.6 ms", "per 512 x 512, isolated"),
    ("a criterion that fails", "2 / 300", "0.67 % at JPEG Q100 vs a 0.5 % bound"),
]
cw = (W - 2 * M) / len(cols)
for i, (lab, val, sub) in enumerate(cols):
    x = M + i * cw
    if i:
        line(x, TY + 18, x, TY + 80, HAIR, 1)
    text(x + 14, TY + 32, lab, 10.2, NOTE, "700", spacing="0.4")
    text(x + 14, TY + 58, val, 15.5, INK, "700", family=MONO)
    text(x + 14, TY + 76, sub, 9.6, NOTE, family=MONO)

# ---- row 2: the learned half against its own control. This is the headline of
# the learned phase, and it needs no external corpus: same split, same families.
TY2 = TY + 104
text(M, TY2, "LEARNED HALF AGAINST ITS OWN CONTROL", 12.5, ACCENT, "700",
     spacing="1.3")
text(W - M, TY2, "runs/ph2-v1 · PH2 stand-in, n = 120 · split by lesion · "
                 "24 held out and opened once", 10.5, NOTE, "400", "end",
     family=MONO)
line(M, TY2 + 8, W - M, TY2 + 8, ACCENT, 1.1)

cols2 = [
    ("C0  classical", "0.5384", "IoU · 3 / 3 false claims", NOTE),
    ("C8  full synthesis", "0.8587", "IoU · 0 / 3 false claims", ACCENT),
    ("the gain", "+0.3203", "IoU, same split", ACCENT),
    ("C10  unseen key", "0.7853", "a 0.0734 drop — gate fails", "#b03a2e"),
    ("C10  key denied", "0.1047", "the property working", NOTE),
    ("params", "0.64 M", "5 epochs, 72 training images", NOTE),
]
for i, (lab, val, sub, col) in enumerate(cols2):
    x = M + i * cw
    if i:
        line(x, TY2 + 18, x, TY2 + 80, HAIR, 1)
    text(x + 14, TY2 + 32, lab, 10.2, NOTE, "700", spacing="0.4")
    text(x + 14, TY2 + 58, val, 15.5, col, "700", family=MONO)
    text(x + 14, TY2 + 76, sub, 9.6, NOTE, family=MONO)

# ============================================================ caption
CY = TY2 + 100
line(M, CY, W - M, CY, RULE, 1)
text(M, CY + 24,
     "Figure 1.  Protection and verification of a 512 × 512 dermoscopic image under "
     "a keyed, zero-training fragile watermark.",
     11.5, INK, "700")
cap = [
    "Black blocks are the system committed on `dev`, measured above. Grey dashed "
    "blocks are the learned refinement: implemented, unit-tested, and trained only in "
    "the preliminary PH2 run on the second measured row — not yet at scale.",
    "Verification takes only the container bytes and the key: no original image and no "
    "tamper mask are available to it, and the function signature enforces this.",
    "The tag is a function of the key, the block address and the block's own quantised "
    "detail coefficients, so a block pasted from elsewhere carries the tag of its old "
    "address and a block whose content changed carries the tag of its old content. "
    "A denial of the key leaves the reader no evidence to amplify: measured IoU falls "
    "from 0.8587 to 0.1047.",
    "Limitations.  0.67 % of images yield a false claim under JPEG Q100, above this "
    "project's 0.5 % bound. PH2 is a stand-in corpus, not a benchmark: ISIC 2019 was "
    "unreachable from the build machine, so no PH2 number may be read as an ISIC one. "
    "The learned model is 0.64 M parameters at 5 epochs against the reference system's "
    "15.1 M at convergence — not a capacity-matched comparison. The 0.832 IoU bar is a "
    "LiTS pixel-level figure and the 97.6 % detection figure is CheXpert; neither corpus "
    "was run, so neither number is claimed.",
]
for i, c in enumerate(cap):
    text(M, CY + 46 + i * 19, c, 10.8, BODY)

ops.append({"op": "raw", "svg": "</svg>"})

# ============================================================ emit
svg = "\n".join(o["svg"] for o in ops if o["op"] == "raw")
root = Path(__file__).resolve().parents[1]
d = root / "docs" / "poster"
d.mkdir(parents=True, exist_ok=True)
(d / "architecture.svg").write_text(svg)
(d / "architecture.html").write_text(
    "<!doctype html><meta charset='utf-8'><title>Figure 1 — system architecture</title>"
    "<style>html,body{margin:0;background:#e8e8e8;display:grid;place-items:center}"
    "svg{max-width:100%;height:auto;background:#fff;box-shadow:0 3px 30px rgba(0,0,0,.15)}"
    "</style>" + svg)
print(f"wrote {d / 'architecture.svg'}  ({len(svg) / 1024:.0f} kB)")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_ops import render                                      # noqa: E402

render(ops, W, H, str(d / "architecture.png"), str(d / "architecture.pdf"), dpi=200)
