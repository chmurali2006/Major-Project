import numpy as np
import pytest
from src.calibration import risk_coverage, fit_selective_rule


def test_perfect_and_wrong():
    assert risk_coverage([.9, .8], [1, 1])["aurc"] == 0
    assert risk_coverage([.9, .8], [0, 0])["aurc"] == 1


def test_ties_not_ordered_by_label():
    a = risk_coverage([.8, .8, .2], [1, 0, 1])
    b = risk_coverage([.8, .8, .2], [0, 1, 1])
    assert a["aurc"] == b["aurc"]
    np.testing.assert_allclose(a["coverage"], [2/3, 1])


def test_freeze_threshold_and_fail_closed():
    rule = fit_selective_rule([.9, .8, .1], [1, 1, 0], 2/3, 0)
    assert rule.feasible and rule.threshold == .8
    assert rule.accept([.95, .2]).tolist() == [True, False]
    impossible = fit_selective_rule([.9, .8], [0, 0])
    assert not impossible.feasible
    assert not impossible.accept([1., 1.]).any()


@pytest.mark.parametrize("confidence,correct", [([], []), ([np.nan], [1]),
    ([1.1], [1]), ([.5], [2]), ([[.5]], [[1]]), ([.5], [1, 0])])
def test_reject_invalid(confidence, correct):
    with pytest.raises(ValueError):
        risk_coverage(confidence, correct)
