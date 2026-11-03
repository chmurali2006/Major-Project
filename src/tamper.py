"""Tamper and benign families. Eight of them, one interface.

    apply(rgb, rng, **kw) -> (changed_rgb, block_mask)

The block mask is ALWAYS measured by differencing the pixels. A family that
returns a declared rectangle is a bug: on PH2 the declared region of condition 4
contained blocks that never changed a pixel, and scoring against it rewarded the
wrong answer.

Every family is block-aligned where the classical protocol was block-aligned, so
the 8x8 verdict grid lines up with the truth. Non-aligned families (blur, noise)
are handled by measuring, not by assuming.
"""

from __future__ import annotations

import cv2
import numpy as np

from .metrics import measured_mask

BLOCK = 8
SIZE = 512


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _block_top_left(rng, size: int, span: int) -> int:
    """A block-aligned origin leaving `span` pixels of room."""
    n = max(1, (size - span) // BLOCK)
    return int(rng.integers(0, n)) * BLOCK


# ---------------------------------------------------------------- T1 copy-move

def copy_move(rgb: np.ndarray, rng: np.random.Generator, span: int = 32,
              n_copies: int = 1) -> np.ndarray:
    """Paste a block-aligned square from one place to another in the same image."""
    out = rgb.copy()
    for _ in range(n_copies):
        s_r = _block_top_left(rng, SIZE, span)
        s_c = _block_top_left(rng, SIZE, span)
        for _attempt in range(20):
            d_r = _block_top_left(rng, SIZE, span)
            d_c = _block_top_left(rng, SIZE, span)
            # keep source and destination disjoint
            if abs(d_r - s_r) >= span or abs(d_c - s_c) >= span:
                break
        else:
            continue
        out[d_r:d_r + span, d_c:d_c + span] = out[s_r:s_r + span, s_c:s_c + span]
    return out


# ---------------------------------------------------------------- T2 lesion insertion

def lesion_insert(rgb: np.ndarray, rng: np.random.Generator,
                  region: np.ndarray | None = None,
                  radius: int | None = None,
                  contrast: float | None = None) -> np.ndarray:
    """Paste a synthetic mass: a soft-edged ellipse with its own texture.

    `region` is an optional HxW bool restricting where the mass may land — for
    LiTS that is the liver mask, which is what makes this the PFF-WM protocol
    rather than an arbitrary blob.
    """
    h, w = rgb.shape[:2]
    r = int(radius if radius is not None else rng.integers(18, 44))
    cy = int(rng.integers(r + 4, h - r - 4))
    cx = int(rng.integers(r + 4, w - r - 4))
    if region is not None:
        candidates = np.argwhere(region)
        if len(candidates) > 50:
            cy, cx = candidates[int(rng.integers(0, len(candidates)))]

    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    ellipse = ((xx / r) ** 2 + (yy / (r * 0.85)) ** 2) <= 1.0
    # soft edge so it looks like tissue, not a sticker
    dist = np.sqrt((xx / r) ** 2 + (yy / (r * 0.85)) ** 2)
    alpha = np.clip((1.0 - dist) / 0.18, 0.0, 1.0) * ellipse

    y0, y1 = cy - r, cy + r + 1
    x0, x1 = cx - r, cx + r + 1
    if y0 < 0 or x0 < 0 or y1 > h or x1 > w:
        return rgb.copy()

    patch = rgb[y0:y1, x0:x1].astype(np.float64)
    gain = float(contrast if contrast is not None else rng.uniform(-0.25, 0.25))
    texture = _rng(int(rng.integers(0, 2**31 - 1))).normal(0, 7, patch.shape)

    # a mass is a coherent structure, not noise: low-frequency shading plus grain
    shade = cv2.GaussianBlur(texture.astype(np.float32), (0, 0), sigmaX=3)
    blob = patch * (1.0 + gain) + shade + texture
    a = alpha[..., None]
    out = rgb.copy()
    out[y0:y1, x0:x1] = np.clip(patch * (1 - a) + blob * a, 0, 255).astype(np.uint8)
    return out


# ---------------------------------------------------------------- T3 lesion removal

def lesion_remove(rgb: np.ndarray, rng: np.random.Generator,
                  radius: int | None = None, method: str = "telea") -> np.ndarray:
    """Erase a region and inpaint it. The clinically interesting forgery."""
    h, w = rgb.shape[:2]
    r = int(radius if radius is not None else rng.integers(22, 52))
    cy = int(rng.integers(r + 4, h - r - 4))
    cx = int(rng.integers(r + 4, w - r - 4))
    mask = np.zeros((h, w), np.uint8)
    cv2.ellipse(mask, (cx, cy), (r, int(r * 0.85)), int(rng.integers(0, 180)),
                0, 360, 255, -1)
    flag = {"telea": cv2.INPAINT_TELEA, "ns": cv2.INPAINT_NS}.get(method, cv2.INPAINT_TELEA)
    return cv2.inpaint(rgb, mask, 7, flag)


# ---------------------------------------------------------------- T4 burned-in text

def burned_text(rgb: np.ndarray, rng: np.random.Generator,
                box: tuple[int, int] = (64, 24),
                text: str | None = None) -> np.ndarray:
    h, w = rgb.shape[:2]
    out = rgb.copy()
    bh, bw = box
    y = _block_top_left(rng, h - bh, bh)
    x = _block_top_left(rng, w - bw, bw)
    label = text or str(rng.choice(["PATIENT A", "CONFIDENTIAL", "REV 2", "SAMPLE 04",
                                    "2026-10-24", "MRN 88213"]))
    dark = bool(rng.integers(0, 2))
    colour = (0, 0, 0) if dark else (255, 255, 255)
    cv2.putText(out, label, (x, y + bh - 6), cv2.FONT_HERSHEY_SIMPLEX,
                bh / 34.0, colour, max(1, bh // 12), cv2.LINE_AA)
    return out


# ---------------------------------------------------------------- T5 cross-image splicing

def splice(donor: np.ndarray, host: np.ndarray, rng: np.random.Generator,
           span: int | None = None) -> np.ndarray:
    """Paste a region taken from a DIFFERENT image.

    The classical battery never measured this and the limitation section admits
    it is only partly caught. It is here because it is the attack a forged
    medical record would actually use.
    """
    span = int(span if span is not None else rng.integers(32, 120))
    s_r = _block_top_left(rng, SIZE, span)
    s_c = _block_top_left(rng, SIZE, span)
    d_r = _block_top_left(rng, SIZE, span)
    d_c = _block_top_left(rng, SIZE, span)
    out = host.copy()
    out[d_r:d_r + span, d_c:d_c + span] = donor[s_r:s_r + span, s_c:s_c + span]
    return out


# ---------------------------------------------------------------- benign

def benign_op(rgb: np.ndarray, kind: str = "jpeg75", rng: np.random.Generator | None = None) -> np.ndarray:
    """Image-processing operations. Label policy belongs to the evaluation protocol.

    The audited fragile-integrity study treats changed JPEG pixels as tampering,
    not as evidence of malicious intent.
    """
    if kind.startswith("jpeg"):
        q = int(kind.replace("jpeg", ""))
        ok, buf = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                               [int(cv2.IMWRITE_JPEG_QUALITY), q])
        return cv2.cvtColor(cv2.imdecode(buf, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    if kind.startswith("sigma"):
        s = float(kind.replace("sigma", ""))
        r = rng or _rng(0)
        noise = r.normal(0, s, rgb.shape)
        return np.clip(rgb.astype(np.float64) + noise, 0, 255).astype(np.uint8)
    if kind.startswith("resize"):
        pct = int(kind.replace("resize", "")) / 100.0
        h, w = rgb.shape[:2]
        small = cv2.resize(rgb, (max(8, int(w * pct)), max(8, int(h * pct))),
                           interpolation=cv2.INTER_CUBIC)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC)
    if kind == "blur2":
        return cv2.GaussianBlur(rgb, (0, 0), 2.0)
    raise ValueError(f"unknown benign op {kind!r}")


def benign_chain(rgb: np.ndarray, rng: np.random.Generator | None = None) -> np.ndarray:
    """scale -> jpeg -> scale -> jpeg. The realistic transmission path."""
    out = benign_op(rgb, "resize80")
    out = benign_op(out, "jpeg60")
    out = benign_op(out, "resize125")
    h, w = rgb.shape[:2]
    out = cv2.resize(out, (w, h), interpolation=cv2.INTER_CUBIC)
    return benign_op(out, "jpeg60")


# ---------------------------------------------------------------- registry

TAMPER = {
    "T1": lambda rgb, rng: copy_move(rgb, rng, span=int(rng.choice([8, 16, 32, 64])),
                                     n_copies=int(rng.integers(1, 3))),
    "T2": lambda rgb, rng: lesion_insert(rgb, rng),
    "T3": lambda rgb, rng: lesion_remove(rgb, rng),
    "T4": lambda rgb, rng: burned_text(rgb, rng),
}

BENIGN = {
    "B1": lambda rgb, rng: benign_op(rgb, str(rng.choice(
        ["jpeg90", "jpeg75", "jpeg50", "sigma1", "resize90"]))),
    "B2": lambda rgb, rng: benign_chain(rgb),
}


def make_pair(rgb: np.ndarray, family: str, seed: int,
              donor: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Apply a family and return (changed image, measured block mask)."""
    rng = _rng(seed)
    rgb = np.asarray(rgb, np.uint8)
    if family in TAMPER:
        out = TAMPER[family](rgb, rng)
    elif family == "T5":
        if donor is None:
            raise ValueError("T5 needs a donor image")
        out = splice(np.asarray(donor, np.uint8), rgb, rng)
    elif family in BENIGN:
        out = BENIGN[family](rgb, rng)
    else:
        raise ValueError(f"unknown family {family!r}")
    out = np.asarray(out, np.uint8)
    mask = measured_mask(rgb, out)
    return out, mask
