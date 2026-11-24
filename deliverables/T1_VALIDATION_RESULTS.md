# T1 — Multi-architecture validation results

**Status:** Returned Kaggle run ingested; fixed-cohort validation experiment complete. These are validation/development diagnostics, not TEST results and not an estimate of external generalization.

## Protocol and integrity

- Fixed adapted-ISIC2019 cohort: 1,500 TRAIN / 500 validation; manifest SHA-256 `c524a43fce2951dbd68514a94d60610a8daa4f88fd40b8b93c53ee1f03f5aa42`.
- The returned run reports `test_accessed: false`. Ingestion found matching source-image hashes, received-image hashes, operator seeds, labels, and membership against retained baseline references for all three models.
- Returned `code/src/multi_arch_classifier.py` SHA-256 matches the checked-in module: `510b94df1e79ce1d894ed9643edf3d89c78b95aed84af190633a6a167ee8d587`.
- The two augmented protocols report ImageNet initialization, 20 epochs, batch size 8 with accumulation 2, and TRAIN-only geometric/color augmentation. Checkpoint selection used validation balanced accuracy; consequently, these same-cohort operator results are descriptive validation analyses, not an independent test.
- Source archive: `google_drive/t1-results-v1.zip` (ZIP integrity checked). Ingest with `python scripts/ingest_t1_multi_arch.py --results-zip <archive>`.

## Intact validation performance

| Model | Accuracy | Balanced accuracy | MEL sensitivity |
|---|---:|---:|---:|
| DenseNet121-Base | 0.864 | 0.7440 | 0.5893 |
| DenseNet121-Aug | 0.812 | 0.7927 | 0.7679 |
| ResNet50-Aug | 0.860 | 0.7573 | 0.6250 |

Both augmented models clear the plan's validation BA criterion (>0.75) and show non-trivial MEL sensitivity. This does not imply TEST performance.

## JPEG70 accuracy–sensitivity pattern

All three models show higher accuracy but lower MEL sensitivity than their own intact validation condition:

| Model | Accuracy change | BA change (paired 95% CI) | MEL sensitivity change |
|---|---:|---:|---:|
| DenseNet121-Base | +2.80 pp | −7.01 pp [−13.04, −1.41] | −19.64 pp |
| DenseNet121-Aug | +2.40 pp | −1.77 pp [−6.80, +3.04] | −7.14 pp |
| ResNet50-Aug | +3.60 pp | −7.34 pp [−13.03, −1.87] | −21.43 pp |

Thus the accuracy–sensitivity paradox persists in this validation experiment. Its magnitude is smaller for DenseNet121-Aug than for the historical baseline, but not for ResNet50-Aug; the paired BA interval for DenseNet121-Aug includes zero. Do not generalize this architecture-specific pattern beyond the fixed validation cohort.

## EditGuard paired validation contrasts

The table below reports the `marked_intact` condition relative to each model's own `operator_without_embedding_intact` condition:

| Model | Marked BA | Δ BA (95% CI) | Marked MEL sensitivity | Δ MEL sensitivity |
|---|---:|---:|---:|---:|
| DenseNet121-Base | 0.6460 | −9.80 pp [−16.06, −3.21] | 0.3393 | −25.00 pp |
| DenseNet121-Aug | 0.7481 | −4.46 pp [−9.15, −0.11] | 0.6786 | −8.93 pp |
| ResNet50-Aug | 0.7753 | +1.79 pp [−2.22, +6.03] | 0.6429 | +1.79 pp |

The returned table also includes the required paired `embedding_given_operator` and combined `total_embedding_plus_operator` rows for intact, copy32, JPEG70, JPEG85, and Gaussian05; inspect `deliverables/tables/table_editguard_ssim_and_multi_arch.csv` for all metrics, class-stratified paired intervals, and conditions. EditGuard image-marking fidelity averaged MSE `170.9716`, per-image PSNR `29.5999 dB`, and SSIM `0.8701` over the returned marked validation images. The direction and size of the classifier contrast varies by architecture; it is not evidence that marking improves clinical classification.

## Artifacts

- `deliverables/tables/table_multi_arch_diagnostic_drift.csv` — 30 model/operator summary rows.
- `deliverables/tables/table_editguard_ssim_and_multi_arch.csv` — EditGuard fidelity and paired-condition summaries.
- `google_drive/t1-results-v1.zip` — returned Kaggle outputs, including per-image predictions and visual panels.
- `deliverables/kaggle_t1_multi_arch_validation.ipynb` — reproducible Kaggle runner.

No TEST images, labels, predictions, or outcomes were accessed in this T1 run.
