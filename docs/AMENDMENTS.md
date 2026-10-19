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
