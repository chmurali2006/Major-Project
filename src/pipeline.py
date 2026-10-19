"""Orchestration: one image in, one verdict out.

This is the only place the modules are wired together. It replaces the
architecture document's separate embed_fragile/embed_robust modules: both
carriers live in carriers.py, and the order in which they are applied is the
single most consequential decision in the design (amendment A-002).

Protect order, fixed:
    1. luma from the reversible colour transform
    2. Carrier B (semi-robust, address-keyed)   <- first
    3. range fitting so the mark cannot clip
    4. digest from LL2, tag from key+address+digest
    5. Carrier A (fragile)                      <- last, therefore exact
    6. PNG with metadata (image id + key check)

Verify order:
    1. read metadata; missing or wrong key id -> CANNOT SAY, never TAMPERED
    2. luma from the same reversible transform
    3. read both carriers
    4. ladder

verify() takes bytes and a key. It cannot see a mask, and the signature says
so (Trap 13).
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

import numpy as np

from .binder import Binder, coarse_digest, digest_margin
from .carriers import FragileCarrier, RobustCarrier, block_region
from .config import Config, DEFAULT
from .container import (Protected, compose, fit_block_luma, png_bytes, png_read,
                        png_text, recover_luma, split_rct)
from .ladder import LadderResult, all_cannot_say, classify, texture_of
from .transform import Haar2

TEXT_IMAGE_ID = "pff_imageid"
TEXT_KEY_ID = "pff_keyid"


@dataclass(frozen=True)
class ProtectedImage:
    png: bytes
    rgb: np.ndarray
    refused: np.ndarray
    image_id: int

    @property
    def refusal_rate(self) -> float:
        return float(self.refused.mean())


@dataclass(frozen=True)
class VerifyResult:
    delta_f: np.ndarray
    delta_sr: np.ndarray
    ladder: LadderResult
    texture: np.ndarray
    image_id: int | None
    key_ok: bool
    digest_margin: np.ndarray | None = None

    @property
    def coverage(self) -> float:
        return self.ladder.coverage()

    @property
    def tampered_fraction(self) -> float:
        return float((self.ladder.verdict == 1).mean())


class System:
    """A protected-image system bound to one secret key."""

    def __init__(self, key: bytes, cfg: Config = DEFAULT):
        if not key:
            raise ValueError("a non-empty key is required")
        self.key = bytes(key)
        self.cfg = cfg

    # ------------------------------------------------------------ helpers
    def _key_id(self, image_id: int) -> str:
        return hmac.new(self.key, b"pff-keyid" + int(image_id).to_bytes(4, "big"),
                        hashlib.sha256).hexdigest()[:16]

    def _metadata(self, image_id: int) -> dict[str, str]:
        return {TEXT_IMAGE_ID: str(int(image_id)), TEXT_KEY_ID: self._key_id(image_id)}

    # ------------------------------------------------------------ protect
    def protect(self, rgb: np.ndarray, region_mask: np.ndarray | None,
                image_id: int) -> ProtectedImage:
        rgb = np.asarray(rgb, dtype=np.uint8)
        if rgb.shape[0] != rgb.shape[1]:
            raise ValueError("expected a square image")
        h, w = rgb.shape[:2]
        haar = Haar2((h, w))
        ny, nx = haar.ny, haar.nx

        y0, cb, cr = split_rct(rgb)
        addresses = np.arange(ny * nx).reshape(ny, nx)

        # ---- 1. Carrier B first (A-002)
        region = block_region(region_mask, ny, nx) if region_mask is not None \
            else np.zeros((ny, nx))
        robust = RobustCarrier(self.key, image_id, self.cfg.beta0, self.cfg.lam,
                               self.cfg.dct_lo, self.cfg.dct_hi, (h, w))
        y_b = haar.from_blocks(robust.write(haar.to_blocks(y0.astype(np.float64)), region))

        # ---- 2. range fitting, so Carrier A can never clip
        # margin must cover the largest pixel change Carrier A can make
        # (about delta/2) plus the strongest Carrier B excursion inside the
        # lesion (beta0*(1+lam)/8). Too small a margin manufactures refusals,
        # and a refused block reads as a broken tag at verify time.
        margin = self.cfg.delta_f / 2.0 + 1.0 + self.cfg.beta0 * (1.0 + self.cfg.lam) / 8.0
        y_fit, refused_fit = fit_block_luma(y_b, cb, cr, margin=margin, max_shift=16.0)

        # ---- 3. digest and tag from the fitted luma
        c = haar.forward(y_fit)
        digests = coarse_digest(c["LL2"], self.cfg.q_digest)
        binder = Binder(self.key, image_id, self.cfg.bind_address)
        tags = binder.tags(addresses, digests)

        # ---- 4. texture gate (dossier §11)
        # Background blocks with no texture are refused and recorded. Lesion
        # blocks always override the threshold, because the diagnostic region
        # is exactly what must be protected.
        refused_gate = np.zeros((ny, nx), dtype=bool)
        if self.cfg.gate_enabled:
            tex = np.asarray(y_fit, np.float64).reshape(ny, 8, nx, 8).std(axis=(1, 3))
            refused_gate = (region < 0.5) & (tex < self.cfg.texture_min)

        # ---- 5. Carrier A last, therefore exact
        fragile = FragileCarrier(self.cfg.delta_f)
        flat = Haar2.details_flat(c)
        marked_flat = fragile.write(flat, tags)
        # a refused block carries no tag: keep its original coefficients so the
        # verifier reads noise and the ladder can abstain with a reason
        if refused_gate.any():
            keep = np.repeat(np.repeat(refused_gate, 1, 0), 1, 1)
            marked_flat[keep] = flat[keep]
        y_marked = haar.inverse({**c, **Haar2.details_unflat(c, marked_flat)})

        # ---- 5. container
        prot: Protected = compose(y_marked, rgb)
        refused = refused_fit | refused_gate | prot.refused
        png = png_bytes(prot.rgb, text=self._metadata(image_id))
        return ProtectedImage(png=png, rgb=prot.rgb, refused=refused, image_id=image_id)

    # ------------------------------------------------------------ verify
    def verify(self, data: bytes) -> VerifyResult:
        """data: the received container bytes. No mask, no original, no sidecar."""
        text = png_text(data)
        if TEXT_IMAGE_ID not in text or TEXT_KEY_ID not in text:
            rgb = png_read(data)
            shape = (rgb.shape[0] // 8, rgb.shape[1] // 8)
            y = recover_luma(rgb)
            return VerifyResult(delta_f=np.full(shape, np.nan), delta_sr=np.full(shape, np.nan),
                                ladder=all_cannot_say(shape), texture=texture_of(y),
                                image_id=None, key_ok=False)

        image_id = int(text[TEXT_IMAGE_ID])
        if text[TEXT_KEY_ID] != self._key_id(image_id):
            rgb = png_read(data)
            shape = (rgb.shape[0] // 8, rgb.shape[1] // 8)
            y = recover_luma(rgb)
            return VerifyResult(delta_f=np.full(shape, np.nan), delta_sr=np.full(shape, np.nan),
                                ladder=all_cannot_say(shape), texture=texture_of(y),
                                image_id=image_id, key_ok=False)

        rgb = png_read(data)
        y = recover_luma(rgb)
        h, w = y.shape
        haar = Haar2((h, w))
        ny, nx = haar.ny, haar.nx
        addresses = np.arange(ny * nx).reshape(ny, nx)

        c = haar.forward(y)
        digests = coarse_digest(c["LL2"], self.cfg.q_digest)
        binder = Binder(self.key, image_id, self.cfg.bind_address)
        expected = binder.tags(addresses, digests)

        fragile = FragileCarrier(self.cfg.delta_f)
        got = fragile.read(Haar2.details_flat(c))
        delta_f = (got != expected).mean(axis=2)

        robust = RobustCarrier(self.key, image_id, self.cfg.beta0, self.cfg.lam,
                               self.cfg.dct_lo, self.cfg.dct_hi, (h, w))
        delta_sr = robust.read(haar.to_blocks(y))

        tex = texture_of(y)
        margin = digest_margin(c["LL2"], self.cfg.q_digest)
        lad = classify(delta_f, delta_sr, tex, self.cfg, digest_margin=margin)
        return VerifyResult(delta_f=delta_f, delta_sr=delta_sr, ladder=lad,
                            texture=tex, image_id=image_id, key_ok=True,
                            digest_margin=margin)
