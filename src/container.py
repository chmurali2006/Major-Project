"""Container: reversible colour transform + lossless PNG.

Trap 1: the container is PNG, always. JPEG is an attack, never a container.
Trap 7: RGB -> luma -> RGB is lossy with a floating-point transform, and two
libraries round differently. This module uses the integer reversible colour
transform from JPEG2000, which is bit-exact in both directions:

    Y  = (R + 2G + B) >> 2
    Cb = B - G
    Cr = R - G
    G  = Y - ((Cb + Cr) >> 2) ,  R = Cr + G ,  B = Cb + G

So the protected luma can be recovered from the saved PNG exactly, while the
chroma - and therefore the clinical colour of a dermoscopy image - survives.

Trap 5: a block whose marked luma cannot be represented without clipping is
reverted and recorded as a capacity refusal. It is never clipped silently.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from PIL import Image

from .config import BLOCK, PNG_COMPRESS_LEVEL


def split_rct(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """uint8 RGB (H,W,3) -> integer Y, Cb, Cr. Exact and reversible."""
    rgb = np.asarray(rgb)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("expected (H, W, 3) RGB")
    r = rgb[..., 0].astype(np.int32)
    g = rgb[..., 1].astype(np.int32)
    b = rgb[..., 2].astype(np.int32)
    return (r + 2 * g + b) >> 2, b - g, r - g


def merge_rct(y: np.ndarray, cb: np.ndarray, cr: np.ndarray) -> np.ndarray:
    """Integer Y, Cb, Cr -> uint8 RGB, clipped to range."""
    y = np.asarray(y, dtype=np.int32)
    g = y - ((np.asarray(cb, np.int32) + np.asarray(cr, np.int32)) >> 2)
    r = np.asarray(cr, np.int32) + g
    b = np.asarray(cb, np.int32) + g
    return np.clip(np.stack([r, g, b], axis=-1), 0, 255).astype(np.uint8)


def out_of_range(y: np.ndarray, cb: np.ndarray, cr: np.ndarray) -> np.ndarray:
    """Per-pixel True where the recombination would clip.

    Uses the *integer* inverse RCT, bit for bit the same arithmetic as
    merge_rct. An earlier version used (cb+cr)/4 in floating point, which
    disagrees with (cb+cr)>>2 by up to 0.75 levels; blocks near the gamut edge
    were then reverted after being tagged, and a clean image accused itself.
    """
    y = np.round(np.asarray(y)).astype(np.int32)
    cb = np.asarray(cb, np.int32)
    cr = np.asarray(cr, np.int32)
    g = y - ((cb + cr) >> 2)
    r = cr + g
    b = cb + g
    return (r < 0) | (r > 255) | (g < 0) | (g > 255) | (b < 0) | (b > 255)


def blocks_out_of_range(bad_pixels: np.ndarray) -> np.ndarray:
    ny, nx = bad_pixels.shape[0] // BLOCK, bad_pixels.shape[1] // BLOCK
    return bad_pixels.reshape(ny, BLOCK, nx, BLOCK).any(axis=(1, 3))


def png_bytes(rgb: np.ndarray, text: dict[str, str] | None = None) -> bytes:
    """Lossless PNG. Optional tEXt chunks carry the image id and key check.

    Metadata is never stored in pixels. A stripped tag is detected on the read
    side and answered with CANNOT SAY, never with INTACT.
    """
    buf = io.BytesIO()
    info = None
    if text:
        from PIL.PngImagePlugin import PngInfo
        info = PngInfo()
        for k, v in text.items():
            info.add_text(k, str(v))
    Image.fromarray(np.asarray(rgb, dtype=np.uint8), "RGB").save(
        buf, format="PNG", compress_level=PNG_COMPRESS_LEVEL, optimize=False,
        pnginfo=info)
    return buf.getvalue()


def png_read(data: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(data)).convert("RGB"))


def png_read_with_text(data: bytes) -> tuple[np.ndarray, dict[str, str]]:
    """Pixels and tEXt chunks from a single decode.

    verify() needs both, and opening the PNG twice was a measurable share of
    its latency - the decoder is the expensive part, not the metadata.
    """
    try:
        im = Image.open(io.BytesIO(data))
        text = dict(getattr(im, "text", {}) or {})
        return np.array(im.convert("RGB")), text
    except Exception:
        return png_read(data), {}


def png_text(data: bytes) -> dict[str, str]:
    """tEXt chunks of a PNG, empty dict if none. Lossy formats return {}."""
    try:
        im = Image.open(io.BytesIO(data))
        return dict(getattr(im, "text", {}) or {})
    except Exception:
        return {}


def png_roundtrip(rgb: np.ndarray) -> np.ndarray:
    """Lossless by contract. The test asserts bit equality."""
    return png_read(png_bytes(rgb))


@dataclass(frozen=True)
class Protected:
    """A protected image plus what the embedder had to refuse."""

    rgb: np.ndarray
    y_marked: np.ndarray
    refused: np.ndarray          # per block, bool
    refusal_reason: str          # 'none' | 'clipping'


def compose(y_marked: np.ndarray, rgb_original: np.ndarray) -> Protected:
    """Build the protected RGB from a float marked luma plane.

    Blocks whose pixels would clip are reverted to the original luma and
    recorded, so every admitted block is exactly representable.
    """
    _, cb, cr = split_rct(rgb_original)
    y0, _, _ = split_rct(rgb_original)

    bad = out_of_range(y_marked, cb, cr)
    refused = blocks_out_of_range(bad)

    y = np.array(y_marked, dtype=np.float64)
    y[refused.repeat(BLOCK, 0).repeat(BLOCK, 1)] = \
        y0[refused.repeat(BLOCK, 0).repeat(BLOCK, 1)]
    y = np.clip(np.round(y), 0, 255).astype(np.int32)

    rgb = merge_rct(y, cb, cr)
    reason = "clipping" if refused.any() else "none"
    return Protected(rgb=rgb, y_marked=y, refused=refused, refusal_reason=reason)


def recover_luma(rgb: np.ndarray) -> np.ndarray:
    """The verifier's only conversion. Pinned and exact."""
    y, _, _ = split_rct(rgb)
    return y.astype(np.float64)


# ---------------------------------------------------------------- range fitting


def luma_bounds(cb: np.ndarray, cr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-pixel luma interval that keeps R, G and B inside 0..255.

    Derived from the inverse RCT:
        g = y - (cb+cr)/4 ,  r = y + (3cr-cb)/4 ,  b = y + (3cb-cr)/4
    """
    cb = np.asarray(cb, np.float64)
    cr = np.asarray(cr, np.float64)
    s = (cb + cr) / 4.0
    lows = np.stack([s, -(3 * cr - cb) / 4.0, -(3 * cb - cr) / 4.0])
    highs = np.stack([255.0 + s, 255.0 - (3 * cr - cb) / 4.0, 255.0 - (3 * cb - cr) / 4.0])
    return lows.max(axis=0), highs.min(axis=0)


def fit_block_luma(y: np.ndarray, cb: np.ndarray, cr: np.ndarray,
                   margin: float = 6.0, max_shift: float = 12.0):
    """Shift whole blocks by an integer DC offset so the mark cannot clip.

    A constant offset inside an 8x8 block changes only LL, never the detail
    coefficients that carry the tag, so a shifted block stays embeddable.
    The shift is applied *before* the digest is computed, so the tag and the
    digest agree. Blocks that cannot be fitted within max_shift are refused.
    """
    lo, hi = luma_bounds(cb, cr)
    ny, nx = y.shape[0] // BLOCK, y.shape[1] // BLOCK
    lo_b = lo.reshape(ny, BLOCK, nx, BLOCK).max(axis=(1, 3))
    hi_b = hi.reshape(ny, BLOCK, nx, BLOCK).min(axis=(1, 3))
    yb = y.reshape(ny, BLOCK, nx, BLOCK)
    need_lo = np.ceil(lo_b + margin - yb.min(axis=(1, 3)))
    need_hi = np.floor(hi_b - margin - yb.max(axis=(1, 3)))
    shift = np.where(need_lo > 0, need_lo, np.where(need_hi < 0, need_hi, 0.0))
    refused = (np.abs(shift) > max_shift) | (hi_b - lo_b < 2 * margin)
    shift = np.where(refused, 0.0, shift)
    out = (yb + shift[:, None, :, None]).reshape(y.shape)
    return out, refused


def field_mask(y: np.ndarray, hi: int = 250, lo: int = 5,
               frac: float = 0.9) -> np.ndarray:
    """Blocks outside the imaging field: saturated white or black surround.

    Dermoscopy images are a circular field of view on a white or black
    background. Those blocks have no headroom to carry a mark, and they say
    nothing about integrity. They are excluded at embed time and excused at
    verify time, and they never count toward the tamper decision.

    The predicate is a fraction of saturated pixels, not a margin in levels, so
    it survives the two-level change a mark makes and survives JPEG, which
    leaves a flat 255 region a flat 255 region.

    Only the component of that surround *connected to the image border* is
    excused. A saturated patch in the middle of the image is not background -
    it is what an attacker paints to hide an edit behind an abstention, and
    the battery's burned-in-text condition does exactly that. Restricting the
    excuse to the border-connected surround closes that hole without touching
    a legitimate capture, whose surround always reaches the border.
    """
    y = np.asarray(y)
    ny, nx = y.shape[0] // BLOCK, y.shape[1] // BLOCK
    b = y.reshape(ny, BLOCK, nx, BLOCK)
    white = (b >= hi).mean(axis=(1, 3))
    black = (b <= lo).mean(axis=(1, 3))
    saturated = (white > frac) | (black > frac)
    if not saturated.any():
        return saturated
    labels, _ = ndimage.label(saturated)
    border = np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    keep = np.unique(border[border > 0])
    return np.isin(labels, keep)


def unmarkable(y: np.ndarray, cb: np.ndarray, cr: np.ndarray,
               margin: float, max_shift: float, slack: float = 0.0) -> np.ndarray:
    """Blocks whose luma cannot carry the mark without leaving the RGB gamut.

    Depends only on chroma (which no carrier touches) and on the block's luma
    extent (which a mark moves by at most two levels). The verifier can compute
    it from the received image alone, so these blocks are excused rather than
    accused - and they never count toward the tamper decision.

    `slack` widens the excused set. Verification passes slack > 0 so that any
    block marked at embed time is still considered markable later; a block can
    only ever be excused, never newly accused, by this rule.
    """
    lo_b, hi_b = luma_bounds(cb, cr)
    ny, nx = y.shape[0] // BLOCK, y.shape[1] // BLOCK
    lo_b = lo_b.reshape(ny, BLOCK, nx, BLOCK).max(axis=(1, 3))
    hi_b = hi_b.reshape(ny, BLOCK, nx, BLOCK).min(axis=(1, 3))
    yb = np.asarray(y, np.float64).reshape(ny, BLOCK, nx, BLOCK)
    need = np.maximum.reduce([
        np.zeros_like(lo_b),
        lo_b + margin - yb.min(axis=(1, 3)),
        -(hi_b - margin - yb.max(axis=(1, 3))),
    ])
    return need > (max_shift - slack)


# ---------------------------------------------------------------- exact gamut


def exact_bounds(cb: np.ndarray, cr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Exact per-pixel luma interval for the *integer* inverse RCT.

    The inverse uses `g = y - ((cb+cr) >> 2)`, so the bounds depend on that
    integer shift t, not on (cb+cr)/4. Using the real-valued form leaves a
    one-level disagreement, and a one-level disagreement at the gamut edge is
    exactly what makes a block revert after it was already tagged.
    """
    cb = np.asarray(cb, np.int32)
    cr = np.asarray(cr, np.int32)
    t = (cb + cr) >> 2
    low = t - np.minimum(0, np.minimum(cb, cr))
    high = 255 + t - np.maximum(0, np.maximum(cb, cr))
    return low, high


def block_gamut(y: np.ndarray, cb: np.ndarray, cr: np.ndarray):
    """Per-block slack toward each gamut edge, in luma levels.

    For every pixel the legal luma interval is [low_i, high_i]. Shifting a block
    by s keeps it legal iff  max_i(low_i - y_i) <= s <= min_i(high_i - y_i).
    The bounds must be reduced *after* subtracting each pixel's own luma, not
    by intersecting gamuts and comparing against the block's darkest and
    brightest pixels - doing the latter pairs the tightest pixel bound with the
    most distant pixel and declares a quarter of a normal image impossible.
    """
    low, high = exact_bounds(cb, cr)
    ny, nx = y.shape[0] // BLOCK, y.shape[1] // BLOCK
    y = np.asarray(y, np.float64)
    return (low - y).reshape(ny, BLOCK, nx, BLOCK), (high - y).reshape(ny, BLOCK, nx, BLOCK)


def window_slack(y: np.ndarray, cb: np.ndarray, cr: np.ndarray) -> np.ndarray:
    """Per-block width of the legal luma window, invariant to any constant shift.

    For each pixel the legal luma interval is [low_i, high_i]. A block can host
    a mark whose per-pixel excursion spans `spread` levels if and only if
    min(high_i - y_i) - max(low_i - y_i) >= spread. Both terms fall by the same
    amount under a constant shift of the block, so this width is shift
    invariant - which is what lets the verifier reproduce the encoder's
    admission decision from the received image alone, with no side channel.
    """
    low, high = exact_bounds(cb, cr)
    ny, nx = y.shape[0] // BLOCK, y.shape[1] // BLOCK
    y = np.asarray(y, np.float64)
    hi_room = (high - y).reshape(ny, BLOCK, nx, BLOCK).min(axis=(1, 3))
    lo_room = (low - y).reshape(ny, BLOCK, nx, BLOCK).max(axis=(1, 3))
    return hi_room - lo_room


def clip_safe_shift(y: np.ndarray, cb: np.ndarray, cr: np.ndarray,
                    margin: float, max_shift: float, slack: float = 0.0):
    """Smallest-magnitude integer shift that keeps every pixel in gamut.

    Returns (shift, impossible). `impossible` marks blocks where no shift within
    +-max_shift works; those are excused, never silently clipped.
    """
    room_lo, room_hi = block_gamut(y, cb, cr)          # per pixel, relative to y
    need_lo = np.ceil((room_lo + margin).max(axis=(1, 3)))
    need_hi = np.floor((room_hi - margin).min(axis=(1, 3)))
    impossible = (need_lo > need_hi) | (need_lo > max_shift) | (need_hi < -max_shift)
    shift = np.where(need_lo > 0, need_lo, np.where(need_hi < 0, need_hi, 0.0))
    impossible = impossible | (np.abs(shift) > max_shift - slack)
    shift = np.where(impossible, 0.0, shift)
    return shift, impossible
