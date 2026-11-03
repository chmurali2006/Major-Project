# A Fragile Watermarking for Medical Image Tamper Detection

**B.Tech Major Project.** Keyed, training-free fragile watermarking with tamper
localisation and calibrated abstention, extended into a synthesis study that
assembles the best published answer to each sub-problem and measures the assembly
against every constituent on a protocol frozen in code.

---

## The one-paragraph version

Published systems in this area each optimise one component and report a single
aggregate, so the field cannot say **which component is carrying the result**.
This project decomposes tamper detection into eight sub-problems, takes the best
measured answer to each, assembles them, and prices every component against every
other on one split. Two components are not reproductions: a **keyed,
training-free evidence channel**, in which the mark is a function of the secret,
the block address and the block's own content, so a fabricated region cannot be
marked; and a verifier that **refuses with a cause** — INTACT, TAMPERED or
CANNOT SAY, with a reason code attached to every refusal. Underneath both sits a
computed result: an 8×8 decision grid cannot express a boundary finer than 8
pixels, so a **flawless** block classifier scores 0.809 pixel IoU on a radius-32
lesion — below the published 0.832 bar, at zero errors. The gap is architectural,
not a learning deficit.

**The deliverable is not a better number. It is an attribution study with a
frozen protocol, in which every number — including the one criterion that fails —
is traceable to a receipt.**

---

## Status

| layer | state | evidence |
|---|---|---|
| keyed protect / verify / three-way verdict | **built and measured** | receipt `isic-full-v8`, 12 970 images, clean tree |
| protocol, metrics, tamper synthesis, evidence channel | **built** | `src/`, 86 tests (78 without torch) |
| learned refinement (AE, PixelRefineNet, saliency, three-way head) | **built and unit-tested, never trained** | forward pass verified, gradients asserted, **no result** |
| the C0–C11 matrix | **designed, not run** | `src/protocol.py` |

The third row is why the matrix is labelled *designed, not run* everywhere in
this repository. Any document, figure or slide that omits that label is claiming
twelve results that do not exist.

---

## Start here

| if you want to | read |
|---|---|
| understand the project as a project — objectives, timeline, deliverables, risks, ethics | **[`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md)** |
| understand how the system works — every stage, constant and invariant | **[`project-context/ARCHITECTURE.md`](project-context/ARCHITECTURE.md)** |
| make a poster, deck or abstract | [`project-context/POSTER_CONTEXT.md`](project-context/POSTER_CONTEXT.md) |
| write the report | [`docs/REPORT_OUTLINE.md`](docs/REPORT_OUTLINE.md) |
| write the literature survey | [`docs/LITERATURE.md`](docs/LITERATURE.md) |
| check whether a number may be printed | [`project-context/facts.json`](project-context/facts.json) |
| know what can go wrong and why | [`docs/DESIGN_REVIEW.md`](docs/DESIGN_REVIEW.md) |
| run it on Kaggle | [`docs/KAGGLE_RUNBOOK.md`](docs/KAGGLE_RUNBOOK.md) |
| see the figure | [`docs/poster/architecture.pdf`](docs/poster/architecture.pdf) |

---

## Install and verify

```bash
python -m venv .venv && . .venv/bin/activate
pip install numpy scipy opencv-python-headless Pillow PyWavelets pytest
pip install torch                      # only needed for the learned half

pytest tests/ -q                       # 86 tests, no GPU, no dataset
                                       #   78 run without torch; the 8 in
                                       #   tests/test_models.py need it
python scripts/smoke_pipeline.py       # end-to-end plumbing check, synthetic data
python src/protocol.py                 # audit the frozen protocol
```

The smoke run is a plumbing check on procedural images with an untrained-scale
model. **It is not a result**, and it is labelled as such everywhere it appears.

---

## Evidence rules

Four rules this repository holds itself to. They are the reason it is worth
reading.

1. **No number without a receipt.** Every printable figure lives in
   `project-context/facts.json` with a provenance string and a status of
   `verified`, `computed`, `published`, `planned`, `unverified` or `forbidden`.
2. **No ratio without its denominator.** `12 969 / 12 970`, not `99.99 %`.
3. **No IoU without its granularity and its ceiling.** `0.9936 block-level` and
   `0.809 at radius 32` are the same sentence.
4. **No suppressed failure.** 2 of 300 images produce a false claim at JPEG Q100,
   exceeding this project's own 0.5 % bound. It appears at full size on the
   poster, in the report, and in `facts.json` as M-09.

A protocol that is imported cannot drift — the same reasoning that put the
protocol in `src/protocol.py` rather than in a document applies to the numbers.

---

## Layout

```
src/
  protocol.py      frozen protocol: corpora, splits, families, metrics, bars, C0-C11, gates
  metrics.py       IoU/Dice/F1/detection, block_ceiling, selective_risk, aurc, stratified_iou
  tamper.py        8 families; ground-truth masks measured by differencing, never declared
  evidence.py      the keyed channel; read_rich -> 10 channels in a fixed order
  degradation.py   the four scalars the refiner conditions on
  models.py        OneClassAE, RefineNet, FusionNet, SaliencyNet, PixelRefineNet, total_loss
  isic_meta.py     layout detection, lesion grouping, stratification

notebooks/         keyswm_isic2019.ipynb - generated from src/, never hand-written
scripts/           build_architecture.py, build_notebook.py, validate_notebook.py, smoke_pipeline.py
tests/             86 tests
docs/              PROJECT_PLAN, REPORT_OUTLINE, LITERATURE, DESIGN_REVIEW, SYNTHESIS_STUDY,
                   KAGGLE_RUNBOOK, poster/
project-context/   ARCHITECTURE, POSTER_CONTEXT, facts.json
```

---

## Three bugs the tests caught

Presented because a report claiming no bugs were found is claiming the tests
found nothing.

**Block-locality inversion.** `reshape(ny,k,nx,k) -> (ny,nx,k*k)` collapses the
axes in the wrong order and scatters one block's coefficients across several
blocks. It round-trips perfectly, so an inverse-only test passes while block
locality is destroyed. Caught by asserting that perturbing one block changes
exactly one block's coefficients.

**The vacuous locality test.** The first version perturbed a block by a constant
offset. A uniform offset lands entirely in `LL2` and never touches a detail
coefficient — correct behaviour that would have made the test meaningless. The
test now uses a pattern, and a second test asserts the constant-offset property
directly.

**Heads that received no gradient.** The v2 pixel-only loss left the block head
and the classifier with `grad=None` on every parameter. They would have looked
trained and been random. Found by a test that asserts every parameter receives a
gradient through `total_loss`, not by inspection.

---

## Scope

**ISIC 2019** is the corpus for the learned phase — free on Kaggle, no approval,
and one of the three corpora the reference system evaluates on, so the comparison
ground is shared.

**LiTS and CheXpert are deferred by decision.** The published localisation bar
(0.832) is measured on LiTS and the published detection figure (97.6 %) on
CheXpert, so **no number from this phase can be placed in either of their
tables**, and none is claimed. The result that needs no external corpus is C0
versus C8 on the same split.

---

## Ethics

Public research corpus only; no identifiable patient data; no diagnostic claim
anywhere; the saliency head is a localisation aid and is never validated against
pathology annotation, so it must not be described as clinical saliency. The
released notebook contains its key — required for reproducibility, and disclosed
as voiding the security claim for that artefact specifically. Full statement in
`docs/PROJECT_PLAN.md` §9.

---

## Reference figures

Quoted from the source papers, with their corpora, and **not** claimed as
comparisons:

| | PFF-WM (Khaldi et al., 2026) |
|---|---|
| detection | 97.6 %, AUC 0.989, 44 ms, 15.1 M — **CheXpert** |
| localisation | IoU 0.832, pixel acc 98.1, F1 90.4 — **LiTS, synthetic lesion insertion** |
| ablation | RefineNet +6.2 IoU · attention +3.1 · dual carrier +0.067 |

That last row is the argument for the study design: a paper that prices its own
components is telling you the field's problem is attribution, not accuracy.
