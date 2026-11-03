"""Tests for the metric layer.

These are the tests that would have caught the classical phase's worst errors:
a metric returning a ratio from a zero denominator, and ground truth being a
declared rectangle instead of a measured difference.
"""

import numpy as np
import pytest

from src.metrics import (aurc, benefit_at, counts, detection_accuracy, dice,
                         iou, measured_mask, pixel_accuracy, pixel_f1,
                         precision, recall, selective_risk, summarise)


# ---------------------------------------------------------------- ground truth

def test_measured_mask_all_false_for_identical():
    a = np.random.default_rng(0).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    m = measured_mask(a, a.copy())
    assert m.shape == (8, 8)
    assert m.sum() == 0


def test_measured_mask_finds_exact_blocks():
    a = np.zeros((64, 64, 3), np.uint8)
    b = a.copy()
    b[16:24, 32:40] = 255            # one 8x8 block
    m = measured_mask(a, b)
    assert m.sum() == 1
    assert m[2, 4]


def test_measured_mask_is_not_the_declared_rectangle():
    """The PH2 condition-4 case: a paste that changes no pixels is not tampering.

    White background pasted onto white background. The declared region is 4
    blocks; the measured mask must be empty, and a system reporting INTACT there
    must not be penalised.
    """
    a = np.full((64, 64, 3), 255, np.uint8)
    b = a.copy()
    b[0:32, 0:32] = a[32:64, 32:64]  # identical pixels
    assert measured_mask(a, b).sum() == 0


def test_measured_mask_geometry_change_covers_everything():
    a = np.zeros((64, 64, 3), np.uint8)
    b = np.zeros((48, 48, 3), np.uint8)
    m = measured_mask(a, b)
    assert m.shape == (6, 6)
    assert m.all()


# ---------------------------------------------------------------- ratios

def test_iou_perfect():
    m = np.zeros((4, 4), bool)
    m[1, 1] = True
    assert iou(m, m) == 1.0


def test_iou_disjoint():
    p = np.zeros((4, 4), bool); p[0, 0] = True
    g = np.zeros((4, 4), bool); g[3, 3] = True
    assert iou(p, g) == 0.0


def test_iou_empty_vs_empty_is_one_documented():
    z = np.zeros((4, 4), bool)
    assert iou(z, z) == 1.0     # convention: agreement, but counts must be read


def test_counts_expose_the_denominator():
    z = np.zeros((4, 4), bool)
    c = counts(z, z)
    assert c == {"tp": 0, "fp": 0, "fn": 0, "gt": 0, "pred": 0}


def test_iou_half():
    p = np.zeros((2, 2), bool); p[0, :] = True
    g = np.zeros((2, 2), bool); g[:, 0] = True
    # tp=1, fp=1, fn=1 -> 1/3
    assert iou(p, g) == pytest.approx(1 / 3)


def test_dice_matches_formula():
    p = np.zeros((2, 2), bool); p[0, :] = True
    g = np.zeros((2, 2), bool); g[:, 0] = True
    # 2*1 / (2*1+1+1) = 0.5
    assert dice(p, g) == pytest.approx(0.5)


def test_precision_recall_edges():
    z = np.zeros((3, 3), bool)
    assert precision(z, z) == 0.0      # no positive predictions
    assert recall(z, z) == 0.0         # no positives in truth


def test_pixel_f1_hand_computed():
    p = np.zeros((4, 4), bool); p[0, :2] = True
    g = np.zeros((4, 4), bool); g[0, :3] = True
    # tp=2 fp=0 fn=1 -> P=1.0 R=2/3 F1=0.8
    assert precision(p, g) == pytest.approx(1.0)
    assert recall(p, g) == pytest.approx(2 / 3)
    assert pixel_f1(p, g) == pytest.approx(0.8)


def test_pixel_accuracy():
    p = np.zeros((10, 10), bool); p[0, 0] = True
    g = np.zeros((10, 10), bool)
    assert pixel_accuracy(p, g) == pytest.approx(0.99)


def test_shape_mismatch_raises():
    with pytest.raises(ValueError):
        iou(np.zeros((2, 2), bool), np.zeros((3, 3), bool))


# ---------------------------------------------------------------- detection

def _res(kind, pred_blocks, gt_blocks=1, family="T1"):
    pred = np.zeros((8, 8), bool)
    gt = np.zeros((8, 8), bool)
    gt.flat[:gt_blocks] = True
    pred.flat[:pred_blocks] = True
    return {"kind": kind, "family": family, "pred": pred, "gt": gt}


def test_detection_accuracy_counts_false_positives():
    results = [_res("tamper", 3), _res("tamper", 0), _res("benign", 0), _res("benign", 2, gt_blocks=0)]
    d = detection_accuracy(results)
    assert d["n_tamper"] == 2 and d["n_benign"] == 2
    assert d["detection_acc"] == pytest.approx(0.5)
    assert d["false_positive_rate"] == pytest.approx(0.5)


def test_benefit_at_threshold():
    results = [_res("tamper", 1, gt_blocks=1), _res("tamper", 1, gt_blocks=40)]
    # first: perfect (IoU 1.0); second: 1/40 -> below 0.5
    assert benefit_at(results, 0.5) == pytest.approx(0.5)


# ---------------------------------------------------------------- abstention

def test_selective_risk_perfect_ranking():
    conf = np.linspace(1, 0, 100)
    correct = conf > 0.5
    r = selective_risk(conf, correct, coverages=(0.1, 0.5, 1.0))
    assert r["cov_0.10"] == pytest.approx(0.0)
    assert r["cov_1.00"] == pytest.approx(0.5)


def test_selective_risk_no_ranking_is_flat():
    rng = np.random.default_rng(0)
    correct = rng.random(1000) > 0.3
    conf = rng.random(1000)                 # useless confidence
    r = selective_risk(conf, correct, coverages=(0.1, 1.0))
    assert r["cov_0.10"] == pytest.approx(0.3, abs=0.15)


def test_aurc_better_for_informative_confidence():
    rng = np.random.default_rng(1)
    correct = rng.random(2000) > 0.3
    good = np.where(correct, rng.uniform(0.6, 1.0, 2000), rng.uniform(0.0, 0.4, 2000))
    bad = rng.random(2000)
    assert aurc(good, correct) < aurc(bad, correct)


def test_selective_risk_empty_returns_nan():
    r = selective_risk(np.array([]), np.array([], bool), coverages=(0.5,))
    assert np.isnan(r["cov_0.50"])


# ---------------------------------------------------------------- aggregate

def test_summarise_reports_denominators():
    results = [_res("tamper", 1, 1), _res("tamper", 0, 4), _res("benign", 0, 0)]
    s = summarise(results)
    fam = s["per_family"]["T1"]
    assert fam["n"] == 2
    assert fam["tp"] == 1 and fam["fn"] == 4
    assert s["n_images"] == 3


# ---------------------------------------------------------------- comparison guards

def test_block_ceiling_is_below_one_for_small_targets():
    """A perfect block detector cannot reach pixel IoU 1.0 on a small lesion.
    This is the fact that decides whether a comparison to a pixel-mask paper is
    even meaningful."""
    from src.metrics import block_ceiling
    yy, xx = np.mgrid[0:512, 0:512]
    disk = ((yy - 256) ** 2 + (xx - 256) ** 2) <= 32 ** 2
    c = block_ceiling(disk)
    assert 0.78 < c < 0.83        # measured 0.809


def test_block_ceiling_converges_slowly():
    """Measured: r=96 -> 0.930, r=128 -> 0.937, r=160 -> 0.950. The ceiling does
    not approach 1 quickly, because the boundary band a block grid must include
    scales with the perimeter while the area scales with the square. Any claim
    of pixel IoU above ~0.95 therefore implies a very large tampered region."""
    from src.metrics import block_ceiling
    yy, xx = np.mgrid[0:512, 0:512]
    def disk(r):
        return ((yy - 256) ** 2 + (xx - 256) ** 2) <= r * r
    assert 0.92 < block_ceiling(disk(96)) < 0.94
    assert 0.93 < block_ceiling(disk(128)) < 0.95
    assert block_ceiling(disk(160)) > 0.945


def test_area_buckets_cover_everything():
    from src.metrics import area_buckets
    assert area_buckets([0.0, 0.004, 0.01, 0.03, 0.1, 0.9]) == [
        "area_0.000-0.005", "area_0.000-0.005", "area_0.005-0.020",
        "area_0.020-0.050", "area_0.050-0.200", "area_0.200-1.010"]


def test_measured_pixel_mask_is_pixel_exact():
    from src.metrics import measured_pixel_mask
    a = np.zeros((64, 64, 3), np.uint8)
    b = a.copy()
    b[16:24, 33:40] = 9          # not block aligned
    pm = measured_pixel_mask(a, b)
    assert pm.sum() == 8 * 7     # exact pixel count, not rounded to blocks


def test_stratified_reports_ceiling_only_with_pixel_truth():
    from src.metrics import stratified_iou
    g = np.zeros((64, 64), bool); g[:2, :2] = True
    block_only = [{"kind": "tamper", "family": "T1", "pred": g, "gt": g}]
    assert "ceiling" not in list(stratified_iou(block_only).values())[0]

    gp = np.zeros((512, 512), bool); gp[:16, :16] = True
    with_pixels = [{"kind": "tamper", "family": "T1", "pred": g, "gt": g,
                    "gt_pixels": gp, "pred_pixels": gp}]
    row = list(stratified_iou(with_pixels).values())[0]
    assert "ceiling" in row and "iou_pixel" in row
