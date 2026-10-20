#!/usr/bin/env python
"""A live demo, for the review: one image, four questions, one figure.

    python scripts/demo.py --data datasets/ph2 --image IMD002

What it shows, in order, each in about a second on a laptop:

  1. **protect** — PSNR of the protected image and what the verifier says about
     the untouched file: every block INTACT, no claim anywhere.
  2. **a lesion is removed** — Telea inpainting over part of the lesion. The
     verifier localises it; the blocks are TAMPERED with a reason.
  3. **a clone is pasted** — 32x32 copy-move from one region to another. The
     verifier localises the *destination*, because the tag names the address.
  4. **the file is recompressed** — JPEG 90. The mark is gone everywhere, so
     the tool abstains everywhere: coverage 0.000, no claim, no guess.

That fourth panel is the honest one, and it is on the same slide on purpose:
the tool's contract is bit-exact handling, and where it cannot read the mark it
says so instead of accusing.

Writes `demo.png` next to --out (default: docs/figures/demo.png) and prints a
table a reviewer can read from the back of the room.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from bench import load_dataset                      # noqa: E402
from src.battery.conditions import BY_ID            # noqa: E402
from src.config import DEFAULT                      # noqa: E402
from src.container import png_bytes, png_text       # noqa: E402
from src.ladder import CANNOT_SAY, INTACT, REASON_NAME, TAMPERED  # noqa: E402
from src.pipeline import System                     # noqa: E402

KEY = b"review-demo-key"
NAMES = {INTACT: "intact", TAMPERED: "TAMPERED", CANNOT_SAY: "cannot say"}


def jpeg(png: bytes, quality: int) -> bytes:
    rgb = np.array(Image.open(io.BytesIO(png)).convert("RGB"))
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, "JPEG", quality=quality, subsampling=0)
    back = np.array(Image.open(io.BytesIO(buf.getvalue())).convert("RGB"))
    return png_bytes(back, text=png_text(png))


def describe(label: str, res) -> dict:
    v = res.ladder.verdict
    counts = {NAMES[k]: int((v == k).sum()) for k in (INTACT, TAMPERED, CANNOT_SAY)}
    reasons = {REASON_NAME[int(r)]: int((res.ladder.reason == r).sum())
               for r in np.unique(res.ladder.reason) if REASON_NAME[int(r)] != "none"}
    print(f"  {label:28} intact {counts['intact']:5d}   tampered {counts['TAMPERED']:5d}   "
          f"cannot say {counts['cannot say']:5d}   coverage {res.coverage:.3f}")
    if reasons:
        print(f"  {'':28} reasons: " + ", ".join(f"{k} {v}" for k, v in reasons.items()))
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dir with images/ and masks/")
    ap.add_argument("--image", default="IMD002")
    ap.add_argument("--out", default="docs/figures/demo.png")
    ap.add_argument("--key", default=None)
    args = ap.parse_args()

    images = load_dataset(args.data)
    by_name = {str(name): (rgb, mask) for rgb, mask, name in images}
    stem = Path(args.image).stem
    if stem not in by_name:
        raise SystemExit(f"{stem} not in {args.data}; have {list(by_name)[:5]}...")
    rgb, mask = by_name[stem]

    sysm = System((args.key or KEY.decode()).encode(), DEFAULT)
    p = sysm.protect(rgb, mask, image_id=4242)
    mse = float(np.mean((p.rgb.astype(float) - rgb.astype(float)) ** 2))
    psnr = 10 * np.log10(255.0 ** 2 / mse) if mse else 99.0

    print(f"\n{stem}  512x512  protected at {psnr:.2f} dB, "
          f"{int(p.refused.sum())} of {p.refused.size} blocks refused (no room for a mark)\n")

    panels = []

    res_clean = sysm.verify(p.png)
    print("1. the untouched protected file")
    c = describe("verify", res_clean)
    panels.append((np.array(Image.open(io.BytesIO(p.png)).convert("RGB")),
                   res_clean, "1. untouched: all intact"))

    forged_inpaint, gt_i = BY_ID[22](p.png)
    res_i = sysm.verify(forged_inpaint)
    print("\n2. the lesion is removed (Telea inpainting)")
    c = describe("verify", res_i)
    print(f"  {int(gt_i.sum())} blocks actually changed")
    panels.append((np.array(Image.open(io.BytesIO(forged_inpaint)).convert("RGB")),
                   res_i, f"2. inpainted: {c['TAMPERED']} found"))

    forged_clone, gt_c = BY_ID[1](p.png)
    res_c = sysm.verify(forged_clone)
    print("\n3. a 32x32 patch is cloned elsewhere in the same image")
    c = describe("verify", res_c)
    print(f"  {int(gt_c.sum())} blocks actually changed")
    panels.append((np.array(Image.open(io.BytesIO(forged_clone)).convert("RGB")),
                   res_c, f"3. cloned: {c['TAMPERED']} found"))

    res_j = sysm.verify(jpeg(p.png, 90))
    print("\n4. the file was recompressed (JPEG 90) — the honest abstention")
    c = describe("verify", res_j)
    panels.append((np.array(Image.open(io.BytesIO(jpeg(p.png, 90))).convert("RGB")),
                   res_j, "4. recompressed: cannot say"))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _figure(panels, rgb, out)
    print(f"\nwrote {out}")
    return 0


def _figure(panels, original, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    n = len(panels)
    fig, axes = plt.subplots(2, n, figsize=(3.1 * n, 6.6))
    for col, (img, res, title) in enumerate(panels):
        v = res.ladder.verdict
        b = img.shape[0] // v.shape[0]
        tam = np.repeat(np.repeat(v == TAMPERED, b, 0), b, 1)
        abst = np.repeat(np.repeat(v == CANNOT_SAY, b, 0), b, 1)

        axes[0, col].imshow(img)
        axes[0, col].set_title(title, fontsize=10)
        axes[0, col].set_xticks([]); axes[0, col].set_yticks([])

        over = img.copy()
        over[tam] = (0.45 * over[tam] + 0.55 * np.array([210, 30, 30])).astype(np.uint8)
        over[abst] = (0.80 * over[abst] + 0.20 * np.array([150, 150, 150])).astype(np.uint8)
        axes[1, col].imshow(over)
        axes[1, col].set_title(f"coverage {res.coverage:.3f}", fontsize=9)
        axes[1, col].set_xticks([]); axes[1, col].set_yticks([])
    handles = [Patch(facecolor="#d21e1e", label="tampered"),
               Patch(facecolor="#969696", label="cannot say"),
               Patch(facecolor="#ffffff", edgecolor="#999999", label="intact")]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=9)
    fig.suptitle("protect once, then ask four questions of the same file", fontsize=11)
    fig.tight_layout(rect=(0, 0.05, 1, 0.955), h_pad=2.6)
    fig.savefig(out, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
