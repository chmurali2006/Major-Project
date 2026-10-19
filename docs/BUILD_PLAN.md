# Build plan — A Fragile Watermarking for Medical Image Tamper Detection

Prepared 2026-10-19, after reading the full context package
(`project-context/`, branch `dev`) and running a design-risk spike.

Status of this document: **historical design record**. It does not override the
dossier, and it is not the current state of the work: where it disagrees with
the dossier, the disagreement is recorded in `docs/AMENDMENTS.md` with the
measurement that forced it, and the measured state of the system is
`docs/MID_PROJECT_REVIEW.md` with `docs/BENCHMARKS.md`. The numbers in §3 are
**mechanism checks on one synthetic phantom**, not results; none of them is
quoted anywhere as a result, and all of them have since been superseded by
measurements on PH2.

---

## 1. What is being built

A zero-training, keyed dual watermark for medical images. Both carriers are
written before an image is shared. On return, the image is checked with the
key alone: every 8×8 block becomes TAMPERED (with an address), INTACT, or
CANNOT SAY with one of four reasons. The claim under test is that position
binding — not image content — is what makes same-image copy-move visible.

Target: an MTech-grade thesis with a frozen 22-condition battery, seven
falsification checks, per-number receipts, and a live laptop demo.

---

## 2. Where the work lives

| Thing | Location | Notes |
|---|---|---|
| Context package | `project-context/` on `dev` | reference only, never imported by code |
| Code | `src/` | layout per `02_ARCHITECTURE.md` §5 |
| Tests | `tests/` | pytest; must run in seconds, no dataset needed |
| Experiment runs | `runs/<date>_<name>/` | receipts in, results out; git-ignored |
| Datasets | never in git | download scripts in `data/`, pixels stay outside the repo |

Branching: feature work → PR into `dev`; a checkpoint PR `dev → main` when a
delivery is solid; tag `checkpoint-NN` on `main`.

---

## 3. What the spike measured before committing to the design

Environment: Python 3.11, numpy 2.4, scipy 1.17, Pillow 13, laptop CPU.
Data: **one synthetic dermoscopy phantom** (512×512, textured skin, elliptical
lesion with mask). These are mechanism checks, not results. No number here may
appear in the thesis.

### 3.1 The paper's fragile reader is broken

PFF-WM Eq. 6 embeds at `q ± Δ/4`; Eq. 7 reads with
`floor(2(c−q)/Δ + 1/2) mod 2`. At `Δ = 8` the embedded value is exactly `±2`,
which lands **on** the reader's decision boundary: `floor(1.0)` vs
`floor(0.9999…)`. A 1e-15 drift flips the bit. Measured bit error on a clean,
untouched in-memory array: **50%**.

Fix: read the **sign** of the residual, `c − round(c/Δ)·Δ`. Boundary at 0,
every embedded point 2 levels away. Clean error becomes exactly 0.

### 3.2 Embed order matters more than anything else in the design

`02_ARCHITECTURE.md` §3 writes Carrier A then Carrier B. Measured on a clean
image after a real PNG round trip, with both carriers at β = 8:

| Order | clean δf, mean | clean δf, max | verdict |
|---|---|---|---|
| A then B | 0.067 | 0.133 | unusable — clean images report tampered |
| **B then A** | **0.000** | **0.000** | exact |

Carrier B perturbs pixels, which perturbs the detail coefficients Carrier A
just quantised — Trap 9, arriving through the back door. Writing B first and A
last makes A exact by construction. Cost to B is small (see 3.4).

### 3.3 The binding ablation now proves the central claim

32×32 healthy-tissue paste over the lesion, both carriers, β = 12, order B→A:

| System | pasted block δf | untouched control δf |
|---|---|---|
| with address in the tag | **0.501** | 0.000 |
| address removed from tag **and** embedder | **0.000** | 0.000 |

The ablated system is blind to copy-move. That is contribution 1, demonstrated.
Note: an ablation must change the embedder too; ablating only the verifier
measures noise, not mechanism (a mistake I made once and will not repeat).

### 3.4 What the fragile carrier can actually see (Δ = 8, B→A, β = 12)

| Edit | δf in the edited block |
|---|---|
| one pixel, +1 level | 0.000 |
| one pixel, +8 levels | 0.067 |
| 8×8 block paste | 0.500 |
| 16×16 block paste | 0.525 |
| 32×32 block paste | 0.501 |
| 64×64 block paste | 0.504 |

Consequence: **the pre-flight check "perturb one pixel by one level → verdict
changes" cannot pass at any Δ that survives its own PNG round trip.** At Δ = 2
the clean round trip already reads 0.072 (unusable); at Δ ≥ 4 a single-pixel
edit is invisible. This is geometry, not tuning: one pixel moves a level-1
Haar detail coefficient by 0.5, and the nearest decision boundary is Δ/4 = 2
levels away.

The system's real sensitivity is **block-scale**: any spatial edit of ~8×8
pixels or larger is caught at δf ≈ 0.50. That is what the 22-condition battery
tests (smallest condition: one 8×8 block). The claim must be restated
accordingly — see amendment A-003.

### 3.5 Semi-robust carrier: works, but misses the ρ target

β sweep, order B→A, Δ = 8, 22 mid-frequency block-DCT coefficients per block,
sequence keyed by (key, image id, **block address**):

| β | PSNR | clean δsr | JPEG 90 δsr | paste δsr | ρ = paste/handling |
|---|---|---|---|---|---|
| 4 | 40.14 dB | 0.332 | 0.348 | 0.615 | 1.8 |
| 8 | 39.81 dB | 0.249 | 0.264 | 0.544 | 2.2 |
| 12 | 39.13 dB | 0.177 | 0.190 | 0.563 | **3.0** |

Separation exists and has the right shape (handling ≈ clean ≪ paste), but
ρ = 3.0 against a design target of ρ > 5. This is an open engineering item, not
a paper claim: candidate fixes are a wider mid-band index set, 2×2-block
aggregation of the correlation statistic, and per-region thresholds.

**Address-keying of Carrier B is mandatory**, and is not stated in the dossier.
If `p` is global, a pasted block carries a *valid* sequence and the trip table
files copy-move under "routine handling" — the central claim dies. Both
carriers must be address-bound.

### 3.6 Digest stability, and runtime

- Coarse LL digest (Q = 32, 12 bits): **100% of blocks unchanged** under JPEG
  90, 75 and 50, with both carriers present. One synthetic image only —
  must be repeated on the real corpus before it is believed.
- Runtime on this sandbox CPU: **70 ms protect, 27 ms verify** per 512×512
  image. The laptop-demo requirement is not in danger.

---

## 4. Frozen design for Phase One

Every value below lands in `src/config.py`, one line each, with a comment
saying whether it came from the literature or was chosen here.

| Parameter | Value | Provenance |
|---|---|---|
| Block / grid | 8×8, 64×64, 4096 blocks | dossier |
| `DELTA_F` | 8 | PFF-WM (CheXpert) |
| `OFFSET_F` | Δ/4 = 2 | dossier; **reader corrected to sign rule** |
| Detail slots per block | 60 (16×3 at L1, 4×3 at L2) | dossier, verified |
| `Q_DIGEST` | 32 | chosen; validated by stability receipt |
| Digest width | 12 bits (4 coeffs × 3 bits, ±3 steps) | chosen |
| Tag | HMAC-SHA256(key, id ‖ address ‖ digest)[:60] | dossier |
| `BETA0` | 12 | chosen from sweep; to be re-validated |
| `LAMBDA` | 2.0 | PFF-WM attention form, mask substituted |
| Carrier B band | block DCT, 3 ≤ u+v ≤ 6 (22 coeffs) | chosen; paper uses global DCT |
| Carrier B keying | (key, image id, **address**) | **correction**, see 3.5 |
| Embed order | **B then A** | **correction**, see 3.2 |
| `TEXTURE_MIN` | 3.0 levels, lesion override | dossier |
| `TAU_F`, `TAU_SR` | grid-searched on validation to joint FPR 1e-4 | dossier |
| Container | PNG only | dossier |

Invariants asserted in code, not prose: LL untouched; A and B index sets
disjoint; PNG round trip bit-identical; clean δf exactly 0; wrong key →
CANNOT SAY, never TAMPERED; verify() has no mask parameter; every verdict
carries a reason; every metric carries a denominator; same command, same bytes.

---

## 5. Build sequence

Each sprint ends in something checkable. Nothing starts before the previous
gate passes.

**S1 — Core spine.** `config.py`, `transform.py` (Haar pair + perfect
reconstruction test), `binder.py` (HMAC tags, digest independence, address
avalanche), `carriers.py` (QIM with sign reader; B-first ordering),
`container.py` (PNG round trip, bit-identical), `verify.py`, `ladder.py`,
`seeds.py`, `receipts.py`, plus the six pre-flight tests (check 3 restated to
block scale).
*Gate:* all six pre-flight checks pass on 100 synthetic phantoms; clean δf =
0.000 on every one; wrong key never returns TAMPERED.

**S2 — Preprocess, gate, and real pixels.** `preprocess.py` (pinned resize,
nearest-neighbour mask, region classes), `gate.py`, texture threshold
validation, digest-stability receipt on real ISIC 2018 images.
*Gate:* region classes reproducible; digest stable ≥ 99% under JPEG 90 and 75;
texture threshold frozen with a receipt.

**S3 — Battery.** 22 conditions, one function each, frozen parameters,
`runner.py`, receipt writer, byte-identical reruns.
*Gate:* battery sheet written, hashed, frozen; reruns byte-identical.

**S4 — Metrics and baselines.** `metrics.py` (block-F1 at three stated
denominators, IoU, FPR, coverage, ρ, bootstrap CIs), trivial bounds,
Wong–Memon floor, SMARTMed re-implementation, comparison protocol adapter.
*Gate:* one procedure, same cases, same seeds for every method; recomputing a
table from stored verdicts reproduces it exactly.

**S5 — Measurement.** Full primary run, seven ablations, secondary LiTS run,
tertiary ISIC 2019 transfer, failure gallery. Runs on your machine or Kaggle;
I supply the scripts and read the receipts.
*Gate:* every table in the thesis exists and traces to a receipt.

**S6 — Write-up and demo.** Thesis, 90-second live demo, poster, generated
tables only.

**S7 — Final.** Splicing, LaMa removal attacker, recovery decision, sealed
held-out run exactly once.

GPU work (EditGuard head-to-head) stays in S6 as a supplement and never gates
the result.

---

## 6. The constraint that shapes everything

**This sandbox cannot reach the datasets.** Outbound network is allowlisted to
GitHub, npm and PyPI; ISIC, Codalab and Kaggle are unreachable. Consequences:

1. All code must be **fully testable without datasets**, on synthetic
   phantoms and generated fixtures. That is a discipline, not a workaround —
   it is also what makes the reproducibility package real.
2. Every dataset run happens where the pixels are: your laptop or Kaggle.
   You run a command; the script writes a receipt and a result file; you send
   me the receipts, not the images.
3. To tune thresholds and measure the digest on real tissue, I need a **small**
   sample — 40 ISIC 2018 images with masks is enough for Phase One. Upload them
   to a private repo or a folder outside git; they never enter `Major-Project`.

If that sample never arrives, S2-S5 can still be built and gated on synthetic
data, but no number enters the thesis until it is measured on real images.

---

## 7. Risks, ranked by what they cost

| Risk | Early signal | Response |
|---|---|---|
| Single-pixel fragility claim is unachievable | δf = 0 on a 1-level edit | Already measured. Restate the claim at block scale (A-003) |
| τsr cannot separate handling from paste | ρ < 5, overlapping distributions | Widen the mid band, aggregate over 2×2 blocks, re-search thresholds |
| Digest flips under benign handling on real images | benign FPR above the line | Coarsen Q, drop to 2 digest coefficients, re-run |
| Binding ablation is run wrong | ablation changes nothing | Ablate embedder and verifier together (3.3) |
| ISIC 2018 / 2019 overlap | transfer gap implausibly small | De-duplication receipt before the tertiary run |
| Scope creep under deadline pressure | a 23rd battery condition | Frozen sheet + dated amendment + full re-run |

---

## 8. Immediate next action

Build S1 on this branch, starting with `config.py`, the Haar pair and its
perfect-reconstruction test, then the binder and its two proofs, then the
carriers, then the six pre-flight checks — each committed with its test.

First PR into `dev` contains S1 and nothing else.
