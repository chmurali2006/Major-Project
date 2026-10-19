import numpy as np

from src.binder import Binder, coarse_digest
from src.config import TAG_BITS


def _ll2(seed=0, scale=120.0):
    rng = np.random.default_rng(seed)
    return rng.normal(0, scale, (16, 16, 2, 2))


def test_digest_reads_only_ll2():
    """Trap 4: the digest must not depend on the coefficients we mark."""
    a = _ll2(1)
    d1 = coarse_digest(a)
    d2 = coarse_digest(a.copy())
    assert np.array_equal(d1, d2)


def test_digest_is_coarse():
    """A small perturbation moves few digests; quantisation does the work.

    The property that matters is statistical, not absolute: JPEG shifts LL2 by
    a level or two, and the great majority of digests must survive that. The
    end-to-end stability figure is measured in test_pipeline (JPEG 90/75/50).
    """
    a = _ll2(2)
    changed = (coarse_digest(a) != coarse_digest(a + 2.0)).mean()
    assert changed < 0.15, f"too brittle: {changed:.1%} of digests moved"


def test_digest_changes_when_content_changes_a_lot():
    a = _ll2(3)
    b = a + 200.0
    assert not np.array_equal(coarse_digest(a), coarse_digest(b))


def test_tag_length_and_determinism():
    b = Binder(b"k" * 16, image_id=42)
    t1 = b.tag(7, 1234)
    t2 = b.tag(7, 1234)
    assert t1.shape == (TAG_BITS,)
    assert np.array_equal(t1, t2)


def test_address_avalanche():
    """Changing the address must change roughly half the bits."""
    b = Binder(b"k" * 16, image_id=42)
    t0 = b.tag(0, 999)
    flips = [int((b.tag(a, 999) != t0).sum()) for a in range(1, 200)]
    assert min(flips) >= 15, f"weak avalanche: min {min(flips)} of {TAG_BITS}"
    assert 18 <= float(np.mean(flips)) <= 42


def test_digest_avalanche():
    b = Binder(b"k" * 16, image_id=42)
    t0 = b.tag(5, 0)
    flips = [int((b.tag(5, d) != t0).sum()) for d in range(1, 200)]
    assert min(flips) >= 15


def test_different_keys_disagree():
    a = Binder(b"key-a", image_id=1)
    b = Binder(b"key-b", image_id=1)
    assert (a.tag(3, 77) != b.tag(3, 77)).sum() > 20


def test_ablation_ignores_address():
    bound = Binder(b"k" * 16, image_id=42, bind_address=True)
    loose = Binder(b"k" * 16, image_id=42, bind_address=False)
    assert not np.array_equal(bound.tag(1, 5), bound.tag(2, 5))
    assert np.array_equal(loose.tag(1, 5), loose.tag(2, 5))
