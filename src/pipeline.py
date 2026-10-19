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
from .container import (Protected, block_gamut, blocks_out_of_range, compose, exact_bounds,
                        field_mask, out_of_range, png_bytes, window_slack,
                        png_read, png_read_with_text, png_text, recover_luma, split_rct)
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
        # ---- 1. Carrier B first (A-002)
        region = block_region(region_mask, ny, nx) if region_mask is not None \
            else np.zeros((ny, nx))
        robust = RobustCarrier(self.key, image_id, self.cfg.beta0, self.cfg.lam,
                               self.cfg.dct_lo, self.cfg.dct_hi, (h, w))
        if self.cfg.use_robust:
            y_b = haar.from_blocks(robust.write(haar.to_blocks(y0.astype(np.float64)), region))
        else:
            y_b = y0.astype(np.float64)
        # Carrier B is semi-robust: it is recovered by correlation, not by
        # reading individual values, so saturating it at the gamut edge costs
        # nothing detectable while keeping the plane legal. Without this the
        # spread-spectrum add pushes vignette and specular pixels out of range,
        # the fit then has to refuse their blocks, and a clean image stops being
        # distinguishable from a tampered one.
        lo_b, hi_b = exact_bounds(cb, cr)
        y_b = np.clip(y_b, lo_b, hi_b)
        # The integer plane a skipped block transmits verbatim. The verifier
        # sees exactly these values inside an unmarked block, so its `field`
        # and window decisions match the encoder's bit for bit.
        y_plan = np.round(y_b)

        # ---- 2. Admission: one shift-invariant predicate both sides compute
        # A block can host a mark with per-pixel spread `s` iff its legal luma
        # window is at least `s` wide. That width is invariant to a constant
        # shift of the block, which is what lets the verifier reproduce this
        # decision from the received image alone, with no side channel.
        field = field_mask(y_plan) if self.cfg.field_excuse else np.zeros((ny, nx), bool)
        room_lo, room_hi = block_gamut(y_plan, cb, cr)
        slack_b = window_slack(y_plan, cb, cr)
        refused_gate = np.zeros((ny, nx), dtype=bool)
        if self.cfg.gate_enabled:
            tex = np.asarray(y_plan, np.float64).reshape(ny, 8, nx, 8).std(axis=(1, 3))
            refused_gate = (region < 0.5) & (tex < self.cfg.texture_min)
        # A block holding a pixel with zero room in one direction cannot carry a
        # signed mark: the gamut would saturate it, and saturating throws away
        # enough of the 60 bits to look like a tamper. Such blocks are refused
        # and, because they are refused, transmitted verbatim - so the verifier
        # recomputes this exact test on exactly these values.
        skip = field | refused_gate | (slack_b < self.cfg.window_min)

        # ---- 3. Carrier A, saturated at the gamut edge.
        # Carrier A writes 60 detail coefficients per block; summed through the
        # inverse Haar that is a per-pixel excursion of up to ~11 levels. Near
        # specular highlights and the white dermoscopy background there is no
        # upward room at all, so a signed mark cannot fit there.
        #
        # Reverting such a block (what compose() does) leaves it carrying the
        # unmarked residual pattern while the verifier expects the tag, so a
        # clean block reads as broken. Shifting the block first cannot fix this
        # without moving the digest it is tagged against. What works is to let
        # the gamut saturate the mark: the 60 bits are redundant, the block
        # keeps the large majority of them, and the block-level disagreement
        # stays far below TAU_F. Measured over PH2: clean blocks reach 0.217
        # disagreement at p1, tampered blocks start at 0.383 at p99.
        c = haar.forward(y_plan)
        digests = coarse_digest(c["LL2"], self.cfg.q_digest)
        tags = Binder(self.key, image_id, self.cfg.bind_address).tags(addresses, digests)
        flat = Haar2.details_flat(c)
        fragile = FragileCarrier(self.cfg.delta_f)
        marked_flat = fragile.write(flat, tags)
        marked_flat[skip] = flat[skip]
        y_marked = haar.inverse({**c, **Haar2.details_unflat(c, marked_flat)})
        saturated = int(((y_marked < lo_b) | (y_marked > hi_b)).sum())
        y_marked = np.clip(y_marked, lo_b, hi_b)

        # ---- 4. container
        prot: Protected = compose(y_marked, rgb)
        refused = skip | refused_gate | prot.refused
        png = png_bytes(prot.rgb, text=self._metadata(image_id, h, w))
        self.last_reports = {"refused_blocks": int(refused.sum()),
                             "compose_refused": int(prot.refused.sum()),
                             "saturated_pixels": saturated}
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
        rgb, text = png_read_with_text(data)
        if TEXT_IMAGE_ID not in text or TEXT_KEY_ID not in text:
            shape = (rgb.shape[0] // 8, rgb.shape[1] // 8)
            y = recover_luma(rgb)
            return VerifyResult(delta_f=np.full(shape, np.nan), delta_sr=np.full(shape, np.nan),
                                ladder=all_cannot_say(shape), texture=texture_of(y),
                                image_id=None, key_ok=False)

        image_id = int(text[TEXT_IMAGE_ID])
        if text[TEXT_KEY_ID] != self._key_id(image_id):
            shape = (rgb.shape[0] // 8, rgb.shape[1] // 8)
            y = recover_luma(rgb)
            return VerifyResult(delta_f=np.full(shape, np.nan), delta_sr=np.full(shape, np.nan),
                                ladder=all_cannot_say(shape), texture=texture_of(y),
                                image_id=image_id, key_ok=False)

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
        # 1 - correlation, so delta_f keeps its meaning: 0 = the block carries
        # its own tag, 1 = it carries no relation to it.
        flat_c = Haar2.details_flat(c)
        delta_f = np.clip(1.0 - fragile.score(flat_c, expected), 0.0, 1.0)
        if not valid.all():
            delta_f[~valid] = 1.0

        robust = RobustCarrier(self.key, image_id, self.cfg.beta0, self.cfg.lam,
                               self.cfg.dct_lo, self.cfg.dct_hi, (h, w))
        delta_sr = (robust.read(haar.to_blocks(y)) if self.cfg.use_robust
                    else np.zeros((ny, nx)))

        tex = texture_of(y)
        margin = digest_margin(c["LL2"], self.cfg.q_digest)
        _, cb_r, cr_r = split_rct(rgb)
        # Wider margin than the embedder used, so the excused set is a strict
        # superset of the skipped set. If a block skipped at embed is not
        # excused here, it reads as fully broken and falsely accuses the image.
        # The same admission predicate the encoder used, recomputed from the
        # received image. It is shift invariant, so a block the encoder left
        # unmarked - and therefore transmitted verbatim - yields exactly the
        # encoder's decision. A marked block's window only ever shrinks by its
        # own excursion, which is at most its reserved margin.
        room_lo_v, room_hi_v = block_gamut(y, cb_r, cr_r)
        # width of each block's legal luma window (A-014); one gamut map serves
        # both this and the gamut-safe test below.
        slack_v = room_hi_v.min(axis=(1, 3)) - room_lo_v.max(axis=(1, 3))
        excused_v = slack_v < self.cfg.window_min
        field_v = field_mask(y) if self.cfg.field_excuse else np.zeros((ny, nx), bool)
        excluded = field_v | excused_v | ~valid
        # Was the image changed as a whole? If the mark is uniformly weak
        # everywhere it should be strong, the sample values were transformed
        # globally - resampled, recompressed, noised - and a fragile mark
        # cannot certify any block afterwards. This is measured over the
        # decidable blocks only, because an excused block holds a clipped mark
        # by construction and would drag the median down on a clean image.
        # Only blocks the gamut cannot have clipped can answer this question:
        # where a pixel sits against the edge, the mark is clipped by
        # construction and its amplitude says nothing about the image. In the
        # blocks that are gamut-safe, a clean image and a copy-move edit both
        # measure 1.00 (p0 = p95), while every global transform measures 0.90
        # or less. See TAU_EVIDENCE.
        gamut_safe = ((room_hi_v > self.cfg.gamut_safe_margin).all(axis=(1, 3))
                      & (room_lo_v < -self.cfg.gamut_safe_margin).all(axis=(1, 3))
                      & ~field_v)
        attenuated = False
        if self.cfg.use_attenuation and gamut_safe.sum() >= self.cfg.corroborate_min_blocks * 8:
            ev = fragile.evidence(flat_c)[gamut_safe]
            attenuated = bool(float(np.median(ev)) < self.cfg.tau_evidence)
        lad = classify(delta_f, delta_sr, tex, self.cfg, digest_margin=margin,
                       excluded=excluded, attenuated=attenuated)
        return VerifyResult(delta_f=delta_f, delta_sr=delta_sr, ladder=lad,
                            texture=tex, image_id=image_id, key_ok=True,
                            digest_margin=margin)
