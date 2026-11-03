"""Validation-only selective verdict calibration and tie-aware risk reporting.

Confidence must be fixed independently of test labels. AURC is a ranking
metric, not a guarantee that confidence is a calibrated probability.
"""
from dataclasses import dataclass
import numpy as np


def _inputs(confidence, correct):
    c = np.asarray(confidence, dtype=float)
    y = np.asarray(correct)
    if c.ndim != 1 or y.shape != c.shape or not c.size:
        raise ValueError("expected nonempty equally sized vectors")
    if not np.isfinite(c).all() or ((c < 0) | (c > 1)).any():
        raise ValueError("confidence must be finite and in [0, 1]")
    if not np.isin(y, [0, 1]).all():
        raise ValueError("correct must contain only binary indicators")
    return c, y.astype(bool)


def risk_coverage(confidence, correct):
    """Accept complete tied groups; never order ties using correctness.

    AURC is a right-step integral over attainable coverage points, including
    the interval from zero to the first accepted group.
    """
    c, y = _inputs(confidence, correct)
    order = np.argsort(-c, kind="stable")
    scores, errors = c[order], (~y[order]).astype(float)
    ends = np.r_[np.flatnonzero(scores[:-1] != scores[1:]), len(c) - 1]
    counts = ends + 1
    coverage = counts / len(c)
    risk = np.cumsum(errors)[ends] / counts
    return {"thresholds": scores[ends], "coverage": coverage, "risk": risk,
            "aurc": float(np.sum(np.diff(np.r_[0., coverage]) * risk))}


@dataclass(frozen=True)
class SelectiveRule:
    threshold: float
    validation_coverage: float
    validation_risk: float
    coverage_floor: float
    max_risk: float
    feasible: bool

    def accept(self, confidence):
        c = np.asarray(confidence, dtype=float)
        if not np.isfinite(c).all() or ((c < 0) | (c > 1)).any():
            raise ValueError("confidence must be finite and in [0, 1]")
        # An infeasible validation constraint fails closed, not silently relaxed.
        return (c >= self.threshold) & self.feasible


def fit_selective_rule(validation_confidence, validation_correct,
                       coverage_floor=0.9, max_risk=0.05):
    """Maximise coverage subject to both validation constraints.

    These are empirical constraints, NOT population-risk guarantees. Fit once
    on validation, freeze, then report test risk and coverage independently.
    """
    if not 0 < coverage_floor <= 1 or not 0 <= max_risk <= 1:
        raise ValueError("invalid coverage/risk constraint")
    curve = risk_coverage(validation_confidence, validation_correct)
    ok = np.flatnonzero((curve["coverage"] >= coverage_floor) &
                        (curve["risk"] <= max_risk))
    if not len(ok):
        return SelectiveRule(float("inf"), 0., float("nan"),
                             coverage_floor, max_risk, False)
    i = ok[-1]
    return SelectiveRule(float(curve["thresholds"][i]),
                         float(curve["coverage"][i]), float(curve["risk"][i]),
                         coverage_floor, max_risk, True)
