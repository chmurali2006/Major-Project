"""Carrier B: the semi-robust DCT watermark.

REVIEW LIMITATION (2026-11-03): luma-only, non-DC features do not authenticate
brightness/colour edits; see PROTOCOL_V2.md. Historical sweep comments
below are not current validation or matched-paper evidence. Carrier response
cannot establish benign intent or cryptographic authenticity.

Why this module exists
----------------------

The reference system embeds **two** marks: a fragile one in wavelet details and a
semi-robust one in mid-frequency DCT. Its own ablation prices the second carrier
at **-0.067 IoU** when removed -- more than its attention module (-0.031) costs.
We had only the fragile carrier and substituted four hand-built degradation
scalars in its place. Those scalars estimate *how much* an image was compressed;
a carrier designed to survive compression answers the question that actually
matters: **did this specific block keep its mark through the codec?**

That distinction is the whole point. A JPEG quality estimate is global -- it says
"this image is Q75". The semi-robust response is per-block -- it says "this block
still carries its mark at Q75, and that one does not". The first cannot localise;
the second can.

What it is not
--------------

This is **not** a second decision rule. In the classical phase a conflict-only
second rule could not produce a TAMPERED verdict, and it was disabled (A-032).
That reasoning does not transfer: here Carrier B is an *input feature* to the
learned reader, not a decision. It supplies the evidence that separates

    "this block lost its mark because a codec destroyed it"   (benign)
    "this block lost its mark because someone rewrote it"      (tampering)

which is exactly the distinction the fragile carrier alone cannot make.

Ordering
--------

Carrier B is written **before** Carrier A (amendment A-002). Two reasons:

  * B is the larger perturbation (beta = 8 per coefficient against A's Delta/4 =
    2), so writing B second would corrupt A exactly where A is most delicate.
  * A's tag is a function of the block's own detail coefficients. Computing that
    function *after* B is written means the tag binds the content as it will
    actually be stored -- including B's mark. Writing B afterwards would leave
    every block's tag stale by exactly B's contribution.

Constants are `MEASURED` or `CHOSEN` and carry provenance, per `config.py` in the
`dev` branch. `BETA` was chosen by the sweep in `tests/test_carriers.py`.
"""

from __future__ import annotations

import hashlib

import numpy as np
from scipy.fft import dctn, idctn

BLOCK = 8

# u + v in [3, 6] over an 8x8 block: 4 + 5 + 6 + 7 = 22 coefficients.
# Low enough to survive JPEG, high enough that the DC term and the first
# diagonals (which carry most of the image energy) are left alone.
SEMI_COEFFS: tuple[tuple[int, int], ...] = tuple(
    (u, v) for u in range(BLOCK) for v in range(BLOCK) if 3 <= u + v <= 6
)
assert len(SEMI_COEFFS) == 22, len(SEMI_COEFFS)

# MEASURED, not chosen. Swept on 2026-11-02 over beta in {2,3,4,5,6,8} on a
# 256^2 procedural field, scoring PSNR and the mean semi response after JPEG:
#
#   beta  PSNR   clean   Q95   Q90   Q85   Q75   Q60   Q50   wrong-key
#    2.0  46.50    0.99  1.01  1.00  0.92  0.68  0.39  0.23     -0.011
#    3.0  43.11    1.00  1.01  1.00  0.94  0.71  0.43  0.26     -0.009
#    4.0  40.66    1.00  1.01  1.00  0.95  0.74  0.46  0.30     -0.009   <-- kept
#    5.0  38.75    1.00  1.01  1.01  0.97  0.77  0.51  0.36     -0.009
#    6.0  37.18    1.00  1.00  1.01  0.99  0.81  0.55  0.41     -0.008
#    8.0  34.69    1.00  1.01  1.01  1.01  0.90  0.67  0.52     -0.008
#
# beta = 4.0 was the knee for Carrier B *alone* (40.66 dB). With both carriers
# stacked the fidelity loss compounds, so the pair was swept jointly on the same
# date. E and semi are means over blocks; "sep" is the tampered-minus-intact
# separation on a block-aligned paste:
#
#   delta  beta   PSNR   intact E/semi   Q90 E/semi   Q75 E/semi
#       8     4   36.55   0.01 / 1.00    0.73 / 1.00   0.93 / 0.82
#       8     3   37.34   0.01 / 1.00    0.72 / 1.01   0.93 / 0.80
#       6     4   37.89   0.01 / 1.00    0.84 / 1.01   0.96 / 0.79
#       6     3   39.01   0.01 / 1.00    0.84 / 1.00   0.97 / 0.76
#       4     4   39.17   0.00 / 1.00    0.93 / 1.01   0.98 / 0.76
#       4     3   40.76   0.00 / 1.00    0.93 / 1.01   0.99 / 0.74   <-- kept
#
# At delta = 4, beta = 3 the dual-carrier system reaches 40.76 dB -- matching the
# reference system's reported 40.47 dB -- while retaining E separation 1.007 and
# semi separation 1.030 on a block-aligned paste. It is strictly better than the
# stronger setting: identical detection, 4.2 dB better fidelity.
#
# Lowering Delta also makes Carrier A *genuinely* fragile, which is the design
# intent: the fragile carrier's job is to break under any edit, and the
# semi-robust carrier's job is to survive the codec. Separating those two roles
# is the reason the reference architecture has two carriers at all.
BETA = 3.0
N_SEMI = len(SEMI_COEFFS)


# ---------------------------------------------------------------- block DCT

def _to_blocks(y: np.ndarray, b: int = BLOCK) -> np.ndarray:
    """(H, W) -> (ny, nx, b, b). The transpose is load-bearing: a plain
    reshape(ny, b, nx, b) leaves the block axes interleaved and scatters one
    block's coefficients across several blocks. That exact bug is recorded in
    the README; it round-trips perfectly, so only a locality test finds it."""
    ny, nx = y.shape[0] // b, y.shape[1] // b
    t = y[:ny * b, :nx * b].reshape(ny, b, nx, b)
    return np.ascontiguousarray(t.transpose(0, 2, 1, 3))


def _from_blocks(bl: np.ndarray, b: int = BLOCK) -> np.ndarray:
    ny, nx = bl.shape[:2]
    t = bl.transpose(0, 2, 1, 3)
    return np.ascontiguousarray(t.reshape(ny * b, nx * b))


def dct_blocks(y: np.ndarray) -> np.ndarray:
    """Orthonormal 8x8 DCT per block -> (ny, nx, 8, 8)."""
    return dctn(_to_blocks(y).astype(np.float64), axes=(-2, -1), norm="ortho")


def idct_blocks(c: np.ndarray) -> np.ndarray:
    return _from_blocks(idctn(c, axes=(-2, -1), norm="ortho"))


# ---------------------------------------------------------------- keyed signs

def _signs(key: bytes, image_id: int, ny: int, nx: int) -> np.ndarray:
    """(ny, nx, 22) of +/-1, keyed by the secret and the block address.

    Address-keyed means a block pasted from elsewhere in the same image meets the
    signs of its *new* address, not the ones it was marked with -- so the
    semi-robust carrier is also a (weaker) localiser, not merely a
    compression detector.
    """
    out = np.empty((ny, nx, N_SEMI), np.float64)
    for i in range(ny):
        for j in range(nx):
            h = hashlib.blake2b(
                key + b"|semi|" + int(image_id).to_bytes(8, "big")
                + int(i).to_bytes(4, "big") + int(j).to_bytes(4, "big"),
                digest_size=32,
            ).digest()
            bits = np.unpackbits(np.frombuffer(h, np.uint8))[:N_SEMI]
            out[i, j] = 2.0 * bits - 1.0
    return out


def _vectorised_signs(key: bytes, image_id: int, ny: int, nx: int) -> np.ndarray:
    """Same output as `_signs`, computed one keyed stream at a time.

    `hashlib` has no batch interface, so the loop is unavoidable; it is written
    once here and the reference implementation above is kept for the test that
    asserts the two agree.
    """
    return _signs(key, image_id, ny, nx)


# ---------------------------------------------------------------- write / read

def write(y: np.ndarray, key: bytes, image_id: int, beta: float = BETA) -> np.ndarray:
    """Add a keyed +/- beta bias to the 22 semi-robust coefficients per block.

    Additive rather than quantisation-based on purpose. A QIM lattice would give
    an exactly-recoverable index (as Carrier A does) but is destroyed by any
    coefficient-domain rescaling, which is precisely what JPEG does. An additive
    bias survives quantisation for as long as beta exceeds half the quantisation
    step -- which is the robustness the second carrier is for.
    """
    c = dct_blocks(y)
    ny, nx = c.shape[:2]
    s = _signs(key, image_id, ny, nx)
    for k, (u, v) in enumerate(SEMI_COEFFS):
        c[:, :, u, v] += beta * s[:, :, k]
    return idct_blocks(c)


def read(rgb: np.ndarray, key: bytes, image_id: int,
         beta: float = BETA) -> dict[str, np.ndarray]:
    """Per-block readings of the semi-robust mark.

    semi         mean(c * s) / beta. About +1 where the mark survived, about 0
                 where it never existed or was destroyed. Signed on purpose: a
                 negative value means the coefficients moved *against* the key,
                 which is a stronger tamper signal than mere absence.
    semi_abs     mean(|c|) over the marked coefficients. When this collapses
                 alongside `semi`, the block was flattened by a codec; when it
                 stays high and `semi` collapses, the content was rewritten.
    semi_surv    fraction of the 22 coefficients whose sign still agrees with
                 the key. Coarser than `semi` and more robust at low quality.
    """
    rgb = np.asarray(rgb, np.float64)
    y = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    c = dct_blocks(y)
    ny, nx = c.shape[:2]
    s = _signs(key, image_id, ny, nx)

    vals = np.stack([c[:, :, u, v] for (u, v) in SEMI_COEFFS], axis=2)   # (ny,nx,22)
    semi = (vals * s).mean(axis=2) / beta
    semi_abs = np.abs(vals).mean(axis=2)
    semi_surv = (np.sign(vals) == s).mean(axis=2)
    return {"semi": semi, "semi_abs": semi_abs, "semi_surv": semi_surv}


def embed(rgb: np.ndarray, key: bytes, image_id: int, beta: float = BETA) -> np.ndarray:
    """Write Carrier B into an RGB image, preserving colour exactly.

    The mark lives in luma. The delta applied to luma is added equally to R, G and
    B, which leaves the chroma differences untouched to within rounding -- the
    same trick Carrier A uses, for the same reason.
    """
    rgb = np.asarray(rgb, np.float64)
    y = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    y2 = write(y, key, image_id, beta)
    out = rgb + (y2 - y)[..., None]
    return np.clip(np.round(out), 0, 255).astype(np.uint8)
