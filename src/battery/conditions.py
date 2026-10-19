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
    Condition(10, "benign", "Gaussian noise sigma=1",
              lambda d: gaussian_noise(d, 1.0),
              "no tamper claim", "any tamper claim"),
    Condition(11, "benign", "resize 90% and back",
              lambda d: resize_roundtrip(d, 0.9),
              "no tamper claim", "any tamper claim"),
)

BY_ID = {c.cid: c for c in FROZEN}
