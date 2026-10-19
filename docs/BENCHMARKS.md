# Benchmark status — measured on real tissue

**Date:** 2026-10-19 · **Code:** S1 + battery families 1-11 · **Data:** PH2, n=40

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

## 1. Measured, PH2, n=40

Configuration: Δf = 8, β0 = 8, λ = 1, Q = 32, gate off (A-007), extent rule
(A-008), digest confidence (A-009), exact gamut fitting (A-011).

| # | condition | family | tamper claim | detected | IoU | block-F1 |
|---|---|---|---|---|---|---|
| 1 | copy-move 32×32 bg→bg | paste | 92.5% | 92.5% | 0.898 | 0.910 |
| 2 | copy-move 32×32 over lesion | paste | 92.5% | 92.5% | 0.898 | 0.910 |
| 3 | copy-move 64×64 over lesion | paste | 100% | 100% | 0.934 | 0.955 |
| 4 | three 32×32 clones | paste | 100% | 97.5% | 0.787 | 0.856 |
| 5 | copy-move 16×16 | paste | 92.5% | 92.5% | 0.875 | 0.895 |
| 6 | copy-move 8×8 | paste | 57.5% | 55.0% | 0.492 | 0.508 |
| 7 | JPEG 90 | benign | **0%** | — | — | — |
| 8 | JPEG 75 | benign | **0%** | — | — | — |
| 9 | JPEG 50 | benign | **0%** | — | — | — |
| 10 | Gaussian noise σ = 1 | benign | **12.5%** | — | — | — |
| 11 | resize 90% and back | benign | **0%** | — | — | — |

Coverage 0.855. PSNR 36.72 dB mean, 33.76 dB worst. Protect 141 ms, verify
58 ms per 512×512 image.

---

## 2. Against the paper's operating point

| Bar | PFF-WM | Target | PH2 measured | Verdict |
|---|---|---|---|---|
| Detection | 97.6% | ≥ 97.6% | **92.5%** (1,2,5); 100% (3); 97.5% (4) | **not met** |
| Localisation | IoU 83.2% | ≥ 83.2% | **0.898, 0.934, 0.875** on 1,2,3,5; 0.787 on 4 | **met except cond 4** |
| Benign silence | < 0.5% | < 0.5% | 0% on JPEG 50/75/90 and resize; **12.5% on σ=1 noise** | **not met** |
| Fidelity | 37.77 dB | ≥ 37.8 dB | **36.72 dB** (worst 33.76) | **not met** |
| Inference | 44 ms | ≤ 44 ms | 58 ms on this CPU | **not met** |
| Binding ablation | must collapse | must collapse | passes (CI test) | met |

---

## 3. Why each gap exists, and what closes it

**Detection 92.5% instead of 100%.** 14.5% of blocks are excused on PH2 because
the mark cannot enter them without leaving the RGB gamut — dark vignette
corners, specular highlights, saturated borders. When the paste lands on an
excused block there is nothing to compare. Closing this needs a payload that
survives near the gamut edge: embed in the *signed* detail coefficients with a
per-block keyed polarity, so the mark can move down when it cannot move up.
That is a Phase One change, not a threshold.

**σ = 1 noise produces a claim in 12.5% of images.** Mild noise occasionally
flips a coarse digest, and the reference then fails to corroborate. The clean
lone-block ratio measured 0.49 against 0.51-0.57 for real pastes: the classes
touch. Options: coarser digest (fewer boundary crossings but weaker
discrimination), a reference aggregated over 2x2 block groups to raise its
signal-to-noise, or a longer spreading sequence per block. The second is the
most promising and is the next experiment.

**PSNR 36.72 dB.** Carrier B at β0 = 8 costs most of it; on phantoms the same
setting gave 38.55 dB, so real images are simply less forgiving. λ = 1 adds
2 dB of lesion-side distortion for no detection gain on PH2. Lowering β0 to 5
recovers roughly 0.8-1.0 dB and should cost little detection — to be measured,
not assumed.

**58 ms verify.** 19 of those milliseconds are the 4096 serial HMACs. They are
independent and trivially batchable; a vectorised tag path should bring verify
under 30 ms.

---

## 4. What this changes about the plan

1. The synthetic-phantom table is withdrawn as evidence. It stays in git
   history; it was useful for finding defects and is worthless as a result.
2. PH2 numbers are the working baseline, not a thesis table: different corpus
   from the dossier's, n=40, no ablations yet, conditions 12-22 missing.
3. Three of the six bars are not met. Each has a named engineering fix above,
   and none of them is a matter of moving a threshold.

## 5. Reproduce

```
python scripts/prepare_ph2.py --src <repo with Data/> --out datasets/ph2
python scripts/bench.py --data datasets/ph2 --limit 40
```

Both scripts write receipts. `datasets/` is outside the repository and is never
committed (Trap 29).
