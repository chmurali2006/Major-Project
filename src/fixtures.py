"""Synthetic phantoms for testing only.

**No number produced on these images may appear in the thesis.** They exist so
the code can be tested without the datasets, which the sandbox cannot reach.
The battery runs on real ISIC 2018 and LiTS images; these do not substitute for
them and are labelled as fixtures everywhere they are used.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter


def phantom(seed: int = 0, size: int = 512,
            lesion_r: float = 96.0, lesion_c: float = 112.0,
            texture: float = 11.0) -> tuple[np.ndarray, np.ndarray]:
    """Dermoscopy-like: warm skin, fine texture, darker textured lesion.

    Returns (rgb uint8 (H,W,3), mask bool (H,W)).
    """
    rng = np.random.default_rng(seed)
    h = w = size
    yy, xx = np.mgrid[0:h, 0:w]

    base = 178 + 24 * np.sin(xx / 90.0) + 14 * np.cos(yy / 70.0)
    fine = gaussian_filter(rng.normal(0, texture, (h, w)), 0.8)
    luma = base + fine

    cy, cx = size * 0.505, size * 0.488
    mask = ((yy - cy) / lesion_r) ** 2 + ((xx - cx) / lesion_c) ** 2 <= 1.0
    les = gaussian_filter(rng.normal(0, texture * 1.5, (h, w)), 1.0)
    luma[mask] = 104 + les[mask] + 9 * np.sin(xx[mask] / 7.0)

    # chroma: skin is red-dominant; the lesion is browner
    cr = np.full((h, w), 26.0)
    cb = np.full((h, w), -18.0)
    cr[mask] = 34.0
    cb[mask] = -6.0
    cr += gaussian_filter(rng.normal(0, 2.0, (h, w)), 1.5)
    cb += gaussian_filter(rng.normal(0, 2.0, (h, w)), 1.5)

    # build RGB from (Y, Cb, Cr) with the same integer transform the container uses
    y32 = np.clip(luma, 0, 255).round().astype(np.int32)
    g = y32 - ((cb.astype(np.int32) + cr.astype(np.int32)) >> 2)
    r = cr.astype(np.int32) + g
    b = cb.astype(np.int32) + g
    rgb = np.clip(np.stack([r, g, b], axis=-1), 0, 255).astype(np.uint8)
    return rgb, mask


def phantom_batch(n: int, size: int = 512, seed0: int = 0):
    for i in range(n):
        yield phantom(seed=seed0 + i, size=size,
                      lesion_r=70.0 + 6.0 * (i % 5),
                      lesion_c=88.0 + 9.0 * (i % 4),
                      texture=8.0 + 1.2 * (i % 6))
