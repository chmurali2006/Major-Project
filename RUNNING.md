# Running and reproducing the project

**Current status (2026-10-19 UTC):** T1 multi-architecture classifier validation has been returned and ingested. Its scope is the fixed 1,500 TRAIN / 500 validation cohort only. No TEST pixels, labels, predictions, or outcomes were accessed in T1. See [`deliverables/T1_VALIDATION_RESULTS.md`](deliverables/T1_VALIDATION_RESULTS.md).

> **Critical boundary:** this repository contains several distinct runners and cohorts. Do not treat this guide, `PROTOCOL_V2.md`, the T1 Kaggle notebook, historical receipts, or a plan as interchangeable. The historical `isic-study-v2` run accessed 1,000 test records; its exact membership is unrecoverable from retained evidence. The later 500-image holdout is non-confirmatory development evidence, and must not be opened for more outcomes or described as untouched. A new confirmatory study requires a genuinely new, provenance-audited cohort and a frozen protocol. PH2 also has prior project use and is not a clean confirmatory external cohort.

## What is safe to run now

### Synthetic CPU demonstration

```sh
python -m pip install -r requirements.txt
python scripts/showcase.py --synthetic --out /tmp/keyswm-showcase
# Open /tmp/keyswm-showcase/index.html.
```

This demonstrates the classical RGB authentication path, not learned pixel segmentation, and synthetic examples are not medical-image performance evidence. Use `--image` only with an authorized image stored outside the repository; resizing is explicit preprocessing and is not preservation of original acquisition pixels.

### Tests and local plumbing

The project includes CPU tests and optional Torch-backed tests. Run the test suite only in an environment with the dependencies specified in `requirements-test.txt`; report exact environment and failures. Unit tests establish code-path assertions, not scientific effectiveness or model performance.

```sh
python -m pip install -r requirements-test.txt
python -m pytest -q
python scripts/preflight.py
```

Training extras are separate. Do not install or upgrade the managed Kaggle Torch/CUDA stack for a notebook execution without checking that notebook's pinned requirements and protocol.

## T1 — completed validation run

- Notebook: `deliverables/kaggle_t1_multi_arch_validation.ipynb`.
- Returned archive: `google_drive/t1-results-v1.zip` in the connected workspace; it includes visual case panels and should not be redistributed without a separate image/licensing review.
- Tables: `deliverables/tables/table_multi_arch_diagnostic_drift.csv` and `deliverables/tables/table_editguard_ssim_and_multi_arch.csv`.
- Report: `deliverables/T1_VALIDATION_RESULTS.md`.
- Ingestion command for a **new** archive/output location:

```sh
python scripts/ingest_t1_multi_arch.py --results-zip /path/to/t1-results.zip --out /path/to/new-output
```

The ingester is intentionally fail-closed and refuses to overwrite existing result tables. It checks returned predictions and integrity/protocol identity against retained validation references. Ingestion is not an independent replay from source pixels/models. Do not add TEST access or reinterpret these results as an independent test.

## Separate protocol-v2 line

`PROTOCOL_V2.md`, `notebooks/keyswm_isic2019.ipynb`, and `deliverables/keyswm_isic2019.ipynb` describe a distinct fragile RGB-HMAC / learned-localization project line. Existing instructions for its planned full multi-seed or `heldout` stages are historical plan material, not a current execution approval. A previous small TRAIN-only diagnostic and a separate incomplete real-image sanity trace exist; neither establishes complete ISIC performance. Do not point this runner at a holdout or use the old `heldout` stage on the current cohort.

Safe synthetic runner checks are permitted. For any future TRAIN/validation-only diagnostic, follow the exact runner's preflight and keep all inputs/caches outside Git. Do not restore a prior protocol checkpoint into a different protocol or study.

## Inputs, privacy, and release boundaries

- Do not put original medical-image pixels, restricted model weights, private keys, credentials, or unreviewed patient metadata in Git or public Drive shares.
- The context bundle is a documentation/source/evidence snapshot; it intentionally omits raw image inputs, model weights, credentials, and some image-bearing result archives.
- Dataset counts and hashes do not prove source authenticity, patient independence, or institutional representativeness. Lesion-disjoint splitting does not establish patient-level independence.
- Verify dataset, upstream code, checkpoint, and paper licences before public release or redistribution. The repository literature file still flags bibliography verification needs.
- A classifier output is a research probe, not a clinical decision. Integrity failure is a content mismatch, not proof of malicious intent.

## Current analysis map

| Workstream | Safe entry point | Status / evidence limit |
|---|---|---|
| T1 multi-architecture classifier impact | `deliverables/T1_VALIDATION_RESULTS.md` | Completed on TRAIN/validation only; validation-selected models; no confirmatory inference. |
| Detached integrity/localization | `deliverables/PROJECT_FULL_OVERVIEW_AND_GAPS.md` and referenced receipts | Validation receipts audited; no full original-pixel replay in this runtime. |
| Matched EditGuard | `deliverables/MATCHED_EDITGUARD_VALIDATION_RETURN_REVIEW.md` | Return structure/arithmetic/signatures checked; no source-pixel/model replay or issuer identity proof. |
| Protocol-v2 RGB-HMAC/learned localization | `PROTOCOL_V2.md` | Separate protocol; full multi-seed study and confirmatory evaluation not established. |
| PH2 | `deliverables/TEST_SPLIT_RECOVERY_DECISION.md`, project master context | Prior project use and incomplete lineage; not clean confirmatory external evidence. |

For current claims and remaining blockers, always start at [`PROJECT_CONTEXT_MASTER.md`](PROJECT_CONTEXT_MASTER.md).