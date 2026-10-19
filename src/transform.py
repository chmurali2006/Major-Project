"""Batched two-level Haar transform on 8x8 blocks.

One implementation, used by both the embedder and the verifier. Trap 8 says
never let two code paths own the transform; the test suite cross-checks this
against PyWavelets on random blocks so the two can never drift apart silently.

Layout of one block's 64 coefficients (orthonormal):

    LL2 (2x2)  LH2 (2x2)
    HL2 (2x2)  HH2 (2x2)      <- level 2, computed from LL1
    LH1 (4x4)  HL1 (4x4)  HH1 (4x4)   <- level 1 details

Carrier A writes the 60 detail coefficients and never LL2.
"""

from __future__ import annotations

import numpy as np

from .config import BLOCK, N_DETAIL

S = np.sqrt(2.0)

#: detail subbands in the fixed slot order used by the tag
SUBORDER = (("LH1", 4), ("HL1", 4), ("HH1", 4), ("LH2", 2), ("HL2", 2), ("HH2", 2))


def _dwt1(a: np.ndarray, axis: int) -> tuple[np.ndarray, np.ndarray]:
    a = np.moveaxis(a, axis, -1)
    lo = (a[..., ::2] + a[..., 1::2]) / S
    hi = (a[..., ::2] - a[..., 1::2]) / S
    return np.moveaxis(lo, -1, axis), np.moveaxis(hi, -1, axis)


def _idwt1(lo: np.ndarray, hi: np.ndarray, axis: int) -> np.ndarray:
    lo, hi = np.moveaxis(lo, axis, -1), np.moveaxis(hi, axis, -1)
    a = np.empty(lo.shape[:-1] + (lo.shape[-1] * 2,), dtype=np.float64)
    a[..., ::2] = (lo + hi) / S
    a[..., 1::2] = (lo - hi) / S
    return np.moveaxis(a, -1, axis)


class Haar2:
    """Two-level Haar over non-overlapping 8x8 blocks of a 2-D plane."""

    def __init__(self, shape: tuple[int, int]):
        h, w = shape
        if h % BLOCK or w % BLOCK:
            raise ValueError(f"image must be a multiple of {BLOCK}, got {shape}")
        self.shape = (h, w)
        self.ny, self.nx = h // BLOCK, w // BLOCK

    # ---- block <-> plane ----
    def to_blocks(self, x: np.ndarray) -> np.ndarray:
        return np.asarray(x, dtype=np.float64).reshape(
            self.ny, BLOCK, self.nx, BLOCK).transpose(0, 2, 1, 3)

    def from_blocks(self, b: np.ndarray) -> np.ndarray:
        return b.transpose(0, 2, 1, 3).reshape(self.shape)

    # ---- transform ----
    def forward(self, x: np.ndarray) -> dict[str, np.ndarray]:
        b = self.to_blocks(x)
        lo_c, hi_c = _dwt1(b, 3)          # along width
        ll1, lh1 = _dwt1(lo_c, 2)         # along height
        hl1, hh1 = _dwt1(hi_c, 2)
        lo2, hi2 = _dwt1(ll1, 3)
        ll2, lh2 = _dwt1(lo2, 2)
        hl2, hh2 = _dwt1(hi2, 2)
        return {"LL2": ll2, "LH1": lh1, "HL1": hl1, "HH1": hh1,
                "LH2": lh2, "HL2": hl2, "HH2": hh2}

    def inverse(self, c: dict[str, np.ndarray]) -> np.ndarray:
        ll1 = _idwt1(_idwt1(c["LL2"], c["LH2"], 2), _idwt1(c["HL2"], c["HH2"], 2), 3)
        lo_c = _idwt1(ll1, c["LH1"], 2)
        hi_c = _idwt1(c["HL1"], c["HH1"], 2)
        return self.from_blocks(_idwt1(lo_c, hi_c, 3))

    # ---- flat detail vectors ----
    @staticmethod
    def details_flat(c: dict[str, np.ndarray]) -> np.ndarray:
        parts = []
        for name, _ in SUBORDER:
            a = c[name]
            parts.append(a.reshape(a.shape[0], a.shape[1], -1))
        out = np.concatenate(parts, axis=2)
        assert out.shape[2] == N_DETAIL, out.shape
        return out

    @staticmethod
    def details_unflat(c: dict[str, np.ndarray], flat: np.ndarray) -> dict[str, np.ndarray]:
        out, i = {}, 0
        for name, width in SUBORDER:
            shape = c[name].shape[2:]
            n = width * width
            out[name] = flat[:, :, i:i + n].reshape(flat.shape[0], flat.shape[1], *shape)
            i += n
        assert i == N_DETAIL
        return out

    def ll2_of(self, x: np.ndarray) -> np.ndarray:
        return self.forward(x)["LL2"]
