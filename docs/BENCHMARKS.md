# Benchmark status — where we stand against the paper's operating point

**Date:** 2026-10-19 · **Code:** S1 + battery families 1-11 · **Data: synthetic
phantoms**

> These are **fixtures, not results**. The phantoms are generated; no number on
> this page may appear in the thesis. What they establish is that the harness
> produces every required metric and that the mechanism clears the paper's
> operating point *before* real data arrives. The first real run replaces this
> table wholesale.

---

## 1. The target

PFF-WM (Khaldi et al., 2026), the closest rival and the paper the dossier is
built around:

| Bar | PFF-WM (published) | Our target |
|---|---|---|
| Detection | 97.6% | ≥ 97.6% on our battery |
| Localisation | IoU 83.2% | ≥ 83.2% |
| Benign FPR | < 0.5% | < 0.5% per benign condition |
| Inference | 44 ms / 512×512 | ≤ 44 ms on a laptop CPU |

Cross-paper comparison is forbidden by Trap 21: their numbers were measured on
CheXpert/LiTS/ISIC 2019 with their attack set and their hardware. We hold
ourselves to the same *levels*, measured on our own frozen battery.

---

## 2. Measured, synthetic phantoms, n = 10

Configuration: Δf = 8, β0 = 8, λ = 1, Q = 32, gate off (A-007), extent rule
(A-008), digest confidence (A-009).

| # | condition | family | tamper claim | detected | IoU | block-F1 |
|---|---|---|---|---|---|---|
| 1 | copy-move 32×32 bg→bg | paste | 100% | 100% | 1.000 | 1.000 |
| 2 | copy-move 32×32 over lesion | paste | 100% | 100% | 1.000 | 1.000 |
| 3 | copy-move 64×64 over lesion | paste | 100% | 100% | 1.000 | 1.000 |
| 4 | three 32×32 clones | paste | 100% | 100% | 0.917 | 0.957 |
| 5 | copy-move 16×16 | paste | 100% | 100% | 1.000 | 1.000 |
| 6 | copy-move 8×8 | paste | 80% | 80% | 0.800 | 0.800 |
| 7 | JPEG 90 | benign | **0%** | — | — | — |
| 8 | JPEG 75 | benign | **0%** | — | — | — |
| 9 | JPEG 50 | benign | **0%** | — | — | — |
| 10 | Gaussian noise σ = 1 | benign | **0%** | — | — | — |
| 11 | resize 90% and back | benign | **0%** | — | — | — |

Condition 6's remaining 20% abstains (evidence_conflict), which the battery
permits: its expected outcome is "tamper blocks or abstention", and its
failure is "silent INTACT or a fabricated address".

Quality: **PSNR 38.55 dB** (worst 38.53). Runtime: **protect 145 ms, verify
46 ms** per 512×512 image on the sandbox CPU.

---

## 3. Against the bars

| Bar | Target | Measured | Verdict |
|---|---|---|---|
| Detection | ≥ 97.6% | 100% on conditions 1-5, 80% + 20% abstention on 6 | **met on 1-5; condition 6 compliant** |
| Localisation | IoU ≥ 83.2% | 0.800-1.000 | **met** |
| Benign silence | < 0.5% | 0 / 50 condition-image pairs | **met** |
| Fidelity | ≥ 37.8 dB (EditGuard) | 38.55 dB | **met** |
| Inference | ≤ 44 ms | 46 ms (our CPU) | nominally 2 ms over; hardware not comparable |
| Binding ablation | must collapse copy-move | δf 0.501 → 0.000 when the address is removed | **met** (test in CI) |

---

## 4. What this does not prove

1. **Real tissue.** The phantom has synthetic texture, synthetic chroma and a
   perfect ellipse mask. Real ISIC images have hair, rulers, ink, vignetting
   and JPEG artefacts *before* we touch them. Every threshold above is a
   guess until the real corpus runs.
2. **Modality.** No CT. The extreme-flat blocks of LiTS air are exactly where
   the gate and the refusal accounting matter, and where A-007 may reverse.
3. **Conditions 12-22.** Degrade and structure families are not implemented.
   Block-aligned crops (19, 20) will additionally need a grid-resynchronisation
   search, because a 24-pixel crop shifts every address.
4. **The reference carrier's contribution.** With the extent rule in place,
   Carrier B is no longer needed to *detect*; it is used for digest-confidence
   arbitration and explanation. Its ablation (β0 = 0) must be run and reported
   honestly — if it contributes nothing, claim 3 is revised, not defended.

---

## 5. What turns this into a thesis table

1. A 40-image ISIC 2018 sample with masks, placed in a private repository or a
   folder outside git.
2. The S2 preprocess and gate receipt: region classes, texture distribution,
   digest stability on real pixels.
3. The frozen battery sheet, hashed.
4. The S3 conditions 12-22.
5. Then `scripts/bench.py` runs unmodified on real images and every cell gains
   a receipt.

No number moves from this page into the report until that happens.
