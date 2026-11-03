"""Degradation estimates: the four scalars the RefineNet conditions on.

Row 6 of the synthesis table (OmniGuard). A degradation-blind localiser cannot
tell "this block lost its mark because someone edited it" from "this block lost
its mark because the whole file went through JPEG 50". Conditioning on a global
estimate of what the file has been through lets the network separate the two.

Every estimator here is training-free and computed from the received image
alone. None of them is exact; they only have to be monotone in the thing they
measure, because the network learns to use the scale, not the value.

The four channels:
    jpeginess   block-boundary energy relative to interior energy  (0 = none)
    noise       robust sigma from the high-pass residual
    sharpness   gradient energy, falls under blur and resampling
    clipping    fraction of pixels pinned at 0 or 255
"""

from __future__ import annotations

import cv2
import numpy as np

BLOCK = 8


def _gray(rgb: np.ndarray) -> np.ndarray:
    rgb = np.asarray(rgb)
    if rgb.ndim == 2:
        return rgb.astype(np.float64)
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float64)


def jpeginess(gray: np.ndarray) -> float:
    """Energy across 8-pixel boundaries divided by energy inside blocks.

    A JPEG-decompressed image has a discontinuity every 8 pixels that the
    original did not have. The ratio is near 1.0 for a pristine PNG and rises
    with compression. Normalised to 0..1 with a soft knee.
    """
    g = _gray(gray)
    h, w = g.shape
    h -= h % BLOCK
    w -= w % BLOCK
    g = g[:h, :w]
    dx = np.abs(np.diff(g, axis=1))
    dy = np.abs(np.diff(g, axis=0))
    bx = dx[:, BLOCK - 1::BLOCK].mean() if dx[:, BLOCK - 1::BLOCK].size else 0.0
    by = dy[BLOCK - 1::BLOCK, :].mean() if dy[BLOCK - 1::BLOCK, :].size else 0.0
    inner_x = np.delete(dx, np.s_[BLOCK - 1::BLOCK], axis=1).mean()
    inner_y = np.delete(dy, np.s_[BLOCK - 1::BLOCK], axis=0).mean()
    inner = (inner_x + inner_y) / 2.0 + 1e-6
    ratio = ((bx + by) / 2.0) / inner
    return float(np.clip((ratio - 1.0) / 1.5, 0.0, 1.0))


def noise_sigma(gray: np.ndarray) -> float:
    """Robust sigma from the Laplacian, the standard MAD estimator."""
    g = _gray(gray)
    lap = cv2.Laplacian(g.astype(np.float32), cv2.CV_32F)
    return float(np.median(np.abs(lap)) / 0.6745)


def sharpness(gray: np.ndarray) -> float:
    """Mean gradient magnitude. Drops under blur and resampling."""
    g = _gray(gray)
    gx = cv2.Sobel(g.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    return float(np.mean(np.hypot(gx, gy)))


def clipping(rgb: np.ndarray) -> float:
    """Fraction of pixels pinned at either end of the range."""
    a = np.asarray(rgb)
    return float(((a == 0) | (a == 255)).mean())


def estimate(rgb: np.ndarray, ref_sharpness: float | None = None) -> np.ndarray:
    """The four channels, scaled to a comparable range for a network input.

    `ref_sharpness` lets a caller normalise against the corpus median, so the
    sharpness channel reads as 'relative to a typical image' rather than an
    absolute gradient energy that varies with content.
    """
    g = _gray(rgb)
    s = sharpness(g)
    rel = 1.0 if ref_sharpness is None or ref_sharpness <= 0 else float(
        np.clip(s / ref_sharpness, 0.0, 2.0))
    return np.array([
        jpeginess(g),
        float(np.clip(noise_sigma(g) / 8.0, 0.0, 2.0)),
        rel,
        clipping(rgb),
    ], np.float32)
