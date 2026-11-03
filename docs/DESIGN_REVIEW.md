> **Historical / pre-audit material.** This file is not evidence for the current audited recipe. See root `VERIFICATION.md` and use fresh measured receipts for submission. In particular, any-overlap block IoU is not a universal ceiling.

# Design review

**Purpose.** Before more code is written, establish which parts of the design can
lose points against published work, with a measurement for each. No claim in
this document rests on an assumption; where something could not be measured, it
is listed as an open question rather than filled in.

Date 2026-10-24. Supersedes the architecture section of `SYNTHESIS_STUDY.md`.

---

## 1. Method

Three checks, not a reading:

1. **Geometric.** For the published metric, compute the best number the
   architecture can reach *if everything worked perfectly*. If that bound is
   below the published bar, no amount of training closes the gap.
2. **Empirical.** Measure the alternatives where a choice was made on judgement.
3. **Gradient.** Assert that every parameter receives a gradient, so no head is
   silently untrained.

---

## 2. Flaws found, ranked by measured cost

### F1 — CRITICAL: the block grid caps pixel IoU below the published bar

The v1 refiner outputs a 64×64 map: one decision per 8×8 block, with the image
downsampled to 64×64 on the way in. So the finest boundary it can express is 8
pixels.

Compute what a **perfect** block classifier scores against an exact pixel mask:

| lesion radius | area | best possible pixel IoU |
|---|---|---|
| 8 | 0.08% | 0.513 |
| 16 | 0.30% | 0.692 |
| 24 | 0.68% | 0.757 |
| **32** | **1.22%** | **0.809** |
| 48 | 2.75% | 0.854 |
| 96 | 11.0% | 0.930 |

The published localisation bar is **0.832**.

**At a lesion radius of 32 pixels, a flawless block-granular system scores
0.809 — below the bar, with zero errors.** The gap is architectural, not a
learning deficit. No amount of training, data or capacity fixes it.

This also explains the published ablation, which I previously mis-read. PFF-WM's
raw autoencoder error map scores 0.770 and their RefineNet scores 0.832. A
block-level map of a ~24–32 px lesion lands at 0.757–0.809; a pixel-resolution
refinement of the same evidence exceeds it. Their +6.2 IoU is not "a better
network" — it is **breaking the quantisation floor by reading the image at full
resolution**.

**Fix.** `PixelRefineNet`: encoder 512→256→128→64, decoder back to 512, skips,
block evidence injected upsampled and by nearest so block edges stay crisp. Two
heads: `pixel_logits` at 512×512 (localisation), `block_logits` at 64×64
(verdict and abstention, which are block-granular by nature). A consistency term
ties them. Implemented and tested.

### F2 — CRITICAL: a claimed component was passed as zeros

Row 1 of the table is the multi-scale attention head. In the notebook the
saliency tensor was literally `torch.zeros(...)` at both call sites. The
configuration was still labelled "full synthesis".

That is a false claim in shipped code, and it is the kind that ends a viva
badly, because it is two greps away from being found.

**Fix.** `SaliencyNet` — parallel Conv 3×3/5×5/7×7, fused, sigmoid. Tested to be
non-constant. **Caveat that must travel with it:** it is trained end-to-end from
the localisation loss, so it learns *where errors matter for localisation*. It is
not validated against pathology annotations and must never be described as a
clinical saliency model.

### F3 — CRITICAL: heads that received no gradient

The v2 pixel-only loss left `block_head` and `cls_head` with `grad=None` on every
parameter. They would have looked trained and been random. Found by a test, not
by inspection.

**Fix.** `total_loss()` is now the single training objective: block mask + pixel
mask + consistency + classification. It returns the four components and the
tests assert each is non-zero and that every parameter has a gradient.

### F4 — IMPORTANT: the IoU mean mixes incompatible scales

The eight families include 8-pixel copy-move (one block out of 4096) and
64-pixel paste. In the smoke run, per-family IoU ranged from **0.069 (T1) to
0.372 (T3)** — a spread driven almost entirely by target size.

A mean over that mixture is dominated by whichever families are most numerous
and is **not comparable to a paper reporting lesion insertion**, where targets
are hundreds of pixels.

**Fix.** `stratified_iou()` reports IoU per tampered-area bucket, each with `n`,
and — when pixel truth is present — the perfect-block ceiling for that bucket.
A shortfall is then attributable to architecture rather than blamed on the model.

### F5 — IMPORTANT: 58 of 60 observations thrown away

v1 fed the autoencoder two scalars per block. Measured linear separability of
tampered vs untouched blocks, held-out:

| input | held-out AUC |
|---|---|
| (corr, survival) — v1 | 0.9901 |
| 10 channels incl. per-band and peak | 0.9953 |

A real but **small** gain. Stated precisely because the temptation is to sell it
as large: the keyed evidence is already highly separable, and this fix is worth
roughly half a point of AUC, not five. `peak |residual|` alone scores AUC 0.904
and was not being used at all.

**Fix.** `evidence.read_rich()` → 10 channels; `RICH_CHANNELS` fixes the order.

### F6 — IMPORTANT: the dual watermark was replaced by heuristics

PFF-WM's own ablation prices the semi-robust second carrier at **AUC 0.989 →
0.952** and **IoU 0.832 → 0.765** when removed. In the classical phase the
semi-robust carrier was disabled (A-032) because a conflict-only second decision
rule cannot produce a TAMPERED verdict.

That reasoning does not transfer. In the synthesis design the second stream is
**not a second decision rule** — it is an *input feature* that survives
compression, so it separates "this block lost its mark because of JPEG" from
"because someone edited it". Its removal cost the source paper more than the
attention head did.

We currently substitute four hand-built degradation scalars.

**Status: not fixed. Highest remaining design risk.** Recommendation is to add a
semi-robust DCT stream before the headline run, because a hand-built JPEG
quality estimate is a strictly weaker signal than a watermark designed to
survive JPEG.

### F7 — MODERATE: capacity is not matched

| model | params |
|---|---|
| v1 FusionNet | 0.96 M |
| PixelRefineNet width 32 | 1.54 M |
| width 96 | 13.74 M |
| **PFF-WM full** | **15.1 M** |

If we underperform while running a 15× smaller model, "we were smaller" is a
weak excuse and the panel will hear it as one. Make width a config and report
the headline at matched capacity.

### F8 — MODERATE: the detection number needs its definition attached

`detection_accuracy` counts an image as detected if **any** block is flagged.
That is permissive, and it is not obviously the same definition the published
figure uses. Our benign set is also only JPEG/noise/resize.

**Fix.** State the definition in the receipt. Without it the number is not
comparable and should not be tabulated.

### F9 — MODERATE: 512² training is 5.5× the cost of 256²

Measured forward pass, batch 4, this CPU:

| resolution | forward | estimated T4 train step |
|---|---|---|
| 256² | 529 ms | ~88 ms |
| 512² | 2 882 ms | ~480 ms |

At 512², 9 000 images and batch 16 is ~562 steps/epoch ≈ 4.5 min/epoch. Sixty
epochs is **4.5 GPU-h for one configuration**; the full C0–C11 matrix does not
fit in one week of the free tier.

**Fix.** Two-stage: train at 256², then fine-tune and evaluate at 512². A
fully-convolutional net transfers across resolution; the difference must be
measured and reported, not assumed to be zero.

### F10 — MINOR: the released notebook publishes the key

Required for reproducibility. It also voids the security claim for that
artifact — anyone with the notebook can forge. C9/C10 measure the property
(wrong key → noise) independently of which key is used. Say this before someone
else does.

---

## 3. The corrected architecture

```
image 512² ──► SaliencyNet (Conv 3/5/7) ──────────────► A  (1×512×512)
            │
            ├──► keyed evidence (10 ch @ 64×64) ───────► E
            ├──► degradation estimates (4) ────────────► D
            │
            └──► PixelRefineNet
                   512 →256→128→ 64   encoder
                    64→128→256→512   decoder with skips
                    inputs: image, A, D broadcast, E upsampled (nearest)
                       │
              ┌────────┴─────────┐
              ▼                  ▼
      pixel_logits 512²     block_logits 64² ──► clamp → verdict (3-way)
      (localisation)         (abstention)
```

Losses: block mask + pixel mask + consistency + classification, all in
`models.total_loss`.

---

## 4. What can honestly be claimed

**Can be claimed, once measured:**
- C0 vs C8 on the same split — the contribution of the learned half.
- Our block-level IoU at a stated tamper-area bucket.
- Pixel IoU **with its ceiling printed beside it**.
- Params and latency at a stated width and resolution.

**Cannot be claimed yet, and this is the important list:**

| claim | blocked by |
|---|---|
| "we beat 0.832 IoU" | 0.832 is LiTS + lesion insertion. We have not run LiTS. |
| "we beat 97.6% detection" | their primary corpus is CheXpert; ours is ISIC. Different family mix. |
| "equal or better at lower cost" | our capacity is not yet matched (F7). |
| "the key prevents forgery" | true of the design, **false of the released notebook** (F10). |

---

## 5. Open questions — do not assume answers

These determine whether a head-to-head comparison is valid at all. Each must be
settled from the paper's full text or from their code before any claim is made:

1. **Is 0.832 a mean over images or a pooled pixel ratio?** These differ
   substantially when target sizes vary.
2. **What is the lesion-size distribution** in their synthetic-tumour protocol?
   Given §2 F1, a comparison at radius 24 and one at radius 64 are not the same
   experiment.
3. **Is their localisation ground truth the tumour mask or the paste
   rectangle?** If the rectangle includes unchanged pixels, their ceiling is
   lower than ours and the numbers are not comparable in either direction.
4. **Is their "detection accuracy" per-image or per-region**, and on what
   class balance?
5. **Are their benign conditions applied before or after embedding?**

Until 1–5 are answered, the only defensible statement about the published bar
is: *"we reproduce the protocol; our number on their corpus and tamper family
will be reported alongside theirs, with the ceiling."*

---

## 6. Verification performed

```
pytest tests/ -q          77 passed
```

New or changed since the last commit:

| area | test |
|---|---|
| pixel architecture | output at 512², 64², 3-class; parametrised over width and resolution |
| saliency | non-constant output (catches the zeros regression) |
| gradients | every parameter receives a gradient through `total_loss` |
| consistency | zero when heads agree, positive when they disagree |
| ceiling | block-ceiling bound reproduced at r=8/16/32/96/128/160 |
| stratification | ceiling reported only with real pixel truth |
| pixel truth | `measured_pixel_mask` is exact, not block-rounded |
| evidence | `read_rich` returns 10 channels in a fixed order |

## 7. What is still not proven

The architecture now *can* exceed the block ceiling. It has not been shown to.
That requires the LiTS run and an answer to open question 2. Until then the
correct posture is: the design no longer contains a known structural ceiling
below the bar, which is a weaker and honest claim than "we will beat it".
