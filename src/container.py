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
    """Per-pixel True where the recombination would clip."""
    y32 = np.asarray(y, np.float64)
    g = y32 - ((np.asarray(cb, np.float64) + np.asarray(cr, np.float64)) / 4.0)
    r = np.asarray(cr, np.float64) + g
    b = np.asarray(cb, np.float64) + g
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
