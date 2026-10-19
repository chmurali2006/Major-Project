# A Fragile Watermarking for Medical Image Tamper Detection — where the work stands

**Date:** 2026-10-20 · **Branch:** `arena/4f1090b0-major-project` (PR #4 → `dev`)
· **Headline receipt:** `runs/2026-10-20-n200-v6/receipt.json`
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
tampered block as authentic on any copy-move condition, makes no claim on any
untouched image, and abstains rather than guess where the gamut leaves no room
for a mark. The tag it verifies names the block's address, its detail content
and its mean, so a copy-move, a repaint and a brightness shift each break it.

---

## 2. The claim, and the evidence for it

Every number below is generated from `runs/2026-10-20-n200-v6/receipt.json` by
`scripts/make_tables.py` or printed by `scripts/bench.py`; the full tables are
in [`docs/BENCHMARKS.md`](BENCHMARKS.md) §1.

| what is claimed | measured | bar | receipt |
|---|---|---|---|
| detects copy-move tampering | **99.90%** of images, conditions 1–5 | ≥ 97.6% | `n200-v6` |
| locates it | **IoU 0.9421**, block-F1 0.955 on the 32×32 paste | ≥ 0.832 | same |
| never calls a copy-move block authentic | **0.0%** silent, conditions 1–6 | — | same |
| never claims on an untouched image | **0 / 200** | 0 | same |
| stays silent on benign handling | **0.0%** on JPEG 90/75/50, resize **and** σ=1 | ≤ 0.5% | same |
| does not visibly damage the image | **38.27 dB** mean, worst image **35.52 dB** | ≥ 37.8 dB mean | same |
| runs fast enough to use | **38.98 ms** verify, 130 ms protect, 512², CPU | ≤ 44 ms | same |
| the binding is what defeats copy-move | ablation A1: detection **1.000 → 0.000** | — | `2026-10-20-ablate` |
| the global-transform rules are load-bearing | ablation A8: resize claims **0.000 → 1.000** without them | — | same |
| the mean binding is what catches burned-in text | ablation A7: condition 21 IoU **0.285 → 0.065** | — | same |

The battery is 22 conditions in five families: six copy-move edits, five benign
transforms, seven degradation chains, four structural changes. It is frozen, it
is run by one command, and it writes a receipt containing the command, the
configuration, the commit, the environment and the per-condition counts, and
records whether the **code paths** were clean when it ran.

---

## 3. What an examiner should be told, before they find it

**3.0 Two rates are reported for every detection claim, and they differ.**
Detection is scored at IoU ≥ 0.10 (the rule fixed before the results). At the
strict IoU ≥ 0.5 reading, conditions 1–5 score 94.0–100% instead of
99.5–100%. The gap is boundary blocks on a 64×64 grid: a 32×32 paste is four
blocks, and one block of error moves IoU by 0.2. Both numbers are in the table
because quoting only the lenient one would misrepresent the localisation.

**3.1 The pin-hole is reduced four-fold, not eliminated.** A tag made only of
Haar *detail* coefficients cannot see a modification that just moves a block's
mean. A-023 (erasure rung) and A-030 (the tag now names the block mean, read
from `LL2`, which the mark cannot touch) took changed blocks reported INTACT
from "at least one on every image" to **5.9%** on burned-in text and **2.9%** on
inpainting. Most of the residual sits in blocks the embedder refused, which
carry no mark at all. Condition 21 is still an alarm rather than a precise
localiser: claims on 99.5% of images, but block-F1 0.437 and IoU 0.286.

**3.2 Worst-case image quality is 35.52 dB, below the 37.8 dB mean bar.** This is
the price of block fitting (A-029): the alternative configuration, margin 3, has
a 37.65 dB worst image but detection of exactly 97.60% — the bar with nothing
behind it. Both receipts ship; §3.5 of `BENCHMARKS.md` has the table.

**3.3 Single-block edits are 95.0%, and every miss abstains.** A one-block edit
carries no spatial redundancy. The lone-block rule prefers `CANNOT_SAY` to a
false accusation, because the same rule stops one digest flip under noise from
accusing a clean scan. Silent rate 0.0%.

**3.4 σ=1 noise is silent because it abstains, not because it passes.** Claim
rate 0.0% at coverage 0.506. The attenuation rule (A-021) recognises a globally
transformed mark. A-017, which would have relabelled the condition, was
withdrawn — the battery is unchanged from the dossier.

**3.5 Structure conditions abstain.** Crop and shift return
`CANNOT_SAY(geometry_change)`; coverage 0.000 is the honest answer, not a
detection result.

**3.5b The corpus is the public PH2 mirror**, not the official BMP
distribution, and it ships no expert masks. `BENCHMARKS.md` §0 says what that
does and does not change; `scripts/prepare_ph2_public.py` writes a per-file
SHA-256 receipt so the corpus is reconstructible.

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
| A-030 | the tag named details only, which cannot see a mean shift | 22.5% of text-changed blocks INTACT | mean (`LL2`) folded into the tag | 22.5% → **5.9%**, c21 IoU .082 → **.286** |

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

0. **Re-run ISIC-300 and the full 2594** with the current configuration
   (A-021, A-029, A-030). `docs/REPRODUCE.md` §2. This is the one claim that is
   still validated on a reproducer rather than on the primary corpus, and A-030
   has never seen ISIC at all.
1. **Push condition 21 past recall.** The mean binding catches text blocks; the
   claim is still wider than the text (IoU 0.286) and 5.9% of changed blocks
   are judged from refused neighbours. Both need a rule that reasons about
   *why* a block has no evidence, not a threshold change.
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
| `docs/AMENDMENTS.md` | every design change with its reason and its evidence — 31 entries |
| `runs/2026-10-20-n200-v6/receipt.json` | the headline run, reproducible from the command it records |
| `docs/figures/battery.png` | the 22 conditions at a glance, generated from that receipt |
| `scripts/bench.py` | the battery harness; exits non-zero on a benign violation |
| `scripts/make_tables.py` | regenerates the tables in `BENCHMARKS.md` from a receipt |
| `scripts/ablate.py` | the falsification harness |
| `README.md` | layout, quickstart, and the metadata-stripping limitation |
