# Kaggle runbook — ISIC 2019 first

## 1. Is 30 GPU-hours/week enough?

Yes, by a wide margin. Measured, not estimated:

Corrected after the v2 architecture. The v1 estimate (30 min per configuration)
was for a 64x64 block model. Pixel-resolution localisation costs 5.5x more, and
the old number is retired.

| stage | measured | at n = 9,000 |
|---|---|---|
| embed + tamper + evidence (10 ch), per image | **~86 ms** | **~13 min** |
| write tampered PNG + masks | — | **~9 min** |
| **preprocessing total** | | **~22 min** |
| pixel model forward, batch 4, 512², on this CPU | 2 882 ms | — |
| same step, T4 | — | ~160 ms |
| training step, batch 8, T4 | — | **~0.96 s** |
| steps per epoch (6 300 train images) | | 787 |
| **one epoch** | | **~13 min** |
| **one 30-epoch configuration** | | **~6.3 GPU-h** |
| **all 12 configurations (C0–C11)** | | **~75 GPU-h** |

So the honest answer has changed: **30 GPU-h/week is enough for one week of
headline runs, not the whole matrix.** A realistic split:

| week | runs | GPU-h |
|---|---|---|
| 1 | C0 (free), C8 headline, C3 (no attention), C9 (key removed) | ~19 |
| 2 | C1, C2, C4, C10 (re-key) | ~19 |
| 3 | C5, C6, C7, C11 + reruns | ~22 |

Two ways to halve it, both of which must be *measured* rather than assumed:
train at 256² for 20 epochs then fine-tune at 512² for 10 (~3.3 GPU-h per
configuration), or reduce `n_total` to 6 000. Report whichever is used.

## 2. Uploading

1. Add the ISIC 2019 dataset from Kaggle Datasets (search `isic 2019`), attach
   it to the notebook. The loader globs `**/*.jpg` under `/kaggle/input`, so the
   exact slug does not matter.
2. Attach `notebooks/keyswm_isic2019.ipynb`. Set **Accelerator = GPU T4 ×2**
   (the code uses one).
3. Internet is not required — no pip installs.

## 3. What the notebook does

| cell | action |
|---|---|
| 1–2 | rebuilds the tested package from an embedded copy; prints a protocol audit |
| 3 | discovers the dataset, reads `lesion_id` from the metadata CSV |
| 4 | splits **by lesion**, then embeds, tampers and extracts evidence |
| 5 | separation check: E on tampered blocks vs E on untouched blocks |
| 6–8 | trains the one-class AE (authentic only), then the fusion model |
| 9 | C0 classical floor, C9/C10 key transfer |
| 10 | **test set, opened once**; writes `receipt.json` |

## 4. The checks that matter

**Cell 5** — evidence separation, on tampered blocks versus untouched blocks:

```
fam       n    E_tamp   E_clean       sep
T1       30    0.9955    0.0071    0.9884
T2       30    0.8151    0.0073    0.8078
T3       30    0.8355    0.0067    0.8288
T4       30    0.9579    0.0070    0.9509
T5       30    0.9939    0.0069    0.9870
```
*(smoke mode, procedural images — not results)*

**Cell 10** — the stratified table is the only IoU table worth reading, because
the ceiling column says what the output grid could have achieved at that target
size. In the smoke run the pixel head beat the block ceiling in one bucket
(pixel 0.845 vs block 0.808, ceiling 0.959), which is the whole point of the v2
architecture and something v1 could not do by construction.

A family with `sep < 0.10` is a **broken family**, not a hard one. The notebook
asserts this and names the offenders.

Note that `B1`/`B2` raise E *everywhere*. That is routine handling destroying
the mark, and it is the entire reason the system needs to abstain.

## 5. Scope: ISIC 2019 only (decided 2026-10-24)

CheXpert and LiTS are deferred. Consequences, so they are not discovered late:

- ISIC 2019 is one of PFF-WM's three corpora, so the run is on shared ground.
- Their detection table is CheXpert and their IoU table is LiTS. **Nothing from
  this phase can be tabulated against either.**
- The result that stands on its own is **C0 vs C8 on the same split** — the
  contribution of the learned half — plus the per-diagnosis and per-area strata.

Additions this phase now carries, because it is the only corpus:

- **per-diagnosis strata** (MEL, NV, BCC, AK, BKL, DF, VASC, SCC) with n and a
  small-n flag; unavailable buckets are reported as unavailable, never merged
  into a silent "unknown".
- **selective risk against coverage** with AURC, so the abstention is shown to
  buy accuracy rather than hide failure.

## 6. What is fair to compare

| comparison | fair? |
|---|---|
| C0 vs C8 **inside this notebook**, same split | **yes** — this is the real result |
| our ISIC 2019 IoU vs PFF-WM's 0.832 | **no** — that bar is LiTS, lesion insertion, pixel IoU |
| our detection accuracy vs their 97.6% | **no** — that figure is CheXpert, and we are not running CheXpert in this phase |

The receipt records `comparable_to_published: false` with the reason attached,
so a number cannot be lifted out of context by accident.

## 7. Known limitations, stated before they are found

1. **Tampering is synthetic.** Every published system in this space synthesises
   tamper; there is no corpus of real medical image forgeries. Disclose it.
2. **T2 has no anatomical constraint on ISIC.** On LiTS the insertion is
   confined to the liver. On ISIC we have no organ mask, so the mass may land
   anywhere. The LiTS notebook fixes this.
3. **The key is published in the notebook.** That is required for
   reproducibility. It also means the *security* claim does not hold for this
   release — an attacker with the notebook knows the key. C9/C10 measure the
   property (wrong key → noise) independent of which key is used. Say this
   plainly; do not let someone else say it for you.
4. **Block-level ground truth.** PFF-WM reports pixel IoU. We report both, but
   only the block number is measured; the pixel number is an upsample of it.
5. **n = 9,000 of 25,331.** A choice for iteration speed, not a limit. Raising
   `CFG['n_total']` costs ~13 more minutes of preprocessing.

## 8. Next notebook

Deferred. When the IoU comparison is wanted, `lits` is the same code with three
changes: T2 confined to the liver mask, pixel truth from the tumour mask, and
the tamper family restricted to lesion insertion. That is the only run that
produces a number allowed to sit beside 0.832.
