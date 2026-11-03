"""Tests for Carrier B, the semi-robust DCT watermark.

The properties asserted here are the ones the architecture depends on. If any of
them fails, the dual-carrier design is not what the report says it is.
"""

from __future__ import annotations

import numpy as np
import pytest

from src import carriers as C


def field(seed: int = 0, size: int = 128) -> np.ndarray:
    rng = np.random.default_rng(seed)
    coarse = rng.integers(50, 200, (size // 16, size // 16, 3)).astype(np.uint8)
    import cv2
    img = cv2.resize(coarse, (size, size), interpolation=cv2.INTER_CUBIC)
    return np.clip(img.astype(np.float64) + rng.normal(0, 6, (size, size, 3)),
                   0, 255).astype(np.uint8)


# ------------------------------------------------------------------ geometry

def test_semi_band_has_22_coefficients():
    assert len(C.SEMI_COEFFS) == C.N_SEMI == 22
    assert all(3 <= u + v <= 6 for u, v in C.SEMI_COEFFS)


def test_dc_and_first_diagonals_are_never_written():
    """The low-frequency terms carry most of the image energy. Writing there
    would be visible and would fight the fragile carrier."""
    written = set(C.SEMI_COEFFS)
    for u in range(8):
        for v in range(8):
            if u + v < 3:
                assert (u, v) not in written


def test_block_dct_round_trips():
    y = np.random.default_rng(0).normal(128, 20, (64, 64))
    assert np.allclose(C.idct_blocks(C.dct_blocks(y)), y, atol=1e-9)


def test_block_decomposition_is_local():
    """Perturbing one block must change exactly one block's coefficients.

    This is the bug recorded in the README: a plain reshape(ny, b, nx, b)
    interleaves the block axes and scatters one block across several, while
    round-tripping perfectly. Only a locality assertion catches it.
    """
    y = np.random.default_rng(0).normal(128, 20, (64, 64))
    a = C.dct_blocks(y)
    b = C.dct_blocks(y.copy())
    b[3, 5] += 1.0
    changed = np.abs(a - b).sum(axis=(2, 3)) > 0
    assert changed.sum() == 1
    assert changed[3, 5]


# ------------------------------------------------------------------ the marking

def test_mark_is_readable_and_absent_without_it():
    x = field()
    m = C.embed(x, b"key", 1)
    assert C.read(m, b"key", 1)["semi"].mean() > 0.8
    assert abs(C.read(x, b"key", 1)["semi"].mean()) < 0.15


def test_wrong_key_reads_nothing():
    """The security property. A wrong key must produce noise, not a weaker mark."""
    m = C.embed(field(), b"right", 1)
    assert abs(C.read(m, b"wrong", 1)["semi"].mean()) < 0.1


def test_each_block_is_bound_to_its_address():
    """A block pasted from elsewhere meets the signs of its new address, so the
    carrier is address-bound as well as key-bound."""
    x = field(size=128)
    m = C.embed(x, b"k", 1)
    moved = m.copy()
    moved[16:32, 16:32] = m[80:96, 80:96]          # paste a block-aligned patch
    r = C.read(moved, b"k", 1)
    inside = r["semi"][2:4, 2:4].mean()
    outside = np.delete(r["semi"].ravel(), np.s_[0]).mean()
    assert inside < 0.5 < outside


def test_fidelity_matches_the_reported_bar():
    """Carrier B alone at BETA must stay above 40 dB, which is the fidelity the
    reference system reports. A carrier that costs more than a few dB is not
    usable on a medical image."""
    x = field()
    m = C.embed(x, b"k", 1)
    psnr = 10 * np.log10(255.0 ** 2 / np.mean((m.astype(np.float64) - x) ** 2))
    assert psnr > 40.0, psnr


def test_colour_is_preserved():
    """The mark lives in luma; chroma differences must survive to within rounding."""
    x = field()
    m = C.embed(x, b"k", 1)
    for a, b in ((0, 1), (1, 2), (0, 2)):
        before = (x[..., a].astype(np.int16) - x[..., b].astype(np.int16))
        after = (m[..., a].astype(np.int16) - m[..., b].astype(np.int16))
        assert np.abs(before - after).max() <= 2


# ------------------------------------------------------------------ robustness

@pytest.mark.parametrize("quality,floor", [(90, 0.8), (85, 0.7), (75, 0.4)])
def test_survives_jpeg(quality, floor):
    """The whole reason this carrier exists. A fragile carrier dies at these
    qualities; this one must not, or the verifier cannot separate a codec from
    an editor."""
    import io

    from PIL import Image

    x = field()
    m = C.embed(x, b"k", 1)
    buf = io.BytesIO()
    Image.fromarray(m).save(buf, "JPEG", quality=quality)
    buf.seek(0)
    j = np.array(Image.open(buf).convert("RGB"))
    assert C.read(j, b"k", 1)["semi"].mean() > floor


def test_fragile_carrier_dies_where_this_one_survives():
    """The separation the architecture is built on, asserted end to end.

    At JPEG Q90 the fragile carrier must report the mark destroyed (E high) while
    the semi-robust carrier must report it intact (semi high). That combination
    is what lets the verifier say routine_handling instead of TAMPERED.
    """
    import io

    from PIL import Image

    from src.evidence import protect, read_full

    x = field(size=256)
    m = protect(x, b"k", 1, profile="dual")
    buf = io.BytesIO()
    Image.fromarray(m).save(buf, "JPEG", quality=90)
    buf.seek(0)
    j = np.array(Image.open(buf).convert("RGB"))

    d = read_full(j, b"k", 1, profile="dual")
    assert d["E"].mean() > 0.5, d["E"].mean()      # fragile mark broken
    assert d["semi"].mean() > 0.7, d["semi"].mean()  # semi-robust mark intact


# ------------------------------------------------------------------ profiles

def test_dual_profile_hits_the_fidelity_bar():
    """The balanced dual-carrier configuration must reach the reference system's
    reported fidelity. This is the number the comparison will be read against."""
    from src.evidence import protect

    x = field(size=256)
    m = protect(x, b"k", 1, profile="dual")
    psnr = 10 * np.log10(255.0 ** 2 / np.mean((m.astype(np.float64) - x) ** 2))
    assert psnr > 40.0, psnr


def test_profiles_are_named_and_resolved():
    from src.evidence import DEFAULT_PROFILE, PROTECT_PROFILES, _profile

    assert DEFAULT_PROFILE in PROTECT_PROFILES
    assert PROTECT_PROFILES["dual"]["delta"] < PROTECT_PROFILES["single"]["delta"]
    d, b = _profile("single", None, None)
    assert d == 8.0 and b is None
    d, b = _profile("dual", None, None)
    assert d == 4.0 and b == 3.0


def test_unknown_profile_is_rejected():
    from src.evidence import _profile

    with pytest.raises(ValueError, match="unknown profile"):
        _profile("nonsense", None, None)
