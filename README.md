# A Fragile Watermarking for Medical Image Tamper Detection

**B.Tech Major Project.** Keyed, training-free fragile watermarking with tamper
localisation and calibrated abstention, extended into a synthesis study that
assembles the best published answer to each sub-problem and measures the assembly
against every constituent on a protocol frozen in code.

## Run this project (current entrypoints)

**Kaggle: [KAGGLE_SETUP.md](KAGGLE_SETUP.md). Local: [RUNNING.md](RUNNING.md). Start there** for local GPU/CPU or Kaggle execution, persistent
outputs, exact commands, interruption recovery and limitations.

- Local: `scripts/run_suite.py` (same pipeline used by Kaggle).
- Kaggle: `notebooks/keyswm_isic2019.ipynb`, generated from the portable source ZIP.
- Checks: `python scripts/preflight.py`, then `python -m pytest -q`.
- Downloads: `deliverables/keyswm-project.zip`; no dataset pixels or credentials.
- Resume: completed-epoch model/optimizer/RNG checkpoints plus immutable source/data/settings checks.

Use Kaggle GPU if you do not have a usable local NVIDIA GPU. Save/download outputs;
interactive session storage alone is not a durable backup. GPU execution is not
validated in the Arena CPU environment. Historical figures below are **not** new
portable-study results; use the current run's receipts and split manifest.

---

## The project

This is an ISIC 2019 assembly/ablation study of keyed watermark evidence,
authentic-only reconstruction, pixel-level localisation and validation-fitted
abstention. Main and attention-enhanced models are compared to classical controls
on paired images. Reconstruction is frozen after intact-TRAIN pretraining; the
image classifier is binary, not a trained unknown class. Abstention is a separate
empirical rule with measured risk/coverage, not a population guarantee.

**The current pipeline is not an exact verified reproduction of a reference paper,
a clinically validated tool, or a cryptographically proven authentication system.**
Benchmark keys are public constants for reproducibility, not production secrets.
Full scientific results must come from the corrected recipe; earlier receipts and
figures cannot be promoted into new results. See [VERIFICATION.md](VERIFICATION.md).

---

## Status

| layer | current implementation state | evidence |
|---|---|---|
| keyed dual carrier, tamper synthesis and learned models | implemented | `src/`, automated tests |
| C8/C12 attention ablation and count controls | runnable; no claim that Carrier B improves results | `scripts/run_isic_study.py`, preserved numerical receipts under `results/` |
| seeded suite, abstention, key probes, held-out T5 and paired bootstrap | implemented; full multi-seed measurements remain to be completed | `scripts/run_suite.py` |
| portable execution, persistence and epoch resume | CPU-tested; Kaggle/CUDA verification required | `RUNNING.md`, `tests/test_persistence.py` |

Do not infer completion of experiments from completion of implementation.
The legacy notebook implementation has been replaced with the canonical CLI source.

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
