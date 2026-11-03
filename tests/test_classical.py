from types import SimpleNamespace
import numpy as np
import pytest
from src.classical import CountRule, fit_count_rule
from src.evidence import FULL_CHANNELS


def sample(tampered):
    ev = np.zeros((len(FULL_CHANNELS), 4, 4))
    ev[FULL_CHANNELS.index('semi')] = 1
    if tampered:
        ev[0, :2] = 1
        ev[FULL_CHANNELS.index('semi'), :2] = 0
    return SimpleNamespace(ev=ev, cls=int(tampered), gt_block=ev[0] > .5)


def test_count_boundary_and_semi_input():
    s = sample(True)
    assert CountRule(.5, 8).predict(s.ev)[1] == 0
    assert CountRule(.5, 7).predict(s.ev)[1] == 1
    e = s.ev.copy()
    e[0] = 0
    assert not CountRule(.5, 0).predict(e)[1]
    assert CountRule(.5, 0, 1).predict(e)[1]


def test_fit_validation_and_missing_class():
    ss = [sample(False), sample(True)]
    for b in (False, True):
        rule = fit_count_rule(ss, b)
        assert [rule.predict(s.ev)[1] for s in ss] == [0, 1]
    with pytest.raises(ValueError):
        fit_count_rule([sample(True)])
