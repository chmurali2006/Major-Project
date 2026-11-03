"""The degradation channels only need to be monotone. Test that they are."""
import numpy as np
import pytest
from src.degradation import clipping, estimate, jpeginess, noise_sigma, sharpness
from src.tamper import benign_op

def img(seed=0):
    import cv2
    rng = np.random.default_rng(seed)
    c = rng.integers(60, 190, (16, 16, 3)).astype(np.uint8)
    return cv2.resize(c, (512, 512), interpolation=cv2.INTER_CUBIC)

def test_estimate_shape():
    assert estimate(img()).shape == (4,)

def test_estimate_is_finite():
    assert np.all(np.isfinite(estimate(img())))

def test_jpeginess_rises_with_compression():
    a = img(1)
    j90, j50, j30 = (jpeginess(x) for x in (benign_op(a, "jpeg90"),
                                            benign_op(a, "jpeg50"),
                                            benign_op(a, "jpeg30")))
    assert j90 <= j50 <= j30

def test_noise_sigma_rises_with_noise():
    a = img(2)
    lo = noise_sigma(benign_op(a, "sigma1"))
    hi = noise_sigma(benign_op(a, "sigma8"))
    assert hi > lo

def test_sharpness_drops_under_blur():
    a = img(3)
    assert sharpness(benign_op(a, "blur2")) < sharpness(a)

def test_clipping_counts_pinned_pixels():
    a = np.full((16, 16, 3), 128, np.uint8)
    assert clipping(a) == 0.0
    a[:8] = 255
    assert clipping(a) == pytest.approx(0.5)

def test_estimate_accepts_gray():
    g = np.random.default_rng(0).integers(0, 255, (64, 64)).astype(np.uint8)
    assert estimate(g).shape == (4,)

def test_channels_are_bounded():
    e = estimate(img(4))
    assert 0.0 <= e[0] <= 1.0
    assert 0.0 <= e[1] <= 2.0
    assert 0.0 <= e[2] <= 2.0
    assert 0.0 <= e[3] <= 1.0
