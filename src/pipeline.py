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
from .container import (Protected, clip_safe_shift, compose, field_mask, png_bytes,
                        png_read, png_text, recover_luma, split_rct)
from .ladder import GEOMETRY_CHANGE, LadderResult, all_cannot_say, classify, texture_of
from .transform import Haar2

TEXT_IMAGE_ID = "pff_imageid"
TEXT_KEY_ID = "pff_keyid"
TEXT_SIZE = "pff_size"


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

    def _metadata(self, image_id: int, h: int = 512, w: int = 512) -> dict[str, str]:
        return {TEXT_IMAGE_ID: str(int(image_id)),
                TEXT_KEY_ID: self._key_id(image_id),
                TEXT_SIZE: f"{h}x{w}"}

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
        field = field_mask(y0)
        # headroom the mark needs: half the quantisation step, plus the
        # strongest Carrier B excursion, plus one level for rounding
        headroom = self.cfg.delta_f / 2 + 1.0 + self.cfg.beta0 * (1.0 + self.cfg.lam) / 8.0
        # blocks the mark cannot occupy without leaving the RGB gamut
        _, excused = clip_safe_shift(y0, cb, cr, margin=0.0,
                                     max_shift=self.cfg.tau_shift_excuse, slack=0.0)

        # ---- 1. Carrier B first (A-002)
        region = block_region(region_mask, ny, nx) if region_mask is not None \
            else np.zeros((ny, nx))
        robust = RobustCarrier(self.key, image_id, self.cfg.beta0, self.cfg.lam,
                               self.cfg.dct_lo, self.cfg.dct_hi, (h, w))
        y_b = haar.from_blocks(robust.write(haar.to_blocks(y0.astype(np.float64)), region))

        # ---- 2. range fitting, so Carrier A can never clip
        skip = field | excused
        skip_px = skip.repeat(8, 0).repeat(8, 1)
        y_b[skip_px] = y0.astype(np.float64)[skip_px]
        shift, refused_fit = clip_safe_shift(y_b, cb, cr, margin=headroom,
                                             max_shift=self.cfg.max_shift)
        refused_fit |= skip
        shift = np.where(refused_fit, 0.0, shift)
        y_fit = haar.from_blocks(haar.to_blocks(y_b) + shift[:, :, None, None])

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
        # A block that was skipped must be skipped by BOTH carriers. Marking it
        # with A alone would push an already out-of-gamut block past the edge,
        # force a revert after tagging, and manufacture a false tamper on a
        # clean image. The verifier excuses these blocks by an independent
        # rule (field or unmarkable), so nothing is lost.
        no_mark = refused_gate | skip
        if no_mark.any():
            marked_flat[no_mark] = flat[no_mark]
        y_marked = haar.inverse({**c, **Haar2.details_unflat(c, marked_flat)})

        # ---- 5. container
        prot: Protected = compose(y_marked, rgb)
        refused = refused_fit | refused_gate | prot.refused
        png = png_bytes(prot.rgb, text=self._metadata(image_id, h, w))
        return ProtectedImage(png=png, rgb=prot.rgb, refused=refused, image_id=image_id)

    # ------------------------------------------------------------ resync
    def _address_grid(self, dr: int, dc: int, ny: int, nx: int) -> np.ndarray:
        """Addresses seen through a block offset, or -1 outside the original grid."""
        full = np.arange(64 * 64).reshape(64, 64)
        pad = np.full((64 + 16, 64 + 16), -1, dtype=np.int64)
        pad[8:8 + 64, 8:8 + 64] = full
        return pad[8 + dr:8 + dr + ny, 8 + dc:8 + dc + nx]

    def _offset_score(self, haar, y, dr, dc, sample=96) -> float:
        """Fraction of sampled blocks whose bits match at this offset."""
        ny, nx = haar.ny, haar.nx
        addr = self._address_grid(dr, dc, ny, nx)
        valid = addr >= 0
        if valid.sum() < sample:
            return -1.0
        c = haar.forward(y)
        digests = coarse_digest(c["LL2"], self.cfg.q_digest)
        got = FragileCarrier(self.cfg.delta_f).read(Haar2.details_flat(c))
        idx = np.argwhere(valid)
        rng = np.random.default_rng(0)
        pick = idx[rng.choice(len(idx), size=min(sample, len(idx)), replace=False)]
        hits = 0
        for r, cidx in pick:
            a = int(addr[r, cidx])
            b = self._binder.tag(a, int(digests[r, cidx]))
            hits += int((got[r, cidx] == b).sum())
        return hits / (len(pick) * 60)

    def _estimate_offset(self, haar, y, image_id: int) -> tuple[int, int, float]:
        self._binder = Binder(self.key, image_id, self.cfg.bind_address)
        best, best_score = (0, 0), -1.0
        for dr in range(-8, 9):
            for dc in range(-8, 9):
                sc = self._offset_score(haar, y, dr, dc)
                if sc > best_score:
                    best, best_score = (dr, dc), sc
        return best[0], best[1], best_score

    # ------------------------------------------------------------ verify
    def verify(self, data: bytes, resync: bool = False) -> VerifyResult:
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
        declared = text.get(TEXT_SIZE)
        if declared and declared != f"{h}x{w}":
            # the container's geometry changed: content may all be authentic,
            # but the image is not the one that was protected. Battery
            # conditions 19 and 20 are exactly this, and reporting INTACT
            # would be the silent failure the battery forbids.
            shape = (h // 8, w // 8)
            return VerifyResult(delta_f=np.full(shape, np.nan), delta_sr=np.full(shape, np.nan),
                                ladder=all_cannot_say(shape, GEOMETRY_CHANGE),
                                texture=texture_of(y), image_id=image_id, key_ok=True)
        haar = Haar2((h, w))
        ny, nx = haar.ny, haar.nx
        addresses = np.arange(ny * nx).reshape(ny, nx)

        c = haar.forward(y)
        digests = coarse_digest(c["LL2"], self.cfg.q_digest)
        binder = Binder(self.key, image_id, self.cfg.bind_address)

        dr, dc = 0, 0
        if resync:
            dr, dc, score = self._estimate_offset(haar, y, image_id)
        addr = self._address_grid(dr, dc, ny, nx) if (dr or dc) else addresses
        valid = addr >= 0
        expected = binder.tags(np.where(valid, addr, 0), digests)
        if not valid.all():
            expected = expected.copy()
            expected[~valid] = 0

        fragile = FragileCarrier(self.cfg.delta_f)
        got = fragile.read(Haar2.details_flat(c))
        delta_f = (got != expected).mean(axis=2)
        if not valid.all():
            delta_f[~valid] = 1.0

        robust = RobustCarrier(self.key, image_id, self.cfg.beta0, self.cfg.lam,
                               self.cfg.dct_lo, self.cfg.dct_hi, (h, w))
        delta_sr = robust.read(haar.to_blocks(y))

        tex = texture_of(y)
        margin = digest_margin(c["LL2"], self.cfg.q_digest)
        _, cb_r, cr_r = split_rct(rgb)
        _, excused_v = clip_safe_shift(y, cb_r, cr_r, margin=0.0,
                                       max_shift=self.cfg.tau_shift_excuse,
                                       slack=self.cfg.excuse_slack)
        excluded = field_mask(y) | excused_v | ~valid
        lad = classify(delta_f, delta_sr, tex, self.cfg, digest_margin=margin,
                       excluded=excluded)
        return VerifyResult(delta_f=delta_f, delta_sr=delta_sr, ladder=lad,
                            texture=tex, image_id=image_id, key_ok=True,
                            digest_margin=margin)
