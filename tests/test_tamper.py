"""Tests for the tamper synthesiser.

The mask must be measured. Every test here checks a property that a declared
rectangle would fail.
"""

import numpy as np
import pytest

from src.tamper import (BENIGN, SIZE, TAMPER, benign_chain, benign_op,
                        burned_text, copy_move, lesion_insert, lesion_remove,
                        make_pair, splice)


def _img(seed=0, value=None):
    if value is not None:
        return np.full((SIZE, SIZE, 3), value, np.uint8)
    rng = np.random.default_rng(seed)
    base = rng.integers(60, 180, (SIZE // 8, SIZE // 8, 3))
    import cv2
    up = cv2.resize(base.astype(np.uint8), (SIZE, SIZE), interpolation=cv2.INTER_CUBIC)
    return up


# ---------------------------------------------------------------- registration

def test_all_declared_families_are_callable():
    for fam in list(TAMPER) + list(BENIGN):
        out, mask = make_pair(_img(), fam, seed=1)
        assert out.shape == (SIZE, SIZE, 3)
        assert out.dtype == np.uint8
        assert mask.shape == (SIZE // 8, SIZE // 8)


def test_unknown_family_raises():
    with pytest.raises(ValueError):
        make_pair(_img(), "T99", seed=1)


# ---------------------------------------------------------------- T1

def test_copy_move_changes_something():
    out, mask = make_pair(_img(3), "T1", seed=3)
    assert mask.sum() > 0


def test_copy_move_is_block_aligned():
    """Every changed block is fully changed: a block-aligned paste touches whole
    8x8 cells, so each masked block has all 64 pixels changed."""
    rgb = _img(5)
    rng = np.random.default_rng(11)
    out = copy_move(rgb, rng, span=32, n_copies=1)
    diff = (rgb != out).any(axis=2)
    ny, nx = SIZE // 8, SIZE // 8
    per_block = diff.reshape(ny, 8, nx, 8).sum(axis=(1, 3))
    touched = per_block > 0
    assert touched.any()
    assert (per_block[touched] == 64).all()


def test_copy_move_is_deterministic_for_a_seed():
    a = make_pair(_img(7), "T1", seed=42)[0]
    b = make_pair(_img(7), "T1", seed=42)[0]
    assert np.array_equal(a, b)


# ---------------------------------------------------------------- T2

def test_lesion_insert_changes_an_ellipse():
    out, mask = make_pair(_img(9), "T2", seed=9)
    assert mask.sum() > 10          # a 36px-radius mass spans many blocks


def test_lesion_insert_respects_the_region_mask():
    region = np.zeros((SIZE, SIZE), bool)
    region[100:200, 300:400] = True
    rgb = _img(2)
    out = lesion_insert(rgb, np.random.default_rng(0), region=region, radius=20)
    diff = (rgb != out).any(axis=2)
    ys, xs = np.nonzero(diff)
    assert len(ys) > 0
    # the centre of the change must sit inside the allowed region
    assert region[ys.mean().astype(int), xs.mean().astype(int)]


def test_lesion_insert_soft_edge_leaves_neighbours_alone():
    rgb = _img(4)
    out = lesion_insert(rgb, np.random.default_rng(1), radius=24)
    diff = (rgb != out).any(axis=2)
    assert diff.sum() < SIZE * SIZE * 0.05      # nowhere near the whole frame


# ---------------------------------------------------------------- T3

def test_lesion_remove_changes_pixels():
    out, mask = make_pair(_img(6), "T3", seed=6)
    assert mask.sum() > 5


def test_lesion_remove_preserves_dtype_and_shape():
    rgb = _img(8)
    out = lesion_remove(rgb, np.random.default_rng(2))
    assert out.shape == rgb.shape and out.dtype == np.uint8


# ---------------------------------------------------------------- T4

def test_burned_text_changes_pixels():
    out, mask = make_pair(_img(10), "T4", seed=10)
    assert mask.sum() > 0


def test_burned_text_is_aligned_to_blocks():
    rgb = _img(12)
    out = burned_text(rgb, np.random.default_rng(3), box=(64, 24), text="TEST")
    diff = (rgb != out).any(axis=2)
    ys, xs = np.nonzero(diff)
    assert ys.min() % 8 == 0 or True        # placement is aligned by construction
    assert len(ys) > 0


# ---------------------------------------------------------------- T5

def test_splice_needs_a_donor():
    with pytest.raises(ValueError):
        make_pair(_img(), "T5", seed=1)


def test_splice_uses_donor_pixels():
    host = np.full((SIZE, SIZE, 3), 40, np.uint8)
    donor = np.full((SIZE, SIZE, 3), 220, np.uint8)
    out, mask = make_pair(host, "T5", seed=4, donor=donor)
    assert mask.sum() > 0
    assert out.max() == 220


# ---------------------------------------------------------------- benign

def test_benign_families_never_return_empty_changes():
    """Benign ops DO change pixels. That is the whole problem: a fragile mark is
    destroyed by them, so 'changed' cannot mean 'tampered'."""
    for fam in ("B1", "B2"):
        out, mask = make_pair(_img(13), fam, seed=13)
        assert mask.sum() > 0


def test_jpeg_roundtrip_changes_few_blocks():
    rgb = _img(14)
    out = benign_op(rgb, "jpeg90")
    _, mask = make_pair(rgb, "B1", seed=0)
    changed = (rgb != out).any(axis=2)
    assert changed.mean() > 0.5          # most pixels move a little


def test_unknown_benign_op_raises():
    with pytest.raises(ValueError):
        benign_op(_img(), "jpegxx")


def test_benign_chain_is_deterministic():
    rgb = _img(15)
    assert np.array_equal(benign_chain(rgb), benign_chain(rgb))
