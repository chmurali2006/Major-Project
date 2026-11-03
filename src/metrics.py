"""Metrics. One implementation, used by every configuration in the matrix.

Two rules, both learned the hard way in the classical phase:

1. **Ground truth is measured, never declared.** A "tampered rectangle" is not
   ground truth. On PH2, one of condition 4's three clones landed white
   background on white background and 4 of 48 labelled blocks never changed a
   pixel. Scoring against the rectangle penalised the verifier for correctly
   reporting those blocks INTACT. `measured_mask` diffs the pixels.

2. **Every metric returns a count as well as a ratio.** An IoU of 0.0 from
   "0 of 0 blocks" and an IoU of 0.0 from "0 of 400 blocks" are different facts.
   Ratios without denominators are how a small denominator becomes a headline.
"""

from __future__ import annotations

import numpy as np

BLOCK = 8


# ---------------------------------------------------------------- masks

def measured_mask(before: np.ndarray, after: np.ndarray, block: int = BLOCK) -> np.ndarray:
    """Ground truth: blocks whose pixels actually changed.

    `before`/`after` are HxWx3 uint8 at the *received* geometry. If the geometry
    changed (crop, shift), every block of the received image is unverifiable
    content and the mask covers it entirely.
    """
    before = np.asarray(before)
    after = np.asarray(after)
    if before.shape != after.shape:
        h, w = after.shape[0] // block, after.shape[1] // block
        return np.ones((h, w), dtype=bool)
    diff = (before != after).any(axis=2)
    ny, nx = diff.shape[0] // block, diff.shape[1] // block
    return diff[:ny * block, :nx * block].reshape(ny, block, nx, block).any(axis=(1, 3))


def to_blocks(block_mask: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Upsample a block mask to pixel resolution."""
    ny, nx = block_mask.shape
    return np.repeat(np.repeat(np.asarray(block_mask, bool), BLOCK, 0), BLOCK, 1)[
        : shape[0], : shape[1]]


# ---------------------------------------------------------------- primitives

def _counts(pred: np.ndarray, gt: np.ndarray) -> tuple[int, int, int]:
    p = np.asarray(pred, bool)
    g = np.asarray(gt, bool)
    if p.shape != g.shape:
        raise ValueError(f"mask shapes differ: {p.shape} vs {g.shape}")
    tp = int((p & g).sum())
    fp = int((p & ~g).sum())
    fn = int((~p & g).sum())
    return tp, fp, fn


def iou(pred: np.ndarray, gt: np.ndarray) -> float:
    """Jaccard index. Two empty masks agree perfectly: IoU = 1.0.

    The convention matters. Treating empty-vs-empty as 0.0 would punish a
    correct abstention; treating it as 1.0 rewards a system that predicts
    nothing. Neither is right in isolation, so callers must read `counts` too.
    """
    tp, fp, fn = _counts(pred, gt)
    denom = tp + fp + fn
    return 1.0 if denom == 0 else tp / denom


def dice(pred: np.ndarray, gt: np.ndarray) -> float:
    tp, fp, fn = _counts(pred, gt)
    denom = 2 * tp + fp + fn
    return 1.0 if denom == 0 else 2 * tp / denom


def precision(pred: np.ndarray, gt: np.ndarray) -> float:
    tp, fp, _ = _counts(pred, gt)
    return 0.0 if tp + fp == 0 else tp / (tp + fp)


def recall(pred: np.ndarray, gt: np.ndarray) -> float:
    tp, _, fn = _counts(pred, gt)
    return 0.0 if tp + fn == 0 else tp / (tp + fn)


def pixel_f1(pred: np.ndarray, gt: np.ndarray) -> float:
    pr, rc = precision(pred, gt), recall(pred, gt)
    return 0.0 if pr + rc == 0 else 2 * pr * rc / (pr + rc)


def pixel_accuracy(pred: np.ndarray, gt: np.ndarray) -> float:
    p = np.asarray(pred, bool)
    g = np.asarray(gt, bool)
    if p.size == 0:
        return 1.0
    return float((p == g).mean())


def counts(pred: np.ndarray, gt: np.ndarray) -> dict[str, int]:
    tp, fp, fn = _counts(pred, gt)
    return {"tp": tp, "fp": fp, "fn": fn, "gt": int(np.asarray(gt, bool).sum()),
            "pred": int(np.asarray(pred, bool).sum())}


# ---------------------------------------------------------------- image level

def image_flagged(pred: np.ndarray, min_blocks: int = 1) -> bool:
    """Did the system raise a tamper claim at all?"""
    return int(np.asarray(pred, bool).sum()) >= min_blocks


def detection_accuracy(results: list[dict]) -> dict[str, float]:
    """Image-level detection over a list of per-image results.

    Each result: {"family": str, "kind": "tamper"|"benign", "pred": mask}.
    A tamper image is detected if any block is flagged. A benign image is a
    false positive if any block is flagged.
    """
    tamper = [r for r in results if r["kind"] == "tamper"]
    benign = [r for r in results if r["kind"] == "benign"]
    det = sum(image_flagged(r["pred"]) for r in tamper) / max(len(tamper), 1)
    fpr = sum(image_flagged(r["pred"]) for r in benign) / max(len(benign), 1)
    acc = (sum(image_flagged(r["pred"]) for r in tamper)
           + sum(not image_flagged(r["pred"]) for r in benign)) / max(len(results), 1)
    return {"detection_acc": det, "false_positive_rate": fpr, "overall_acc": acc,
            "n_tamper": len(tamper), "n_benign": len(benign)}


def benefit_at(results: list[dict], threshold: float = 0.5) -> float:
    """Fraction of tampered images localised to at least `threshold` IoU."""
    tamper = [r for r in results if r["kind"] == "tamper"]
    if not tamper:
        return 0.0
    hits = sum(iou(r["pred"], r["gt"]) >= threshold for r in tamper)
    return hits / len(tamper)


# ---------------------------------------------------------------- abstention

def selective_risk(confidence: np.ndarray, correct: np.ndarray,
                   coverages: tuple[float, ...] = (1.0, 0.9, 0.75, 0.5, 0.25, 0.1)) -> dict[str, float]:
    """Risk among the blocks the system chose to answer.

    This is the metric that makes abstention honest. A system that abstains on
    everything has coverage 0 and undefined risk — the curve shows it
    collapsing, which is the point. Report the whole curve, never one point.
    """
    conf = np.asarray(confidence, np.float64).ravel()
    ok = np.asarray(correct, bool).ravel()
    if conf.size != ok.size:
        raise ValueError("confidence and correct must be the same length")
    if conf.size == 0:
        return {f"cov_{c:.2f}": float("nan") for c in coverages}
    order = np.argsort(-conf)
    out: dict[str, float] = {}
    for c in coverages:
        k = max(1, int(round(c * conf.size)))
        sel = order[:k]
        out[f"cov_{c:.2f}"] = float(1.0 - ok[sel].mean())
    return out


def aurc(confidence: np.ndarray, correct: np.ndarray, steps: int = 50) -> float:
    """Tie-aware right-step AURC; lower is better.

    ``steps`` remains for API compatibility. Historical trapezoidal receipts
    are not numerically interchangeable with this exact attainable-coverage
    integral. Empty input retains the legacy NaN result.
    """
    from .calibration import risk_coverage
    if np.asarray(confidence).size == 0:
        return float("nan")
    return risk_coverage(confidence, correct)["aurc"]


# ---------------------------------------------------------------- aggregate

def summarise(results: list[dict]) -> dict:
    """One configuration on one corpus. Ratios with their denominators."""
    tamper = [r for r in results if r["kind"] == "tamper"]
    out_per_family: dict[str, dict] = {}
    for r in tamper:
        fam = r["family"]
        bucket = out_per_family.setdefault(fam, {"ious": [], "counts": [], "n": 0})
        bucket["ious"].append(iou(r["pred"], r["gt"]))
        bucket["counts"].append(counts(r["pred"], r["gt"]))
        bucket["n"] += 1
    per_family = {}
    for fam, b in out_per_family.items():
        tp = sum(c["tp"] for c in b["counts"])
        fp = sum(c["fp"] for c in b["counts"])
        fn = sum(c["fn"] for c in b["counts"])
        denom = tp + fp + fn
        per_family[fam] = {
            "n": b["n"],
            "iou_mean": float(np.mean(b["ious"])),
            "iou_pooled": 1.0 if denom == 0 else tp / denom,
            "tp": tp, "fp": fp, "fn": fn,
        }
    det = detection_accuracy(results)
    return {
        "detection": det,
        "benefit_at_0.5": benefit_at(results, 0.5),
        "iou_mean": float(np.mean([iou(r["pred"], r["gt"]) for r in tamper])) if tamper else 0.0,
        "per_family": per_family,
        "n_images": len(results),
    }


# ---------------------------------------------------------------- comparison guards

def block_ceiling(pixel_mask: np.ndarray, block: int = BLOCK) -> float:
    """Pixel IoU that a PERFECT block-granular detector scores on this mask.

    This is the number that decides whether a comparison is fair. An 8x8 verdict
    grid cannot express a boundary finer than 8 pixels, so for a circular lesion
    of radius 32 (1.2% of a 512x512 frame) even a flawless block classifier tops
    out at 0.809 pixel IoU. A system reporting pixel masks from a 64x64 grid
    therefore cannot reach a published pixel IoU above this ceiling, whatever
    it learns.

    Measured, circular lesions on 512x512:
        r=8   -> 0.513     r=32 -> 0.809     r=96  -> 0.930
        r=16  -> 0.692     r=48 -> 0.854     r=128 -> 0.937    r=160 -> 0.950

    Always report this beside a block-granular IoU so a shortfall is
    attributable to the architecture rather than blamed on the model.
    """
    m = np.asarray(pixel_mask, bool)
    ny, nx = m.shape[0] // block, m.shape[1] // block
    blocks = m[:ny * block, :nx * block].reshape(ny, block, nx, block).any(axis=(1, 3))
    approx = np.repeat(np.repeat(blocks, block, 0), block, 1)
    return iou(approx, m[:ny * block, :nx * block])


def disk_mask(radius: float, size: int = 512) -> np.ndarray:
    """A binary disk of the given radius, at the WORST-CASE grid placement.

    The centre is `size / 2`, which for size = 512 and block = 8 lands exactly on
    a block boundary (256 = 32 blocks). A disk straddling a boundary touches more
    blocks than one centred inside a block, so this placement maximises the
    block-approximation area and therefore MINIMISES the ceiling.

    That matters: the claim is an upper bound ("no block-granular system can
    exceed this"), and an upper bound has to be computed at the least favourable
    placement. Centring at 255.5 instead -- the block centre -- gives 0.812 at
    r = 8 rather than 0.513 and would quietly invert the argument.
    """
    yy, xx = np.mgrid[0:size, 0:size]
    c = size / 2.0
    return ((yy - c) ** 2 + (xx - c) ** 2) <= float(radius) ** 2


def disk_ceiling(radius: float, size: int = 512, block: int = BLOCK) -> float:
    """Best achievable pixel IoU for a circular region of this radius.

    This is the number the report prints beside every block-granular IoU. It
    depends only on the grid and the target size -- no model, no training, no
    dataset -- which is why it cannot be argued with.
    """
    return block_ceiling(disk_mask(radius, size), block=block)


def area_buckets(fracs, edges=(0.0, 0.005, 0.02, 0.05, 0.20, 1.01)) -> list[str]:
    """Stratify images by tampered area. IoU is strongly area-dependent, so a
    mean over a mixed set is dominated by whichever bucket is most numerous and
    says nothing about any particular scale."""
    out = []
    for f in np.asarray(fracs, np.float64):
        for lo, hi in zip(edges[:-1], edges[1:]):
            if lo <= f < hi:
                out.append(f"area_{lo:.3f}-{hi:.3f}")
                break
        else:
            out.append("area_overflow")
    return out


def stratified_iou(results: list[dict], block: int = BLOCK) -> dict[str, dict]:
    """IoU per tampered-area bucket.

    A result may carry a block mask (`gt`, `pred`), a pixel mask (`gt_pixels`),
    or a pixel prediction (`pred_pixels`). The block IoU is always reported; the
    pixel IoU only when real pixel ground truth is present, because upsampling a
    block mask to pixels and scoring it against a block mask would be a
    category error -- both sides would be the same grid.

    `ceiling` is the best pixel IoU a perfect block detector could reach on the
    pixel truth in that bucket. Quote it beside any block-granular number.
    """
    tamper = [r for r in results if r["kind"] == "tamper"]
    if not tamper:
        return {}
    has_pixels = all("gt_pixels" in r for r in tamper)
    fracs = [np.asarray(r["gt_pixels"] if has_pixels else r["gt"], bool).mean()
             for r in tamper]
    labels = area_buckets(fracs)
    out: dict[str, dict] = {}
    for lab in sorted(set(labels)):
        sel = [i for i, l in enumerate(labels) if l == lab]
        row = {
            "n": len(sel),
            "iou_block": float(np.mean([iou(tamper[i]["pred"], tamper[i]["gt"]) for i in sel])),
            "gt_area_mean": float(np.mean([fracs[i] for i in sel])),
        }
        if has_pixels:
            gp = [np.asarray(tamper[i]["gt_pixels"], bool) for i in sel]
            pp = [np.asarray(tamper[i]["pred_pixels"], bool)
                  if "pred_pixels" in tamper[i] else upsample_to(tamper[i]["pred"], gp[k].shape)
                  for k, i in enumerate(sel)]
            row["iou_pixel"] = float(np.mean([iou(pp[k], gp[k]) for k in range(len(sel))]))
            row["ceiling"] = float(np.mean([block_ceiling(gp[k], block) for k in range(len(sel))]))
        out[lab] = row
    return out


def upsample_to(block_mask: np.ndarray, shape: tuple[int, int], block: int = BLOCK
                ) -> np.ndarray:
    """Block mask -> pixel mask by box replication."""
    m = np.asarray(block_mask, bool)
    up = np.repeat(np.repeat(m, block, 0), block, 1)
    out = np.zeros(shape, bool)
    h = min(shape[0], up.shape[0])
    w = min(shape[1], up.shape[1])
    out[:h, :w] = up[:h, :w]
    return out


def measured_pixel_mask(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """Pixel-level ground truth: exactly which pixels changed.

    The block mask is what the verdict layer reasons over; the pixel mask is
    what localisation is scored on. Keeping both means the reported pixel IoU
    is a real pixel IoU and not an 8x upscale of a block decision -- which
    would be impossible to exceed the block ceiling and would look like a model
    failure when it is a measurement choice.
    """
    before = np.asarray(before)
    after = np.asarray(after)
    if before.shape != after.shape:
        return np.ones(after.shape[:2], bool)
    return (before != after).any(axis=2)
