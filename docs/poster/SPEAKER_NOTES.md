# Poster guide — what to say, and what to refuse to say

**Context for generating anything from this project:**
`project-context/POSTER_CONTEXT.md` and `project-context/facts.json`.

**One figure:** `docs/poster/architecture.png` (200 dpi) and
`docs/poster/architecture.pdf` (vector — print this). `architecture.svg` is the
editable source.

The figure is drawn as a paper figure, not an infographic: monochrome, hairline
rules, square corners, function names in monospace, and a caption at the foot
that states the limitations. The only colour is the blue used for the learned
refinement, which does not exist yet — so "what is built" and "what is planned"
are distinguishable at a glance without any decorative styling.

Three columns, in execution order: **PROTECT** (once, at acquisition),
**VERIFY** (every check), **LEARNED REFINEMENT** (not built). Under each column
header is the real entry point: `pipeline.protect()`, `pipeline.verify()`,
`src/models.py`.

Every block carries three things a panel can check: what it does, the real call
site in monospace, and the real constants along the foot.

---

## The 30-second version

> "We built a keyed fragile watermark for dermoscopic images. It needs no
> training, it localises tampering to an 8×8 block, and it can refuse to answer
> when the file has just been handled normally. On 2,594 ISIC 2018 images it
> detects tampering at 99.99% with zero false claims on benign files. What we
> are building now is the learned refinement — and the reason is one specific
> measurement, which is the third band of this poster."

Then stop. Let them point.

---

## Reading the poster

### PROTECT and VERIFY — the established system

The only band with numbers, because it is the only band with receipts.

| number | where it comes from |
|---|---|
| 99.99% detection | 12,969 of 12,970 tampered conditions |
| 0.9936 IoU | block level against measured ground truth |
| 0.00% benign false claims | 0 of 12,970 benign |
| 40.47 dB PSNR | mean over the run |
| 58.6 ms verify | isolated run, target laptop |

Say: *"every one of these is read from a receipt committed on `dev` at `a794cef`,
with `code_dirty: false`."* That single sentence is worth more than the numbers,
because it means someone else can rerun it.

The five-step chain is the mechanism. If asked **"how do you detect tampering
without the original image?"**, the answer is the tag binder box: the tag is a
function of the key, the block's address, and the block's own content. The
verifier recomputes what the tag *should* be and compares. A pasted block carries
the tag for its old address; an edited block carries the tag for its old content.
Either way it disagrees with itself.

### LEARNED REFINEMENT — grey, dashed, not built

The honest framing: *"this is written, tested, and not yet trained on real data."*

The one thing to land here is the **ceiling argument** in the PixelRefineNet box:

> "An 8×8 verdict grid cannot express a boundary finer than 8 pixels. We
> computed what a *perfect* block classifier scores against an exact pixel mask:
> on a lesion of radius 32 — about 1% of the frame — it tops out at 0.809 pixel
> IoU. The published bar is 0.832. So a flawless block system is below the bar,
> and no amount of training fixes that. The published ablation's +6.2 IoU is not
> a better network; it is reading the image at full resolution."

That is the single strongest thing on this poster, because it is a *derivation*,
not a result, and it explains someone else's numbers.

### The comparison — twelve configurations

Twelve runs, each isolating one component. C8 is the full synthesis. C9 removes
the key, C10 re-keys, C11 holds out a tamper family.

Say: *"the protocol is frozen before the first training run, so the number we
report is not the best of many tries."*

### The measured table and the caption

This box is deliberate. Point at it and say:

> "I would rather tell you what we cannot claim than have you find it. Our pixel
> IoU is not comparable to 0.832, because that was measured on LiTS and we are
> running ISIC. Our detection is not comparable to 97.6%, because that was
> CheXpert. And one of our own criteria fails: JPEG Q100 produces 2 false claims
> in 300, which is 0.67%, above our own 0.5% bar."

Panels remember the person who volunteered the weakness.

---

## Five questions, with answers

**"What's new here?"**
> "Not the embedding — QIM in Haar details is classical and I say so. New is
> three things: a keyed tag that binds address and content so a forgery cannot be
> constructed; a three-way verdict that can refuse with a named reason; and a
> measured ceiling argument that predicts where a block-granular system must
> lose to a pixel-granular one."

**"Why not just hash the image?"**
> "We implemented that as a baseline. It localises perfectly and accuses 100% of
> legitimately re-saved files, because a hash is destroyed by a JPEG re-save
> exactly as much as by an edit. The whole engineering problem is telling those
> two apart."

**"Why is detection 99.99% but IoU only 0.99?"**
> "Different questions. Detection asks whether anything is wrong. IoU asks
> whether we drew the boundary in the right place, and it is bounded by the 8×8
> grid."

**"Isn't this just the PFF-WM paper?"**
> "We implemented its embedder, and we say so. Its system is five modules and we
> built one. Bands 02 and 03 are the other four, plus two things it does not have
> — the key and the abstention."

**"When will you have the learned numbers?"**
> "Not at this review, and I would rather say that than show a number from a
> half-trained model. The protocol is frozen and the notebook is ready; the runs
> are what remain."

---

## What NOT to say

| don't | why |
|---|---|
| "we beat state of the art" | we have not run their corpora. It is checkable and it is false. |
| "zero-training" as the headline | it is a property, not an advantage to a DL-oriented panel. It is the *control*, not the pitch. |
| "99.99% accurate" without "detection" | the IoU is 0.9936 and the two get conflated in a hurry. |
| "the deep learning part works" | it is written and tested, not trained. Band 02 says so. |
| "there are no flaws" | there is a disclosed failing criterion. Claiming none while one is printed is the worst possible position. |

---

## If the poster must be reproduced

```bash
python3 scripts/build_poster.py     # needs matplotlib; writes all three files
```
The SVG declares itself as 420 × 594 mm, so a print dialog set to A2 will not
distort it. It is vector, so it also prints cleanly at A1 and A0.
