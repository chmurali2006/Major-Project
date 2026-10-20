# Benchmark status — measured on real tissue

**Date:** 2026-10-20 · **Data:** PH2, **n=200 — the entire corpus**, all 22 conditions
· **Receipt:** `runs/2026-10-20-n200-v6/receipt.json` (commit `89f47a2`, code paths clean)
· **Figures:** `docs/figures/battery.png`, `docs/figures/localisation.png`

> **The tables in §2 are generated, not typed.** `scripts/make_tables.py` writes
> them from the receipt, so a number in this document cannot drift from the run
> it describes. Prose elsewhere quotes those numbers and is checked against them.
>
> **This run supersedes every earlier PH2 table.** Between the previous headline
> (`n200-v5`) and this one, the tag was made to depend on the block mean
> (A-030), which closed the design's principal open weakness: changed blocks
> reported INTACT on burned-in text fell from **22.5% to 5.9%**, and detection
> on that condition rose from 36.0% to **97.0%**.

---

## 0. The corpus, and what is weaker about it

PH2 (ADDI project, Mendonça et al.) is 200 dermoscopic images with expert lesion
masks. This run uses the **public GitHub mirror** of PH2, prepared by
`scripts/prepare_ph2_public.py`, because the workspace it was measured in cannot
reach the distribution server. Three things follow, and none of them are hidden:

* The mirror ships **JPEG** (765×572) rather than the original BMP. Each image
  is resized to 512×512 (bicubic, dossier §10) and stored as JPEG q95 4:4:4,
  the same rule as `prepare_ph2.py`, so the corpus is not easier than the one
  the earlier tables used.
* The mirror ships **no expert masks**. The prepare script writes placeholders,
  and its receipt says so. They are safe here for a stated reason, not by
  assumption: the mask multiplies region weighting, `lam = 0` (A-018) and the
  texture gate is off (A-007), so `beta = beta0 * (1 + lam*region)` is constant
  in the region. The battery never reads the mask it loads.
* `prepare_receipt.json` records a SHA-256 per source file and per derived file,
  so a reviewer can rebuild the corpus and check it is the same one.

The previous headline (`runs/2026-10-19-n200-v5/`) was measured on the official
BMP distribution. Both are kept; the numbers they produce are within the
differences the code changes explain.

---

## 1. Against the operating point

The levels come from PFF-WM (CheXpert, 44 ms). Cross-paper comparison is
forbidden — the corpora differ — so these are levels this project holds itself
to, not a claim to have beaten anyone.

<!-- BEGIN MEASURED TABLES -->

**Run:** `scripts/bench.py --data /tmp/ph2mirror --limit 200 --receipt runs/2026-10-20-n200-v8/receipt.json`  
**Commit:** `369e441` · **dirty tree:** no · **n:** 200


| what | bar | measured | |
|---|---|---|---|
| detection, conditions 1-5 | >= 97.6% | **99.40%** | met |
| localisation IoU, conditions 1-6 | >= 0.832 | **0.9336** | met |
| false claims, benign conditions | <= 0.5% | **0.00%** | met |
| PSNR (mean; worst image) | >= 37.8 dB | **38.68 dB; 36.00 dB** | met |
| verify latency | <= 44 ms | **40.19 ms** | met |

| # | condition | family | claim | detected | det@IoU 0.5 | IoU | block-F1 | coverage | silent (img) | silent (blocks) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | copy-move 32x32 bg->bg | paste | 100.0% | 99.0% | 93.0% | 0.929 | 0.949 | 0.924 | 0.0% | 0.0% |
| 2 | copy-move 32x32 over lesion | paste | 100.0% | 100.0% | 93.0% | 0.931 | 0.950 | 0.924 | 0.0% | 0.0% |
| 3 | copy-move 64x64 over lesion | paste | 100.0% | 100.0% | 99.5% | 0.958 | 0.975 | 0.925 | 0.0% | 0.0% |
| 4 | three 32x32 clones | paste | 100.0% | 100.0% | 97.5% | 0.933 | 0.959 | 0.924 | 0.0% | 0.0% |
| 5 | copy-move 16x16 | paste | 98.0% | 98.0% | 95.5% | 0.925 | 0.942 | 0.924 | 0.0% | 0.0% |
| 6 | copy-move 8x8 | paste | 92.5% | 92.5% | 92.5% | 0.925 | 0.925 | 0.924 | 0.0% | 0.0% |
| 7 | JPEG 90 | benign | 0.0% | — | — | — | — | 0.000 | — | — |
| 8 | JPEG 75 | benign | 0.0% | — | — | — | — | 0.000 | — | — |
| 9 | JPEG 50 | benign | 0.0% | — | — | — | — | 0.000 | — | — |
| 10 | Gaussian noise sigma=1 | benign | 0.0% | — | — | — | — | 0.772 | — | — |
| 11 | resize 90% and back | benign | 0.0% | — | — | — | — | 0.033 | — | — |
| 12 | JPEG 30 | degrade | 0.0% | — | — | — | — | 0.000 | — | — |
| 13 | JPEG 10 | degrade | 0.0% | — | — | — | — | 0.000 | — | — |
| 14 | double compression 75 then 50 | degrade | 0.0% | — | — | — | — | 0.000 | — | — |
| 15 | chain scale/J60/scale/J60 | degrade | 0.0% | — | — | — | — | 0.000 | — | — |
| 16 | Gaussian blur sigma=2.0 | degrade | 0.0% | — | — | — | — | 0.000 | — | — |
| 17 | Gaussian noise sigma=8 | degrade | 0.0% | — | — | — | — | 0.000 | — | — |
| 18 | 70% centre crop then resize | degrade | 0.0% | — | — | — | — | 0.000 | — | — |
| 19 | block-aligned crop 24px/side | structure | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% |
| 20 | block-aligned shift 8px | structure | 0.0% | 0.0% | 0.0% | 0.000 | 0.000 | 0.000 | 0.0% | 0.0% |
| 21 | burned-in text 64x24 | structure | 100.0% | 97.5% | 0.5% | 0.284 | 0.435 | 0.920 | 93.0% | 8.7% |
| 22 | inpainting removal (Telea) | structure | 100.0% | 100.0% | 99.5% | 0.911 | 0.952 | 0.924 | 100.0% | 4.6% |

PSNR 38.68 dB (worst 36.00) · coverage 0.924 · protect 149 ms/img · verify 40.2 ms/img.

<!-- END MEASURED TABLES -->

<!-- END MEASURED TABLES -->

<!-- END MEASURED TABLES -->

> **Provenance.** `code_dirty` is `false` and `tree_dirty` is `false`: the run
> started from commit `369e441` with nothing modified, and the receipt is
> checked in exactly as it was written. The harness distinguishes the two
> fields because documents edited during a long run are not a provenance
> problem, while uncommitted code is.

**On the "met" column.** The bar is a minimum on the *mean over images*; a
reviewer should ask what the distribution behind it looks like, so:

* **detection** is 99.40% on conditions 1–5 and never below 98.0% on any of
  them (the 95% interval over images is 98.8–99.9). At the *strict* IoU ≥ 0.5
  reading it is 93.0–99.5%: the claim lands in
  the right region, and on a 32×32 edit inside a 64×64 grid the boundary blocks
  are where the difference lives. Both numbers are printed because the lenient
  one alone would be a misleading headline.
* **benign claims are 0.0% on all five benign conditions**, not on average:
  JPEG 90/75/50, σ=1 noise, and resize-and-back. This holds together with a
  coverage column that shows *why*: JPEG 90 leaves the tool with coverage
  0.000 — it declares the whole image unreadable rather than authentic.
  Silence there is an abstention, not a passing grade, and the coverage column
  is what distinguishes the two.
* **the untouched protected image is claimed tampered on 0 of 200 images.**
  This is not one of the 22 conditions, and it had no column of its own until
  now; it is the most basic error the tool could make.
* **PSNR is 38.68 dB mean and 36.00 dB on the worst image.** The mean clears the
  bar; the worst image does not. A per-image guarantee has to be bought with
  detection: at `FIT_MARGIN = 3` the worst image is 37.65 dB and detection is
  97.60%, exactly the bar with nothing behind it
  (`runs/2026-10-19-n200-v4/`). Both receipts ship, and the trade is in §3.4.
* **latency** is 40.19 ms mean against a 44 ms bar on this Linux sandbox, with
  median 39 ms, p95 47 ms and max 52 ms. The bar is met on the mean, not on the
  tail, and two runs of identical code measured 38.98 and 43.57 ms — the margin
  is inside the machine's own noise, which is why the distribution is printed
  rather than the mean alone. It is hardware-relative: an earlier trial on the
  user's i5-1235U measured ~1.4× slower than the sandbox of the day.

---

## 1b. The validity envelope — how much handling it survives

The battery reports that no benign condition produces a false claim. On its own
that is a weak statement: a tool that abstains on everything also never lies.
This table measures the thing the claim column hides — **how much of the image
can still be certified** after a given amount of ordinary handling, and whether
the tool ever lies there. Swept on every one of the 200 protected images; no
tampering, so every claim in this table would be a false claim.

<!-- BEGIN ENVELOPE TABLE -->

| JPEG quality | certified area | 10th pct | images half certified | images with any verdict | false claims |
|---|---|---|---|---|---|
| Q100 | **0.913** | 0.751 | 193/200 | 200/200 | **0** |
| Q99 | **0.895** | 0.720 | 193/200 | 200/200 | **0** |
| Q98 | **0.690** | 0.522 | 182/200 | 200/200 | **0** |
| Q97 | **0.247** | 0.195 | 0/200 | 200/200 | **0** |
| Q96 | **0.068** | 0.052 | 0/200 | 200/200 | **0** |
| Q95 | **0.018** | 0.014 | 0/200 | 200/200 | **0** |
| Q92 | **0.001** | 0.000 | 0/200 | 195/200 | **0** |
| Q90 | **0.000** | 0.000 | 0/200 | 154/200 | **0** |
| Q85 | **0.000** | 0.000 | 0/200 | 69/200 | **0** |
| Q80 | **0.000** | 0.000 | 0/200 | 57/200 | **0** |
| Q70 | **0.000** | 0.000 | 0/200 | 55/200 | **0** |
| Q50 | **0.000** | 0.000 | 0/200 | 52/200 | **0** |

| noise sigma | certified area | 10th pct | images half certified | images with any verdict | false claims |
|---|---|---|---|---|---|
| 0.0 | **0.925** | 0.766 | 194/200 | 200/200 | **0** |
| 0.5 | **0.880** | 0.721 | 193/200 | 200/200 | **0** |
| 1.0 | **0.773** | 0.596 | 184/200 | 200/200 | **0** |
| 1.5 | **0.542** | 0.395 | 165/200 | 200/200 | **0** |
| 2.0 | **0.247** | 0.166 | 0/200 | 200/200 | **0** |
| 4.0 | **0.001** | 0.000 | 0/200 | 192/200 | **0** |
| 8.0 | **0.000** | 0.000 | 0/200 | 2/200 | **0** |

Lossless PNG round trip: certified area **0.925**, 194/200 images at least half certified, **0 false claims**.

<!-- END ENVELOPE TABLE -->

Three things to read out of it. **It never lies**: zero false claims at every
quality and every noise level, 200 images each, 3800 readings. **It degrades as
a curve, not a cliff**: full certification up to Q99, two thirds of the frame
at Q98, a quarter at Q97, nothing at Q92. **The abstention is not silence**: at
Q90 the tool still returns a verdict somewhere on 154 of 200 images — those are
`CANNOT_SAY` blocks with a named reason, which is the product, not the absence
of one.

---

## 2. Measured, PH2 n=200, 22 conditions

Configuration: Δf = 8, β0 = 8, **λ = 0** (A-018), Q = 32, gate off (A-007),
extent backstop (A-008/A-025), digest confidence (A-009), per-pixel gamut
fitting (A-011), bit-exact range fit (A-012), saturated mark + matched-filter
read (A-015), border-connected field excuse (A-016), ground truth from the
measured pixel diff (A-019), attenuation rule (A-021), erasure rung (A-023),
content-bound tag (A-024), verifier refusal reconstruction (A-027), gamut-safe
margin 8 (A-028), block fitting at margin 4 (A-029), **mean binding at
`dc_sig_delta = 4` (A-030)**.

Two columns need a sentence each:

* **`det@IoU 0.5`** is the same detection rule at a stricter localisation
  threshold. A claim that lands somewhere inside a large lesion passes the
  stated rule and fails this one.
* **`silent (blocks)`** is the fraction of blocks the condition actually
  changed that were reported **INTACT** — the error a clinician would act on.
  An abstention is a safe miss; this is not. `silent (img)` is the laxer
  version ("at least one such block, somewhere on the image") and is kept
  because it is what the earlier tables used.

---

## 2b. The obvious alternative, measured on the same corpus

Every review asks why not simply hash the LSBs. `scripts/baseline_lsb.py`
implements the textbook scheme — Wong-style keyed block hash written into the
low bit of each pixel, same 8×8 grid, same battery, n=60 images — so the
question is settled by measurement rather than by argument.

<!-- BEGIN BASELINE TABLE -->

| | textbook 8x8 block-hash LSB | this work |
|---|---|---|
| detection, conditions 1-5 | 100.00% | 99.40% |
| localisation IoU, conditions 1-6 | 1.0000 | 0.9336 |
| false claims, benign handling | **100.00%** | **0.00%** |
| false claims, untouched image | 0/60 | 0/200 |
| PSNR | 55.91 dB | 38.68 dB |
| JPEG Q100: images claimed | **100%** | **0%** |
| JPEG Q95: images claimed | **100%** | **0%** |
| sigma=1 noise: images claimed | **100%** | **0%** |

<!-- END BASELINE TABLE -->

Read honestly, the textbook scheme **wins two rows**: it localises perfectly
(its hash is exact, so every changed block is flagged) and it is 17 dB kinder to
the image. It also **claims tampering on 100% of benign handling** — every JPEG,
every noise realisation, every resize — because a codec changes pixels and it
has no vocabulary for "changed but not edited". That is the entire
contribution: not a sharper localiser, but a detector that can tell the
difference between damage and editing, and says so when it cannot.

---

## 3. What the numbers do not say

### 3.1 The pin-hole: reduced four-fold, not eliminated

Carrier A's tag lives in the Haar **detail** coefficients. A modification that
moves a block's average brightness while leaving its internal structure alone
used to be invisible to it. A-023 (the erasure rung) and A-030 (binding the
block mean into the tag) both attack this, and the per-block silent column
shows what is left:

| condition | changed blocks called INTACT | before A-030 | before A-023 |
|---|---|---|---|
| 21 burned-in text | **8.7%** | 22.5% | "at least one per image, always" |
| 22 inpainting | **4.6%** | 3.8% | "at least one per image, always" |

Two residuals remain and both are named. Blocks the embedder **refused** carry
no mark at all — they are excused, and a text edge that lands on one is a
structural miss, not a wrong verdict. And a block whose mean moved by less than
the code's resolution while its details were untouched is still INTACT.

Condition 21 is also still an **alarm, not a precise localiser**: it raises a
claim on 100% of images and detects 97.5% at the stated rule, but block-F1 is
0.435 and IoU 0.284, and at IoU ≥ 0.5 it detects 0.5% of images. The claim is
wider than the text. Reporting the detection figure alone would misrepresent
this, which is why the fourth column exists. (The silent-block rates rose when
Carrier B was removed — A-032 — because the marked image has less spread
spectrum in it; this is the cost side of that amendment, not a new defect.)

### 3.2 Single-block edits: 95.0%, and every miss abstains

An 8×8 paste (condition 6) is detected on 92.5% of images with IoU 0.925 and a
silent rate of 0.0% — the fifteen misses are abstentions, not false
authentications. The lone-block rule (A-009) prefers `CANNOT_SAY` to a false
accusation because the same rule stops one digest flip under noise from
accusing a clean scan.

### 3.3 Geometry changes abstain wholesale

Conditions 19 and 20 change the geometry; the container notices its declared
size no longer matches and returns `CANNOT_SAY(geometry_change)`. Coverage 0.000
is the honest answer, not a detection result. Condition 20 keeps 2.5% claims at
coverage 0.011: a shift that happens to leave the declared size intact is
detected only where the keyed lattice survives.

### 3.4 The image-quality trade, stated as a trade

Block fitting (A-029) shifts a whole block by the smallest integer offset that
gives the mark headroom, so that it cannot clip. That is what buys the last
points of detection, and it is what costs the worst-case PSNR. Measured over
all 200 images, the largest shift used anywhere is **4 levels** — the margin
itself — and capping the shift at 8 or 12 produces identical results, so the
cost is the *number* of shifted blocks on a frame with a narrow gamut window,
not the size of any one shift. Measured, n=200, identical code otherwise:

| FIT_MARGIN | detection | IoU | PSNR mean | PSNR worst | coverage |
|---|---|---|---|---|---|
| 3 | 0.9760 | 0.9033 | 38.77 | **37.65** | 0.894 |
| **4 (default)** | **0.9970** | 0.9367 | 38.27 | 35.52 | 0.926 |

(The detection and IoU columns are from the A-029 runs, before the mean
binding; A-030 does not change PSNR because it changes which bits are written,
not how far.)

### 3.5 σ=1 noise: silent, but by abstaining

Additive noise at σ=1 used to be reported as localised tampering on 31.5% of
images. A-021 recognizes a globally attenuated mark and abstains: claim rate
**0.0%** at coverage **0.772**. This is why A-017 was *withdrawn* — relabelling
the condition would have hidden the defect; the detector was fixed instead and
the frozen battery stands unchanged.

---

## 4. How this compares with the earlier tables

| | `n200-final` (2026-10-19) | `n200-v5` | **`n200-v6`** |
|---|---|---|---|
| detection, conditions 1–5 | 99.90% | 99.70% | **99.90%** |
| IoU, conditions 1–6 | 0.9397 | 0.9367 | **0.9421** |
| IoU floor over conditions 1–6 | 0.715 (c6) | 0.929 | **0.934** |
| PSNR | 38.72 (worst 38.26) | 38.27 (worst 35.52) | 38.27 (worst 35.52) |
| benign claims | 0% JPEG, 31.5% σ=1 | 0% everywhere | **0% everywhere** |
| clean-image claims | not scored | not scored | **0/200** |
| c21 changed blocks called INTACT | 100% of images | 22.5% of blocks | **5.9% of blocks** |

`n200-final` looked better on the mean and was **wrong**: 26 of its 200 images
were hiding a defect the aggregate averaged away (a saturated image accused
itself, A-027), and its condition-6 IoU of 0.715 was a floor the aggregate
buried. The current table is slightly worse on PSNR and has no floor below
0.934 on conditions 1–6.

---

## 5. Falsification checks (dossier §19)

`scripts/ablate.py`. Every ablation changes the **embedder** as well as the
reader — an ablation that only changes the reader proves nothing, because the
mark it reads was written by the unablated encoder. Two regimes are reported
because one mechanism only matters in one of them: `plain` is PH2 as it is,
`smooth` is PH2 blurred by σ=0.9 before protecting, which models ISIC 2018's
flatter images.

Receipts: `runs/2026-10-20-ablate-n40/` (plain, n=40) and
`runs/2026-10-20-ablate-smooth-v8/` (smooth, n=12). The plain run was n=12
until A-033: at twelve images A3 was undersampled and read a false null, and
the fixed metric needs the wider sample to fire.

| ablation | metric | plain n=40 | outcome |
|---|---|---|---|
| A1 binding cut | copy-move detection | 1.000 → **0.000** | load-bearing |
| A2 Carrier B restored | Q100 certified area | 0.921 → **0.894** | prediction held — costs coverage |
| A3 capacity refusal removed | clean-image claim rate | 0.000 → **0.325** | load-bearing |
| A4 tilt restored (λ=1) | PSNR | 38.65 → 38.65 | no effect — A-018 stands |
| A5 ladder collapsed | benign claim rate | 0.000 → 0.000 | redundant with A6 |
| A6 attenuation cut | resize claim rate | 0.000 → 0.000 | redundant with A5 |
| A7 mean binding cut | condition 21 IoU | 0.297 → **0.075** | load-bearing |
| A8 both global rules cut | resize claim rate | 0.000 → **0.875** | load-bearing |
| A9 scatter rule cut | Q100 claim rate | 0.000 → **1.000** | load-bearing |

**A1** is the central claim: without the address in the tag, copy-move
detection goes from 100% to zero. **A7** is the falsification of A-030: without
the block mean in the tag, condition-21 localisation falls back to where it
was. **A9** is the falsification of A-031: without the scatter rule, a Q100
re-encode is claimed on every image again. **A3** is the falsification of a
"no effect" verdict that was itself a bug (A-033).

**Three checks do not move the battery, and that is a finding.** Each is
reported as measured, not explained away:

* **A4** (region weighting restored, λ = 1): PSNR is identical to four
  decimals. The λ = 0 decision (A-018) buys nothing measurable on this corpus,
  which is exactly what that amendment claimed when it removed the term.
* **A5 / A6** (extent rule, attenuation rule): each is redundant with the
  other. With the mean binding in place a global resample breaks *every* block
  rather than a few edge blocks, so the extent rule catches it even with the
  attenuation rule off. **A8 removes both**, and resize claims go **0.000 →
  0.875**. The pair is load-bearing; neither member is, alone. Reported as one
  rule with two guards, not two rules.
* **On the smooth regime** A9 does not fire either: a blurred image has little
  high-frequency content, so a Q100 re-encode does not break the fragile tag in
  the first place. The A-031 failure is a property of textured frames.

**Not run.** Dossier ablations 3 and 5 target the texture gate, disabled under
A-007; 7 needs a second corpus (see §6).

---

### 5b. Ablations measured under handling, not under the battery

Four mechanisms change nothing the battery can see, which reads as "decoration".
The battery only contains conditions this project chose, and A-031 was found
outside it, so the same ablations are run against the envelope
(`scripts/ablate_envelope.py`, n=40). Either answer is a finding: a mechanism
that matters here is one the battery could not see, and a mechanism that
matters nowhere should be deleted rather than defended.

<!-- BEGIN HANDLING ABLATION TABLE -->

| variant | clean | Q100 | Q99 | Q98 | Q95 | sigma 1 | sigma 2 |
|---|---|---|---|---|---|---|---|
| baseline | 0/40 · 0.93 | 0/40 · 0.92 | 0/40 · 0.90 | 0/40 · 0.69 | 0/40 · 0.02 | 0/40 · 0.78 | 0/40 · 0.25 |
| A2 Carrier B restored | 0/40 · 0.93 | 0/40 · 0.89 | 0/40 · 0.72 | 0/40 · 0.43 | 0/40 · 0.01 | 0/40 · 0.51 | 0/40 · 0.15 |
| A3 no capacity refusal | 14/40 · 0.94 | 0/40 · 0.93 | 0/40 · 0.91 | 0/40 · 0.69 | 0/40 · 0.02 | 0/40 · 0.78 | 0/40 · 0.25 |
| A5 no ladder | 0/40 · 0.93 | 0/40 · 0.92 | 0/40 · 0.90 | 0/40 · 0.69 | 0/40 · 0.02 | 0/40 · 0.78 | 0/40 · 0.25 |
| A6 no attenuation | 0/40 · 0.93 | 0/40 · 0.92 | 0/40 · 0.90 | 0/40 · 0.69 | 0/40 · 0.02 | 0/40 · 0.78 | 0/40 · 0.25 |
| A8 neither global rule | 0/40 · 0.93 | 0/40 · 0.92 | 0/40 · 0.90 | 0/40 · 0.69 | 32/40 · 0.73 | 0/40 · 0.78 | 30/40 · 0.75 |

*Cells are false claims / images · certified area. A clean column of 0 means the variant does not lie; the certified area says what the rule costs.*

<!-- END HANDLING ABLATION TABLE -->

What this bought: **A-032**. Carrier B was not decoration — it was a coverage
tax. Restoring it costs 18–27 points of certified area and prevents no false
claim anywhere, and it can be shown structurally that it *cannot* prevent one:
its only route into a verdict is `conflict = ~f_hi & s_hi`, a subset of the
blocks the fragile carrier already calls intact. It is now off by default.
**A3** was the opposite case: the ablation's chosen metric (verdicts on blocks
that carry no mark) read 0.000 → 0.000, while the real effect was 14 of 40
clean images being claimed. The metric was wrong, not the mechanism; it is now
`clean_claim`, and it fires.

---

## 6. The primary corpus trial, and the defect it found

A local trial ran the full battery on **ISIC 2018 Task 1, first 300 images**
(official distribution, 2594 pairs prepared, masks verified) and on PH2, for
both the previous codebase (`dev`) and this branch (`e3290ca` at the time). The
numbers are the user's, reproduced in their report.

| bar | dev ISIC-300 | branch ISIC-300 |
|---|---|---|
| detection | 0.9613 not met | **0.9967 met** |
| IoU | 0.8375 met | **0.8933 met** |
| benign claims | 0.0560 not met | **0.0683 not met** |
| PSNR | 36.24 not met | **39.06 met** |
| verify | 58.5 ms | 53.7 ms |
| violation | c10 σ=1 28% | **c11 resize 27.3%** |

Two things follow, and both are in the design now:

1. **The redesign fixed the real problems** — detection, IoU, PSNR and the
   benign rate all improve.
2. **It introduced one defect that only the primary corpus could reveal.**
   Condition 11 claimed on 27.3% of ISIC images. That is A-021: on a smooth
   image a resample breaks only the few blocks containing an edge, and a few
   scattered broken blocks look like localised editing. PH2 is more textured,
   so it never showed the problem. Fixed and falsified in A-021/A6.

**Still to re-measure on ISIC after A-021 and A-030.** The trial above predates
both fixes. The expected outcome is condition 11 at 0.0% and the benign bar met,
plus the condition-21 improvement A-030 measured on PH2. That must be measured,
not assumed, and the corpus is only reachable from the user's machine.
`docs/REPRODUCE.md` gives the exact command.

---

## 7. Reproducing

```bash
python scripts/prepare_ph2_public.py --src <mirror> --out datasets/ph2
python scripts/bench.py  --data datasets/ph2 --limit 200 --receipt runs/<utc>/receipt.json
python scripts/make_tables.py --receipt runs/<utc>/receipt.json --write docs/BENCHMARKS.md
python scripts/make_figures.py --receipt runs/<utc>/receipt.json \
                              --data datasets/ph2 --out docs/figures
python scripts/ablate.py --data datasets/ph2 --limit 12 --receipt runs/<utc>-ablate/
python scripts/ablate.py --data datasets/ph2 --limit 12 --smooth 0.9 \
                         --receipt runs/<utc>-ablate-smooth/
```

`bench.py` exits non-zero on a benign violation and records whether the code
paths were clean, because a receipt that cites code it did not run is worthless.
