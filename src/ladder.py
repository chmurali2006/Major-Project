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
             cfg: Config, digest_margin: np.ndarray | None = None,
             excluded: np.ndarray | None = None,
             attenuated: bool = False) -> LadderResult:
    df = np.asarray(delta_f, dtype=np.float64)
    dsr = np.asarray(delta_sr, dtype=np.float64)
    tex = np.asarray(texture, dtype=np.float64)
    if df.shape != dsr.shape or df.shape != tex.shape:
        raise ValueError("delta_f, delta_sr and texture must share a shape")

    f_hi = df > cfg.tau_f
    s_hi = dsr > cfg.tau_sr

    verdict = np.full(df.shape, INTACT, dtype=np.int8)
    reason = np.full(df.shape, NONE_, dtype=np.int8)

    # ---- rung 1: how widespread is the damage?
    #
    # The fragile carrier is decisive: a clean block has delta_f == 0 and a
    # replaced block has delta_f ~ 0.5. What it cannot say by itself is why.
    # The answer is spatial:
    #
    #   widespread  the mark is broken on a large share of the image
    #               -> routine handling. JPEG 90 breaks ~100% of blocks.
    #   confined    almost every block is intact and a few are broken
    #               -> those blocks were edited. The largest battery edit
    #                  (64x64) touches 1.6% of blocks.
    #
    # This is the job the dossier gives the two-carrier rule - separate
    # "recompressed" from "edited" - carried out by extent instead of by an
    # absolute reference threshold, because measurement showed the absolute
    # thresholds overlap (JPEG 90 delta_f ~ 0.37; paste ~ 0.50).
    broken = f_hi                          # any mismatch at all
    strong = df > cfg.tau_strong           # decisive: content or digest moved

    # Blocks outside the imaging field carry no mark and no evidence. They are
    # removed from the area count, or a white surround would be read as a
    # globally degraded image and every clean PH2 scan would abstain.
    if excluded is not None:
        excluded = np.asarray(excluded, bool)
        broken = broken & ~excluded
        strong = strong & ~excluded

    area = float(broken.mean()) if broken.size else 0.0
    widespread = bool(area > cfg.tau_area)

    # ---- rung 1a: was the image changed as a whole?
    #
    # `attenuated` is supplied by the verifier: it is true when the tag's own
    # amplitude is uniformly below what a full mark would be, measured only in
    # blocks where the RGB gamut cannot have clipped the mark (see
    # TAU_EVIDENCE). A local edit leaves that measurement at 1.00, because a
    # copy-move pastes already-marked pixels. A global transform - resample,
    # recompression, additive noise - attenuates it everywhere. So a broken
    # block in an attenuated image is not evidence of an edit: the image was
    # transformed, and a fragile mark cannot certify it afterwards.
    #
    # This is the fix for condition 11 on ISIC 2018. On a smooth image most
    # blocks carry almost no detail, so a +-2 level mark survives a 90% resize
    # round trip and only the few blocks containing an edge break. Few broken
    # blocks, scattered along edges, look exactly like localised tampering:
    # measured 27.3% false claims on ISIC-300 against 0.0% on the more textured
    # PH2. Reproducer: the same transform on pre-blurred PH2 claimed 79-96%.

    # NOTE: `not widespread`, never `~widespread`. On a Python bool the tilde
    # yields an int (-1), which silently converts a boolean mask into integer
    # fancy indexing and scatters verdicts over unrelated blocks.
    tamper = strong & (not widespread) & (not attenuated)
    verdict[tamper] = TAMPERED

    handling = broken & (widespread | attenuated)
    verdict[handling] = CANNOT_SAY
    reason[handling] = ROUTINE_HANDLING

    # weak breakage confined to a few blocks: not decisive either way
    weak_local = broken & (not widespread) & ~strong
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
    decisive_clean = conflict & (df == 0.0)
    verdict[decisive_clean] = INTACT
    reason[decisive_clean] = NONE_

    # ---- rung 1b: digest confidence
    #
    # A single strong block with no strong neighbour is either a one-block
    # edit (battery condition 6) or one block whose coarse digest flipped
    # under mild noise. The bit error is ~0.5 in both cases. What separates
    # them is whether the digest *could* have flipped: a flip requires a
    # coefficient within a level or two of a quantisation boundary.
    if digest_margin is not None:
        support_all = _neighbour_count(tamper)
        lone = tamper & (support_all == 0)
        marginal = (lone
                    & (np.asarray(digest_margin) < cfg.digest_margin_min)
                    & (dsr < cfg.tau_sr_lone))
        verdict[marginal] = CANNOT_SAY
        reason[marginal] = EVIDENCE_CONFLICT

    # ---- rung 2: weak evidence needs support from its neighbours
    weak = tamper & (df < cfg.tau_strong)
    if weak.any():
        support = _neighbour_count(tamper)
        isolated = weak & (support < cfg.corroborate_min)
        verdict[isolated] = CANNOT_SAY
        reason[isolated] = ROUTINE_HANDLING

    # ---- outside the imaging field: no mark, no evidence
    if excluded is not None and excluded.any():
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
