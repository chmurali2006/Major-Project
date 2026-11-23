import numpy as np

from src.legacy_metrics import block_f1, bootstrap_ci, detected, iou


def test_iou_perfect_and_disjoint():
    a = np.zeros((4, 4), bool); a[1, 1] = True
    assert iou(a, a) == 1.0
    b = np.zeros((4, 4), bool); b[2, 2] = True
    assert iou(a, b) == 0.0


def test_iou_partial():
    a = np.zeros((4, 4), bool); a[0, 0] = a[0, 1] = True
    b = np.zeros((4, 4), bool); b[0, 0] = b[1, 0] = True
    assert iou(a, b) == 1 / 3


def test_detection_rule_is_stated():
    a = np.zeros((4, 4), bool); a[0, 0] = True
    b = np.zeros((4, 4), bool); b[0, 0] = True; b[3, 3] = True
    assert detected(a, b, 0.1)
    assert not detected(a, b, 0.9)


def test_f1_counts_denominator():
    pred = np.zeros((4, 4), bool); pred[0, 0] = True
    gt = np.zeros((4, 4), bool); gt[0, 0] = True; gt[1, 1] = True
    r = block_f1(pred, gt)
    assert r.n == 16                      # the denominator is reported
    assert abs(r.value - 2 * 1.0 * 0.5 / 1.5) < 1e-12


def test_bootstrap_interval_brackets_mean():
    v = np.random.default_rng(0).normal(0.5, 0.1, 200)
    lo, hi = bootstrap_ci(v, n=500)
    assert lo < np.mean(v) < hi
