"""Frozen parameters for the whole project.

Architecture rule: this is the only module allowed to contain a tunable
number. Every other module imports from here. Each entry records whether the
value came from the literature or was chosen here and validated later.

Provenance codes
  LIT  taken from a published source (named)
  CHOSEN  selected here; see docs/AMENDMENTS.md for the measurement that
          supports it, or the sprint gate that will validate it
  DERIVED  arithmetic on another value in this file
"""

from dataclasses import dataclass, replace

# ---------------------------------------------------------------- geometry
BLOCK = 8                     # CHOSEN  dossier §9
GRID = 64                     # DERIVED 512 / 8
IMAGE_SIZE = 512              # CHOSEN  dossier §9
N_BLOCKS = GRID * GRID        # DERIVED 4096
N_DETAIL = 60                 # DERIVED (16+4)*3, verified in test_transform

# ---------------------------------------------------------------- fragile carrier
DELTA_F = 8.0                 # LIT     PFF-WM (CheXpert), Khaldi 2026
OFFSET_F = DELTA_F / 4.0      # DERIVED quarter step, dossier §13
TAG_BITS = 60                 # DERIVED one bit per detail coefficient

# ---------------------------------------------------------------- digest
Q_DIGEST = 32.0               # CHOSEN  validated by the stability receipt
DIGEST_COEFFS = 4             # DERIVED level-2 LL is 2x2
DIGEST_BITS = 12              # DERIVED 4 coeffs x 3 bits
DIGEST_CLIP = 3               # CHOSEN +-3 quantisation steps

# ---------------------------------------------------------------- semi-robust carrier
BETA0 = 8.0                   # CHOSEN  sweep: same detection as 12 at +0.8 dB
LAMBDA_REGION = 1.0           # LIT form, value CHOSEN by sweep (+0.65 dB,
                              #          same detection; 2.0 costs 2.5 dB)
DCT_LO = 3                    # CHOSEN  block band u+v in [3,6], 22 coeffs
DCT_HI = 6                    # CHOSEN  see A-005
ROBUST_TAG_BIT = 0            # DERIVED the keyed sign comes from the sequence

# ---------------------------------------------------------------- gate and ladder
TEXTURE_MIN = 3.0             # CHOSEN  dossier §11, validated in S2
GATE_ENABLED = False          # CHOSEN  by measurement, A-007: the gate costs
                              #          11 points of detection and half the IoU
                              #          for 0.08 dB. Falsification check 3.
MAX_SHIFT = 16.0              # CHOSEN  largest block DC shift allowed to fit
                              #         the mark inside the RGB gamut
EXCUSE_SLACK = 3.0            # CHOSEN  widening of the excused set at verify
AMP_MIN = 2.0                  # MEASURED  smallest per-block pixel excursion
                              # accepted as a mark. Below this the integer
                              # round in compose() can erase the sign, so the
                              # block is refused instead of tagged unreliably.
WINDOW_MIN = 32.0             # MEASURED  smallest per-block gamut window the
                              # encoder will attempt. A block's legal luma
                              # window has p1=74 levels over PH2, and Carrier A's
                              # worst per-block excursion spread is 20.7, so 32
                              # leaves room for the mark and keeps the refusal
                              # set empty. The measure is shift-invariant, so the
                              # verifier reproduces it exactly.
TAU_SHIFT_EXCUSE = 5.0        # DERIVED the mark moves a pixel by at most this much
TAU_F = 0.60                 # MEASURED  a block is "broken" when its normalised
                            # correlation with the expected tag falls below
                            # 0.40, i.e. 3 standard deviations (1/sqrt(60) =
                             # 0.13) above the zero mean of a block carrying no
                             # tag. Measured on PH2: clean blocks reach 0.406 at
                            # their worst and 0.714 at p1; tampered blocks reach
                            # 0.439 at their worst and 0.325 at p99. The blank
                            # blocks that remain in the statistic are excused by
                            # the container's own geometry rules.

TAU_SR = 0.25                 # CHOSEN  paste32 p50 0.54; safe because a clean
                              # block has delta_f == 0 and never reaches this cell
TAU_STRONG = 0.75             # MEASURED  decisive evidence: correlation with the
                            # expected tag below 0.25, i.e. the block carries
                            # essentially none of its own tag. Must stay well
                            # above TAU_F - `strong` is nested inside `broken`,
                            # and a block only weakly degraded (sigma=1 noise
                            # leaves correlation near 0.5) is neither.
DIGEST_MARGIN_MIN = 2.0       # CHOSEN  LL2 levels from a quantisation boundary below
                              #         which the digest is not trustworthy
TAU_SR_LONE = 0.55            # CHOSEN  PH2: clean lone blocks reach 0.49,
                              #         called tampered if its reference is decisively
                              #         broken (two-sided evidence)
TAU_AREA = 0.05               # CHOSEN  fraction of blocks that may be broken
                              #         before the damage is called widespread.
                              #         Widespread = handling; confined = an edit.
                              #         Battery's largest edit is 64x64 = 1.6%.
CORROBORATE_MIN = 2           # CHOSEN  neighbours needed for weak evidence

# ---------------------------------------------------------------- evaluation
IOU_DETECT = 0.10             # CHOSEN  the stated detection rule, Trap 16
BOOTSTRAP_N = 2000            # CHOSEN  dossier §18
BOOTSTRAP_SEED = 20261019     # CHOSEN  seed inventory entry

# ---------------------------------------------------------------- container
PNG_COMPRESS_LEVEL = 6        # CHOSEN  lossless, pinned for byte-identical reruns

PROVENANCE = {
    "BLOCK": "CHOSEN dossier §9",
    "DELTA_F": "LIT PFF-WM 2026",
    "OFFSET_F": "DERIVED",
    "Q_DIGEST": "CHOSEN",
    "BETA0": "CHOSEN from spike",
    "LAMBDA_REGION": "LIT PFF-WM attention form",
    "TEXTURE_MIN": "CHOSEN dossier §11",
    "TAU_F": "CHOSEN, grid-searched S2",
    "TAU_SR": "CHOSEN from spike",
    "IOU_DETECT": "CHOSEN, Trap 16",
}


@dataclass(frozen=True)
class Config:
    """An experiment's frozen configuration. All defaults come from above."""

    delta_f: float = DELTA_F
    q_digest: float = Q_DIGEST
    beta0: float = BETA0
    lam: float = LAMBDA_REGION
    dct_lo: int = DCT_LO
    dct_hi: int = DCT_HI
    texture_min: float = TEXTURE_MIN
    gate_enabled: bool = GATE_ENABLED
    max_shift: float = MAX_SHIFT
    excuse_slack: float = EXCUSE_SLACK
    window_min: float = WINDOW_MIN
    amp_min: float = AMP_MIN
    tau_shift_excuse: float = TAU_SHIFT_EXCUSE
    tau_f: float = TAU_F
    tau_sr: float = TAU_SR
    tau_strong: float = TAU_STRONG
    tau_area: float = TAU_AREA
    digest_margin_min: float = DIGEST_MARGIN_MIN
    tau_sr_lone: float = TAU_SR_LONE
    corroborate_min: int = CORROBORATE_MIN
    iou_detect: float = IOU_DETECT
    bind_address: bool = True          # ablation switch, falsification check 1

    def with_(self, **kw) -> "Config":
        return replace(self, **kw)


DEFAULT = Config()
