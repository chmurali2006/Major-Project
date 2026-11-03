"""Validation-fitted count controls using fragile and semi-robust evidence.

Carrier B is a feature, not proof that a codec is benign. Both controls score
JPEG recompression as a tamper event under the fragile-integrity protocol.
"""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass(frozen=True)
class CountRule:
    tau: float
    k: int
    semi_weight: float = 0.0

    def maps(self, evidence):
        from .evidence import FULL_CHANNELS
        e = np.asarray(evidence)
        score = e[0].astype(float)
        if self.semi_weight:
            semi = e[FULL_CHANNELS.index('semi')].astype(float)
            score = score + self.semi_weight * np.clip(1 - semi, 0, 2)
        return score > self.tau

    def predict(self, evidence):
        mask = self.maps(evidence)
        return mask, int(mask.sum() > self.k)

    def to_dict(self):
        return asdict(self)


def fit_count_rule(samples, carrier_b=False):
    """Validation-only grid; maximise balanced accuracy, then tampered IoU."""
    from .metrics import iou
    samples = list(samples)
    labels = np.array([s.cls for s in samples])
    if not (labels == 0).any() or not (labels == 1).any():
        raise ValueError('count calibration requires intact and tampered validation cases')
    best = None
    for weight in ((0., .25, .5, 1.) if carrier_b else (0.,)):
        for tau in np.arange(.1, 2.01, .1):
            rule = CountRule(float(tau), 0, weight)
            masks = [rule.maps(s.ev) for s in samples]
            counts = np.array([m.sum() for m in masks])
            loc = np.mean([iou(m, s.gt_block) for m, s in zip(masks, samples) if s.cls])
            for k in (0, 1, 2, 4, 8, 16, 32, 64, 128, 256):
                pred = counts > k
                bal = .5 * (pred[labels == 1].mean() + (~pred[labels == 0]).mean())
                key = (float(bal), float(loc), -weight, -float(tau), -k)
                if best is None or key > best[0]:
                    best = key, CountRule(float(tau), k, weight)
    return best[1]
