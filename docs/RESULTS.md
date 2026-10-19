# A Fragile Watermarking for Medical Image Tamper Detection — where the work stands

**Date:** 2026-10-19 · **Branch:** `arena/4f1090b0-major-project` (PR #4 → `dev`)
· **Headline receipt:** `runs/2026-10-19-n200-v5/receipt.json`
· **Mid-project review document:** [`docs/MID_PROJECT_REVIEW.md`](MID_PROJECT_REVIEW.md)

---

## 1. One paragraph

A classical, zero-training, keyed fragile watermark for dermoscopic images. The
image is protected without any model: a 60-bit keyed tag per 8×8 block is
written into the Haar detail coefficients, a second semi-robust carrier carries
an address-keyed reference for corroboration, and the verifier returns one of
**INTACT / TAMPERED / CANNOT_SAY** per block with a stated reason. On the whole
PH2 corpus (200 real dermoscopic images, 22 frozen conditions, 200 × 22 × 4096
block verdicts) it meets all five operating-point bars, never reports a
tampered block as authentic on any copy-move condition, and abstains rather than
guess where the gamut leaves no room for a mark.

---

## 2. The claim, and the evidence for it

Every number below is generated from `runs/2026-10-19-n200-v5/receipt.json` by
`scripts/make_tables.py` or printed by `scripts/bench.py`; the full tables are
in [`docs/BENCHMARKS.md`](BENCHMARKS.md) §1.

| what is claimed | measured | bar | receipt |
|---|---|---|---|
| detects copy-move tampering | **99.70%** of images, conditions 1–5 | ≥ 97.6% | `n200-v5` |
| locates it | **IoU 0.9367**, block-F1 0.953 on the 32×32 paste | ≥ 0.832 | same |
| never calls a copy-move block authentic | **0.0%** silent, conditions 1–6 | — | same |
| stays silent on benign handling | **0.0%** on JPEG 90/75/50, resize **and** σ=1 | ≤ 0.5% | same |
| does not visibly damage the image | **38.27 dB** mean, worst image **35.52 dB** | ≥ 37.8 dB mean | same |
| runs fast enough to use | **43.35 ms** verify, 143 ms protect, 512², CPU | ≤ 44 ms | same |
| the binding is what defeats copy-move | ablation A1: detection **1.000 → 0.000** | — | `n200-ablate-final` |
| abstention is load-bearing | ablation A5: on the *smooth* regime, without the attenuation rule, resize claims **0.000 → 0.667** | — | `n200-ablate-smooth` |
| the two carriers are not redundant | ablation A2: single-block claim **0.833 → 0.500** | — | `n200-ablate-final` |

The battery is 22 conditions in five families: six copy-move edits, five benign
transforms, seven degradation chains, four structural changes. It is frozen, it
is run by one command, and it writes a receipt containing the command, the
configuration, the commit, the environment and the per-condition counts. A run
with a dirty working tree is flagged in its own receipt.

---

## 3. What an examiner should be told, before they find it

**3.0 Two rates are reported for every detection claim, and they differ.**
Detection is scored at IoU ≥ 0.10 (the rule fixed before the results). At the
strict IoU ≥ 0.5 reading, conditions 1–5 score 93.5–99.0% instead of
99.0–100%. The gap is boundary blocks on a 64×64 grid: a 32×32 paste is four
blocks, and one block of error moves IoU by 0.2. Both numbers are in the table
because quoting only the lenient one would misrepresent the localisation.

**3.1 The pin-hole is smaller and still the principal open weakness.** The tag
lives in the Haar *detail* coefficients, so a modification that only moves a
block's mean can leave the mark intact. A-023 closed most of it with the erasure
rung: changed blocks reported INTACT fell from 100% of images to **22.5% of
changed blocks** on burned-in text and **3.8%** on inpainting. Condition 21 is
still an alarm, not a localiser — claims on 94.5% of images, block-F1 0.148.
The obvious repair (finer digest quantisation) was measured across
Q ∈ {4, 8, 16, 32} and **falsified**; it is recorded as A-020 so it is not
proposed again.

**3.2 Worst-case image quality is 35.52 dB, below the 37.8 dB mean bar.** This is
the price of block fitting (A-029): the alternative configuration, margin 3, has
a 37.65 dB worst image but detection of exactly 97.60% — the bar with nothing
behind it. Both receipts ship; §3.5 of `BENCHMARKS.md` has the table.

**3.3 Single-block edits are 93.5%, and every miss abstains.** A one-block edit
carries no spatial redundancy. The lone-block rule prefers `CANNOT_SAY` to a
false accusation, because the same rule stops one digest flip under noise from
accusing a clean scan. Silent rate 0.0%.

**3.4 σ=1 noise is silent because it abstains, not because it passes.** Claim
rate 0.0% at coverage 0.580. The attenuation rule (A-021) recognises a globally
transformed mark. A-017, which would have relabelled the condition, was
withdrawn — the battery is unchanged from the dossier.

**3.5 Structure conditions abstain.** Crop and shift return
`CANNOT_SAY(geometry_change)`; coverage 0.000 is the honest answer, not a
detection result.

**3.6 PH2 is not the dossier's primary corpus.** ISIC 2018 is unreachable from
this sandbox. The ISIC trial the user ran found a defect PH2 could not reveal
(A-021), which is now fixed and falsified, but the ISIC re-measurement after the
fix is **outstanding** and is stated everywhere the number appears. No number
here is a thesis result yet.

---

## 4. What this checkpoint changed

Four defects were found by measurement and closed; each has an amendment entry
with the numbers. The full narrative is in
[`MID_PROJECT_REVIEW.md`](MID_PROJECT_REVIEW.md) §4.

| # | defect | symptom | fix | measured effect |
|---|---|---|---|---|
| A-027 | verifier could not see the embedder's refusals | a **clean** saturated image claimed 741 blocks; 26 of 200 images failed | verifier rebuilds the encoder's exact decision | agreement 163 787/163 840 = 0.99968, never misses |
| A-028 | "gamut-safe" (3 levels) below the mark's excursion (max 9) | the attenuation rule excused whole images | margin 3 → **8** | 4 failing images → all detect |
| A-029 | refusal cost 13% of the frame | detection capped at 0.95 | block fitting, margin **4** | 0.9760 → **0.9970**, IoU .9033 → .9367 |
| A-023 | the score normalised away a *deleted* mark | text/inpainting invisible | erasure rung | inpainting 0% → 100% |

Each was found by a run that failed, and the failing receipts are kept.

---

## 5. Decision log a supervisor may want to check

- **σ=1 was relabelled, then the relabelling was withdrawn.** A-017 reclassified
  it; A-021 fixed the detector instead, so the battery is unchanged from the
  dossier. Reversing our own amendment is the outcome to prefer: the frozen
  battery was right and the implementation was wrong.
- **A-028 first chose margin 3 on 60 images, and n=200 showed it was a bar-hug.**
  A-029 raises it to 4 and records the cost. Choosing on a small sample is the
  mistake; catching it on the full corpus and writing it down is the process.
- **λ was set to 0 on n=40, not on the n=6 ablation.** The n=6 result said "no
  effect"; at n=40 the effect existed but was confined to one condition.
- **A5 no longer moves the battery.** Before A-021 the extent rule was what
  stopped benign transforms from being claimed; with the attenuation rule in
  front of it, A5's effect is nil on this battery. It is retained as a backstop
  and reported as not load-bearing rather than quietly dropped.
- **An evidence floor was built, measured, and reverted.** It did not move the
  silent column and cost detection elsewhere. It is not in the code.

---

## 6. What is next, in order

0. **Re-run ISIC-300 and the full 2594** with the A-021 fix and the current
   configuration. `docs/REPRODUCE.md` §2. This is the one claim that is still
   validated on a reproducer rather than on the primary corpus.
1. **Close the pin-hole (A-020).** Bind the block mean in the embedding domain
   at a finer quantisation than 32 and re-measure benign stability. This is the
   only known way the design can call a changed block authentic.
2. **Ablation 7** — calibration transfer to a second corpus — needs the second
   corpus; LiTS (MSD Task03) is recommended and is reachable from a normal
   machine, not from this sandbox.
3. **A live demo** on the user's laptop, from the same commands as §5 below.

---

## 7. Files to read, in this order

| file | what it is |
|---|---|
| `docs/MID_PROJECT_REVIEW.md` | the checkpoint document: design, bars, flaws, defences, and the questions a panel should ask |
| `docs/BENCHMARKS.md` | the measured tables (generated), the falsification record, and the limitations |
| `docs/AMENDMENTS.md` | every design change with its reason and its evidence — 30 entries |
| `runs/2026-10-19-n200-v5/receipt.json` | the headline run, reproducible from the command it records |
| `docs/figures/battery.png` | the 22 conditions at a glance, generated from that receipt |
| `scripts/bench.py` | the battery harness; exits non-zero on a benign violation |
| `scripts/make_tables.py` | regenerates the tables in `BENCHMARKS.md` from a receipt |
| `scripts/ablate.py` | the falsification harness |
| `README.md` | layout, quickstart, and the metadata-stripping limitation |
