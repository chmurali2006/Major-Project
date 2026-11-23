import numpy as np
import pywt
import pytest

from src.config import N_DETAIL
from src.transform import Haar2


def test_perfect_reconstruction_random():
    rng = np.random.default_rng(0)
    x = rng.normal(0, 40, (64, 64))
    hb = Haar2(x.shape)
    rec = hb.inverse(hb.forward(x))
    assert np.abs(rec - x).max() < 1e-10


def test_perfect_reconstruction_uint8_plane():
    rng = np.random.default_rng(1)
    x = rng.integers(0, 256, (128, 128)).astype(np.float64)
    hb = Haar2(x.shape)
    assert np.abs(hb.inverse(hb.forward(x)) - x).max() < 1e-10


def test_agrees_with_pywavelets():
    """Trap 8: two implementations must not drift. Cross-check on one block."""
    rng = np.random.default_rng(2)
    block = rng.normal(0, 30, (8, 8))
    hb = Haar2((8, 8))
    c = hb.forward(block)
    cA, _ = pywt.dwt2(block, "haar", mode="periodization")
    ll2_pywt, _ = pywt.dwt2(cA, "haar", mode="periodization")
    # the two-level approximation must agree bit for bit
    assert np.allclose(ll2_pywt, c["LL2"], atol=1e-12)


def test_detail_slots_are_sixty():
    rng = np.random.default_rng(3)
    x = rng.normal(0, 10, (32, 32))
    hb = Haar2(x.shape)
    c = hb.forward(x)
    flat = Haar2.details_flat(c)
    assert flat.shape == (4, 4, N_DETAIL)


def test_details_do_not_touch_ll():
    rng = np.random.default_rng(4)
    x = rng.normal(0, 10, (32, 32))
    hb = Haar2(x.shape)
    c = hb.forward(x)
    flat = Haar2.details_flat(c) + 5.0
    rebuilt = hb.forward(hb.inverse({**c, **Haar2.details_unflat(c, flat)}))
    assert np.abs(rebuilt["LL2"] - c["LL2"]).max() < 1e-9
    assert np.abs(Haar2.details_flat(rebuilt) - flat).max() < 1e-9


def test_rejects_non_multiple_shapes():
    with pytest.raises(ValueError):
        Haar2((510, 512))
