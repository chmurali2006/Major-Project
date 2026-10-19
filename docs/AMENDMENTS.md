# Amendments to the dossier

Rule being followed (`01_PROJECT_DOSSIER.md` §7 and `04_PITFALLS_AND_TRAPS.md`
Trap 18): a change to the design or the battery is written down with its date,
its reason and its evidence, and every affected run is repeated.

**Status of every entry here: PROPOSED, not ratified.** Evidence comes from a
single synthetic dermoscopy phantom (512×512), Python 3.11, one laptop CPU. It
is enough to stop the design, not enough to enter a thesis. Each amendment
must be re-measured on the real ISIC 2018 trial slice before the Phase Two
freeze.

---

## A-001 — QIM reader replaced: sign of the residual, not floor at the boundary

**Date:** 2026-10-19 · **Affects:** Module 4, Module 7, Trap 2, pre-flight 3

**Dossier says:** `bit = (round((c' − round(c'/Δ)·Δ)/(Δ/2)) + 1) mod 2`
(quoted from PFF-WM Eq. 7).

**Problem.** At Δ = 8, Eq. 6 embeds at `q ± 2`. Evaluating Eq. 7 there gives
exactly `1.0` or `0.0`, i.e. the embedded point sits **on** the reader's
decision boundary. `floor(1.0) = 1` but `floor(0.9999999999999999) = 0`.
Measured bit error on a clean in-memory array with no processing at all: **50%**.

**Amendment.** `bit = 1 if (c' − round(c'/Δ)·Δ) > 0 else 0`. The decision
boundary moves to the midpoint between the two embedded levels, Δ/4 away from
each. Clean bit error: **0.000**.

**Consequence.** None for fidelity or capacity. Sensitivity is set by Δ, not by
the reader (see A-003).

---

## A-002 — Embedding order reversed: Carrier B first, Carrier A last

**Date:** 2026-10-19 · **Affects:** Module 4, Module 5, §13, §3 of the architecture

**Dossier says:** write detail coefficients (A), then mid-frequency DCT (B).

**Problem.** B perturbs pixels after A has quantised the detail coefficients,
so it re-breaks bits A just wrote — Trap 9 arriving through the back door.
Measured on a clean image after a PNG round trip, both carriers at β = 8:

| order | clean δf mean | clean δf max |
|---|---|---|
| A then B | 0.067 | 0.133 |
| B then A | 0.000 | 0.000 |

A clean image reporting 6.7% bit errors would put roughly a tenth of blocks
into a tampered or abstained cell before any attack exists.

**Amendment.** Embed B first, then A. A is exact by construction. The cost to B
is small and is absorbed by its strength parameter.

---

## A-003 — Fragility is block-scale, not pixel-level

**Date:** 2026-10-19 · **Affects:** §2, §6 claim 1, §7 bar 1, Trap 2,
pre-flight check 3, battery conditions 5-6

**Dossier says:** "Any one-level change crosses a decision boundary"
(§13), and pre-flight check 3 requires that perturbing one pixel by one level
changes a block's verdict.

**Problem.** A single pixel moves a level-1 Haar detail coefficient by 0.5
levels (weight 1/2 in 2D). The nearest decision boundary is Δ/4 = 2 levels
away at Δ = 8. A one-level pixel edit therefore flips **zero** bits.
Measured, Δ = 8, B→A:

| edit | δf in the edited block |
|---|---|
| one pixel +1 | 0.000 |
| one pixel +8 | 0.067 |
| 8×8 paste | 0.500 |
| 32×32 paste | 0.501 |

Lowering Δ does not rescue the claim: at Δ = 2 the clean round trip already
reads δf = 0.072 (unusable), at Δ = 4 a one-level pixel edit still reads 0.000
and a +4 edit reads 0.050.

**Amendment.**
1. The claim becomes: *the mark is fragile at block scale — any spatial edit of
   roughly one 8×8 block or larger is detected; a constant-offset change to a
   single block (DC only) is invisible by construction, because the digest is
   taken from LL, which such an edit replaces.*
2. Pre-flight check 3 is restated: *paste one 8×8 block from a distant address
   onto a control block; the pasted block must report tampered and the
   untouched control must report intact.*
3. Trap 2's guard is restated the same way. Its warning sign (a one-level
   change leaving INTACT) is expected behaviour at this granularity and must be
   documented as a limitation rather than treated as a bug.
4. Battery conditions 5 and 6 (16×16 and 8×8 paste) remain valid and are still
   the smallest real tests; nothing in the battery edits a single pixel.

**Consequence.** The thesis may not claim pixel-level sensitivity. Claim 6 in
§6 already prices a localisation floor of one block; this amendment makes the
same price explicit on sensitivity.

---

## A-004 — Carrier B's spreading sequence must be address-keyed

**Date:** 2026-10-19 · **Affects:** Module 5, Module 7, §14 trip table, claim 1

**Dossier says:** "p is a key-derived pseudo-random sequence" (§13) — derived
from the key, with the address used only by Carrier A's tag.

**Problem.** If `p` depends only on the key and the image identity, a block
copied from A to B carries a *valid* sequence for B's verifier. Fragile error
is high (the tag is address-bound) but semi-robust error is low, so the trip
table files copy-move under **CANNOT SAY — routine handling**, which is exactly
the confusion the two-carrier design exists to prevent.

**Amendment.** Both carriers are bound to the address:
`p, w = f(key, image_id, block_address)`. Then a moved block fails both
carriers and lands in TAMPERED, while benign recompression fails only A and
lands in routine handling.

**Consequence.** None measurable on fidelity. It is an invariant and gets a
unit test: copy-move must never land in the routine-handling cell.

---

## A-005 — Carrier B is per-block DCT, not global DCT

**Date:** 2026-10-19 · **Affects:** Module 5, BlockRecord.robust_error, §13

**Dossier's source paper** embeds the semi-robust mark in a **global**
512×512 DCT with `0.15·min(H,W) ≤ u+v ≤ 0.35·min(H,W)`, i.e. roughly 10⁴
coefficients for the whole image. The dossier's data model, however, requires a
`robust_error` **per 8×8 block**, and the trip table is applied per block.

**Problem.** A global spread-spectrum mark has no block-local support; δsr
cannot be computed per block from it without an arbitrary re-derivation.

**Amendment.** Carrier B uses the DCT of each 8×8 block, mid-frequency band
`3 ≤ u+v ≤ 6` (22 coefficients per block), sequence keyed by
(key, image_id, address). Measured separation at β = 12: clean 0.177,
JPEG 90 0.190, pasted block 0.563.

**Open item, not settled by this amendment.** The fragility ratio measured
this way is ρ ≈ 3.0 against a design target of ρ > 5. Candidate remedies, to be
tested in S2: widen the band to `2 ≤ u+v ≤ 7`, aggregate the correlation over
2×2 block groups before thresholding, or search τsr per region. The target
stays at 5 until a measurement says it cannot be met.

---

## A-006 — Carrier B is embedded before Carrier A is declared exact

**Date:** 2026-10-19 · **Affects:** Phase One gate

**Addition, not a change.** Because B precedes A, the Phase One gate gains one
check beyond the dossier's six:

> With both carriers enabled, on 100 clean images: δf = 0.000 on every admitted
> block, before and after a PNG round trip.

The dossier's check 1 covers A alone. This covers the interaction, which is
where the spike found the only clean-image failure.

---

## Amendment log

| ID | Date | Subject | Status |
|---|---|---|---|
| A-001 | 2026-10-19 | QIM reader corrected | proposed |
| A-002 | 2026-10-19 | Embed order B→A | proposed |
| A-003 | 2026-10-19 | Fragility restated at block scale | proposed |
| A-004 | 2026-10-19 | Carrier B address-keyed | proposed |
| A-005 | 2026-10-19 | Carrier B per-block DCT | proposed |
| A-006 | 2026-10-19 | Extra Phase One gate | proposed |

---

## A-007 — Texture gate disabled at the operating point

**Date:** 2026-10-19 · **Affects:** Module 2, §11, falsification check 3

**Dossier says:** background blocks below 3.0 levels of texture are refused and
recorded as capacity refusals.

**Measured**, synthetic phantoms, n=6, both carriers, same everything else:

| gate | PSNR | detection (paste 1-6) | block IoU | benign false claims |
|---|---|---|---|---|
| on | 37.18 dB | 89% | 0.527 | 6/30 |
| **off** | 37.10 dB | **100%** | **0.986** | **0/30** |

The gate buys **0.08 dB** and costs **11 points of detection and 46 points of
IoU**. A refused block carries no tag, so it reads as a broken tag at verify
time; refusing them is what turns a clean-ish block into a false accusation.
Refusals also cannot be communicated to the verifier without a side channel an
attacker could edit.

**Amendment.** `GATE_ENABLED = False` is the operating point. The gate code and
its flag stay: falsification check 3 turns it back on, and the LiTS run may
need it where clamping makes blocks genuinely unmarkable.

**Caveat.** Dermoscopy phantoms are not ISIC. The texture distribution of real
skin may make the gate cheaper or more expensive. Re-validate in S2 and record
the number before the freeze.

---

## A-008 — The tamper decision is spatial extent, not absolute thresholds

**Date:** 2026-10-19 · **Affects:** §14 trip table, Module 8, claim 3

**Dossier says:** four-cell trip table on absolute `delta_f` and `delta_sr`,
with thresholds grid-searched to a joint false-positive rate of 1e-4.

**Measured**, block-level, three phantoms:

| condition | delta_f mean | delta_f p99 | delta_sr mean | delta_sr p95 |
|---|---|---|---|---|
| clean | 0.000 | 0.000 | 0.143 | 0.420 |
| JPEG 90 | 0.372 | 0.533 | 0.153 | 0.451 |
| JPEG 75 | 0.463 | 0.617 | 0.243 | 0.526 |
| JPEG 50 | 0.489 | 0.633 | 0.351 | 0.533 |
| paste 32x32 | 0.515 | 0.692 | 0.551 | 0.910 |

The distributions **overlap on both axes**. Heavy JPEG and a paste both give
`delta_f` near 0.5; the reference carries the same host-interference tail
under benign handling that it does under editing. No pair of absolute
thresholds separates them, and a search for one would be fitting the fixture.

**Amendment.** The first rung becomes a test of *extent*:

    broken   = delta_f > tau_f
    strong   = delta_f > tau_strong
    widespread = mean(broken) > tau_area          (tau_area = 0.05)

    widespread  -> CANNOT SAY, reason routine_handling
    confined    -> strong blocks are TAMPERED

This is the job the dossier assigns to the two-carrier rule — separate
"recompressed" from "edited" — carried out by spatial extent. The largest
battery edit (64x64) touches 1.6% of blocks; a global operation touches
essentially all of them.

**Consequences, stated as limitations.**
1. A paste applied *on top of* a globally degraded image lands in the
   widespread regime and is reported as handling. Compound attacks are outside
   the frozen battery; this goes in the limitations chapter.
2. The four cells remain in the code and in the report as the *explanation* of
   a verdict, but they no longer decide it.
3. Claim 3 must be re-worded: the contribution is abstention with separated
   reasons, and the separation is by extent and digest confidence, not by an
   absolute reference threshold.

---

## A-009 — Digest confidence for isolated blocks

**Date:** 2026-10-19 · **Affects:** Module 3, Module 8

**Problem.** Under Gaussian noise sigma = 1 (battery condition 10, benign), a
coarse LL2 coefficient occasionally crosses a quantisation boundary. That
changes the whole 60-bit tag for that block: `delta_f` jumps to ~0.5 at one
isolated block, indistinguishable from a one-block paste. Measured: one false
tamper claim in ten images, against a benign bar of 0.5%.

**Amendment.** The verifier computes, per block, the distance from each LL2
coefficient to the nearest digest quantisation boundary. A lone strong block
whose digest is marginal **and** whose semi-robust reference is not decisively
broken is reported CANNOT SAY (evidence_conflict) rather than TAMPERED.

**Measured effect** (n=10): benign false claims 0/50. Condition 6 detection
80%; the remaining 20% abstain, which the battery explicitly permits for
condition 6 ("tamper signal or abstention; never silent INTACT or a fabricated
address").

---

## A-010 — Operating-point parameters, after the sweeps

**Date:** 2026-10-19 · **Affects:** `src/config.py`

| parameter | value | evidence |
|---|---|---|
| `BETA0` | 8.0 | same detection as 12 and 16, +0.8 dB over 12 |
| `LAMBDA_REGION` | 1.0 | same detection as 2.0, +0.65 dB |
| `Q_DIGEST` | 32 | stability 100% under JPEG 90/75/50 |
| `TAU_F` | 0.05 | clean `delta_f` is exactly 0 |
| `TAU_STRONG` | 0.25 | live band between noise flips and replace |
| `TAU_AREA` | 0.05 | largest battery edit is 1.6% of blocks |
| `TAU_SR` | 0.25 | paste32 p50 = 0.54 |
| `TAU_SR_LONE` | 0.45 | single-block paste p75 = 0.53 |
| `DIGEST_MARGIN_MIN` | 2.0 levels | noise sigma=1 moves LL2 by ~0.25 |
| fit margin | `delta/2 + 1 + beta0(1+lam)/8` | zero refusals on phantoms |

All values are CHOSEN and must be re-validated on the real corpus before the
battery is frozen. None is a thesis number yet.

---

## Amendment log

| ID | Date | Subject | Status |
|---|---|---|---|
| A-001 | 2026-10-19 | QIM reader corrected | proposed |
| A-002 | 2026-10-19 | Embed order B→A | proposed |
| A-003 | 2026-10-19 | Fragility restated at block scale | proposed |
| A-004 | 2026-10-19 | Carrier B address-keyed | proposed |
| A-005 | 2026-10-19 | Carrier B per-block DCT | proposed |
| A-006 | 2026-10-19 | Extra Phase One gate | proposed |
| A-007 | 2026-10-19 | Texture gate disabled | proposed |
| A-008 | 2026-10-19 | Tamper decision by spatial extent | proposed |
| A-009 | 2026-10-19 | Digest confidence for isolated blocks | proposed |
| A-010 | 2026-10-19 | Operating-point parameters | proposed |
| A-011 | 2026-10-19 | Gamut slack measured per pixel | proposed |
| A-012 | 2026-10-19 | Range fit bit-exact with the integer RCT | proposed |
| A-013 | 2026-10-19 | Mark headroom measured, not assumed | proposed |
| A-014 | 2026-10-19 | Verified excuse is a superset of the embed skip | proposed |
| A-015 | 2026-10-19 | Mark saturated at the gamut; matched-filter read | proposed |
| A-016 | 2026-10-19 | Field excuse restricted to the border-connected surround | proposed |
| A-017 | 2026-10-19 | `sigma = 1` noise reclassified out of "benign" | **WITHDRAWN by A-021** |
| A-018 | 2026-10-19 | Region weighting removed (λ=0) | **accepted** |
| A-019 | 2026-10-19 | Ground truth from the measured pixel diff | **accepted** |
| A-020 | 2026-10-19 | Mean-only modifications are invisible | **OPEN — principal weakness** |
| A-021 | 2026-10-19 | Global-attenuation abstention | **accepted** |
| A-022 | 2026-10-19 | Per-block tag MAC: HMAC-SHA256 → keyed BLAKE2b | **accepted** |

---

## A-011 — Gamut slack is measured per pixel, not per block

**Date:** 2026-10-19 · **Affects:** `container.block_gamut`, module 6

**Dossier says:** a block can be shifted if the union of the pixels' legal
intervals is non-empty.

**Why it changed:** the union is the wrong object. A block shift moves every
pixel together, so what matters is the intersection of the intervals, and the
bounds must be reduced *after* subtracting each pixel's own luma. The union
version paired the tightest pixel bound with the most distant pixel and
declared 43% of normal PH2 blocks unmarkable.

**Evidence:** PH2, 12 images. Blocks refused fell from 75% to under 10%;
coverage of markable blocks rose from 0.247 to 0.905 (IMD392) and from 1.3%
refused to 0.0% (IMD396).

## A-012 — The range fit is bit-exact with the integer RCT

**Date:** 2026-10-19 · **Affects:** `container.exact_bounds`, `container.out_of_range`

**Why it changed:** the inverse transform uses `g = y − ((cb+cr) >> 2)`. The
real-valued form `(cb+cr)/4` disagrees with that integer shift by up to 0.75
levels. A one-level disagreement at the gamut edge is enough to revert a block
*after* it has been tagged, which makes a clean image accuse itself.

**Evidence:** with the float form, PH2 clean images reported 60% false tamper
blocks; with the bit-exact form the same images reported 0.

## A-013 — The mark's headroom is measured, not assumed

**Date:** 2026-10-19 · **Affects:** `pipeline.protect`, module 6

**Dossier assumption:** Carrier A moves a pixel by `Δ/4 = 2` levels, so a
2-level margin is enough.

**Measured:** Carrier A writes 60 detail coefficients per block. Summed through
the inverse Haar, the per-pixel excursion is **7.1 levels on average and 11 at
the maximum** — three to five times the assumed value. Every block therefore
needed a range shift that had not been reserved, and `compose()` reverted
blocks that had already been tagged.

**Evidence:** PH2, 12 images, 49 152 blocks: |Δpixel| p50 = 7, p95 = 9,
max = 11. Block excursion *spread* p50 = 13, max = 20.7.

## A-014 — The verifier's excused set must contain the encoder's skip set

**Date:** 2026-10-19 · **Affects:** `pipeline.verify`, `ladder.classify`

**Rule:** if a block is left unmarked at embed, the verifier must be able to
recognise that fact from the received image alone, and excuse it. If it
cannot, the block reads as fully broken and a clean image accuses itself.

**Why it is hard:** the encoder's decision depends on data the verifier does
not have (the tag, and therefore the mark). The only sound predicates are
those that are **invariant to a constant shift of the block**, because the
verifier sees the marked plane and the encoder saw the unmarked one.

**Resolution:** two such invariants are used — the in-field predicate
(A-016) and the per-block gamut window width
(`max(low−y) … min(high−y)`), whose width is unchanged by any constant shift.
A refusal that is not one of these is a bug, not a capacity limit, and is
asserted against in `tests/`.

## A-015 — The mark is saturated at the gamut, and read by matched filter

**Date:** 2026-10-19 · **Affects:** `pipeline.protect`, `carriers.FragileCarrier`,
`ladder.classify`, `config.TAU_F`, `config.TAU_STRONG`, module 4

**Problem.** Dermoscopy has large saturated regions: 54% of pixels in the
dark-vignette PH2 image IMD392 sit within one level of the gamut edge, and on
that image 85% of blocks contain a pixel with *zero* room in one direction
(72%, 80% on IMD393/394; 8% median over a ten-image sample). A signed mark
cannot fit there at all.

**Decision.** Do not revert such a block and do not try to shift it — both
change the digest the block is tagged against, which reintroduces A-014. Let
the gamut saturate the mark instead, and make the reader insensitive to how
much of the mark survived:

- `FragileCarrier.score` returns the normalised correlation between the
  residual vector and the keyed sign vector, not a per-bit match.
- `delta_f = 1 − score`. Clean block = 0, block carrying no tag = 1.
- `TAU_F = 0.60`: the null statistic (no tag) has standard deviation
  `1/sqrt(60) = 0.13`, so 0.40 correlation is 3σ. A block is "broken" below
  0.40 correlation.
- `TAU_STRONG = 0.75` (correlation < 0.25). It must stay **above** `TAU_F`
  because `strong` nestles inside `broken`; with the old 0.25 a block only
  mildly degraded by noise was promoted to decisive evidence.

**Evidence (PH2, 8 images, 32 768 blocks, clipping allowed with no exclusion):**

| population | worst | p99 | p50 |
|---|---|---|---|
| clean, correlation | 0.406 | — | 1.000 |
| clean, correlation p1 | — | 0.714 | — |
| tampered (paste), correlation | 0.439 | 0.325 | 0.060 |

A threshold at 0.40 leaves **zero** clean blocks below it and 0.35% of
tampered blocks below it.

**Battery effect (PH2 n=20, 22 conditions):** detection 100% (conditions 1–5),
IoU 0.906, PSNR 38.24 dB, benign claims 0% on JPEG 90/75/50 and resize,
verify 41 ms. `sigma = 1` noise still claims on 40% of images; see A-017.

## A-016 — The field excuse covers only the border-connected surround

**Date:** 2026-10-19 · **Affects:** `container.field_mask`, `pipeline.verify`

**Problem.** The "outside the imaging field" excuse was a pure local test
(90% of pixels saturated). An attacker can satisfy that test anywhere in the
image — paint a white rectangle and the blocks under it are excused, so the
edit hides behind an abstention. Battery condition 21 (burned-in text) is
exactly this attack.

**Decision.** Excuse only the saturated component that is **connected to the
image border**. A legitimate capture's surround always reaches the border; a
painted patch in the interior does not.

**Evidence:** condition 21 claim rose 45% → 50%; IoU unchanged. The remaining
misses are text drawn *on* the white surround, where no mark exists to
destroy — a capacity limit, not a detector failure, and it is reported as
`CANNOT_SAY(capacity_refusal)` rather than `INTACT`.

## A-017 — WITHDRAWN

**Status:** withdrawn 2026-10-19 by **A-021**. The reclassification existed
because the tool accused 31.5% of σ=1 images of tampering. It no longer does:
the global-attenuation rule abstains on them, so condition 10 passes as
originally frozen, in the `benign` family. The battery is therefore byte-for-
byte the dossier's, which is a stronger position than changing a frozen
condition and it is why the change is reversed rather than kept.

The text below is retained as the record of what was believed and why.

## A-017 (withdrawn) — `sigma = 1` noise is not benign for a fragile mark

**Date:** 2026-10-19 · **Affects:** battery condition 10, `docs/BENCHMARKS.md`
**Status:** ACCEPTED, 2026-10-19, on the project owner's direction ("do what is
best and what a supervisor will agree to"). Option 1 below was taken. This
changes a frozen condition, and every table produced after it says so.

**Observation.** On PH2 (n=20) condition 10 — additive Gaussian noise,
`sigma = 1` — is claimed as tampering on 40% of images. It is the only bar the
system currently fails. Every other benign condition is silent: JPEG 90, 75
and 50 and resize 90% all claim on 0% of images.

**Why it happens.** A fragile mark is destroyed by any change to the sample
values; that is its definition, not a defect. `sigma = 1` perturbs every
detail coefficient by about 0.29 levels against a mark amplitude of 2, which
is enough to erase the mark in patches. On this corpus it breaks 20–30 blocks
in the images it affects — 0.5–0.7% of the image, below the 5% extent rule, so
the ladder reads it as *localised* damage, which is what a tamper looks like.

**Why the battery's label is questionable.** The frozen battery places
condition 10 in the `benign` family. For a *fragile* scheme that label asserts
the mark should survive additive noise, which contradicts fragility. For a
*semi-fragile* scheme the assertion would be reasonable; this design is
fragile by Carrier A and semi-robust by Carrier B, and the ladder already has
a `CANNOT_SAY(routine_handling)` verdict for global degradation — but
localised breakage is by construction reported as tampering.

**Measured, for the decision:**

| condition | claim rate | coverage |
|---|---|---|
| JPEG 90 / 75 / 50 | 0% / 0% / 0% | 0.067 / 0.007 / 0.004 |
| resize 90% and back | 0% | 0.318 |
| noise `sigma = 1` | 40% | 0.852 |
| noise `sigma = 8` | 0% | 0.004 |

Note the shape: JPEG and `sigma = 8` destroy the mark *everywhere*, the extent
rule catches that and abstains. `sigma = 1` destroys it in patches, so the
tool localises them. The tool is behaving consistently; the condition's
family is what is in question.

**Options.**

1. **Reclassify condition 10 as `degrade`** (recommended). Rationale: a
   modification is not benign handling for a fragile mark. Benign then
   contains only operations that preserve sample values, and benign claim rate
   is 0%. The cost is that the battery changes after it was frozen, which must
   be recorded as such — not presented as a measurement.
2. **Keep the label and report the 40% as a known, documented failure.** The
   headline "benign FPR < 0.5%" then cannot be claimed.
3. **Add a scattered-breakage rule** (many small disconnected broken regions →
   abstain). Measured and rejected: `sigma = 1` breakage is 95% neighbour-
   connected and 77 blocks wide, indistinguishable from a 64×64 paste by
   spatial structure. Implementing it would cost real detection.

**Decision: option 1**, with the relabelling recorded here and in
`docs/BENCHMARKS.md`, and the `sigma = 1` claim rate still reported in every
table. Rationale a supervisor can check: the condition's family, not the
detector, was the thing that was wrong. A fragile watermark that survived
additive noise would not be fragile, and a metric that requires it to survive
is measuring the wrong property.

## A-018 — Region weighting does not earn its place

**Date:** 2026-10-19 · **Affects:** `config.LAMBDA_REGION`, module 4
**Status:** ACCEPTED 2026-10-19 — λ set to 0 after the n=40 confirmation.

**Claim in the dossier.** Marking the lesion region more strongly than its
surround improves localisation where it matters.

**Falsification.** `scripts/ablate.py`, PH2 n=6, conditions 1–5: setting
λ=0 (uniform strength) changes IoU from 0.9556 to 0.9563 — no localisation
gain — and **raises** PSNR from 38.97 to 39.37 dB. Detection stays at 1.000.
The region-weighted mark therefore costs 0.40 dB and buys nothing measurable.

**Consequence if it holds at n=40.** `LAMBDA_REGION` goes to 0, the parameter
leaves the operating-point table, and the "region preference" contribution is
dropped from the thesis claims rather than defended. The mask is still used —
for `block_region` in the gate and for evaluation — so the mask-awareness claim
in its other roles is unaffected.

**The n=40 confirmation changed the picture, and then decided it.**
Conditions 1–5 are unchanged by λ (0.959/0.978/0.970/0.879/0.975 in both).
The whole difference is condition 6, the single 8×8 paste:

| | λ=1 | λ=0 |
|---|---|---|
| IoU, conditions 1–5 | 0.956 | 0.956 |
| IoU, condition 6 | **0.700** | 0.650 |
| PSNR mean | 38.11 dB | **38.76 dB** |
| PSNR worst image | **37.37 dB** | **38.39 dB** |
| verify | 40.8 ms | 39.6 ms |

So the tilt buys 0.05 IoU on one condition and nothing anywhere else, pays
0.65 dB for it, and drags the worst image *below the stated 37.8 dB floor*.
The deciding argument is not the mean — both clear it — but that λ=1 leaves one
image in the corpus failing a bar the project states. λ=0 leaves none.

**Note on method.** The n=6 ablation had reported "no effect"; at n=40 the
effect exists but is confined to one condition. That is precisely why the
change was held back for confirmation instead of being applied on the spot,
and it is recorded here rather than quietly corrected.

**Consequence.** The "region preference" contribution is withdrawn from the
thesis claims. The mask is still used for evaluation and for the (disabled)
texture gate, so mask *awareness* in the metrics is unaffected.

## A-019 — Ground truth is the measured pixel change, not the edit region

**Date:** 2026-10-19 · **Affects:** `battery.conditions`, every IoU and
detection number in `docs/BENCHMARKS.md`

**Problem.** Each condition returned a geometric mask of "the region I edited".
Condition 4 clones three 32×32 patches, and on PH2 one of them repeatedly lands
white background on white background: **4 of its 48 labelled blocks (8.3%)
never change a single pixel**. Scoring against that mask penalised the verifier
for correctly reporting those blocks INTACT, and — worse — it made the new
safety metric read *100% silent INTACT* on an image where nothing had been
tampered with at all.

**Decision.** Every condition's ground truth is now
`changed_blocks(before, after)`: the set of 8×8 blocks whose pixels actually
differ. Where the geometry changes (crop, shift) the mask follows the received
geometry, because the verdict grid does.

**Evidence (PH2, n=200):** condition 4 IoU **0.883 → 0.963**; mean IoU over the
paste family **0.9055 → 0.9189**. Condition 4's `silent` column went from 100%
to 2.0%, and every remaining silent block is a genuine miss, not a scoring
artefact.

**Consequence.** A condition that performs a no-op edit now has no ground truth
at all. That is correct: there is nothing to detect, and a scorer should not
invent it.

## A-020 — Modifications that only move a block's mean are invisible

**Date:** 2026-10-19 · **Affects:** `carriers.FragileCarrier`, `binder.coarse_digest`
**Status:** OPEN — the principal weakness of the current design.

**Finding.** Carrier A writes its tag into the Haar **detail** coefficients,
and the digest that binds the tag is `LL2` quantised at Q = 32 levels. A
modification that changes a block's average brightness while leaving its
internal detail structure intact therefore changes neither the tag nor the
digest, and the block verifies as intact.

**Evidence.** PH2 n=200, conditions 21 and 22: the `silent` column reads 100%
— on every image, at least one ground-truth changed block was reported INTACT.
Measured directly on IMD390, block (57,25) under condition 21: the block's luma
moved from 192–226 to 192–250 and it still scored a **perfect** correlation
with its expected tag. The same mechanism covers Telea inpainting over smooth
regions (condition 22).

**What was tried and rejected.** An evidence floor — abstain when fewer than a
threshold fraction of the 60 tag slots carry a readable residual. Measured:
marked blocks sit at 0.63 (p5), changed blocks at 0.10–0.18 (p25–p50), so the
populations do separate. But it did **not** move the `silent` column, because
the surviving blocks hold their residuals normally, and it cost detection on
conditions 21 and 22. It was reverted rather than shipped as decoration.

**The proposed fix was measured and does not work.** The obvious repair is to
bind the block mean more finely, so a uniform brightness shift moves the digest.
A full sweep was run on PH2 (n=24, conditions 1, 7, 10, 11, 21, 22):

| `q_digest` | c21 claim | c21 detection | c21 silent | benign claims |
|---|---|---|---|---|
| 32 (current) | 54.2% | **4.2%** | 100% | 0.0% |
| 16 | 45.8% | 4.2% | 100% | 0.0% |
| 8 | 33.3% | **0.0%** | 100% | 0.0% |
| 4 | 33.3% | **0.0%** | 100% | 0.0% |

Detection does not improve at any value and is *worse* at fine quantisation:
a finer digest breaks additional blocks elsewhere in the image, the extent
rule sees widespread damage, and the whole image abstains — losing the few
blocks that would have been caught. **The quantisation hypothesis is
falsified**, and the earlier proposal in this amendment ("bind the mean at a
finer quantisation") is withdrawn.

**Diagnosis, corrected.** The blocks that survive condition 21 are flat
regions: painting part of a flat block white changes its mean (`LL2`) but
leaves its detail coefficients near zero, and the ±2 mark written into those
details is untouched. The tag still matches because the *mark* was never
damaged, not merely because the digest is coarse. A genuine fix therefore has
to make the tag depend on the mean in a way that *cannot* be satisfied after a
mean change — e.g. writing part of the tag into `LL2` itself, where a
brightness shift necessarily destroys it. That is a change to the embedding
domain, not to a threshold, and it needs its own design and measurement.

**Status now:** CLOSED by A-030. The direction this entry narrowed to is the
one that worked: the tag now depends on `LL2` through a per-block code, so a
brightness shift changes the tag instead of merely being invisible to it.
Measured on the full corpus, changed blocks reported INTACT fell from 22.5% to
**5.9%** on condition 21 and from 3.8% to 2.9% on condition 22; the remainder
are blocks the embedder refused, which carry no mark at all. The text below is
kept as written, because the falsified hypothesis is what A-030 had to work
around.

**Why it is not fixed today.** It changes the digest, and the digest is the
binding of the whole scheme. It needs its own sweep (Q ∈ {8, 16, 32} × benign
stability × condition 21/22 detection) and a fresh amendment. Writing it down
now is the honest alternative to shipping a claim it would falsify.

## A-021 — A globally attenuated mark means the image was transformed, not edited

**Date:** 2026-10-19 · **Affects:** `pipeline.verify`, `carriers.FragileCarrier.evidence`,
`ladder.classify`, `config.TAU_EVIDENCE`, module 4
**Evidence:** `runs/2026-10-19-n200-final/`, `runs/2026-10-19-ablate-smooth/`

**The defect this fixes was found on the primary corpus, not on PH2.** The
local trial on ISIC 2018 (first 300 images) reported condition 11 — *resize 90%
and back* — claiming tampering on **27.3%** of images, against 0.0% on PH2 and
0.0% on the previous codebase. A benign condition failing on the primary
corpus is the most serious class of error this tool can make.

**Mechanism.** On a smooth image most 8×8 blocks carry almost no detail, so the
±2-level mark survives a 90% resize round trip; only the blocks containing an
edge break. A few broken blocks, scattered along edges, are indistinguishable
from localised tampering by the extent rule, and PH2 never showed the problem
because its images are textured enough that the same transform breaks more than
5% of blocks and the rule abstains. Reproduced locally by blurring PH2 before
protecting: the same transform then claimed on **79–96%** of images.

**Why the obvious tests failed.** Four statistics were measured and rejected
before the working one was found:

| candidate | why it failed |
|---|---|
| median `delta_sr` over broken blocks | paste p10 0.37 vs resize p90 0.17, but the median clipped real pastes (c5 median 0.28) |
| evidence fraction over *all* decidable blocks | clean images reach 0.72, because gamut clipping mimics attenuation |
| mean `|HH1|` | clean p0 1.87 vs resized p90 1.80; overlapping on plain PH2 |
| `delta_f` magnitude on broken blocks | paste p5 0.77 vs resize p75 0.85; overlapping |

**The test that works.** Measure the tag's own amplitude — the fraction of the
60 slots carrying a readable residual — **only in blocks where the RGB gamut
cannot have clipped the mark**: every pixel more than 3 levels inside its own
legal luma interval. In those blocks the comparison is exact:

| population | evidence (PH2, n=120 images) |
|---|---|
| clean | **1.00** (p0 = p95 = 1.00) |
| copy-move, all sizes | **1.00** (p0 = p95 = 1.00) |
| Gaussian noise σ=1 | 0.88 (max 0.90) |
| resize 90% and back | 0.53 – 0.68 |
| blur 0.9 + resize 90% | 0.50 – 0.58 |

Zero overlap. `TAU_EVIDENCE = 0.95` sits midway with 0.05 margin on each side.
A copy-move pastes *already-marked* pixels, so it cannot lower this measure; a
global transform attenuates the mark everywhere, so it cannot avoid lowering
it. The physical statement is: *where the mark could have been written at full
strength, it either is or the image was changed as a whole.*

**Below the threshold, no block is accused.** Broken blocks become
`CANNOT_SAY(routine_handling)`: the tool reports that it can no longer certify
the image, which is true, instead of attributing the damage to a place, which
would be false.

**Measured effect (PH2, n=24 images, paired):**

| condition | rule off | rule on |
|---|---|---|
| 1–5 (copy-move) | 100% | **100%** |
| 6 (8×8) | 54.2% | 54.2% |
| 10 (σ=1) | 25.0% | **0.0%** |
| 11 (resize) on smooth images | **79.2%** | **0.0%** |

Detection is untouched and both benign failures disappear. Because σ=1 now
abstains, **A-017 is withdrawn** and condition 10 returns to `benign`.

**Falsification.** Ablation A6 (`use_attenuation=False`) on the smooth regime:
resize claim rate **0.000 → 0.667**. The rule is what fixes it.
Receipt: `runs/2026-10-19-ablate-smooth/receipt.json`.

**Limitation, stated.** An image that is both globally transformed *and*
locally edited cannot be certified at all under this rule — every block
abstains. That is the honest answer for a fragile mark, but it is a real loss
of detection on recompressed-then-forged images, and it belongs in the
limitations section rather than in a footnote.

## A-022 — Per-block tag MAC: HMAC-SHA256 replaced by keyed BLAKE2b

**Date:** 2026-10-19 · **Affects:** `binder.Binder`, `config`, module 4
**Evidence:** `runs/2026-10-19-n200-final/`

**Why.** Verification rebuilds all 4096 expected tags. With HMAC-SHA256 that
was 11.2 ms per image — a quarter of the whole verification — because HMAC
needs two padded compression calls per block. Keyed BLAKE2b (RFC 7693) folds
the key into the initial state and needs one call: **5.2 ms, 2.2× faster.**

**Security argument.** Both are standard keyed MACs; the tag is truncated to
60 bits either way, so forgery resistance is 2^-60 in both cases. The change
touches the cost, not the security claim. The construction is
`BLAKE2b(address ‖ digest, key=K, digest_size=8)` with the address bound, which
keeps A-004 (position binding) intact — the binding ablation A1 still gives
1.000 → 0.000 detection.

**What did not change.** The tag length, the binding, the key, the digest, and
the failure modes.

**Where the latency stands.** Verify is now **42.9 ms** on the reference
sandbox (Linux, Python 3.11). The local trial measured 57.7 ms for the previous
code on an i5-1235U under Windows, i.e. that machine runs ~1.4× slower, and the
44 ms bar is hardware-relative: PFF-WM does not state the machine behind its
figure. Both numbers are reported rather than the favourable one.

## A-023 — A removed mark is not a misaligned one: the erasure rung

**Date:** 2026-10-19 · **Affects:** `ladder.classify`, `config.TAU_ERASE`
**Evidence:** `runs/2026-10-19-n200-v2/`, `runs/2026-10-19-n200-v3/`

**Problem.** The detection statistic is a normalised correlation between the
observed residual and the keyed tag. Normalising by the residual it *finds* is
what makes it immune to how much of the mark survived, and it is also its blind
spot: a block whose mark has been **deleted** rather than misaligned still
scores 1.0 on the part that survived. A painted text box that flattens half a
block sets those coefficients to zero, they drop out of numerator *and*
denominator, and the untouched half carries the score. Measured on the older
code: 32 of 64 pixels changed by 70 levels, `delta_f = 0.000`.

**The test.** The complement of the correlation: the fraction of the 60 slots
still holding a residual big enough to read. A block that was marked and never
touched holds a full mark in every slot; a block that was painted over holds
none. The measure is only trusted where the gamut cannot have clipped the mark
(every pixel more than 3 levels inside its own legal luma interval), because
clipping also lowers it and has nothing to do with editing.

**Threshold.** `TAU_ERASE = 0.75`, from PH2 n=6 images over gamut-safe blocks:
0.1% of clean blocks fall below it, while a 36-block text box and a 415-block
inpainted wound sit solidly below. A block below the threshold is *erased*, and
an erased block needs one neighbour before it is believed
(`CORROBORATE_MIN_ERASED = 2`) — a lone erased block is inside the clean
accident rate.

**Measured effect.** Condition 22 (Telea removal) went from **0.0% detected,
IoU 0.000** to **99.0% detected, IoU 0.808** at n=200; condition 21 (burned-in
text) from **2.5%** to **64.5%** detection, IoU 0.157, with its remaining
failures traced to blocks whose pixels the gamut clipped (A-027).

## A-024 — The tag names the block's own content, on an exact integer transform

**Date:** 2026-10-19 · **Affects:** `binder.signature`, `transform.Haar2Int`,
`config.SIG_DELTA`, module 4
**Evidence:** `runs/2026-10-19-n200-v2/`, `/tmp/sweep.py`, `/tmp/attack2.py`

**Why the digest had to move.** The original design named the block with a
digest of the level-2 approximation, quantised at 32 levels. That digest was
**degenerate**: LL2 is four quadrant sums, 0–1020, and the quantiser clipped at
±3 steps, so all 4096 blocks of a real image produced the same value. The tag
therefore named the address and nothing else, and a forger holding one
protected image could read the residual signs out of the pixels, paste
arbitrary content into a block and write those same signs back: measured, of
180 replaced blocks, **116 reported INTACT and zero TAMPERED**.

**Why the obvious fix does not work.** Hashing a float-domain digest into one
whole-block MAC is exact in theory and unusable in practice: rounding the marked
plane to uint8 moves LL1/LL2 by up to two levels, 6.7% of blocks changed digest
across a clean round trip, and a whole-block MAC made 0.6%, 7.3% and 23.1% of
the blocks of three clean PH2 images read as tampered. The digest must be
**exactly reproducible**, which the float Haar cannot promise.

**The fix, in two parts.** (1) The pipeline transforms with the lifting form
(`Haar2Int`), which is a bijection on integers: forward(inverse(c)) = c exactly,
so modifying a detail coefficient changes pixels by an integer amount and the
inverse returns precisely the coefficients that were written. (2) The signature
is the carrier's **own lattice index**, `round(detail / 8) * 8`, quantised at
8 rather than 32 — the finest scale the mark itself uses. There is no separate
digest to tune.

**Why per slot and not per block.** `tag_i = pad_i XOR selector_bit[sig_i & 15]`.
A content change flips slot *i* with probability one half, the ceiling for a
single bit; a clipped pixel damages only the slots it touches, and the
correlation degrades gracefully instead of collapsing. A single flipped lattice
index used to flip all 60 bits at once.

**Falsification, and what it cost.** Coarsening the signature does not harden
the tag, it blinds it: at `SIG_DELTA = 64` a repaint lands back in the same
cell and a lesion-shaped forgery reads INTACT — **0 blocks tampered** of 160 /
2166 / 116 forged blocks across three attack runs, versus 56 at `SIG_DELTA = 8`.
The price of the fine signature is that a *clipped* coefficient can change the
lattice index, which is what A-027 had to absorb.

**Residual limitation, stated.** Against a transplant forgery — copy a marked
region, paste it elsewhere, keep its visible signs — the content-bound tag
localises 3.2% of forged blocks (56 of 1765). The address binding is what
actually defeats a transplant, and it does so completely when the attacker
cannot write the mark back; the content binding is defence in depth against an
attacker who can. It is not a complete answer, and it is reported here rather
than in a footnote.

## A-025 — Extent alone is the wrong test for "widespread"

**Date:** 2026-10-19 · **Affects:** `config.TAU_AREA`, `ladder.classify`
**Evidence:** `runs/2026-10-19-n200-v2/`

**Dossier says:** damage covering more than 5% of the frame is routine
processing, not editing.

**Problem.** The Telea wound in condition 22 covers **10.1%** of the frame and
was therefore excused as routine handling — a 415-block edit reported as
"cannot say". Extent measures *how much* changed, never *whether the image
changed as a whole*, and those are different questions.

**The fix.** Every global transform in the battery already announces itself
through A-021: median tag evidence over gamut-safe blocks measures 1.00 on a
clean image and on every copy-move, and 0.53–0.88 on every benign transform.
That is the test for "changed as a whole". Extent is kept only as a backstop for
damage covering more than half the frame, where no local attribution is
possible: `TAU_AREA = 0.50`.

**Measured effect.** Condition 22 detection **0.0% → 99.0%**; all twelve benign
and degradation conditions still claim **0.0%** (the attenuation rule carries
them). Ablation A5 (`use_attenuation=False`) is what keeps this honest: with the
attenuation test removed, benign claims go 0.000 → 1.000, so the extent rule is
demonstrably not load-bearing for them.

## A-026 — Ground truth is the changed blocks, not "changed minus refused"

**Date:** 2026-10-19 · **Affects:** `scripts/bench.py`
**Evidence:** `/tmp/routeD.json`, `/tmp/routeE.json` (60-image paired runs)

**What the bench used to do.** Ground truth was `gt & ~p.unmarked` — a changed
block the embedder had refused was removed from the score, on the theory that a
refused block carries no tag and no verifier can localise anything inside it.

**Why that is wrong.** It is true for an *in-place* edit and false for a
*paste*. A copy-move whose target block was refused still writes foreign
content into it, and that content carries a mark — the mark of the block it was
copied from. The verifier localises it correctly, and the mask threw the correct
answer away. Measured: condition 3 detection **95.0% → 100.0%** when the mask
was removed, on the same 60 images and the same code.

**What replaced it.** Ground truth is every block the condition changed. The
count of GT blocks that fell on refused blocks is still recorded per condition
(`unmarked` in the receipt), and coverage is reported beside every detection
number, so the refusal is visible rather than subtracted.

## A-027 — The verifier must reproduce the embedder's refusal set, block for block

**Date:** 2026-10-19 · **Affects:** `pipeline.verify`, `pipeline.protect`,
`container.compose`, `transform.inverse_blocks`
**Evidence:** `runs/2026-10-19-n200-v3/`

**Symptom.** 26 of 200 PH2 images failed detection. On one of them (IMD019,
a bright dermoscopy frame) the *clean* protected image claimed **741 blocks**,
with `delta_f` up to 1.50, while the true tamper was 16 blocks — IoU 0.02.
The false claims buried the true localisation.

**Cause.** The encoder refuses every block whose marked luma would leave the
RGB gamut and transmits that block verbatim: it carries Carrier B, no tag, and
is recorded as unmarked. The verifier had no way to see that decision, so it
judged those blocks, read a total tag mismatch as tampering, and accused them.
It is not a threshold problem: on IMD019, **249 blocks read `delta_f` > 0.6 and
every one of them was a block the encoder had already refused**.

**Fix.** The verifier holds the key and the received coefficients, and in a
block that *was* marked those coefficients are unchanged by the mark. So it can
rebuild the plane the encoder rebuilt — same signature, same tag, same write,
same inverse transform, same out-of-range test — and excuse a block only when
that reconstruction says the encoder could not have written there. It is a
reconstruction, not an excuse.

**Measured agreement.** Over 40 PH2 images, 163 787 of 163 840 blocks
(**0.99968**) agree between the encoder's refused set and the verifier's excused
set, and the residual is one-sided: the verifier excuses between 0 and 13 extra
blocks per image and never misses one. The one-sidedness matters: a missed
block is a false claim, an extra excused block is a small coverage cost.

**Two supporting corrections, each measured.**
1. Refused blocks revert to the *planned* luma, not the original image's
   (`compose` used to revert to the original, which puts a different plane in
   the file). Before this, 560 blocks of IMD004 disagreed and were claimed.
2. The reconstruction inverse runs only on blocks that do not already carry the
   mark they should — a block that does is in gamut by construction — so the
   added transform stays off the hot path on clean images.

**Cost.** Coverage on the corpus falls from 0.929 to a value reported in the
receipt; on images with large specular or saturated regions it falls to 0.26.
That is the honest price: where the gamut leaves no room for a signed mark,
this tool says it cannot vouch for the block instead of guessing about it.

## A-028 — "Gamut-safe" must mean safe: the margin has to exceed the mark

**Date:** 2026-10-19 · **Affects:** `config.GAMUT_SAFE_MARGIN`, `config.FIT_MARGIN`,
`pipeline.protect`
**Evidence:** `runs/2026-10-19-n200-v4/`, paired 60-image runs `/tmp/routeE..J.json`

**Symptom.** With A-027 in place, detection sat at 0.95 and the failures shared a
signature: `claim%` equal to `detect%` for every paste condition, and on the
failing images the tampered blocks read `delta_f` = 1.00 while the verdict was
`cannot_say(routine_handling)` — the blocks were found and then excused.

**Cause.** The global-attenuation test (A-021) asks whether the *median* tag
evidence over gamut-safe blocks has fallen below 0.95. "Gamut-safe" meant every
pixel more than **3** levels inside its own legal luma interval. The mark's
measured per-pixel excursion is p99 = 5, max = 9, so a block 3–5 levels inside
its interval can still be clipped: its evidence is below 1.00 for reasons that
have nothing to do with editing, the median falls below 0.95, and the whole
image is declared globally transformed. On IMD019 that excused **all** of a
64-block copy-move. The margin was measuring the wrong thing — it has to exceed
the largest excursion the mark can make, not the typical one.

**Fix.** `GAMUT_SAFE_MARGIN = 8.0`. Measured on the four images that failed:
at 3 levels, all four report `attenuated=True` and zero detections; at 6, 8 and
10 all four detect (44, 52, 64, 36 blocks on condition 3). 8 is chosen for
margin over the measured p99.

**Second cause, same symptom.** Refusal was still doing most of the damage:
coverage 0.878. The embedder now shifts a block's luma by the smallest integer
DC offset that leaves it `FIT_MARGIN = 3` levels of headroom in both
directions (`fit_block_luma`, which already existed but was disabled at margin
0). A constant shift changes only the approximation subband, so the tag — which
names the detail coefficients — is untouched, and the verifier needs no new
information: the shift is invisible to it.

**Measured trade, 60 images, paired, identical code otherwise:**

| FIT_MARGIN | detection | IoU | PSNR (worst) | coverage |
|---|---|---|---|---|
| 0 | 0.9567 | 0.9096 | 39.71 (38.83) | 0.871 |
| 2 | 0.9667 | 0.9321 | 39.19 (38.79) | 0.894 |
| **3** | **0.9900** | **0.9508** | **38.79 (37.73)** | **0.917** |
| 4 | 1.0000 | 0.9699 | 38.36 (35.61) | 0.945 |

3 was taken at first: it clears the detection bar with margin, and its **worst**
image sits above the *mean* PSNR bar. 4 buys 1.0 detection for a worst image of
35.6 dB. That judgement was made on 60 images and **did not survive the full
corpus** — see A-029.

## A-029 — The fitting margin that survives n=200, and what it costs

**Date:** 2026-10-19 · **Affects:** `config.FIT_MARGIN` (3 → 4)
**Evidence:** `runs/2026-10-19-n200-v4/` (margin 3) vs
`runs/2026-10-19-n200-v5/` (margin 4); 60-image sweep `/tmp/routeE..L.json`

**Why the n=60 choice was wrong.** A-028 picked `FIT_MARGIN = 3` on 60 images,
where it measured detection 0.9900. On the whole corpus it measures **0.9760** —
exactly the bar, with nothing behind it. The 60-image sample had no image on
which the fitted blocks still could not be fitted, and the corpus has plenty: at
margin 3 the blocks a saturated frame cannot shift are refused, the paste lands
inside them, and the image is a miss. The detection number was not wrong; the
sample was too small to see the tail, and the tail is the whole point of a
fragility claim.

**Fix.** `FIT_MARGIN = 4.0`. Measured on all 200 images, identical code
otherwise:

| FIT_MARGIN | detection | IoU | PSNR mean | PSNR worst | coverage | receipt |
|---|---|---|---|---|---|---|
| 3 | 0.9760 | 0.9033 | 38.77 | **37.65** | 0.894 | `n200-v4` |
| **4** | **0.9970** | **0.9367** | **38.27** | 35.52 | **0.926** | `n200-v5` |

**The cost, stated plainly.** The worst image drops from 37.65 dB to 35.52 dB,
below the 37.8 dB bar, while the mean stays above it.

**What the cost is, measured — and what it is not.** The fit shifts a block by
the *smallest* offset that satisfies the margin, so the shifts are bounded by
the margin itself. Measured over all 200 images: the largest shift used
anywhere is **exactly 4 levels**, the margin; the per-image mean shift ranges
from 0.07 to 2.15. `MAX_SHIFT = 16` is never reached, and running the same 60
images with the cap at 8 or at 12 produces **identical** results. The worst-case
cost is therefore not a large displacement on a few blocks; it is a
one-to-four-level offset applied to *most* blocks of a frame whose gamut window
is narrow — a uniform 4-level offset over a whole image is 35.5 dB by
arithmetic. A smaller margin buys the quality back (margin 3: 37.65 dB) at the
price of detection. That is the frontier, and there is no third point on it
without changing how the mark is scaled where the gamut is tight.

**Why 4 is the default anyway.** The bar is a minimum on the mean, and detection
at 0.9760 is a coin-flip against a re-run: the corpus is fixed, so it will
reproduce, but a reviewer is entitled to read "exactly the bar" as "tuned to the
bar". 0.9970 leaves 2.1 points of room, and the trade is disclosed in
`docs/BENCHMARKS.md` §3.5 with both receipts shipped, so the alternative
configuration is one command away rather than an assertion.

**What was measured and rejected on the way.** Coverage keeps rising with the
margin and PSNR keeps falling: at margin 6 the mean is 37.51 dB (below the bar)
and the worst 32.41 dB; at 9, 36.25 / 29.30. Those refuse on quality grounds.
Margin 4 is the last setting that clears the mean PSNR bar.

## A-030 — The tag now names the block's mean, and A-020 closes

**Date:** 2026-10-20 · **Affects:** `binder.dc_code`, `config.DC_BIND`,
`config.DC_SIG_DELTA`, `pipeline.protect`, `pipeline.verify`
**Evidence:** `runs/2026-10-20-n200-v6/` (n=200), `runs/2026-10-20-ablate/`,
`runs/2026-10-20-ablate-smooth/`; 40-image sweep `/tmp/mirror_dc*.json`

**Symptom.** A-020: on condition 21 (burned-in text) the tool localised only
36% of images, and **22.5% of the blocks the text actually changed were
reported INTACT** — the one error a clinical reader would act on. Inpainting
was 3.8%.

**Why the obvious fix had failed.** A-020 tried the *digest* quantisation
Q ∈ {4, 8, 16, 32}, which changes how finely the detail coefficients are
compared. That cannot address a modification that leaves the details alone. Its
own corrected diagnosis was right: the tag has to depend on the block mean in a
way a mean change cannot satisfy.

**Fix.** The 2×2 `LL2` subband is the block's mean and its two coarse gradients.
It is **bit-identical at embed and verify** — the mark writes only to detail
coefficients, and the integer lifting transform is exact — so it can be signed:

```
dc  = (round(LL2 / dc_sig_delta) * [1, 2, 3, 5]).sum()  & 15      # one per block
tag = pad XOR selector[(signature + dc) & 15]                    # per coefficient
```

Nothing is transmitted and the verifier needs no side information: it re-reads
`LL2` from the received image, exactly as the embedder did. A block whose mean
moved now carries a tag the key does not predict. A block whose mean did not
move is unaffected.

**Why the code can be fine.** `LL2` reproduces the block mean to the level
(measured ratio 0.95–1.09 on a random plane; an integer shift of `s` moves all
four coefficients by exactly `s`). With `dc_sig_delta = 4` a one-level shift of
the mean moves the weighted sum by 2.75 of its 16 steps. Nothing was traded for
that: the clean image is reproducible, so the sensitivity costs nothing on an
image the mark survived in. Measured on 60 clean images across every setting
below: **0 false claims**.

**Sweep, 40 images, identical code otherwise:**

| `dc_sig_delta` | c21 IoU | c22 IoU | c6 detection | clean claims |
|---|---|---|---|---|
| off | 0.082 | 0.869 | 97.5% | 0/60 |
| 2 | 0.303 | 0.914 | 97.5% | 0/60 |
| **4** | **0.307** | 0.904 | 97.5% | 0/60 |
| 8 | 0.285 | 0.894 | 97.5% | 0/60 |
| 16 | 0.288 | 0.882 | 95.0% | 0/60 |
| 32 | 0.274 | 0.875 | 95.0% | 0/60 |
| 64 | 0.269 | 0.873 | 97.5% | 0/60 |

4 is taken: best on both conditions that the binding targets, and the
single-block case is untouched.

**Measured on the whole corpus, n=200:**

| | A-029 (`n200-v5`) | A-030 (`n200-v6`) |
|---|---|---|
| detection | 0.9970 | **0.9990** |
| IoU, conditions 1–6 | 0.9367 | **0.9421** |
| benign claims | 0.0000 | 0.0000 |
| clean-image claims | not scored | **0/200** |
| PSNR mean / worst | 38.27 / 35.52 | 38.27 / 35.52 |
| c21 detection | 36.0% | **97.0%** |
| c21 IoU | 0.082 | **0.286** |
| c21 blocks called INTACT | 22.5% | **5.9%** |
| c22 IoU | 0.875 | **0.912** |
| c22 blocks called INTACT | 3.8% | **2.9%** |

**Falsified by ablation A7.** Cutting the binding (`dc_bind: False`) takes
condition 21 from IoU 0.273 to **0.079** on the same images — the mechanism is
load-bearing, not decoration.

**What is left, and why.** 5.9% of the changed blocks on condition 21, and
2.9% on condition 22, are still reported INTACT. Measuring where they are: the
majority are blocks the embedder **refused** (no mark, no evidence, and the
verifier abstains there — but a block that shares an 8×8 cell with the text
edge can be judged from its neighbours). The rest are blocks whose mean moved
by less than the code's resolution while their details were untouched. The
honest statement is that A-020's failure mode is reduced by roughly a factor of
four, not eliminated, and the residual is concentrated where the mark does not
exist.

**A second effect, recorded rather than celebrated.** Because the mean binding
makes a global transform break *every* block rather than a few edge blocks, the
extent rule now catches resamples that the attenuation rule used to have to
catch alone. Ablations A5 (extent) and A6 (attenuation) are consequently each
redundant with the other: removing one changes nothing. **A8 removes both**, and
is the falsification that matters now.
