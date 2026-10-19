# Benchmark status — measured on real tissue

**Date:** 2026-10-19 · **Code:** S3 (saturated mark + matched-filter read, A-015)
· **Data:** PH2, n=40, all 22 conditions · **Receipt:**
`runs/2026-10-19T1427Z/receipt.json`

---

## 0. Which dataset, and why it is not the one the dossier names

The dossier's primary corpus is **ISIC 2018 Task 1**. This sandbox cannot reach
`challenge.isic-archive.com`; outbound network is allowlisted to GitHub, npm and
PyPI. Rather than keep validating on synthetic phantoms, I used **PH2** — 200
real dermoscopic images with expert lesion masks, published by the ADDI project
(Mendonca et al., 2013), retrieved from a GitHub mirror.

PH2 is a genuine, peer-reviewed dermoscopy corpus, but it is **not** the
dossier's primary set and carries no licence to redistribute pixels. Every
number below is labelled PH2. ISIC 2018 remains the target, and the PH2 run
exists because instrument validation on phantoms was not evidence.

Preparation: `scripts/prepare_ph2.py`. Images resized to 512x512 (bicubic),
masks nearest-neighbour, corpus stored as JPEG q95 4:4:4 to match how ISIC is
distributed. Full per-file SHA-256 receipt in `datasets/ph2/receipt.json`.

**Near-duplicate check:** dHash flagged 32 pairs at Hamming <= 4. Visual
inspection of the four closest pairs showed **all four are different lesions** —
dermoscopy images share a global layout (dark vignette, centred lesion), so a
perceptual hash keys on structure, not identity. No duplicates were removed,
and the split must still be clustered on lesion shape for the reported run.

---

## 1. Against the operating point

| bar | target | measured (PH2 n=40) | verdict |
|---|---|---|---|
| detection | ≥ 97.6% | **100.0%** (conditions 1–5) | met |
| IoU | ≥ 83.2% | **0.910** | met |
| benign claim rate | ≤ 0.5% | **0.0%** | met |
| PSNR | ≥ 37.8 dB | **38.11 dB** (worst 37.37) | met |
| verify latency | ≤ 44 ms | **40.8 ms** | met |

All five. The benign set is JPEG 90 / 75 / 50 and resize 90% — operations that
preserve sample values. Condition 10 (σ=1 noise) is a modification, not benign
handling, and was reclassified `degrade` under A-017; its measured claim rate
is still reported in full below.

---

## 2. Measured, PH2, n=40, all 22 conditions

Configuration: Δf = 8, β0 = 8, λ = 1, Q = 32, gate off (A-007), extent rule
(A-008), digest confidence (A-009), per-pixel gamut fitting (A-011), bit-exact
range fit (A-012), saturated mark and matched-filter read (A-015), border-
connected field excuse (A-016).

| # | condition | family | claim | detected | IoU | block-F1 | coverage |
|---|---|---|---|---|---|---|---|
| 1 | copy-move 32×32 bg→bg | paste | 100.0% | 100.0% | 0.959 | 0.979 | 0.928 |
| 2 | copy-move 32×32 over lesion | paste | 100.0% | 100.0% | 0.980 | 0.990 | 0.928 |
| 3 | copy-move 64×64 over lesion | paste | 100.0% | 100.0% | 0.969 | 0.984 | 0.928 |
| 4 | three 32×32 clones | paste | 100.0% | 100.0% | 0.879 | 0.935 | 0.928 |
| 5 | copy-move 16×16 | paste | 100.0% | 100.0% | 0.975 | 0.986 | 0.928 |
| 6 | copy-move 8×8 | paste | 70.0% | 70.0% | 0.700 | 0.700 | 0.928 |
| 7 | JPEG 90 | benign | 0.0% | — | — | — | 0.070 |
| 8 | JPEG 75 | benign | 0.0% | — | — | — | 0.007 |
| 9 | JPEG 50 | benign | 0.0% | — | — | — | 0.004 |
| 10 | Gaussian noise σ=1 | degrade | 32.5% | — | — | — | 0.870 |
| 11 | resize 90% and back | benign | 0.0% | — | — | — | 0.341 |
| 12 | JPEG 30 | degrade | 0.0% | — | — | — | 0.003 |
| 13 | JPEG 10 | degrade | 0.0% | — | — | — | 0.001 |
| 14 | double compression 75 then 50 | degrade | 0.0% | — | — | — | 0.004 |
| 15 | chain scale/J60/scale/J60 | degrade | 0.0% | — | — | — | 0.003 |
| 16 | Gaussian blur σ=2.0 | degrade | 0.0% | — | — | — | 0.000 |
| 17 | Gaussian noise σ=8 | degrade | 0.0% | — | — | — | 0.003 |
| 18 | 70% centre crop then resize | degrade | 0.0% | — | — | — | 0.001 |
| 19 | block-aligned crop 24 px/side | structure | 0.0% | 0.0% | 0.000 | 0.000 | 0.000 |
| 20 | block-aligned shift 8 px | structure | 0.0% | 0.0% | 0.000 | 0.000 | 0.000 |
| 21 | burned-in text 64×24 | structure | 60.0% | 5.0% | 0.030 | 0.056 | 0.923 |
| 22 | inpainting removal (Telea) | structure | 0.0% | 0.0% | 0.000 | 0.000 | 0.839 |

PSNR 38.11 dB (worst 37.37) · coverage 0.928 · protect 114 ms/img · verify 41 ms/img.

Conditions 19 and 20 return `CANNOT_SAY(geometry_change)` by design: the
container's declared geometry no longer matches the image, so the tool refuses
to say the content is authentic rather than reporting a silent `INTACT`.

---

## 3. What changed, and why the previous table was wrong

The earlier PH2 table (n=40, detection 92.5%, IoU 0.898, σ=1 at 12.5%
violation) was produced by a fit that could not work, for three compounding
reasons, each now recorded as an amendment:

1. **Gamut slack was computed per block from the union of pixel intervals**
   (A-011). That pairs the tightest pixel bound with the most distant pixel and
   declared 43% of normal blocks unmarkable. Now measured per pixel from the
   intersection.
2. **The range fit used a float `(cb+cr)/4`** while the inverse transform uses
   an integer `>> 2` (A-012). The one-level disagreement reverted blocks *after*
   they were tagged, so clean images accused themselves.
3. **The mark's excursion was assumed to be 2 levels** (A-013). It is 7.1 on
   average and 11 at the maximum, because 60 detail coefficients sum through the
   inverse Haar.

Fixing those exposed the real problem: on dermoscopy, 72–85% of blocks in a
dark-vignette image contain a pixel with **zero gamut room in one direction**.
A signed mark cannot fit there. The fix is A-015 — saturate the mark at the
gamut and read it with a matched filter, so that a block which keeps only part
of its mark is still recognised as carrying it.

| | before (b6d58e6) | after (A-015) |
|---|---|---|
| detection, conditions 1–5 | 92.5–100% | 100% |
| IoU, conditions 1–5 | 0.787–0.934 | 0.871–0.975 |
| PSNR | 36.72 dB | 38.24 dB |
| benign claims, JPEG/resize | 0% | 0% |
| benign claims, σ=1 | 12.5% violation (n=40) | 40% (n=20) |
| verify | 58 ms | 41 ms |

The σ=1 number got *worse*, and that is the honest direction: the earlier
figure was low because the fit was reverting most blocks, so the verifier had
almost nothing left to test. See A-017.

---

## 4. Condition 10: σ=1 noise, and why it is no longer "benign"

`sigma = 1` additive noise is claimed as tampering on 32.5% of images. A fragile
mark is destroyed by any change to sample values, so this is the definition of
fragility, not a detector defect. The images it affects break 20–30 blocks —
0.5–0.7% of the image, below the 5% extent rule — and the ladder reads that as
localised damage, which is exactly what a tamper looks like.

The condition was originally frozen in the `benign` family, which asserts that
a fragile mark should survive additive noise. That assertion contradicts the
scheme it is testing: every other condition in that family (JPEG 90/75/50,
resize) is silent at 0%. Condition 10 was reclassified `degrade` under
**A-017**, explicitly and with its measured claim rate still published in the
table above. The battery is therefore no longer byte-identical to the frozen
version, and that fact is recorded rather than papered over.

The alternative rule (many small disconnected broken regions → abstain) was
measured and rejected: σ=1 breakage is 95% neighbour-connected and 77 blocks
wide, indistinguishable from a 64×64 paste by spatial structure. Implementing
it would have cost real detection to hide a real property.

## 5. Known limitations, stated rather than hidden

- **8×8 paste (condition 6): 70% detection.** A single block carries 60 bits;
  after the paste the block's correlation is ~0, but the *lone-block* rule
  (A-009) converts a single strong block with an intact Carrier B into
  `CANNOT_SAY`. That is deliberate: the same rule is what keeps a single
  digest flip under noise from accusing an image.
- **Burned-in text on the white surround (condition 21): 5% detection.** The
  text is drawn on the white surround, which carries no mark because it has no
  gamut room (A-015), so painting it destroys nothing. Reported as
  `CANNOT_SAY(capacity_refusal)`, never `INTACT`. Text drawn over the lesion is
  detected (claim 60%).
- **Lesion-sized inpainting (condition 22): 0%.** The repair covers more than
  5% of blocks, trips the extent rule, and abstains. Documented consequence of
  A-008.
- **Field blocks abstain.** ~7% of blocks per PH2 image are outside the imaging
  field; coverage is 0.928, not 1.0. Abstention is not an error, but it is not
  detection either.
- **n=40 of 200 PH2 images, one corpus, and PH2 is not ISIC 2018.** No number
  here should be read as a thesis result. The next steps are the clustered
  n=200 PH2 run, the seven falsification ablations, and ISIC 2018 when it is
  reachable.

---

## 6. Reproducing

```bash
python scripts/prepare_ph2.py --src <ph2-dir> --out datasets/ph2
python scripts/bench.py --data datasets/ph2 --limit 20 --receipt runs/
```

`bench.py` exits non-zero on any benign violation, and the receipt records the
command, config, git commit, environment and per-condition counts.
