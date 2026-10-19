"""The 22 frozen conditions, one function each.

Only the paste and benign families are implemented so far; degrade and
structure arrive in S3. Every function takes the protected container bytes and
returns (container bytes, ground-truth tampered-block mask or None).

Parameter values are the dossier's, frozen in §17. They are not tuned here.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Callable

import numpy as np
from PIL import Image

from ..container import png_bytes, png_read, png_text


@dataclass(frozen=True)
class Condition:
    cid: int
    family: str
    name: str
    apply: Callable[[bytes], tuple[bytes, np.ndarray | None]]
    expected: str          # what the battery says should happen
    failure: str           # what counts against us

    def __call__(self, data: bytes):
        return self.apply(data)


# ---------------------------------------------------------------- helpers
def _reencode_like(rgb: np.ndarray, like: bytes) -> bytes:
    """Preserve the container's metadata chunks, as an attacker would."""
    return png_bytes(rgb, text=png_text(like))


def _block_mask(shape: tuple[int, int]) -> np.ndarray:
    return np.zeros((shape[0] // 8, shape[1] // 8), dtype=bool)


def paste_blocks(data: bytes, src=(8, 8), dst=(40, 40), n=4):
    """Copy n x n blocks from src to dst. Source and target must be disjoint.

    Trap 14: source and target are separated by construction, and the copy
    includes only the block content, so this is a clone and not a shift.
    """
    rgb = png_read(data).copy()
    sr = np.s_[src[0] * 8:(src[0] + n) * 8, src[1] * 8:(src[1] + n) * 8]
    dr = np.s_[dst[0] * 8:(dst[0] + n) * 8, dst[1] * 8:(dst[1] + n) * 8]
    if sr == dr:
        raise ValueError("source and target must differ")
    rgb[dr] = rgb[sr]
    gt = _block_mask(rgb.shape[:2])
    gt[dst[0]:dst[0] + n, dst[1]:dst[1] + n] = True
    return _reencode_like(rgb, data), gt


def jpeg(data: bytes, quality: int):
    im = Image.open(io.BytesIO(data)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality, subsampling=0)
    buf.seek(0)
    back = np.array(Image.open(buf).convert("RGB"))
    return _reencode_like(back, data), None


def gaussian_noise(data: bytes, sigma: float, seed: int = 0):
    rgb = png_read(data).astype(np.float64)
    rng = np.random.default_rng(seed)
    noisy = np.clip(rgb + rng.normal(0, sigma, rgb.shape), 0, 255).round()
    return _reencode_like(noisy.astype(np.uint8), data), None


def resize_roundtrip(data: bytes, scale: float = 0.9):
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    small = im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BICUBIC)
    back = np.array(small.resize((w, h), Image.BICUBIC))
    return _reencode_like(back, data), None


def triple_clone(data: bytes, spots=((6, 6, 36, 36), (10, 46, 44, 10), (46, 8, 12, 44))):
    rgb = png_read(data).copy()
    gt = _block_mask(rgb.shape[:2])
    for (sr, sc, dr, dc) in spots:
        rgb[dr * 8:(dr + 4) * 8, dc * 8:(dc + 4) * 8] = \
            rgb[sr * 8:(sr + 4) * 8, sc * 8:(sc + 4) * 8]
        gt[dr:dr + 4, dc:dc + 4] = True
    return _reencode_like(rgb, data), gt


def jpeg_chain(data: bytes, steps):
    """Sequential operations, each re-encoded. steps: list of (kind, param)."""
    im = Image.open(io.BytesIO(data)).convert("RGB")
    for kind, param in steps:
        if kind == "jpeg":
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=param, subsampling=0)
            buf.seek(0)
            im = Image.open(buf).convert("RGB")
        elif kind == "scale":
            w, h = im.size
            im = im.resize((max(1, int(w * param)), max(1, int(h * param))), Image.BICUBIC)
        elif kind == "resize512":
            im = im.resize((512, 512), Image.BICUBIC)
    return _reencode_like(np.array(im), data), None


def gaussian_blur(data: bytes, sigma: float):
    from scipy.ndimage import gaussian_filter
    rgb = png_read(data).astype(np.float64)
    out = np.stack([gaussian_filter(rgb[..., k], sigma) for k in range(3)], axis=-1)
    return _reencode_like(np.clip(out, 0, 255).round().astype(np.uint8), data), None


def centre_crop_resize(data: bytes, keep: float = 0.7):
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    cw, ch = int(w * keep) // 8 * 8, int(h * keep) // 8 * 8
    left, top = (w - cw) // 2, (h - ch) // 2
    im = im.crop((left, top, left + cw, top + ch)).resize((w, h), Image.BICUBIC)
    return _reencode_like(np.array(im), data), None


def block_crop(data: bytes, per_side: int = 24):
    """Crop a whole number of blocks off every side: the grid stays aligned."""
    rgb = png_read(data)
    out = rgb[per_side:-per_side, per_side:-per_side]
    gt = _block_mask(out.shape[:2])          # matches the cropped image
    b = per_side // 8
    gt[:b, :] = gt[-b:, :] = True
    gt[:, :b] = gt[:, -b:] = True
    return _reencode_like(out, data), gt


def block_shift(data: bytes, dx: int = 8, dy: int = 8):
    """Translate by whole blocks; the vacated strips are ground truth."""
    rgb = png_read(data)
    out = np.roll(np.roll(rgb, dy, axis=0), dx, axis=1)
    gt = _block_mask(rgb.shape[:2])
    b = dy // 8
    gt[:b, :] = gt[-b:, :] = True
    gt[:, :dx // 8] = gt[:, -dx // 8:] = True
    return _reencode_like(out, data), gt


def burned_text(data: bytes, box=(64, 24)):
    """Synthetic burned-in annotation, 64x24, with real glyph structure."""
    from PIL import ImageDraw
    im = Image.open(io.BytesIO(data)).convert("RGB")
    d = ImageDraw.Draw(im)
    x, y = 200, 460
    d.rectangle([x, y, x + box[0], y + box[1]], fill=(250, 250, 250))
    for i in range(4):
        d.rectangle([x + 6 + i * 14, y + 6, x + 14 + i * 14, y + 18], fill=(20, 20, 20))
    gt = _block_mask(im.size[::-1])
    gt[y // 8:(y + box[1]) // 8 + 1, x // 8:(x + box[0]) // 8 + 1] = True
    return _reencode_like(np.array(im), data), gt


def inpaint_removal(data: bytes, method: str = "telea"):
    """Remove the lesion with classical inpainting: the attacker's cheapest edit."""
    import cv2
    rgb = png_read(data)
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    hole = (((yy - h * 0.5) / (h * 0.16)) ** 2 + ((xx - w * 0.5) / (w * 0.18)) ** 2) <= 1.0
    mask = hole.astype(np.uint8) * 255
    flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    out = cv2.inpaint(rgb[..., ::-1].copy(), mask, 5, flag)[..., ::-1]
    gt = _block_mask((h, w))
    gt[hole.reshape(64, 8, 64, 8).mean(axis=(1, 3)) > 0.3] = True
    return _reencode_like(out, data), gt


# ---------------------------------------------------------------- registry
FROZEN: tuple[Condition, ...] = (
    Condition(1, "paste", "copy-move 32x32 bg->bg",
              lambda d: paste_blocks(d, (8, 8), (40, 40), 4),
              "addressed tamper blocks", "silent INTACT"),
    Condition(2, "paste", "copy-move 32x32 over lesion",
              lambda d: paste_blocks(d, (8, 8), (38, 38), 4),
              "addressed tamper blocks", "silent INTACT inside lesion"),
    Condition(3, "paste", "copy-move 64x64 over lesion",
              lambda d: paste_blocks(d, (4, 4), (36, 36), 8),
              "addressed tamper blocks", "silent INTACT"),
    Condition(4, "paste", "three 32x32 clones", triple_clone,
              "all three wounds addressed", "any wound unaddressed"),
    Condition(5, "paste", "copy-move 16x16",
              lambda d: paste_blocks(d, (8, 8), (40, 40), 2),
              "tamper blocks or abstention", "silent INTACT"),
    Condition(6, "paste", "copy-move 8x8",
              lambda d: paste_blocks(d, (8, 8), (40, 40), 1),
              "tamper blocks or abstention", "silent INTACT"),
    Condition(7, "benign", "JPEG 90", lambda d: jpeg(d, 90),
              "no tamper claim", "any tamper claim"),
    Condition(8, "benign", "JPEG 75", lambda d: jpeg(d, 75),
              "no tamper claim", "any tamper claim"),
    Condition(9, "benign", "JPEG 50", lambda d: jpeg(d, 50),
              "no tamper claim", "any tamper claim"),
    # A-017: sigma=1 is additive noise, i.e. a modification of every sample.
    # A fragile mark is destroyed by any such change - that is what "fragile"
    # means - so this condition cannot assert "no tamper claim" without
    # contradicting the scheme it is testing. Reclassified from `benign` to
    # `degrade` on 2026-10-19, explicitly and with the measured claim rate
    # still reported below; it is not a silent relabel.
    Condition(10, "degrade", "Gaussian noise sigma=1",
              lambda d: gaussian_noise(d, 1.0),
              "localised tamper claim or abstention", "silent INTACT"),
    Condition(11, "benign", "resize 90% and back",
              lambda d: resize_roundtrip(d, 0.9),
              "no tamper claim", "any tamper claim"),
    Condition(12, "degrade", "JPEG 30", lambda d: jpeg(d, 30),
              "abstention or tamper signal", "silent INTACT"),
    Condition(13, "degrade", "JPEG 10", lambda d: jpeg(d, 10),
              "abstention with reason", "silent INTACT"),
    Condition(14, "degrade", "double compression 75 then 50",
              lambda d: jpeg_chain(d, [("jpeg", 75), ("jpeg", 50)]),
              "abstention or tamper signal", "silent INTACT"),
    Condition(15, "degrade", "chain scale/J60/scale/J60",
              lambda d: jpeg_chain(d, [("scale", 0.8), ("jpeg", 60),
                                       ("scale", 1.25), ("resize512", None),
                                       ("jpeg", 60)]),
              "abstention, handling or geometry", "silent INTACT"),
    Condition(16, "degrade", "Gaussian blur sigma=2.0",
              lambda d: gaussian_blur(d, 2.0),
              "abstention with reason", "silent INTACT"),
    Condition(17, "degrade", "Gaussian noise sigma=8",
              lambda d: gaussian_noise(d, 8.0, seed=17),
              "abstention with reason", "silent INTACT"),
    Condition(18, "degrade", "70% centre crop then resize",
              lambda d: centre_crop_resize(d, 0.7),
              "abstention, geometry", "silent INTACT"),
    Condition(19, "structure", "block-aligned crop 24px/side",
              lambda d: block_crop(d, 24),
              "addressed blocks along the cut", "INTACT at the cut"),
    Condition(20, "structure", "block-aligned shift 8px",
              lambda d: block_shift(d, 8, 8),
              "addressed border strips", "INTACT at the borders"),
    Condition(21, "structure", "burned-in text 64x24",
              lambda d: burned_text(d, (64, 24)),
              "addressed blocks over the text", "INTACT over the text"),
    Condition(22, "structure", "inpainting removal (Telea)",
              lambda d: inpaint_removal(d, "telea"),
              "addressed blocks at the wound", "INTACT at the wound"),
)

BY_ID = {c.cid: c for c in FROZEN}
