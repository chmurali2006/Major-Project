"""The two carriers.

Carrier A - fragile, position-bound tags (assignment A-001/A-002).
    write: q = round(c/delta)*delta ;  c' = q + (2b-1)*delta/4
    read : bit = 1 if (c - q) > 0 else 0

The reader is the sign of the residual, not PFF-WM's floor rule. Their rule
places the embedded point exactly on the decision boundary, which reads as a
coin flip under any floating-point noise; measured 50% bit error on a clean
image. See A-001.

Carrier B - semi-robust, address-keyed spread spectrum (A-004/A-005).
    c' = c + beta(block) * w(block) * p(block, u, v)
Both p and w are keyed by (key, image_id, block address), so a moved block
carries the wrong reference and lands in TAMPERED rather than in the benign
handling cell.

Embedding order is B then A (A-002): A must be written last or B re-breaks it.
"""

from __future__ import annotations

import hashlib
import hmac

import numpy as np
from scipy.fft import dctn, idctn

from .config import N_BLOCKS

# ---------------------------------------------------------------- Carrier A


#: Synthesis energy of a unit impulse in each subband of the *integer* transform,
#: measured by inverse-transforming a single coefficient (scripts/verify_gain.py).
#: The lifting form is not orthonormal, so a level-2 coefficient moves eight
#: times the pixel energy a level-1 one does. Writing the same amplitude into
#: every slot therefore put most of the distortion in 12 of the 60 slots and
#: cost 0.8 dB of PSNR. The amplitude below is round(delta/4 / sqrt(energy)),
#: floored at one level: the smallest integer that still lands clear of the
#: lattice point at the centre of its cell.
SUB_ENERGY = (("LH1", 2.0), ("HL1", 2.0), ("HH1", 1.0),
              ("LH2", 8.0), ("HL2", 8.0), ("HH2", 4.0))


def slot_amplitude(delta: float, floor: int = 1) -> np.ndarray:
    """Per-slot mark amplitude, in integer coefficient levels, order = SUBORDER."""
    from .transform import SUBORDER
    energy = dict(SUB_ENERGY)
    out = []
    for name, _width in SUBORDER:
        amp = max(floor, int(round((delta / 4.0) / np.sqrt(energy[name]))))
        out.append(np.full(_width * _width, amp, dtype=np.float64))
    return np.concatenate(out)


class FragileCarrier:
    def __init__(self, delta: float, amp: np.ndarray | None = None):
        self.delta = float(delta)
        self.amp = slot_amplitude(self.delta) if amp is None else np.asarray(amp, np.float64)
        if self.amp.shape != (60,):
            raise ValueError("amp must have one entry per detail slot")
        #: smallest residual that counts as "readable" - half the weakest slot
        self.amp_min = float(self.amp.min())

    def write(self, coeff: np.ndarray, bits: np.ndarray) -> np.ndarray:
        """coeff, bits: (ny, nx, 60). Returns marked coefficients."""
        q = np.round(coeff / self.delta) * self.delta
        return q + (2.0 * bits.astype(np.float64) - 1.0) * self.amp

    def read(self, coeff: np.ndarray, q: np.ndarray | None = None) -> np.ndarray:
        q = np.round(coeff / self.delta) * self.delta if q is None else q
        return (coeff - q > 0).astype(np.uint8)

    def evidence(self, coeff: np.ndarray, q: np.ndarray | None = None) -> np.ndarray:
        """Fraction of the 60 tag slots holding a residual big enough to read.

        A marked block whose pixels never touch the gamut holds a full mark in
        every slot, so this is 1.0. A block that has been through a global
        transform - resampling, added noise, recompression - holds a shrunken
        one. Measured over blocks that are decidable (not excused for gamut
        reasons), PH2 gives 1.00 for clean images and for every copy-move edit,
        against 0.55-0.61 for a 90% resize round trip and 0.88 for sigma=1.
        The populations do not overlap, which is what makes this the test for
        'the image was changed as a whole'.
        """
        q = np.round(coeff / self.delta) * self.delta if q is None else q
        return (np.abs(coeff - q) > 0.5 * self.amp_min).mean(axis=2)

    def score(self, coeff: np.ndarray, bits: np.ndarray,
              q: np.ndarray | None = None) -> np.ndarray:
        """Per-block normalised correlation between residual and expected tag.

        `read` asks each of the 60 bits independently, which is brittle: a
        pixel pushed against the RGB gamut saturates its share of the mark and
        flips a whole run of bits at once, so a clean block can disagree with
        20% of its own tag. The matched filter asks the weaker and correct
        question - is the residual *vector* aligned with the keyed sign vector
        - and is therefore insensitive to how much of the mark survived.

        1.0 means the residual is exactly the expected pattern, 0.0 means no
        relation. For a block carrying no tag the statistic is centred on zero
        with standard deviation 1/sqrt(60) = 0.13, so TAU_F is set at 3 of
        those standard deviations.
        """
        q = np.round(coeff / self.delta) * self.delta if q is None else q
        r = coeff - q
        s = 2.0 * np.asarray(bits, np.float64) - 1.0
        num = (r * s).sum(axis=2)
        den = np.maximum(np.abs(r).sum(axis=2), 1e-9)
        return num / den

    @staticmethod
    def would_clip(marked_plane: np.ndarray) -> np.ndarray:
        """Per-block flag: any pixel outside 0..255 after the inverse transform.

        Trap 5: a block that would clip is refused and recorded, never clipped
        silently, because a clipped pixel destroys its own tag.
        """
        bad = (marked_plane < 0.0) | (marked_plane > 255.0)
        ny, nx = marked_plane.shape[0] // 8, marked_plane.shape[1] // 8
        return bad.reshape(ny, 8, nx, 8).any(axis=(1, 3))


# ---------------------------------------------------------------- Carrier B


def band_indices(lo: int, hi: int) -> np.ndarray:
    idx = np.array([(u, v) for u in range(8) for v in range(8) if lo <= u + v <= hi])
    if len(idx) == 0:
        raise ValueError("empty mid-frequency band")
    return idx


def _keyed_stream(key: bytes, image_id: int, n: int, n_blocks: int) -> tuple[np.ndarray, np.ndarray]:
    """Unit sequences P (n_blocks, n) and keyed signs W (n_blocks,).

    The address enters as the row index, so a block pasted from address A
    still carries row A while the verifier reads row B.
    """
    m = hmac.new(key, image_id.to_bytes(4, "big"), hashlib.sha256).digest()
    rng = np.random.default_rng(int.from_bytes(m[:8], "big"))
    p = rng.standard_normal((n_blocks, n))
    p /= np.linalg.norm(p, axis=1, keepdims=True)
    signs = np.where(rng.integers(0, 2, n_blocks) == 1, 1.0, -1.0)
    return p, signs


class RobustCarrier:
    def __init__(self, key: bytes, image_id: int, beta0: float, lam: float,
                 lo: int, hi: int, shape: tuple[int, int] = (512, 512)):
        self.beta0, self.lam = float(beta0), float(lam)
        self.idx = band_indices(lo, hi)
        ny, nx = shape[0] // 8, shape[1] // 8
        self.ny, self.nx = ny, nx
        self.P, self.W = _keyed_stream(key, image_id, len(self.idx), ny * nx)
        self.Wb = self.W.reshape(ny, nx)

    # -- embed -------------------------------------------------------
    def write(self, blocks: np.ndarray, region: np.ndarray | None = None,
              headroom_scale: np.ndarray | None = None) -> np.ndarray:
        """blocks (ny,nx,8,8); region (ny,nx) in {0,1} drives the strength.

        headroom_scale in [0,1] throttles the mark where the pixels sit close
        to the RGB gamut edge. Dermoscopy images are full of such pixels -
        vignette corners and specular highlights - and an unthrottled
        spread-spectrum add pushes them out of gamut, which then forces the
        frag ile carrier's fit to reject the block. Throttling here keeps the
        block markable and costs only reference strength where there was no
        room for it anyway.
        """
        beta = self.beta0 * (1.0 + self.lam * (region if region is not None else 0.0))
        if headroom_scale is not None:
            beta = beta * headroom_scale
        C = dctn(blocks, axes=(2, 3), norm="ortho")
        u, v = self.idx[:, 0], self.idx[:, 1]
        C[:, :, u, v] += beta[:, :, None] * self.Wb[:, :, None] * self.P.reshape(self.ny, self.nx, -1)
        return idctn(C, axes=(2, 3), norm="ortho")

    # -- read --------------------------------------------------------
    def read(self, blocks: np.ndarray) -> np.ndarray:
        """Per-block error in [0, 1]. 0 = reference intact, 0.5 = replaced.

        Normalised by beta0 only. Blocks inside the lesion were written at
        (1+lam)*beta0, so their score saturates above 1 and clips to 0 error.
        The verifier therefore needs no mask - a standing validity rule.
        """
        if self.beta0 <= 0:
            # ablation: Carrier B removed. No reference, so it has no opinion.
            return np.zeros(blocks.shape[:2], dtype=np.float64)
        C = dctn(np.asarray(blocks, dtype=np.float64), axes=(2, 3), norm="ortho")
        u, v = self.idx[:, 0], self.idx[:, 1]
        obs = np.einsum("ijc,ijc->ij", C[:, :, u, v], self.P.reshape(self.ny, self.nx, -1))
        signed = self.Wb * obs / self.beta0
        return np.clip(0.5 * (1.0 - signed), 0.0, 1.0)


# ---------------------------------------------------------------- region map


def block_region(region_mask: np.ndarray, ny: int, nx: int, threshold: float = 0.5) -> np.ndarray:
    """Fractional mask -> per-block 0/1 dominance."""
    frac = np.asarray(region_mask, dtype=np.float64).reshape(ny, 8, nx, 8).mean(axis=(1, 3))
    return (frac > threshold).astype(np.float64)
