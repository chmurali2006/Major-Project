"""Keyed fragile watermark evidence (8x8 blocks, Haar details, QIM tags).

This is a research integrity signal, not a proof of cryptographic unforgeability.
The benchmark uses public test keys; an attacker knowing those constants is not
excluded by the experiments. Wrong-key/rekey behaviour is measured by the runner.
No clinical safety, adversarial-security or literature-novelty claim follows from
these functions alone.
"""

from __future__ import annotations

import hashlib
import hmac

import numpy as np

BLOCK = 8
DELTA = 8.0
N_SLOTS = 60


# ---------------------------------------------------------------- luma

def luma(rgb: np.ndarray) -> np.ndarray:
    rgb = np.asarray(rgb, np.float64)
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


# ---------------------------------------------------------------- haar

def haar2(x: np.ndarray) -> dict[str, np.ndarray]:
    """Two-level 2D Haar on a (H, W) plane, stride-2, block-local for 8x8 tiles.

    With H, W multiples of 8 the level-1 tiles are 4x4 and level-2 tiles are
    2x2, so no coefficient ever mixes two blocks. That is what lets the verifier
    read each block in isolation.
    """
    def _lvl(a):
        a00, a01 = a[0::2, 0::2], a[0::2, 1::2]
        a10, a11 = a[1::2, 0::2], a[1::2, 1::2]
        return ((a00 + a01 + a10 + a11) / 2.0,
                (a00 + a01 - a10 - a11) / 2.0,
                (a00 - a01 + a10 - a11) / 2.0,
                (a00 - a01 - a10 + a11) / 2.0)

    ll1, lh1, hl1, hh1 = _lvl(x)
    ll2, lh2, hl2, hh2 = _lvl(ll1)
    return {"LL2": ll2, "LH2": lh2, "HL2": hl2, "HH2": hh2,
            "LH1": lh1, "HL1": hl1, "HH1": hh1}


def haar2_inverse(c: dict[str, np.ndarray]) -> np.ndarray:
    def _ilvl(ll, lh, hl, hh):
        a = np.zeros((ll.shape[0] * 2, ll.shape[1] * 2), np.float64)
        a[0::2, 0::2] = (ll + lh + hl + hh) / 2.0
        a[0::2, 1::2] = (ll + lh - hl - hh) / 2.0
        a[1::2, 0::2] = (ll - lh + hl - hh) / 2.0
        a[1::2, 1::2] = (ll - lh - hl + hh) / 2.0
        return a
    ll1 = _ilvl(c["LL2"], c["LH2"], c["HL2"], c["HH2"])
    return _ilvl(ll1, c["LH1"], c["HL1"], c["HH1"])


def details(c: dict[str, np.ndarray]) -> np.ndarray:
    """(ny, nx, 60) view of the detail coefficients, band order fixed."""
    bands = [c["LH1"], c["HL1"], c["HH1"], c["LH2"], c["HL2"], c["HH2"]]
    ny, nx = c["LL2"].shape[0] // 2, c["LL2"].shape[1] // 2
    out = []
    for b in bands:
        k = b.shape[0] // ny
        # (ny, k, nx, k) -> transpose -> (ny, nx, k, k) -> flatten the tile.
        # Reshaping (ny, k, nx, k) straight to (ny, nx, k*k) collapses the axes
        # in the wrong order and scatters one block's coefficients across
        # several blocks. It still round-trips, so an inverse-only test passes
        # while block locality is destroyed.
        out.append(b.reshape(ny, k, nx, k).transpose(0, 2, 1, 3).reshape(ny, nx, k * k))
    return np.concatenate(out, axis=2)


def details_set(c: dict[str, np.ndarray], flat: np.ndarray) -> dict[str, np.ndarray]:
    """Inverse of `details`."""
    ny, nx = c["LL2"].shape[0] // 2, c["LL2"].shape[1] // 2
    out = dict(c)
    i = 0
    for name, k in [("LH1", 4), ("HL1", 4), ("HH1", 4), ("LH2", 2), ("HL2", 2), ("HH2", 2)]:
        blk = (flat[:, :, i:i + k * k].reshape(ny, nx, k, k)
               .transpose(0, 2, 1, 3).reshape(ny * k, nx * k))
        out[name] = blk
        i += k * k
    return out


# ---------------------------------------------------------------- keying

def _key_stream(key: bytes, image_id: int, n_blocks: int) -> tuple[np.ndarray, np.ndarray]:
    """60 keyed pad bits and a 16-entry selector, per block."""
    # int() coercion is deliberate: callers pass numpy integers constantly
    # (array indices), and numpy ints have no .to_bytes.
    m = hmac.new(key, int(image_id).to_bytes(4, "big"), hashlib.sha256).digest()
    rng = np.random.default_rng(int.from_bytes(m[:8], "big"))
    pad = rng.integers(0, 2, (n_blocks, N_SLOTS)).astype(np.uint8)
    sel = rng.integers(0, 2, (n_blocks, 16)).astype(np.uint8)
    return pad, sel


def signature(flat: np.ndarray, delta: float = DELTA) -> np.ndarray:
    """Which lattice cell each coefficient sat in. Exactly recoverable after
    marking, because the QIM offset never crosses a cell boundary."""
    return np.round(flat / delta).astype(np.int64)


def _dc_code(ll2: np.ndarray) -> np.ndarray:
    """A coarse 4-bit code of the block mean, from the band the mark never writes.

    LL2 holds 4x the block mean (two levels of unnormalised Haar), so its range
    is 0..1020 on an 8-bit image. Dividing by 16 and masking to 4 bits gives a
    16-way code: coarse enough that a small perturbation cannot flip it, fine
    enough that replacing a block's content usually does.
    """
    ll2 = np.asarray(ll2, np.float64)
    ny, nx = ll2.shape[0] // 2, ll2.shape[1] // 2
    m = ll2[:ny * 2, :nx * 2].reshape(ny, 2, nx, 2).mean(axis=(1, 3))
    return (np.floor(m / 16.0).astype(np.int64) & 0xF)


def tags(key: bytes, image_id: int, flat: np.ndarray,
         ll2_means: np.ndarray, delta: float = DELTA) -> np.ndarray:
    """(ny, nx, 60) expected tag bits."""
    ny, nx = flat.shape[:2]
    pad, sel = _key_stream(key, image_id, ny * nx)
    sig = signature(flat, delta).reshape(ny * nx, N_SLOTS)
    dc = _dc_code(ll2_means).reshape(ny * nx, 1)
    idx = (sig + dc) % 16
    chosen = np.take_along_axis(sel, idx, axis=1)
    return (pad ^ chosen).reshape(ny, nx, N_SLOTS).astype(np.uint8)


# ---------------------------------------------------------------- embed / read

def embed(rgb: np.ndarray, key: bytes, image_id: int,
          delta: float = DELTA, amp: float | None = None) -> np.ndarray:
    """Write the keyed tag into the 60 detail slots of every block."""
    y = luma(rgb)
    c = haar2(y)
    flat = details(c)
    a = delta / 4.0 if amp is None else float(amp)
    t = tags(key, image_id, flat, c["LL2"], delta)
    q = np.round(flat / delta) * delta
    marked = q + (2.0 * t.astype(np.float64) - 1.0) * a
    y2 = haar2_inverse(details_set(c, marked))
    y2 = np.clip(y2, 0, 255)
    # put the marked luma back, keeping colour
    rgb = np.asarray(rgb, np.float64)
    gained = y2 - y
    out = rgb + gained[..., None]
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def read(rgb: np.ndarray, key: bytes, image_id: int,
         delta: float = DELTA, amp: float | None = None) -> dict[str, np.ndarray]:
    """Produce the two evidence maps the network consumes."""
    a = delta / 4.0 if amp is None else float(amp)
    y = luma(rgb)
    c = haar2(y)
    flat = details(c)
    r = flat - np.round(flat / delta) * delta         # residual from the lattice
    t = tags(key, image_id, flat, c["LL2"], delta)
    s = 2.0 * t.astype(np.float64) - 1.0

    num = (r * s).sum(axis=2)
    den = np.maximum(np.abs(r).sum(axis=2), 1e-9)
    corr = num / den                                   # 1 = exact tag, 0 = none
    survival = (np.abs(r) > 0.5 * a).mean(axis=2)      # fraction of readable slots
    return {"corr": corr, "E": 1.0 - corr, "S": survival}


# ---------------------------------------------------------------- richer read

BAND_SLICES = ((0, 16), (16, 32), (32, 48), (48, 52), (52, 56), (56, 60))
BAND_NAMES = ("LH1", "HL1", "HH1", "LH2", "HL2", "HH2")


def read_rich(rgb, key, image_id, delta=DELTA, amp=None):
    """Like `read`, but keeps the per-band structure instead of collapsing to two
    scalars.

    Why: `read` throws away 58 of the 60 per-block observations. Measuring
    linear separability of tampered vs untouched blocks, the collapsed pair
    (corr, survival) reached 0.990 held-out AUC and the richer set reached
    0.995. That is a small gain, not a large one -- the keyed evidence is
    already highly separable -- but it is free, and a downstream network can
    only use what it is given.

    Returns, all (ny, nx):
        corr       whole-block tag agreement      (high = intact)
        surv       fraction of readable slots     (low = mark decayed)
        peak       largest |residual| in block    (AUC 0.90 toward tampered)
        mag        mean |residual|
        band_*     6 per-band agreements
    """
    a = delta / 4.0 if amp is None else float(amp)
    y = luma(rgb)
    c = haar2(y)
    flat = details(c)
    r = flat - np.round(flat / delta) * delta
    t = tags(key, image_id, flat, c["LL2"], delta)
    s = 2.0 * t.astype(np.float64) - 1.0

    corr = (r * s).sum(axis=2) / np.maximum(np.abs(r).sum(axis=2), 1e-9)
    out = {
        "corr": corr,
        "E": 1.0 - corr,
        "surv": (np.abs(r) > 0.5 * a).mean(axis=2),
        "peak": np.abs(r).max(axis=2),
        "mag": np.abs(r).mean(axis=2),
    }
    for name, (lo, hi) in zip(BAND_NAMES, BAND_SLICES):
        out["band_" + name] = ((r[:, :, lo:hi] * s[:, :, lo:hi]).sum(axis=2)
                               / np.maximum(np.abs(r[:, :, lo:hi]).sum(axis=2), 1e-9))
    return out


RICH_CHANNELS = ("E", "surv", "peak", "mag",
                 "band_LH1", "band_HL1", "band_HH1", "band_LH2", "band_HL2", "band_HH2")


def rich_tensor(rgb, key, image_id, **kw):
    """(10, ny, nx) float32 stack in the order given by RICH_CHANNELS."""
    d = read_rich(rgb, key, image_id, **kw)
    return np.stack([d[c] for c in RICH_CHANNELS]).astype(np.float32)


# ---------------------------------------------------------------- dual carrier
#
# Everything above is Carrier A alone: the fragile mark. The reference system
# embeds two marks, and its own ablation prices the second one at -0.067 IoU when
# removed -- more than its attention module costs. `carriers.py` implements it.
#
# The order below is NOT incidental. See amendment A-002 and carriers.py.

from . import carriers as _carriers      # noqa: E402

# Two named protection profiles. The single-carrier profile is the one the
# measured classical result was produced under and must stay bit-reproducible;
# the dual-carrier profile is the balanced configuration above. Adding Carrier B
# forced a rebalance of Carrier A's amplitude, and that rebalance is a measured
# decision, not a tuning convenience -- see the sweep in carriers.py.
PROTECT_PROFILES = {
    "single": {"delta": DELTA, "beta": None},     # Carrier A only; the measured C0
    "dual":   {"delta": 4.0,   "beta": 3.0},      # both carriers; PSNR 40.76 dB
}
DEFAULT_PROFILE = "dual"

SEMI_CHANNELS = ("semi", "semi_abs", "semi_surv")
FULL_CHANNELS = RICH_CHANNELS + SEMI_CHANNELS          # 13 channels
N_FULL = len(FULL_CHANNELS)


def _profile(profile: str, delta: float | None, beta: float | None):
    """Resolve a named profile, letting explicit arguments override it."""
    if profile not in PROTECT_PROFILES:
        raise ValueError(f"unknown profile {profile!r}; "
                         f"choose from {sorted(PROTECT_PROFILES)}")
    p = PROTECT_PROFILES[profile]
    return (p["delta"] if delta is None else float(delta),
            p["beta"] if beta is None else float(beta))


def protect(rgb: np.ndarray, key: bytes, image_id: int,
            profile: str = DEFAULT_PROFILE,
            delta: float | None = None, beta: float | None = None) -> np.ndarray:
    """Apply both carriers in the only order that works.

        Carrier B (semi-robust, DCT)  ->  Carrier A (fragile, Haar)

    B first because it is the larger perturbation (beta = 4 per coefficient
    against A's Delta/4 = 2), and because A's tag is a function of the block's
    own detail coefficients -- computing that function after B is written binds
    the tag to the content as it will actually be stored. Writing B afterwards
    would leave every tag stale by exactly B's contribution.
    """
    d, b = _profile(profile, delta, beta)
    marked = rgb if b is None else _carriers.embed(rgb, key, image_id, beta=b)
    return embed(marked, key, image_id, delta=d)


def read_full(rgb: np.ndarray, key: bytes, image_id: int,
              profile: str = DEFAULT_PROFILE,
              delta: float | None = None,
              beta: float | None = None) -> dict[str, np.ndarray]:
    """All 13 evidence channels: 10 fragile + 3 semi-robust.

    The three semi channels answer a question the fragile ten cannot:

        semi, semi_abs, semi_surv provide possible cues about mark survival.

    They cannot prove whether an edit was benign or malicious. Their empirical
    usefulness is measured against controls, including any regressions.
    """
    dt, bt = _profile(profile, delta, beta)
    out = read_rich(rgb, key, image_id, delta=dt)
    out.update(_carriers.read(rgb, key, image_id,
                              beta=_carriers.BETA if bt is None else bt))
    return out


def full_tensor(rgb: np.ndarray, key: bytes, image_id: int,
                **kw) -> np.ndarray:
    """(13, ny, nx) float32 in the order given by FULL_CHANNELS."""
    d = read_full(rgb, key, image_id, **kw)
    return np.stack([d[c] for c in FULL_CHANNELS]).astype(np.float32)
