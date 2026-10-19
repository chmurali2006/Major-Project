import numpy as np

from src.container import (compose, fit_block_luma, merge_rct, out_of_range,
                           png_bytes, png_read, png_roundtrip, png_text,
                           recover_luma, split_rct)
from src.fixtures import phantom


def test_rct_is_exactly_reversible():
    rng = np.random.default_rng(0)
    rgb = rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)
    y, cb, cr = split_rct(rgb)
    assert np.array_equal(merge_rct(y, cb, cr), rgb)


def test_rct_recovers_luma_after_png():
    rgb, _ = phantom(seed=1, size=64)
    y, _, _ = split_rct(rgb)
    back = png_read(png_bytes(rgb))
    assert np.array_equal(recover_luma(back), y.astype(np.float64))


def test_png_roundtrip_is_bit_identical():
    rgb, _ = phantom(seed=2, size=64)
    assert np.array_equal(png_roundtrip(rgb), rgb)


def test_metadata_survives_png():
    rgb, _ = phantom(seed=3, size=64)
    data = png_bytes(rgb, text={"pff_imageid": "17", "pff_keyid": "abc"})
    assert png_text(data)["pff_imageid"] == "17"
    assert png_text(data)["pff_keyid"] == "abc"


def test_fit_prevents_clipping():
    rgb, _ = phantom(seed=4)
    y, cb, cr = split_rct(rgb)
    noisy = y.astype(np.float64) + 3.0
    fitted, refused = fit_block_luma(noisy, cb, cr)
    assert refused.mean() < 0.01
    bad = out_of_range(fitted, cb, cr)
    admitted = ~refused.repeat(8, 0).repeat(8, 1)
    assert not bad[admitted].any()


def test_compose_reverts_refused_blocks():
    """Contract: a refused block keeps its original luma, exactly, and says so."""
    rgb, _ = phantom(seed=5)
    y, _, _ = split_rct(rgb)
    p = compose(y.astype(np.float64) + 1.0, rgb)
    if p.refused.any():
        blk = np.repeat(np.repeat(p.refused, 8, 0), 8, 1)
        assert np.array_equal(p.y_marked[blk], y.astype(np.float64)[blk])
        assert p.refusal_reason == "clipping"
    # the saved RGB must reproduce the marked luma exactly
    assert np.array_equal(recover_luma(p.rgb), p.y_marked.astype(np.float64))
