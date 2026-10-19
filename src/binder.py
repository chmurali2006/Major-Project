"""Tag binder: position-bound keyed tags.

    digest = coarse(LL2 of the block)          never written by any carrier
    tag    = HMAC-SHA256(key, image_id || address || digest)[:60]

Trap 4 is the reason the digest reads LL2 only. Trap 10 is the reason the
address is inside the MAC: a tag that does not name its own position can be
moved with impunity, and copy-move would be invisible.

A-004: Carrier B's sequence is address-keyed too (see carriers.py). Both
carriers must bind to the address, or a moved block keeps a valid reference.
"""

from __future__ import annotations

import hashlib
import hmac

import numpy as np

from .config import DIGEST_BITS, DIGEST_CLIP, DIGEST_COEFFS, Q_DIGEST, TAG_BITS


def coarse_digest(ll2: np.ndarray, q: float = Q_DIGEST) -> np.ndarray:
    """4 level-2 LL coefficients, coarsely quantised, packed into 12 bits.

    Coarse on purpose: benign handling must not move the digest across a
    quantisation boundary, because every bit of the tag depends on it.
    """
    d = np.clip(np.round(ll2 / q), -DIGEST_CLIP, DIGEST_CLIP).astype(np.int64) + DIGEST_CLIP
    d = d.reshape(d.shape[0], d.shape[1], DIGEST_COEFFS)   # (0..2*CLIP)
    packing = 2 * DIGEST_CLIP + 1                          # 7 values, 3 bits
    out = np.zeros(ll2.shape[:2], dtype=np.int64)
    for i in range(DIGEST_COEFFS):
        out = (out << 3) | d[..., i]
    assert int(out.max()) < (1 << DIGEST_BITS), "digest overflow"
    assert packing <= 8
    return out


def digest_margin(ll2: np.ndarray, q: float = Q_DIGEST) -> np.ndarray:
    """Distance, in luma levels, from the nearest digest quantisation boundary.

    The coarse digest is only reliable when every one of its four coefficients
    sits comfortably inside its quantisation cell. If a coefficient is within a
    level or two of a boundary, mild noise can move it across, which changes
    the whole 60-bit tag and manufactures a spurious "tampered" block. The
    verifier can see that condition in the received image, without knowing the
    original, and abstain instead of accusing.
    """
    x = np.asarray(ll2, np.float64) / q
    frac = np.abs(x - np.round(x)) * q          # 0 .. q/2, in luma levels
    return frac.reshape(frac.shape[0], frac.shape[1], -1).min(axis=2)


class Binder:
    """Keyed, position-bound tag generator. The key never travels."""

    def __init__(self, key: bytes, image_id: int, bind_address: bool = True):
        if not key:
            raise ValueError("empty key")
        self.bind_address = bool(bind_address)
        if not 0 <= image_id < 2**32:
            raise ValueError("image_id must fit in 32 bits")
        self._image_id = image_id
        base = hmac.new(key, digestmod=hashlib.sha256)
        base.update(image_id.to_bytes(4, "big"))
        # every block MAC starts from this prefix; copy() avoids re-keying
        self._base = base

    def tag(self, address: int, digest: int) -> np.ndarray:
        m = self._base.copy()
        if self.bind_address:
            m.update(int(address).to_bytes(4, "big"))
        m.update(int(digest).to_bytes(2, "big"))
        raw = m.digest()
        return np.unpackbits(np.frombuffer(raw, dtype=np.uint8))[:TAG_BITS].copy()

    def tags(self, addresses: np.ndarray, digests: np.ndarray) -> np.ndarray:
        ny, nx = digests.shape
        out = np.empty((ny, nx, TAG_BITS), dtype=np.uint8)
        for r in range(ny):
            for c in range(nx):
                out[r, c] = self.tag(int(addresses[r, c]), int(digests[r, c]))
        return out
