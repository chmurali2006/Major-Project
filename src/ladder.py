"""The ladder: trip table, then three rungs, then a reason code.

Every block leaves this module with a verdict **and** a reason, including
INTACT. A verdict without a reason is a guess.

Rung 1  trip table on (fragile error, semi-robust error).
Rung 2  neighbour corroboration, applied only to WEAK evidence. Decisive
        evidence (a full tag mismatch, delta_f >= tau_strong) stands alone -
        otherwise a single 8x8 paste, battery condition 6, would be censored.
Rung 3  texture context. A flat received block was probably refused at embed
        time, and a refused block carries no tag, so its bits read as noise.
        Such a block cannot be called tampered and must abstain with
        'capacity_refusal'. This is the price the gate charges and it is
        reported as coverage, not hidden.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage
from scipy.ndimage import median_filter

from .config import Config

# verdict codes
INTACT, TAMPERED, CANNOT_SAY = 0, 1, 2
VERDICT_NAME = {INTACT: "intact", TAMPERED: "tampered", CANNOT_SAY: "cannot_say"}

# reason codes (the four named reasons plus key mismatch)
NONE_ = 0
ROUTINE_HANDLING = 1
CAPACITY_REFUSAL = 2
GEOMETRY_CHANGE = 3
EVIDENCE_CONFLICT = 4
KEY_MISMATCH = 5
REASON_NAME = {
    NONE_: "none",
    ROUTINE_HANDLING: "routine_handling",
    CAPACITY_REFUSAL: "capacity_refusal",
    GEOMETRY_CHANGE: "geometry_change",
    EVIDENCE_CONFLICT: "evidence_conflict",
    KEY_MISMATCH: "key_mismatch",
}


@dataclass(frozen=True)
class LadderResult:
    verdict: np.ndarray        # (ny, nx) int8
    reason: np.ndarray         # (ny, nx) int8

    @property
    def tampered(self) -> np.ndarray:
        return self.verdict == TAMPERED

    def coverage(self) -> float:
        return float((self.verdict != CANNOT_SAY).mean())


def _neighbour_count(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(np.int16)
    p = np.pad(m, 1)
    total = np.zeros_like(m, dtype=np.int16)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            if dy == 1 and dx == 1:
                continue
            total += p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    return total


def classify(delta_f: np.ndarray, delta_sr: np.ndarray, texture: np.ndarray,
             cfg: Config,
             excluded: np.ndarray | None = None,
             attenuated: bool = False,
             erased: np.ndarray | None = None) -> LadderResult:
    df = np.asarray(delta_f, dtype=np.float64)
    dsr = np.asarray(delta_sr, dtype=np.float64)
    tex = np.asarray(texture, dtype=np.float64)
    if df.shape != dsr.shape or df.shape != tex.shape:
        raise ValueError("delta_f, delta_sr and texture must share a shape")

    f_hi = df > cfg.tau_f
    s_hi = dsr > cfg.tau_sr

    verdict = np.full(df.shape, INTACT, dtype=np.int8)
    reason = np.full(df.shape, NONE_, dtype=np.int8)
    zeros = np.zeros(df.shape, bool)

    broken = f_hi                      # any mismatch at all
    decisive = df > cfg.tau_strong     # the block lost its tag

    # Blocks outside the imaging field carry no mark and no evidence. They are
    # removed from the area count, or a white surround would be read as a
    # globally degraded image and every clean PH2 scan would abstain.
    excluded = zeros if excluded is None else np.asarray(excluded, bool)
    broken = broken & ~excluded
    decisive = decisive & ~excluded

    # ---- erasure: the mark is not misaligned, it is gone.
    #
    # The correlation score is normalised by the residual it finds, so a block
    # whose mark was deleted still scores 1.0 on the part that survived. The
    # per-block evidence is the complement: what fraction of the sixty slots
    # still hold a readable residual. On a gamut-safe block the answer must be
    # all of them, so anything less is physical removal. A lone erased block
    # sits inside the clean accident rate (0.1% of blocks at this threshold),
    # so it needs neighbours; a painted box (36 blocks) or an inpainted wound
    # (415) supplies them.
    erased_ok = zeros
    if erased is not None:
        erased = np.asarray(erased, bool) & ~excluded
        support_e = _neighbour_count(decisive | erased)
        erased_ok = erased & (support_e >= cfg.corroborate_min_erased)
        broken = broken | erased_ok
        decisive = decisive | erased_ok

    # ---- how widespread is the damage?
    #
    # Extent alone used to decide this, at 5% of the frame. That is the wrong
    # test: the Telea wound covers 10.1% and was excused as routine handling,
    # while every global transform in the battery already announces itself
    # through `attenuated` (median tag evidence <= 0.95 over gamut-safe
    # blocks). The extent rule is kept only as a backstop for damage that
    # covers more than half the frame, where no local attribution is possible.
    area = float(broken.mean()) if broken.size else 0.0
    widespread = bool(area > cfg.tau_area)

    # ---- rung 2: weak evidence, corroborated by its neighbours
    #
    # The tag is bound to content per slot, which is what lets it survive the
    # gamut clamps a clean image inflicts. The price is that a content change
    # flips only the slots it touches, so a forged region reads as *partial*
    # disagreement rather than total loss. Partial disagreement is worth
    # acting on when it is a region: a lesion removal covers hundreds of
    # adjacent blocks, while the one percent of blocks a clean image damages
    # at the gamut edge are scattered singletons and abstain.
    weak = broken & ~decisive
    weak_ok = zeros
    if weak.any():
        labels, n = ndimage.label(weak, structure=np.ones((3, 3), dtype=int))
        sizes = np.bincount(labels.ravel(), minlength=n + 1)
        big = sizes >= cfg.weak_cluster_min
        big[0] = False
        weak_ok = weak & big[labels] if n else zeros
        decisive = decisive | weak_ok

    # NOTE: `not widespread`, never `~widespread`. On a Python bool the tilde
    # yields an int (-1), which silently converts a boolean mask into integer
    # fancy indexing and scatters verdicts over unrelated blocks.
    tamper = decisive & (not widespread) & (not attenuated)
    verdict[tamper] = TAMPERED

    handling = broken & (widespread | attenuated)
    verdict[handling] = CANNOT_SAY
    reason[handling] = ROUTINE_HANDLING

    # weak breakage confined to a few blocks: not decisive either way
    weak_local = broken & (not widespread) & ~decisive
    verdict[weak_local] = CANNOT_SAY
    reason[weak_local] = EVIDENCE_CONFLICT

    conflict = ~f_hi & s_hi
    verdict[conflict] = CANNOT_SAY
    reason[conflict] = EVIDENCE_CONFLICT

    # ---- decisive-clean
    # A perfect 60/60 tag match cannot be produced without the key: under any
    # forgery its probability is 2^-60. When the fragile carrier is exact and
    # the semi-robust reference complains, the reference is the one that is
    # wrong - host interference with a unit-norm sequence, not evidence.
    # `& ~erased_ok` is load-bearing. A half-erased block scores a perfect
    # correlation on the half of its mark that survived, so df == 0 exactly -
    # and this rule used to hand it back as INTACT after the erasure test had
    # already called it TAMPERED.
    decisive_clean = conflict & (df == 0.0) & ~erased_ok
    verdict[decisive_clean] = INTACT
    reason[decisive_clean] = NONE_

    # ---- outside the imaging field: no mark, no evidence
    if excluded.any():
        verdict[excluded] = CANNOT_SAY
        reason[excluded] = CAPACITY_REFUSAL

    # ---- rung 3: flat block, no reliable tag can have been written.
    # Only meaningful while the gate is on: if the embedder marked every block,
    # a flat received block is not evidence of anything.
    cannot_judge = cfg.gate_enabled & (tex < cfg.texture_min) & (verdict != INTACT)
    verdict[cannot_judge] = CANNOT_SAY
    reason[cannot_judge] = CAPACITY_REFUSAL

    return LadderResult(verdict=verdict, reason=reason)


def all_cannot_say(shape: tuple[int, int], why: int = KEY_MISMATCH) -> LadderResult:
    return LadderResult(verdict=np.full(shape, CANNOT_SAY, dtype=np.int8),
                        reason=np.full(shape, why, dtype=np.int8))


def texture_of(luma: np.ndarray) -> np.ndarray:
    """Per-block local standard deviation of the received luma, 8-bit levels."""
    h, w = luma.shape
    return np.asarray(luma, np.float64).reshape(h // 8, 8, w // 8, 8).std(axis=(1, 3))
