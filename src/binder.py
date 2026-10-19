"""Tag binder: position-bound, content-bound keyed tags.

    signature = round(detail / delta)         60 values, the block's own texture
    tag       = BLAKE2b(key, image_id || address || signature)[:60]

Why the signature is the detail coefficients and not a coarse digest
--------------------------------------------------------------------
The original design hashed the level-2 approximation (LL2). That is the only
subband the mark does not write, so it looked like the natural choice. It is
not usable: LL2 is 4 x the quadrant means, i.e. 0..1020 on an 8-bit image,
and the quantiser clipped at +-3 steps of 32. Every block of every real image
therefore produced the same digest - measured: one unique value over 4096
blocks on PH2 - so the tag named the address and nothing else.

That is a forgery path, not a cosmetic defect. An attacker who holds one
protected image can read the residual signs straight out of the pixels, paste
arbitrary content, and write those same signs back: the verifier recomputes
the same address-only tag and accepts the forgery. Measured against the old
binder: 180 blocks replaced, 116 of them reported INTACT, zero TAMPERED.

The fix exploits exactness. With the integer lifting transform (see
transform.Haar2Int) the embedding stage leaves the coefficient quantisation
index untouched: it writes q +- delta/4, and round((q +- delta/4)/delta) is
still q/delta. So the index that the verifier recovers with
`signature()` is bit-identical to the one the embedder saw in the *unmarked*
block, and it is a function of the block's own texture.

Why the content enters per slot, not through the message
--------------------------------------------------------
Hashing the whole signature into one MAC is exact but brittle: a single
coefficient moved across a cell boundary flips every one of the 60 tag bits.
That happens on a *clean* image wherever the RGB gamut pins a pixel - pure red
and pure black are common in dermoscopy - because a pinned pixel cannot carry
a luma mark and the clip moves its coefficients. Measured: a whole-block MAC
made 0.6%, 7.3% and 23.1% of the blocks of three clean PH2 images read as
tampered.

So the keyed material is a 60-bit pad plus a 16-bit selector, and slot i takes

    tag_i = pad_i XOR selector_bit[sig_i mod 16]

A content change flips slot i with probability one half - the ceiling for a
single bit - so a transplanted mark has expected correlation zero with its
host, while a clipped pixel damages only the slots it actually touches and
the correlation degrades gracefully. An
attacker who copies the visible signs and cannot see the pad keeps one bit of
uncertainty per slot: guessing a whole block costs 2^-59, the same as
forging the MAC. One bit per slot is the ceiling for any tag that can be
read out of the pixels at all.

`delta` is the carrier's own step, so no extra parameter is introduced: the
signature is exactly the lattice cell each coefficient sat in before marking.
"""

from __future__ import annotations

import hashlib

import numpy as np

from .config import TAG_BITS


def signature(coeff: np.ndarray, delta: float, sig_delta: float,
              q: np.ndarray | None = None) -> np.ndarray:
    """Coarse content code of each detail coefficient.

    The embedder signs the *lattice point* q = round(c/delta)*delta, not the
    raw coefficient. The verifier recovers q +- amp from the marked block, so
    quantising q at a multiple of the carrier's step - `sig_delta` must be an
    integer multiple of `delta` - is stable by construction: q is never closer
    than `delta` to a `sig_delta` boundary, and the amplitude is smaller than
    `sig_delta / 2`. Signing the raw coefficient instead left the residual
    quantisation error in the comparison and made 4% of clean blocks disagree
    with their own tag for no reason at all.
    """
    if q is None:
        q = np.round(np.asarray(coeff, np.float64) / delta) * delta
    return np.clip(np.round(q / sig_delta), -127, 127).astype(np.int8)


class Binder:
    """Keyed, position-bound tag generator. The key never travels."""

    _ADDR = tuple(i.to_bytes(4, "big") for i in range(4096))

    #: 8 bytes of pad bits + 2 bytes of selector = 10
    _RAW = 10

    def __init__(self, key: bytes, image_id: int, bind_address: bool = True):
        if not key:
            raise ValueError("empty key")
        self.bind_address = bool(bind_address)
        if not 0 <= image_id < 2**32:
            raise ValueError("image_id must fit in 32 bits")
        self._image_id = image_id
        if not 0 < len(key) <= 64:
            raise ValueError("BLAKE2b keys must be 1..64 bytes")
        self._key = key
        self._prefix = image_id.to_bytes(4, "big")
        # A primed hash object, copied per block, is about twice as fast as
        # constructing one: the key schedule and the BLAKE2 parameter block are
        # computed once here instead of 4096 times inside verify.
        self._base = hashlib.blake2b(key=key, digest_size=self._RAW,
                                     person=self._prefix)

    def _raw(self, address: int) -> bytes:
        """One keyed BLAKE2b call per block (RFC 7693).

        HMAC-SHA256 is the conventional choice and was used until latency was
        measured: it needs two padded compression calls per block, 4096 times
        per verification, and that was half of verify's total cost. Keyed
        BLAKE2b is a standard MAC with the key folded into its initial state,
        so it needs one call, and it is bit-for-bit deterministic. Both give
        2^-60 forgery resistance once truncated to the 60-bit tag, so the
        security argument does not change; only the cost does. Recorded as
        A-022 with both timings measured.

        The image id is bound through the key schedule rather than the message
        so that two images protected with the same key cannot share tags.
        """
        h = self._base.copy()
        if self.bind_address:
            h.update(self._ADDR[address])
        return h.digest()

    @staticmethod
    def _mix(raw: bytes, sig) -> np.ndarray:
        """pad XOR selector bit chosen by each coefficient's own content."""
        bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8))
        pad = bits[:TAG_BITS]
        sel = int.from_bytes(raw[8:10], "big")
        index = (np.asarray(sig, np.int64) & 15).astype(np.int64)
        chosen = (sel >> index) & 1
        return pad ^ chosen.astype(np.uint8)

    def tag(self, address: int, sig) -> np.ndarray:
        return self._mix(self._raw(int(address)), sig)

    def tags(self, addresses: np.ndarray, signatures: np.ndarray) -> np.ndarray:
        """All block tags at once.

        The per-block cost here is the single largest item in verify, so the
        loop builds the raw MAC bytes and unpacks them in one numpy call
        instead of once per block. Same tags, same security argument.
        """
        ny, nx = signatures.shape[:2]
        buf = bytearray()
        for r in range(ny):
            for c in range(nx):
                buf += self._raw(int(addresses[r, c]))
        raws = np.frombuffer(bytes(buf), dtype=np.uint8).reshape(ny * nx, self._RAW)
        bits = np.unpackbits(raws, axis=1)[:, :TAG_BITS].reshape(ny, nx, TAG_BITS)
        sels = (raws[:, 8].astype(np.int64) << 8) | raws[:, 9].astype(np.int64)
        index = (np.asarray(signatures, np.int64) & 15).reshape(ny * nx, -1)
        chosen = (sels[:, None] >> index) & 1
        return bits ^ chosen.astype(np.uint8).reshape(ny, nx, TAG_BITS)
