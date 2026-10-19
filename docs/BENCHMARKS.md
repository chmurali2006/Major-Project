# Benchmark status — measured on real tissue

**Date:** 2026-10-19 · **Code:** `1662968` + docs (clean tree at run time)
· **Data:** PH2, **n=200 — the entire corpus**, all 22 conditions
· **Receipt:** `runs/2026-10-19-n200-final/receipt.json`

> **This table supersedes the earlier PH2 run.** The change is A-021, which
> fixes a defect the *primary* corpus exposed and PH2 could not: see §5.

---

## 1. Against the operating point

| bar | target | measured (PH2 n=200) | verdict |
|---|---|---|---|
| detection | ≥ 97.6% | **99.90%** (conditions 1–5) | met |
| IoU | ≥ 83.2% | **0.9397** | met |
| benign claim rate | ≤ 0.5% | **0.0%** | met |
| PSNR | ≥ 37.8 dB | **38.72 dB** (worst 38.26) | met |
| verify latency | ≤ 44 ms | **42.9 ms** | met |

**Every bar is met on every image**, not on average: the worst image in the
corpus is 38.28 dB, above the 37.8 dB floor. That was the deciding argument for
λ=0 in A-018.

The benign set is JPEG 90 / 75 / 50, resize 90% and σ=1 noise — **all five at
0.0%**. Condition 10 is in that set because A-017 was withdrawn: the tool now
abstains on a globally attenuated mark (A-021) instead of accusing it, so the
battery is unchanged from the dossier.

---

## 2. Measured, PH2 n=200, 22 conditions

Configuration: Δf = 8, β0 = 8, **λ = 0** (A-018), Q = 32, gate off (A-007),
extent rule (A-008), digest confidence (A-009), per-pixel gamut fitting (A-011),
bit-exact range fit (A-012), saturated mark + matched-filter read (A-015),
border-connected field excuse (A-016), ground truth from the measured pixel
diff (A-019).

`silent%` is the fraction of images on which at least one ground-truth tampered
block was reported **INTACT**. An abstention is a safe miss; calling a tampered
block authentic is the failure a clinician would act on.

| # | condition | family | claim | detected | IoU | block-F1 | coverage | silent |
|---|---|---|---|---|---|---|---|---|
| 1 | copy-move 32×32 bg→bg | paste | 100.0% | 100.0% | 0.995 | 0.997 | 0.936 | 0.0% |
| 2 | copy-move 32×32 over lesion | paste | 100.0% | 100.0% | 0.994 | 0.997 | 0.936 | 0.0% |
| 3 | copy-move 64×64 over lesion | paste | 100.0% | 100.0% | 0.951 | 0.975 | 0.936 | 0.0% |
| 4 | three 32×32 clones | paste | 100.0% | 100.0% | 0.989 | 0.994 | 0.936 | 0.0% |
| 5 | copy-move 16×16 | paste | 99.5% | 99.5% | 0.994 | 0.997 | 0.936 | 0.0% |
| 6 | copy-move 8×8 | paste | 72.0% | 72.0% | 0.715 | 0.715 | 0.936 | 0.0% |
| 7 | JPEG 90 | benign | 0.0% | — | — | — | 0.071 | — |
| 8 | JPEG 75 | benign | 0.0% | — | — | — | 0.007 | — |
| 9 | JPEG 50 | benign | 0.0% | — | — | — | 0.004 | — |
| 10 | Gaussian noise σ=1 | benign | **0.0%** | — | — | — | 0.856 | — |
| 11 | resize 90% and back | benign | **0.0%** | — | — | — | 0.341 | — |
| 12 | JPEG 30 | degrade | 0.0% | — | — | — | 0.002 | — |
| 13 | JPEG 10 | degrade | 0.0% | — | — | — | 0.001 | — |
| 14 | double compression 75 then 50 | degrade | 0.0% | — | — | — | 0.004 | — |
| 15 | chain scale/J60/scale/J60 | degrade | 0.0% | — | — | — | 0.002 | — |
| 16 | Gaussian blur σ=2.0 | degrade | 0.0% | — | — | — | 0.000 | — |
| 17 | Gaussian noise σ=8 | degrade | 0.0% | — | — | — | 0.003 | — |
| 18 | 70% centre crop then resize | degrade | 0.0% | — | — | — | 0.001 | — |
| 19 | block-aligned crop 24 px/side | structure | 0.0% | 0.0% | 0.000 | 0.000 | 0.000 | 0.0% |
| 20 | block-aligned shift 8 px | structure | 0.0% | 0.0% | 0.000 | 0.000 | 0.000 | 66.0% |
| 21 | burned-in text 64×24 | structure | 51.5% | 2.5% | 0.023 | 0.043 | 0.931 | 100.0% |
| 22 | inpainting removal (Telea) | structure | 0.0% | 0.0% | 0.000 | 0.000 | 0.845 | 100.0% |

PSNR 38.72 dB (worst 38.26) · coverage 0.936 · protect 129 ms/img · verify 43 ms/img.

Conditions 19 and 20 return `CANNOT_SAY(geometry_change)` by design.

---

## 3. What the numbers do not say

### 3.1 The pin-hole: modifications that only move a block's mean

Carrier A's tag lives in the Haar **detail** coefficients, and the digest that
binds it is quantised at Q = 32 levels. A modification that changes a block's
average brightness while leaving its internal detail structure intact therefore
changes neither the tag nor the digest, and the block verifies as intact.

Conditions 21 and 22 do exactly that. Burned-in text at (250,250,250) over white
surround and Telea inpainting over a smooth region both flatten or uniformly
shift blocks, and the `silent` column reads 100%: on every image, at least one
changed block was reported INTACT. Measured directly on IMD390 block (57,25):
the block's luma moved from 192–226 to 192–250, and it still scored a perfect
correlation with its expected tag.

This is the design's **principal open weakness**. It is not a tuning problem.
The fix is a finer DC binding — include the block mean in the digest at a much
finer quantisation than 32 — and that trades directly against the benign
stability the current digest buys (100% stable under JPEG 50). It needs its own
measurement, and it is the next piece of work, not something to be waved away.

An evidence floor was implemented, measured and **reverted**: it did not move
this column and it cost detection on conditions 21 and 22. A mechanism that
does not do what it claims does not ship.

### 3.2 Single-block edits: 69%, and the misses abstain

Condition 6 is one 32×32... one 8×8 block. 69% are detected; every miss is
`CANNOT_SAY`, and `silent` is 0.0%. The lone-block rule (A-009) deliberately
prefers abstention to a false accusation here, because the same rule is what
keeps a single digest flip under noise from accusing a clean scan.

### 3.3 Structure conditions abstain wholesale

Conditions 19 and 20 change the geometry; the container notices its declared
size no longer matches and returns `CANNOT_SAY(geometry_change)` rather than
`INTACT`. Coverage 0.000 is the honest answer, not a failure — but it is not
detection either.

### 3.4 σ=1 noise (was the worst failure, now 0%)

Additive noise at σ=1 destroys the mark in patches, and the patches used to be
reported as localised tampering on 31.5% of images. A-021 fixes it: the mark's
amplitude, measured where the gamut cannot have clipped it, drops to 0.88
against 1.00 for a clean image, so the tool recognises a global transformation
and abstains instead of attributing damage. **Claim rate 0.0%.**

This is why A-017 was *withdrawn*. Relabelling the condition would have hidden
the defect; the detector was fixed instead, and the frozen battery stands
unchanged.

---

## 4. How this compares with the earlier table

The first PH2 table (n=40, `b6d58e6`) reported 92.5% detection and IoU 0.898.
It was produced by a fit that could not work, for three compounding reasons:

1. **Gamut slack per block from the union of pixel intervals** (A-011) —
   declared 43% of normal blocks unmarkable.
2. **Float `(cb+cr)/4`** where the inverse transform uses `>> 2` (A-012) —
   reverted blocks after they were tagged.
3. **The mark's excursion assumed to be 2 levels** (A-013) — measured 7.1 mean,
   11 max.

Fixing those exposed the real problem: 72–85% of blocks in a dark-vignette
image hold a pixel with zero gamut room in one direction. A-015 (saturate the
mark, read it with a matched filter) is the structural answer.

| | before | after |
|---|---|---|
| detection, conditions 1–5 | 92.5–100% | **99.5–100%** |
| IoU, conditions 1–5 | 0.787–0.934 | **0.956–0.970** |
| PSNR | 36.72 dB | **38.72 dB** (worst 38.28) |
| benign claims | 0% JPEG, 12.5% σ=1 | **0%** JPEG, 31.5% σ=1 |
| verify | 58 ms | **40.5 ms** |
| corpus | n=40 | **n=200 (whole corpus)** |

---

## 5. Falsification checks (dossier §19)

`scripts/ablate.py`. Every ablation changes the **embedder** as well as the
reader. Two regimes are reported because one mechanism only matters in one of
them: `plain` is PH2 as it is, `smooth` is PH2 blurred by σ=0.9 before
protecting, which models ISIC 2018's flatter images.

Receipts: `runs/2026-10-19-ablate-final/` (plain),
`runs/2026-10-19-ablate-smooth/` (smooth).

| ablation | metric | plain | smooth | outcome |
|---|---|---|---|---|
| A1 binding cut | copy-move detection | 1.000 → **0.000** | 1.000 → **0.000** | load-bearing |
| A2 corroboration cut | 8×8-paste claim | 0.500 → **0.167** | 0.500 → **0.167** | load-bearing |
| A3 capacity refusal removed | unmarked blocks judged | 0.0000 → 0.0007 | 0.0000 → 0.0007 | measurable, small |
| A4 tilt restored (λ=1) | PSNR | 38.71 → **38.48** | 39.65 → **39.37** | load-bearing |
| A5 ladder collapsed | benign claim rate | 0.000 → 0.000 | 0.000 → 0.000 | **no effect — see below** |
| A6 attenuation cut | resize claim, smooth regime | 0.000 → 0.000 | 0.000 → **0.667** | load-bearing |

**A1** is the central claim: without the address in the tag, copy-move
detection goes from 100% to zero.

**A6** is the falsification of A-021, and it only shows in the smooth regime —
which is exactly the corpus that exposed the defect. Without the rule, two
thirds of smooth images claim tampering after a benign resize.

**A2** shows the carriers are not redundant: without Carrier B the single-block
claim falls to a sixth.

**A4** measures the A-018 decision from the other side: restoring region
weighting costs 0.23–0.28 dB.

**A3 is small but real.** Without the capacity refusal the tool judges 0.07% of
blocks it never marked. It is retained because asserting integrity over an
unmarked block is wrong regardless of count, and because it supplies the
`capacity_refusal` reason.

**A5 no longer moves the battery, and that is a finding.** Before A-021 the
extent rule was what stopped benign transforms from being claimed (collapsing
it drove benign claims to 1.000). With the attenuation rule in place, benign
transformations are recognised before extent is consulted, so A5's effect on
this battery is nil. The extent rule is retained because it is the rule that
converts *widespread substituted* content into an abstention, a case this
battery does not contain at a scale that would show it — and because removing it
would need its own measurement. Recorded honestly rather than left looking
load-bearing.

**Not run.** Dossier ablations 3 and 5 target the texture gate, disabled under
A-007; 7 needs a second corpus and is now the top priority (see §6).

---

## 6. The primary corpus trial, and the defect it found

A local trial ran the full battery on **ISIC 2018 Task 1, first 300 images**
(official S3 distribution, 2594 pairs prepared, masks verified) and on PH2, for
both the previous codebase (`dev`, `ea3b368`) and this one (`e3290ca` at the
time). The numbers are the user's, reproduced in their report.

| bar | dev ISIC-300 | this branch ISIC-300 | dev PH2-200 | this branch PH2-200 |
|---|---|---|---|---|
| detection | 0.9613 not met | **0.9967 met** | 0.9390 not met | **0.9990 met** |
| IoU | 0.8375 met | **0.8933 met** | 0.7917 not met | **0.9050 met** |
| benign claims | 0.0560 not met | **0.0683 not met** | 0.0360 not met | **0.0000 met** |
| PSNR | 36.24 not met | **39.06 met** | 36.41 not met | **38.30 met** |
| verify | 58.5 ms | 53.7 ms | 62.3 ms | 57.7 ms |
| violation | c10 σ=1 28% | **c11 resize 27.3%** | c10 σ=1 18% | none |

Two things follow, and both are in the design now:

1. **The redesign fixed the real problems** — detection, IoU, PSNR and benign
   rate all improve on both corpora.
2. **It introduced one defect that only the primary corpus could reveal.**
   Condition 11 claimed on 27.3% of ISIC images. That is A-021: on a smooth
   image a resample breaks only the few blocks containing an edge, and a few
   scattered broken blocks look like localised editing. PH2 is more textured,
   so it never showed the problem. Fixed and falsified in A-021/A6.

**Still to re-measure on ISIC after A-021.** The trial above predates the fix.
The expected outcome is condition 11 at 0.0% and the benign bar met; that must
be measured, not assumed, and the ISIC corpus is only reachable from the
user's machine. `docs/REPRODUCE.md` gives the exact command.

**Condition 21 remains the honest gap** — 28.7% claims with 0.3% detection on
ISIC, 51.5% with 2.5% on PH2. That is A-020. The obvious repair (a finer digest)
was measured across Q ∈ {4, 8, 16, 32} and **does not work**: detection stays at
0–4.2% and falls to zero at fine quantisation, because extra blocks break
elsewhere and the extent rule abstains for the whole image. The surviving
blocks are flat regions where a partial repaint changes the mean but leaves the
detail-carried mark intact. Closing it needs the tag to depend on the mean in
the embedding domain, not a threshold change — see A-020, which records the
falsified hypothesis so it is not proposed again.

---

## 7. Reproducing

```bash
python scripts/prepare_ph2.py --src <ph2-repo> --out datasets/ph2
python scripts/bench.py  --data datasets/ph2 --limit 200 --receipt runs/<utc>/
python scripts/ablate.py --data datasets/ph2 --limit 6   --receipt runs/<utc>-ablate/
python scripts/ablate.py --data datasets/ph2 --limit 6 --smooth 0.9 \
                         --receipt runs/<utc>-ablate-smooth/
```

`bench.py` exits non-zero on a benign violation and warns if the working tree
is dirty, because a receipt that cites code it did not run is worthless.
