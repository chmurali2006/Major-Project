# Historical classical implementation retained from dev; not protocol v2.
"""Metrics, implemented once and imported everywhere.

Every number leaves this module with its denominator attached (Trap 12) and,
where it is an accuracy, next to its coverage (Trap 11/17). Nothing here knows
what a "good" value is; that is the battery sheet's job.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Rate:
    value: float
    n: int
    denominator: str

    def __str__(self) -> str:
        return f"{self.value:.4f} (n={self.n}, {self.denominator})"


def block_confusion(pred: np.ndarray, gt: np.ndarray) -> tuple[int, int, int]:
    pred = np.asarray(pred, bool).ravel()
    gt = np.asarray(gt, bool).ravel()
    tp = int((pred & gt).sum())
    fp = int((pred & ~gt).sum())
    fn = int((~pred & gt).sum())
    return tp, fp, fn


def block_f1(pred: np.ndarray, gt: np.ndarray, answered: np.ndarray | None = None,
             denominator: str = "all") -> Rate:
    """Block-F1 with the denominator stated.

    denominator:
      'all'      every block in the image
      'attacked' union of predicted and ground-truth blocks
      'answered' blocks the system did not abstain on
    """
    pred = np.asarray(pred, bool)
    gt = np.asarray(gt, bool)
    if answered is not None:
        answered = np.asarray(answered, bool)
        if denominator == "answered":
            pred, gt = pred & answered, gt & answered
            n = int(answered.sum())
        elif denominator == "attacked":
            keep = pred | gt
            pred, gt = pred & keep, gt & keep
            n = int(keep.sum())
        else:
            n = pred.size
    else:
        n = pred.size if denominator == "all" else int((pred | gt).sum())

    tp, fp, fn = block_confusion(pred, gt)
    if tp == 0:
        return Rate(0.0, n, denominator)
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    return Rate(2 * precision * recall / (precision + recall), n, denominator)


def iou(pred: np.ndarray, gt: np.ndarray) -> float:
    pred = np.asarray(pred, bool)
    gt = np.asarray(gt, bool)
    union = int((pred | gt).sum())
    if union == 0:
        return 1.0
    return float((pred & gt).sum() / union)


def detected(pred: np.ndarray, gt: np.ndarray, iou_threshold: float) -> bool:
    """The detection rule, fixed before results (Trap 16)."""
    return iou(pred, gt) >= iou_threshold


def false_positive_rate(pred: np.ndarray, gt: np.ndarray) -> Rate:
    """Fraction of images with a tamper claim when there is no tampering."""
    assert not np.asarray(gt, bool).any(), "FPR is only defined without ground truth"
    claim = bool(np.asarray(pred, bool).any())
    return Rate(float(claim), 1, "image")


def coverage(verdict: np.ndarray, code_cannot_say: int = 2) -> float:
    return float((np.asarray(verdict) != code_cannot_say).mean())


def fragility_ratio(semantic_sr: np.ndarray, benign_sr: np.ndarray) -> float:
    """rho, per the dossier: semantic response over routine-handling response."""
    a = float(np.mean(semantic_sr))
    b = float(np.mean(benign_sr))
    return float("inf") if b == 0 else a / b


def bootstrap_ci(values: np.ndarray, stat=np.mean, n: int = 2000,
                 seed: int = 20261019, alpha: float = 0.05) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    v = np.asarray(values, float)
    if v.size == 0:
        return (float("nan"), float("nan"))
    draws = rng.choice(v, size=(n, v.size), replace=True)
    stats = stat(draws, axis=1)
    return (float(np.quantile(stats, alpha / 2)), float(np.quantile(stats, 1 - alpha / 2)))
