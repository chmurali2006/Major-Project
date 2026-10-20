# A Fragile Watermarking for Medical Image Tamper Detection — where the work stands

**Date:** 2026-10-20 · **Branch:** `arena/4f1090b0-major-project` (PR #4 → `dev`)
· **Headline receipt:** `runs/2026-10-20-n200-v8/receipt.json`
· **Mid-project review document:** [`docs/MID_PROJECT_REVIEW.md`](MID_PROJECT_REVIEW.md)

---

## 1. One paragraph

A classical, zero-training, keyed fragile watermark for dermoscopic images. The
image is protected without any model: a 60-bit keyed tag per 8×8 block — bound
to the block's address, its detail content and its mean — is written into the
Haar detail coefficients. The verifier needs only the image: it recomputes every
tag and returns one of **INTACT / TAMPERED / CANNOT_SAY** per block, with a
stated reason. On the whole PH2 corpus (200 real dermoscopic images, 22 frozen
conditions, 200 × 22 × 4096 block verdicts) it clears all five operating-point
bars, reports **no** changed block as authentic on any copy-move condition,
makes no claim on any untouched image, and abstains rather than guess where the
gamut leaves no room for a mark. Measured outside the battery, on a swept
envelope of re-encodes and noise, it never makes a false claim at any of 3 800
readings, and keeps 91% of the frame certified at Q100 and 89% at Q99.

---

## 2. The claim, and the evidence for it

Every number below is generated from `runs/2026-10-20-n200-v8/receipt.json` by
`scripts/make_tables.py` or printed by `scripts/bench.py`; the full tables are
in [`docs/BENCHMARKS.md`](BENCHMARKS.md) §1.

| what is claimed | measured | bar | receipt |
|---|---|---|---|
| detects copy-move tampering | **99.40%** of images, conditions 1–5 | ≥ 97.6% | `n200-v8` |
| locates it | **IoU 0.9336**, block-F1 0.949 on the 32×32 paste | ≥ 0.832 | same |
| never calls a copy-move block authentic | **0.0%** silent, conditions 1–6 | — | same |
| never claims on an untouched image | **0 / 200** | 0 | same |
| stays silent on benign handling | **0.0%** on JPEG 90/75/50, resize **and** σ=1 | ≤ 0.5% | same |
| stays silent under *any* re-encode or noise | **0 claims in 3 800 readings**, Q100→Q50, σ=0→8 | — | `envelope-v8` |
| does not visibly damage the image | **38.68 dB** mean, worst image **36.00 dB** | ≥ 37.8 dB mean | `n200-v8` |
| runs fast enough to use | **40.19 ms** verify mean (median 39, p95 47) | ≤ 44 ms | same |
| the binding is what defeats copy-move | ablation A1: detection **1.000 → 0.000** | — | `ablate-v8` |
| the global-transform rules are load-bearing | A8: resize claims **0.000 → 0.917** without them | — | same |
| the mean binding catches burned-in text | A7: condition-21 IoU **0.301 → 0.067** | — | same |
| the scatter rule separates codec from surgery | A9: Q100 claims **0.000 → 1.000** without it | — | same |

Three comparisons a reader needs and would otherwise have to ask for:

| | this work | textbook 8×8 LSB hash | source |
|---|---|---|---|
| detection, conditions 1–5 | 99.40% | 100.00% | `baseline-lsb`, n=60 |
| IoU, conditions 1–6 | 0.9336 | 1.0000 | same |
| **false claims on benign handling** | **0.00%** | **100.00%** | same |
| PSNR | 38.68 dB | 55.91 dB | same |
| 95% CI on detection (n=200) | [98.8, 99.9] | — | `scripts/uncertainty.py` |

The battery is 22 conditions in five families: six copy-move edits, five benign
transforms, seven degradation chains, four structural changes. It is frozen, it
is run by one command, and it writes a receipt containing the command, the
configuration, the commit, the environment and the per-condition counts, and
records whether the **code paths** were clean when it ran.

---

## 3. What an examiner should be told, before they find it

**3.0 Two rates are reported for every detection claim, and they differ.**
Detection is scored at IoU ≥ 0.10 (the rule fixed before the results). At the
strict IoU ≥ 0.5 reading, conditions 1–5 score 93.0–99.5% instead of
99.0–100%. The gap is boundary blocks on a 64×64 grid: a 32×32 paste is four
blocks, and one block of error moves IoU by 0.2. Both numbers are in the table
because quoting only the lenient one would misrepresent the localisation.

**3.1 An 8×8 re-encode is the dangerous middle, and it was found outside the
battery.** Every JPEG condition in the frozen battery is Q ≤ 90, where the mark
dies everywhere and the whole image abstains. At Q100 the mark breaks in 6.4%
of blocks and *nothing in the battery could see it*: the tool claimed tampering
on **196 of 200 untouched images**. The scatter rule (A-031) now distinguishes a
codec's isolated islands (median 64–250 of them) from surgery (1–5), and the
count is **0 of 200**. This is the most important finding in the review pass: a
frozen battery that I chose had a hole in it, and only a measurement outside it
found the hole.

**3.2 The second carrier was a coverage tax, not a second opinion (A-032).** Its
only route into a verdict is `conflict = ~f_hi & s_hi`, a subset of the blocks
the fragile carrier already calls intact — so no threshold could ever make it
create a `TAMPERED`, only a `CANNOT_SAY`. Measured: restoring it costs 18–27
points of certified area under handling and prevents no false claim anywhere.
It is off by default. The cost of removing it is real and is reported:
detection 0.9990 → 0.9940, IoU 0.9421 → 0.9336, and PSNR **improves** 38.27 →
38.68 dB.

**3.3 The pin-hole is reduced four-fold, not eliminated.** A tag made only of
Haar *detail* coefficients cannot see a modification that just moves a block's
mean. A-023 (erasure rung) and A-030 (the tag now names the block mean, read
from `LL2`, which the mark cannot touch) took changed blocks reported INTACT
from "at least one on every image" to **5.9%** on burned-in text and **2.9%** on
inpainting. Most of the residual sits in blocks the embedder refused, which
carry no mark at all. Condition 21 is still an alarm rather than a precise
localiser: claims on 99.5% of images, but block-F1 0.435 and IoU 0.284.

**3.4 Worst-case image quality is 36.00 dB, below the 37.8 dB mean bar.** This
is the price of block fitting (A-029): the alternative configuration, margin 3,
has a 37.65 dB worst image but detection of exactly 97.60% — the bar with
nothing behind it. Both receipts ship; §3.5 of `BENCHMARKS.md` has the table.

**3.5 Single-block edits are 92.5%, and every miss abstains.** A one-block edit
carries no spatial redundancy. The lone-block rule prefers `CANNOT_SAY` to a
false accusation, because the same rule stops one digest flip under noise from
accusing a clean scan. Silent rate 0.0%.

**3.6 σ=1 noise is silent because it abstains, not because it passes.** Claim
rate 0.0% at coverage 0.772. The attenuation rule (A-021) recognises a globally
transformed mark. A-017, which would have relabelled the condition, was
withdrawn — the battery is unchanged from the dossier.

**3.7 Structure conditions abstain.** Crop and shift return
`CANNOT_SAY(geometry_change)`; coverage 0.000 is the honest answer, not a
detection result.

**3.8 The latency bar is met on the mean, not on the tail.** Mean 40.19 ms,
median 39 ms, p95 47 ms, max 52 ms on this sandbox. Two runs of identical code
measured 38.98 and 43.57 ms mean, so the margin against a 44 ms bar is inside
the machine's own noise. The distribution is printed by every run because the
mean alone would be a flattering number.

**3.9 A zero count is not a zero rate.** 0 benign claims in 1 000 trials bounds
the rate at 0.30% (rule of three), not 0.000%. 0 claims on 200 untouched images
bounds it at 1.50%. Both bounds are quoted wherever the counts are, and
`scripts/uncertainty.py` prints percentile bootstrap intervals over images for
every rate: detection [98.8, 99.9], IoU [0.9223, 0.9440], coverage
[0.9170, 0.9317].

**3.10 The corpus is the public PH2 mirror**, not the official BMP
distribution, and it ships no expert masks. `BENCHMARKS.md` §0 says what that
does and does not change; `scripts/prepare_ph2_public.py` writes a per-file
SHA-256 receipt so the corpus is reconstructible.

**3.11 PH2 is not the dossier's primary corpus.** ISIC 2018 is unreachable from
this sandbox. The ISIC trial the user ran found a defect PH2 could not reveal
(A-021), which is now fixed and falsified, but the ISIC re-measurement after the
fix is **outstanding** and is stated everywhere the number appears. No number
here is a thesis result yet.

---

## 4. What this checkpoint changed

Seven defects were found by measurement and closed; each has an amendment entry
with the numbers. The full narrative is in
[`MID_PROJECT_REVIEW.md`](MID_PROJECT_REVIEW.md) §4.

| # | defect | symptom | fix | measured effect |
|---|---|---|---|---|
| A-031 | a Q100 re-encode was read as surgery | **196 of 200** untouched images claimed | scattered damage is a codec: ≥12 islands → abstain | 196/200 → **0/200**, coverage .91 at Q100 |
| A-032 | a carrier that could only veto | 18–27 pts of coverage lost, no claim prevented | removed from the default configuration | Q99 coverage **.72 → .89**, PSNR +0.41 dB |
| A-027 | verifier could not see the embedder's refusals | a **clean** saturated image claimed 741 blocks | verifier rebuilds the encoder's exact decision | agreement 163 787/163 840 = 0.99968 |
| A-028 | "gamut-safe" (3 levels) below the mark's excursion (max 9) | the attenuation rule excused whole images | margin 3 → **8** | 4 failing images → all detect |
| A-029 | refusal cost 13% of the frame | detection capped at 0.95 | block fitting, margin **4** | 0.9760 → **0.9970**, IoU .9033 → .9367 |
| A-023 | the score normalised away a *deleted* mark | text/inpainting invisible | erasure rung | inpainting 0% → 100% |
| A-030 | the tag named details only, which cannot see a mean shift | 22.5% of text-changed blocks INTACT | mean (`LL2`) folded into the tag | 22.5% → **5.9%**, c21 IoU .082 → **.286** |

Two of these (A-031, A-032) were found in the second review pass, by measuring
*outside* the frozen battery. That is the strongest argument for the battery
being one instrument among several rather than the whole method.

---

## 5. Decision log a supervisor may want to check

- **σ=1 was relabelled, then the relabelling was withdrawn.** A-017 reclassified
  it; A-021 fixed the detector instead, so the battery is unchanged from the
  dossier. Reversing our own amendment is the outcome to prefer: the frozen
  battery was right and the implementation was wrong.
- **A-028 first chose margin 3 on 60 images, and n=200 showed it was a bar-hug.**
  A-029 raises it to 4 and records the cost. Choosing on a small sample is the
  mistake; catching it on the full corpus and writing it down is the process.
- **A-032 removed a mechanism the design had justified on paper**, after the
  envelope showed it could only lower coverage. Keeping it would have been
  cheaper to explain and worse to defend.
- **An ablation was re-specified rather than reported as a null result.** A3's
  metric measured the wrong thing (verdicts on unmarked blocks) and read
  0.000 → 0.000 while 14 of 40 clean images were being claimed. The metric is
  now `clean_claim`; the mechanism was right all along.
- **λ was set to 0 on n=40, not on the n=6 ablation.** The n=6 result said "no
  effect"; at n=40 the effect existed but was confined to one condition.
- **A5 no longer moves the battery.** With the attenuation rule in front of it,
  its effect is nil; jointly with A6 (A8) it is load-bearing. Reported as one
  rule with two guards rather than two rules.

---

## 6. What is next, in order

0. **Re-run ISIC-300 and the full 2594** with the current configuration
   (A-021, A-029, A-030, A-031, A-032). `docs/REPRODUCE.md` §2. This is the one
   claim still validated on a reproducer rather than on the primary corpus.
1. **Push condition 21 past recall.** IoU 0.284 and 5.9% of changed blocks
   judged from refused neighbours. Needs a rule that reasons about *why* a
   block has no evidence, not a threshold change.
2. **A held-out split.** `bench.py --offset` exists for it; every constant was
   chosen on these 200 images, and the honest test is the corpus the choices
   never saw (ISIC).
3. **Ablation 7** — calibration transfer to a second corpus — needs the second
   corpus; LiTS (MSD Task03) is recommended and is reachable from a normal
   machine, not from this sandbox.
4. **A live demo** on the user's laptop, from the same commands as §7.

---

## 7. Files to read, in this order

| file | what it is |
|---|---|
| `docs/MID_PROJECT_REVIEW.md` | the checkpoint document: design, bars, flaws, defences, and the questions a panel should ask |
| `docs/BENCHMARKS.md` | the measured tables (generated), the envelope, the baseline, the falsification record, and the limitations |
| `docs/AMENDMENTS.md` | every design change with its reason and its evidence — 32 entries |
| `runs/2026-10-20-n200-v8/receipt.json` | the headline run, reproducible from the command it records |
| `runs/2026-10-20-envelope-v8/receipt.json` | 3 800 handling readings: coverage and false claims |
| `docs/figures/battery.png` | the 22 conditions at a glance, generated from that receipt |
| `docs/figures/demo.png` | four questions asked of one protected file |
| `scripts/bench.py` | the battery harness; exits non-zero on a benign violation |
| `scripts/measure_envelope.py` | the validity envelope |
| `scripts/baseline_lsb.py` | the textbook scheme, measured on the same corpus |
| `scripts/uncertainty.py` | bootstrap intervals and rule-of-three bounds |
| `README.md` | layout, quickstart, and the metadata-stripping limitation |
