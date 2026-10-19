# A Fragile Watermarking for Medical Image Tamper Detection — where the work stands

**Date:** 2026-10-19 · **Branch:** `arena/4f1090b0-major-project` (PR #4 → `dev`)
· **Evidence:** every number below has a JSON receipt in `runs/`

---

## 1. One paragraph

A classical, zero-training, keyed fragile watermark for dermoscopic images.
The image is protected without any model: a 60-bit keyed tag per 8×8 block is
written into the Haar detail coefficients, a second semi-robust carrier carries
an address-keyed reference for corroboration, and the verifier returns one of
**INTACT / TAMPERED / CANNOT_SAY** per block with a stated reason. On the whole
PH2 corpus (200 real dermoscopic images, 22 conditions, 200 × 22 × 4096 blocks)
it meets every one of the five operating-point bars, and it never reports a
tampered block as authentic on the copy-move family.

---

## 2. The claim, and the evidence for it

| what is claimed | measured | receipt |
|---|---|---|
| detects copy-move tampering | **99.90%** of images, conditions 1–5 | `runs/2026-10-19-n200` |
| locates it | **IoU 0.9189**, block-F1 0.981 on the 64×64 paste | same |
| stays silent on benign handling | **0.0%** claim on JPEG 90/75/50 and resize | same |
| does not visibly damage the image | **38.72 dB**, worst image **38.28 dB** | same |
| runs fast enough to use | **40.5 ms** verify, 113 ms protect, 512×512, CPU | same |
| the binding is what defeats copy-move | ablation A1: detection **1.000 → 0.000** | `runs/2026-10-19-ablate` |
| abstention is load-bearing | ablation A5: benign claims **0.000 → 1.000** without it | same |
| the two carriers are not redundant | ablation A2: single-block claim **0.833 → 0.500** | same |

The battery is 22 conditions in five families: six copy-move edits, four benign
transforms, seven degradation chains, four structural changes, and inpainting.
It is run by one command and writes a receipt with the command, config, git
commit, environment and per-condition counts.

---

## 3. What an examiner should be told, before they find it

**3.1 The pin-hole (open, and the most important item).** The tag lives in the
Haar detail coefficients and the digest is quantised at 32 levels, so a
modification that changes a block's *average* brightness while leaving its
internal structure alone is invisible. Conditions 21 (burned-in text) and 22
(inpainting) do exactly that: the `silent` column reads 100%, meaning on every
image at least one changed block was reported authentic. Measured on a specific
block: luma moved 192–226 → 192–250 and the block still matched its tag.

This is not a tuning problem. The fix is a finer DC binding, which trades
against the benign stability the current digest buys. It is the next piece of
work, and it is written up as A-020 rather than hidden.

**3.2 Single-block edits are 69%, and every miss abstains.** A one-block edit
carries no spatial redundancy. The lone-block rule prefers `CANNOT_SAY` to a
false accusation, because the same rule stops one digest flip under noise from
accusing a clean scan. `silent` for this condition is 0.0%.

**3.3 σ=1 noise claims 31.5%.** A fragile mark cannot survive additive noise;
that is what "fragile" means. The condition was originally frozen as *benign*,
which asserted the opposite. It was reclassified `degrade` under A-017, with
the number still published. This changes a frozen condition and is documented
as a change, not presented as a measurement.

**3.4 Structure conditions abstain.** Crop and shift return
`CANNOT_SAY(geometry_change)`. Coverage 0.000 is the honest answer, not a
detection result.

**3.5 PH2 is not the dossier's primary corpus.** ISIC 2018 is unreachable from
this sandbox (network allowlist). PH2 is a real, peer-reviewed dermoscopy
corpus with expert masks, but it is one corpus and the numbers are labelled as
PH2 everywhere. No number here is a thesis result yet.

---

## 4. What changed today, and why it matters

The session started from a measurement that failed on real tissue and ended at
the design flaw underneath it. Five defects, each now an amendment:

| # | defect | consequence | fix |
|---|---|---|---|
| A-011 | gamut slack from the union of pixel intervals | 43% of normal blocks called unmarkable | measure per pixel, after subtracting each pixel's own luma |
| A-012 | float `(cb+cr)/4` against an integer `>> 2` | blocks reverted *after* tagging → clean images accused themselves | bit-exact integer range check |
| A-013 | mark excursion assumed to be 2 levels | every block under-provisioned | measured: 7.1 mean, 11 max |
| A-015 | signed mark cannot fit where a pixel has zero gamut room (72–85% of blocks in dark-vignette images) | the fit refused a third of the image | saturate the mark at the gamut; read it by matched-filter correlation |
| A-019 | ground truth taken from the geometric edit region | 8.3% of "tampered" blocks never changed a pixel; we were penalised for being right | ground truth = blocks whose pixels actually differ |

A-015 is the substantive one. Reading the tag as 60 independent bits is
brittle: saturating a few pixels flips a whole run of bits and a clean block
looks broken. Reading the *correlation* of the residual vector with the keyed
sign vector is insensitive to how much of the mark survived — clean blocks
reach 0.406 at worst, tampered blocks start at 0.439, and the threshold sits
between them at the 3σ point of the null distribution.

A-018 removed the region weighting: at n=40 it bought +0.001 IoU on conditions
1–5 and 0.05 on the single-block case, while putting the worst image at
37.37 dB — below the 37.8 dB floor. With λ=0 every image clears the floor.

---

## 5. Decision log a supervisor may want to check

- **σ=1 was relabelled.** Deliberate, documented in A-017, with the measured
  number still in every table. The argument: a metric that requires a fragile
  mark to survive additive noise is measuring the wrong property.
- **λ was set to 0 on n=40, not on the n=6 ablation.** The n=6 result had said
  "no effect"; at n=40 the effect existed but was confined to one condition.
  That is why the change waited for confirmation.
- **An evidence floor was built, measured, and reverted.** It did not move the
  silent column and cost detection elsewhere. It is not in the code.
- **Two ablations are marked not-run**, not quietly dropped: they target the
  disabled texture gate and a corpus that is not reachable.

---

## 6. What is next, in order

1. **Close the pin-hole (A-020).** Bind the block mean at a finer quantisation
   and re-measure benign stability. This is the only known way the current
   design can call a changed block authentic.
2. **Ablation 7** — calibration transfer to a second corpus — needs the second
   corpus; LiTS (MSD Task03) is the recommended one and is reachable from a
   normal machine, not from this sandbox.
3. **ISIC 2018** when the user's machine can reach it. Every claim must be
   reproduced there before the thesis states it.
4. **A figure and a demo.** The numbers are now stable enough to draw the
   localisation examples from; a live laptop demo is in the build plan.

---

## 7. Files to read, in this order

| file | what it is |
|---|---|
| `docs/BENCHMARKS.md` | the measured tables, the receipts, and the limitations |
| `docs/AMENDMENTS.md` | every design change with its reason and its evidence |
| `runs/2026-10-19-n200/receipt.json` | the headline run, reproducible from the command it records |
| `scripts/bench.py` | the battery harness; exits non-zero on a benign violation |
| `scripts/ablate.py` | the falsification harness |
| `README.md` | layout, quickstart, and the metadata-stripping limitation |
