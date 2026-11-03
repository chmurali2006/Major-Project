"""Tests for the keyed evidence channel.

The properties that matter:
  * the transform round-trips exactly enough to keep the signature stable
  * a clean protected image reads as intact
  * a pasted block reads as broken (address + content both wrong)
  * the wrong key reads as broken (the mark is keyed, not decorative)
  * the maps have the shapes the network expects
"""

import numpy as np
import pytest

import src.evidence as evidence_mod
from src.evidence import (BLOCK, DELTA, N_SLOTS, details, details_set, embed,
                          haar2, haar2_inverse, luma, read, signature, tags)

KEY = b"test-key-0"
SIZE = 512


def _img(seed=0):
    import cv2
    rng = np.random.default_rng(seed)
    base = rng.integers(70, 190, (SIZE // 16, SIZE // 16, 3))
    return cv2.resize(base.astype(np.uint8), (SIZE, SIZE), interpolation=cv2.INTER_CUBIC)


# ---------------------------------------------------------------- transform

def test_haar_round_trips():
    x = np.random.default_rng(0).random((64, 64)) * 255
    c = haar2(x)
    x2 = haar2_inverse(c)
    assert np.allclose(x, x2, atol=1e-9)


def test_details_count_is_sixty():
    x = np.random.default_rng(1).random((64, 64)) * 255
    flat = details(haar2(x))
    assert flat.shape == (8, 8, N_SLOTS)


def test_details_set_inverts_details():
    x = np.random.default_rng(2).random((64, 64)) * 255
    c = haar2(x)
    flat = details(c)
    c2 = details_set(c, flat)
    assert np.allclose(haar2_inverse(c2), x, atol=1e-9)


def test_transform_is_block_local():
    """Changing one block must not change any other block's coefficients."""
    x = np.random.default_rng(3).random((64, 64)) * 255
    y = x.copy()
    # a pattern, not a constant: a uniform offset lands entirely in LL2 and
    # never touches a detail coefficient, which is correct and would make this
    # test vacuous.
    y[8:16, 8:16] += np.arange(8)[None, :] * 3.0
    f1, f2 = details(haar2(x)), details(haar2(y))
    changed = np.abs(f1 - f2).sum(axis=2) > 1e-9
    # exactly the block at (1,1) in an 8x8 grid of blocks
    assert changed[1, 1]
    assert changed.sum() == 1


def test_uniform_offset_lands_in_ll2_only():
    """The property behind block-locality, stated directly."""
    x = np.random.default_rng(4).random((32, 32)) * 255
    y = x.copy()
    y[8:16, 8:16] += 12.0
    f1, f2 = details(haar2(x)), details(haar2(y))
    assert np.allclose(f1, f2)         # details untouched
    l1, l2 = haar2(x)["LL2"], haar2(y)["LL2"]
    assert not np.allclose(l1, l2)     # the offset is in the approximation


# ---------------------------------------------------------------- signature

def test_signature_is_stable_after_embedding():
    """The exactness property the whole scheme rests on: the quantisation index
    the verifier recovers is the one the embedder saw in the unmarked block."""
    rgb = _img(4)
    y = luma(rgb)
    flat_before = details(haar2(y))
    marked = embed(rgb, KEY, 1)
    flat_after = details(haar2(luma(marked)))
    assert np.array_equal(signature(flat_before), signature(flat_after))


def test_tags_are_keyed():
    rgb = _img(5)
    flat = details(haar2(luma(rgb)))
    ll2 = haar2(luma(rgb))["LL2"]
    t1 = tags(b"key-a", 1, flat, ll2)
    t2 = tags(b"key-b", 1, flat, ll2)
    assert not np.array_equal(t1, t2)
    assert t1.shape == (SIZE // BLOCK, SIZE // BLOCK, N_SLOTS)


def test_tags_depend_on_image_id():
    rgb = _img(6)
    flat = details(haar2(luma(rgb)))
    ll2 = haar2(luma(rgb))["LL2"]
    assert not np.array_equal(tags(KEY, 1, flat, ll2), tags(KEY, 2, flat, ll2))


def test_tags_depend_on_content():
    a = _img(7)
    b = _img(8)
    fa, fb = details(haar2(luma(a))), details(haar2(luma(b)))
    la, lb = haar2(luma(a))["LL2"], haar2(luma(b))["LL2"]
    assert not np.array_equal(tags(KEY, 1, fa, la), tags(KEY, 1, fb, lb))


# ---------------------------------------------------------------- reading

def test_clean_image_reads_intact():
    rgb = _img(9)
    marked = embed(rgb, KEY, 1)
    ev = read(marked, KEY, 1)
    assert ev["corr"].mean() > 0.9
    assert ev["S"].mean() > 0.85
    assert ev["E"].shape == (SIZE // BLOCK, SIZE // BLOCK)


def test_wrong_key_reads_broken():
    rgb = _img(10)
    marked = embed(rgb, KEY, 1)
    good = read(marked, KEY, 1)["corr"].mean()
    bad = read(marked, b"wrong-key", 1)["corr"].mean()
    assert good > 0.8
    assert bad < 0.4


def test_pasted_block_reads_broken():
    """Copy-move: the block carries the tag written for its old address."""
    rgb = _img(11)
    marked = embed(rgb, KEY, 1)
    ev_clean = read(marked, KEY, 1)

    tampered = marked.copy()
    tampered[320:352, 320:352] = marked[64:96, 64:96]     # 4x4 blocks pasted
    ev = read(tampered, KEY, 1)

    region = np.s_[320 // 8:320 // 8 + 4, 320 // 8:320 // 8 + 4]
    assert ev["corr"][region].mean() < ev_clean["corr"][region].mean() - 0.2


def test_content_change_reads_broken():
    rgb = _img(12)
    marked = embed(rgb, KEY, 1)
    tampered = marked.copy()
    tampered[100:180, 100:180] = 255 - tampered[100:180, 100:180]
    ev = read(tampered, KEY, 1)
    region = np.s_[100 // 8:180 // 8, 100 // 8:180 // 8]
    assert ev["E"][region].mean() > ev["E"][~np.zeros_like(ev["E"], bool)].mean()


def test_survival_drops_when_the_mark_is_erased():
    rgb = _img(13)
    marked = embed(rgb, KEY, 1)
    clean = read(marked, KEY, 1)["S"].mean()
    import cv2
    blurred = cv2.GaussianBlur(marked, (0, 0), 2.0)
    assert read(blurred, KEY, 1)["S"].mean() < clean


def test_output_ranges():
    rgb = _img(14)
    ev = read(embed(rgb, KEY, 1), KEY, 1)
    assert np.all(ev["E"] >= -1e-6) and np.all(ev["E"] <= 2.0 + 1e-6)
    assert np.all(ev["S"] >= 0) and np.all(ev["S"] <= 1.0)


def test_numpy_integer_image_id_is_accepted():
    """Callers pass array indices, which are numpy ints. These have no
    .to_bytes, and the failure is a TypeError deep inside the key stream."""
    rgb = _img(20)
    marked = evidence_mod.embed(rgb, KEY, np.int64(7))
    ev = evidence_mod.read(marked, KEY, np.int64(7))
    assert ev["corr"].mean() > 0.8


def test_matches_python_int():
    rgb = _img(21)
    a = evidence_mod.embed(rgb, KEY, 5)
    b = evidence_mod.embed(rgb, KEY, np.int64(5))
    assert np.array_equal(a, b)
