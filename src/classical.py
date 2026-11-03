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
    from .decision import fit_boundary
    from .metrics import upsample_to
    samples=list(samples)
    best=None
    for weight in ((0., .25, .5, 1.) if carrier_b else (0.,)):
        scores=[s.ev[0].astype(float) + weight*np.clip(1-s.ev[10],0,2) for s in samples]
        pixels=[upsample_to(b,s.gt_pixel.shape) if hasattr(s,'gt_pixel') else b
                for s,b in zip(samples,scores)]
        key,tau,k=fit_boundary(samples,scores,pixels)
        objective=key[:2]+(-weight,)+key[2:]
        if best is None or objective>best[0]: best=(objective,CountRule(tau,k,weight))
    return best[1]
