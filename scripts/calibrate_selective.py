"""Fit on validation, evaluate once on a distinct test NPZ.

Each NPZ must contain image_id, confidence, correct. Confidence is an existing
model score; this command does not manufacture it from test correctness.
"""
import argparse
import json
from dataclasses import asdict
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.calibration import fit_selective_rule, risk_coverage


def load(path):
    with np.load(path, allow_pickle=False) as z:
        ids = z['image_id'].astype(str)
        confidence, correct = z['confidence'], z['correct']
    risk_coverage(confidence, correct)  # validate even if no test case is accepted
    if ids.ndim != 1 or len(ids) != len(confidence) or len(set(ids)) != len(ids):
        raise ValueError('expected unique image ids aligned with scores')
    return ids, confidence, correct


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--validation', type=Path, required=True)
    ap.add_argument('--test', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--coverage-floor', type=float, default=.9)
    ap.add_argument('--max-risk', type=float, default=.05)
    args = ap.parse_args()
    vi, vc, vy = load(args.validation)
    ti, tc, ty = load(args.test)
    if set(vi) & set(ti):
        raise ValueError('validation/test image overlap')
    rule = fit_selective_rule(vc, vy, args.coverage_floor, args.max_risk)
    accepted = rule.accept(tc)
    fields = asdict(rule)
    if not rule.feasible:
        fields['threshold'] = None
        fields['validation_risk'] = None
    receipt = {'rule': fields, 'n_validation': len(vi), 'n_test': len(ti),
               'test_coverage': float(accepted.mean()),
               'test_risk': float(1 - ty[accepted].mean()) if accepted.any() else None,
               'test_aurc': risk_coverage(tc, ty)['aurc'],
               'note': 'Empirical validation constraints, no population-risk guarantee.'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(args.out)


if __name__ == '__main__':
    main()
