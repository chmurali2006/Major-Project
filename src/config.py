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

# ---------------------------------------------------------------- tag signature
# The tag names the block's own quantised detail coefficients (A-024). There is
# no separate digest to tune: the quantisation step is DELTA_F, because the
# signature is exactly the lattice cell the carrier is about to write into.
SIG_CLIP = 127                # DERIVED int8 signature range
SIG_DELTA = 8.0               # DERIVED  the signature is the carrier's own
                              # lattice index, so content is named at the finest
                              # scale the mark itself uses. The tag survives a
                              # clip because it is mixed per slot, not because
                              # the signature is coarse.

# ---------------------------------------------------------------- semi-robust carrier
BETA0 = 8.0                   # CHOSEN  sweep: same detection as 12 at +0.8 dB
LAMBDA_REGION = 0.0           # MEASURED  region-weighted strength (the old 1.0)
                            # buys +0.05 IoU on the single 8x8-paste case and
                            # nothing at all on conditions 1-5, while costing
                            # 0.65 dB mean PSNR and putting the worst image at
                            # 37.37 dB - below the 37.8 dB floor. At 0.0 every
                            # image in the corpus clears the floor (worst
                            # 38.39 dB). A-018.
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
FIT_MARGIN = 4.0              # MEASURED  levels of headroom a block is fitted
                              #         to have before it is marked. The mark's
                              #         measured per-pixel excursion is p99 = 5,
                              #         max = 9; a block that cannot be fitted
                              #         within MAX_SHIFT is refused. Fitting is
                              #         what turns refused blocks into markable
                              #         ones, and it is where the image quality
                              #         goes. Measured on all 200 PH2 images
                              #         (A-029): margin 3 -> detection 0.9760,
                              #         PSNR 38.77 (worst 37.65); margin 4 ->
                              #         0.9970, 38.27 (worst 35.52). 3 sits
                              #         exactly on the detection bar with no
                              #         room, 6 pushes the mean PSNR under its
                              #         own bar. 4 is the last setting that
                              #         clears the mean, and its worst image is
                              #         reported rather than hidden.
EXCUSE_SLACK = 3.0            # CHOSEN  widening of the excused set at verify
AMP_MIN = 2.0                  # MEASURED  smallest per-block pixel excursion
                              # accepted as a mark. Below this the integer
                              # round in compose() can erase the sign, so the
                              # block is refused instead of tagged unreliably.
USE_ROBUST = True             # falsification switch: False removes Carrier B
                              # from both the embedder and the verifier. Used by
                              # scripts/ablate.py, never by a reported run.
FIELD_EXCUSE = True           # falsification switch: False stops excusing the
                              # out-of-field surround. Used by scripts/ablate.py.
TAU_ERASE = 0.75              # MEASURED  per-block tag evidence below which the
                              # mark was physically removed from a block the
                              # gamut cannot have clipped. PH2 n=6 images,
                              # gamut-safe blocks only:
                              #   clean            0.1% of blocks below 0.75
                              #   sigma=1          0.2%
                              #   text 64x24      88.5% of the changed blocks
                              #   inpaint (Telea) 91.3% of the changed blocks
                              # A lone erased block is within the clean accident
                              # rate, so it needs CORROBORATE_MIN_ERASED support;
                              # a painted box or an inpainted wound is a solid
                              # region and carries it. This is the A-020 fix.
CORROBORATE_MIN_ERASED = 2    # MEASURED  erased neighbours needed before an
                              # erased block is believed. Clean PH2 images
                              # produce isolated pairs at most; a 36-block text
                              # box and a 415-block inpainted wound are solid.
TAU_EVIDENCE = 0.95           # MEASURED  median tag evidence over gamut-safe
                              # blocks below which the image was transformed as
                              # a whole rather than edited in places.
                              # PH2 n=120 images, blocks where every pixel sits
                              # > 3 levels inside its own gamut interval:
                              #   clean        1.00 (p0 = p95 = 1.00)
                              #   copy-move    1.00 (p0 = p95 = 1.00)
                              #   sigma=1      0.88 (max 0.90)
                              #   90% resize   0.53-0.68
                              # blur + resize  0.50-0.58
                              # Zero overlap; 0.95 sits midway with 0.05 margin
                              # on both sides.
GAMUT_SAFE_MARGIN = 8.0       # MEASURED  levels a pixel must sit inside its own
                              # gamut interval for its block to count as
                              # gamut-safe. It has to exceed the largest
                              # per-pixel excursion the mark can make, or a
                              # "safe" block still clips, its evidence falls
                              # below 1.00 for reasons that have nothing to do
                              # with editing, and the attenuation test then
                              # abstains on a clean image. Measured on PH2:
                              # at 3 levels, 3 of the first 60 images had a
                              # median evidence below 0.95 and every copy-move
                              # block in them was excused as routine handling
                              # (detection 0.95 with zero claims); at 6, 8 and
                              # 10 the same images detect all 16-64 blocks.
                              # 8 leaves a margin over the measured excursion.
USE_ATTENUATION = True        # falsification switch: False disables the
                              # global-attenuation abstention (A-021).
CORROBORATE_MIN_BLOCKS = 8     # CHOSEN  broken blocks needed before the
                              # substituted/transformed test is trusted.
                              # Below this the median reference error is noise,
                              # and the lone-block rule (A-009) decides instead.
WINDOW_MIN = 32.0             # MEASURED  smallest per-block gamut window the
                              # encoder will attempt. A block's legal luma
                              # window has p1=74 levels over PH2, and Carrier A's
                              # worst per-block excursion spread is 20.7, so 32
                              # leaves room for the mark and keeps the refusal
                              # set empty. The measure is shift-invariant, so the
                              # verifier reproduces it exactly.
TAU_SHIFT_EXCUSE = 5.0        # DERIVED the mark moves a pixel by at most this much
TAU_F = 0.30                 # MEASURED  a block is "broken" when its normalised
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
TAU_STRONG = 0.60             # MEASURED  decisive evidence: correlation with the
                            # expected tag below 0.25, i.e. the block carries
                            # essentially none of its own tag. Must stay well
                            # above TAU_F - `strong` is nested inside `broken`,
                            # and a block only weakly degraded (sigma=1 noise
                            # leaves correlation near 0.5) is neither.
TAU_AREA = 0.50               # MEASURED  fraction of blocks that may be broken
                              #         before the damage is called widespread
                              #         unconditionally. Extent alone is the wrong
                              #         test: the Telea wound covers 10.1% of the
                              #         frame and every global transform in the
                              #         battery trips the attenuation test
                              #         (median evidence <= 0.90), so raising this
                              #         to 0.5 hands global handling to A-021 and
                              #         stops a large local edit being excused as
                              #         "routine processing". A-025.
CORROBORATE_MIN = 2           # CHOSEN  neighbours needed for weak evidence
SCATTER_MIN_COMPONENTS = 12   # MEASURED  how many disconnected islands of damage
                              #           it takes before the damage is read as a
                              #           global codec rather than surgery. JPEG
                              #           codes each 8x8 block independently, so a
                              #           re-encode damages a scatter of isolated
                              #           blocks; a paste, a paint box or an
                              #           inpainted wound damages one contiguous
                              #           region. Measured on 60 PH2 images: a
                              #           Q100/q99/q98 re-encode leaves a median of
                              #           64/103/250 islands (p5 = 33/72/131), while
                              #           every edit condition stays at 1-9 (max 9,
                              #           the burned-in text). 12 sits between the
                              #           two populations with room on both sides.
                              #           A-031.
WEAK_CLUSTER_MIN = 64         # MEASURED  size, in connected blocks, that
                              # partial tag disagreement must form before it is
                              # believed. A clean image damages about 1% of its
                              # blocks at the gamut edge; those scars are
                              # scattered, and the largest connected one over
                              # eight PH2 images was 45 blocks. A forged region -
                              # a lesion painted out - is hundreds. A neighbour
                              # count cannot tell five scattered from five
                              # adjacent; a connected component can.

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
    "TAU_ERASE": "MEASURED, A-023",
    "BETA0": "CHOSEN from spike",
    "LAMBDA_REGION": "LIT PFF-WM attention form",
    "TEXTURE_MIN": "CHOSEN dossier §11",
    "TAU_F": "CHOSEN, grid-searched S2",
    "TAU_SR": "CHOSEN from spike",
    "IOU_DETECT": "CHOSEN, Trap 16",
}


DC_BIND = True                # MEASURED  bind the block's LL2 subband (its
                              #           mean and coarse gradients) into the
                              #           tag. The detail coefficients cannot
                              #           see a modification that only moves a
                              #           block's average, which is exactly what
                              #           burned-in text does; LL2 can, and the
                              #           mark never touches LL2, so it is bit
                              #           identical at embed and verify. A-030.
DC_SIG_DELTA = 4.0            # MEASURED  luma levels per step of the LL2 code.
                              #           LL2 reproduces the block mean to the
                              #           level (measured ratio 0.95-1.09 over a
                              #           random plane, and an integer shift of s
                              #           moves all four coefficients by exactly
                              #           s), so the code is exact on any image
                              #           the mark survives in and can be made
                              #           fine: a mean shift of one luma level
                              #           already moves the weighted sum by 2.75
                              #           of its 16 steps. Measured over 4/8/16/32/64
                              #           on 40 images: all five fix condition 21
                              #           (IoU 0.082 -> 0.27-0.31) and 4 leaves the
                              #           single-block case intact, A-030.


@dataclass(frozen=True)
class Config:
    """An experiment's frozen configuration. All defaults come from above."""

    delta_f: float = DELTA_F
    sig_delta: float = SIG_DELTA
    beta0: float = BETA0
    lam: float = LAMBDA_REGION
    dct_lo: int = DCT_LO
    dct_hi: int = DCT_HI
    texture_min: float = TEXTURE_MIN
    gate_enabled: bool = GATE_ENABLED
    max_shift: float = MAX_SHIFT
    fit_margin: float = FIT_MARGIN
    excuse_slack: float = EXCUSE_SLACK
    window_min: float = WINDOW_MIN
    corroborate_min_blocks: int = CORROBORATE_MIN_BLOCKS
    tau_evidence: float = TAU_EVIDENCE
    tau_erase: float = TAU_ERASE
    corroborate_min_erased: int = CORROBORATE_MIN_ERASED
    gamut_safe_margin: float = GAMUT_SAFE_MARGIN
    use_attenuation: bool = USE_ATTENUATION
    use_robust: bool = USE_ROBUST
    field_excuse: bool = FIELD_EXCUSE
    amp_min: float = AMP_MIN
    tau_shift_excuse: float = TAU_SHIFT_EXCUSE
    tau_f: float = TAU_F
    tau_sr: float = TAU_SR
    tau_strong: float = TAU_STRONG
    tau_area: float = TAU_AREA
    corroborate_min: int = CORROBORATE_MIN
    weak_cluster_min: int = WEAK_CLUSTER_MIN
    scatter_min_components: int = SCATTER_MIN_COMPONENTS
    iou_detect: float = IOU_DETECT
    bind_address: bool = True          # ablation switch, falsification check 1
    dc_bind: bool = DC_BIND            # A-030: bind LL2 into the tag
    dc_sig_delta: float = DC_SIG_DELTA

    def with_(self, **kw) -> "Config":
        return replace(self, **kw)


DEFAULT = Config()
