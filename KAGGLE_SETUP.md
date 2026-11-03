# Kaggle submission run: attach → verify → stage → save → restore

Use **`notebooks/keyswm_isic2019.ipynb`** (standalone download also in `deliverables/`).
The embedded source is the canonical CLI implementation, not a second model.
This is a runnable research study, **not a guarantee of paper parity or clinical validity**.
Kaggle/CUDA execution must be verified on your account; development tests here use CPU.

## 1. Prepare inputs before enabling/using long GPU runs

1. Create a Kaggle notebook and import/upload the supplied `.ipynb`.
2. Use **Add Input / Add Data** (label depends on UI) to attach:
   - **ISIC 2019 Training Input:** 25,331 training JPEGs. Prefer extracted files over a ZIP; do not select only the test set, a small lesion subset, ISIC 2018, or PH2.
   - **ISIC 2019 Training Ground Truth:** a CSV with `image,MEL,NV,BCC,AK,BKL,DF,VASC,SCC` (optional `UNK`, zero for training labels).
   Both may be in one attached dataset, or separate attachments. You do not need to upload them into the source ZIP.
3. Choose a public input you are permitted to use, or create a **private Kaggle Dataset** containing your authorised official download. No Kaggle dataset slug is hardcoded or assumed correct. Search results called “ISIC 2019” can contain partial or different data: verify actual contents.
4. Choose an available **GPU accelerator** in settings. A single GPU is used; a multi-GPU selection does not automatically accelerate this code. Check your account's **current displayed quota and session limit**—neither a fixed number of free hours nor session availability is assumed.
5. Internet can stay off if dependencies are present. If imports fail, enable Internet and `INSTALL_MISSING=True` for setup. The notebook deliberately does not replace Kaggle's Torch/CUDA wheel. Restart the kernel if you changed an already-imported numerical package.

**I cannot attach inputs to your Kaggle account from Arena.** The notebook enumerates what is actually attached and audits it before training.

## 2. Configure the first saved version

In the configuration cell:

```python
STAGE = 'check'
SEED = 0
DATA = None
METADATA = None
IMAGE_ZIP = None
ALLOW_LABELLED_SUBSET = False
RESTORE_FROM = None
```

If discovery lists more than one candidate, explicitly set the actual paths shown in the input sidebar, for example:

```python
DATA = Path('/kaggle/input/<actual-attachment>/<training-image-folder>')
METADATA = Path('/kaggle/input/<actual-attachment>/<ground-truth-file>.csv')
```

These are **templates**, not existing Kaggle slugs. `DATA` is a directory searched recursively for lowercase `.jpg`, not a CSV or ZIP. If an attached archive is your only image source, set `IMAGE_ZIP` to that actual ZIP file; safe extraction and a disk-space check happen before audit. Prefer already-extracted training images to avoid repeating extraction each session.

The audit requires this profile by default:

| class | labels |
|---|---:|
| MEL | 4,522 |
| NV | 12,875 |
| BCC | 3,323 |
| AK | 867 |
| BKL | 2,624 |
| DF | 239 |
| VASC | 253 |
| SCC | 628 |
| **total** | **25,331** |

It rejects missing images, duplicate image ids, invalid one-hot values and conflicting labels; deduplicates identical label rows; writes a canonical CSV and `dataset_audit.json`. A subset is allowed **only** with `ALLOW_LABELLED_SUBSET=True` and remains explicitly labelled a subset. The GitHub mirror previously measured here has 20,455 unique labels; that exception is not silently accepted as a complete official corpus.

Counts/ids alone do not prove a mirror's identity, image resolution or freedom from patient/lesion leakage. Selected image bytes are fingerprinted by the experiment. Where lesion/patient identifiers are absent the split is image-level; do not claim otherwise.

## 3. Use Save Version without spending twice

Recommended: set the configuration, then **Save Version → Save & Run All** (or the equivalent full execution option). This executes in the saved job. Monitor its logs/status. The `check` stage trains both tiny models for wiring only, produces non-claimable receipts, and tests the same data/GPU path as the full job.

Do **not** first run a full interactive training job and then launch a second fresh Save & Run All of the same job by accident. If you already ran interactively, download the ZIP immediately; use a save-with-current-outputs option only if your UI provides it and verify it really retained files. Saving code alone is not a result backup.

After completion, open the saved version's **Output** files and verify that the result ZIP, source manifest, and `isic-runs/...` tree exist. Download the result ZIP and retain this exact notebook/source version on your local disk. A failed/interrupted child still attempts to export finished checkpoints and logs, but a platform hard shutdown can prevent finalisation. Save/checkpoint files in an unsaved interactive filesystem are not durable.

## 4. Run one full model/seed per saved version

The defaults for full stages are **2000 train / 150 validation / 1000 test, 3 epochs, width 16**. Set them before the first full job and freeze them. The two model configurations and controls share the same selected images, attack schedule and splits. Runtime, dependency versions, input hashes and source fingerprint are saved. Evidence preparation uses CPU even in a GPU-enabled session, so it still consumes session time.

| saved job | STAGE | SEED | restore input |
|---|---|---:|---|
| wiring check | `check` | 0 | none |
| first measured model | `C8` | 0 | none—do not restore tiny wiring outputs into the full study |
| paired attention ablation | `C12` | 0 | previous full-study output |
| second training seed | `C8`, then `C12` in two jobs | 1 | preceding full-study output each time |
| third training seed | `C8`, then `C12` in two jobs | 2 | preceding full-study output each time |
| held-out-family test | `heldout` | 0 | preceding full-study output |

For every subsequent job:

1. Attach the preceding **saved notebook output** using the notebook/output input option in Kaggle. If that UI is unavailable, download the result ZIP, extract it locally, upload those output files as a **private Kaggle Dataset**, then attach it.
2. Set `RESTORE_FROM` to its **whole study directory**, e.g. the actual input path ending in `isic-runs/isic2019-v4`. If you uploaded an extracted result ZIP as a dataset, the study files might instead be at the attachment root. It should contain `seed-0/`, logs, and the other completed seed folders—not just a `.pt` file.
3. Keep `STUDY_NAME`, training settings, input bytes and source version unchanged. Change only `STAGE` and `SEED` as shown above.
4. Save & Run All as a new version. The notebook copies prior read-only outputs into `/kaggle/working`, restores or skips completed work, and adds the requested job. It does **not** retrain C8 when continuing with C12.
5. Verify and download the new outputs before proceeding. Preserve all seed folders in the chain.

`C8` and `C12` are runtime selections from a frozen `C8,C12` experiment, not a mutation of the scientific configuration. `heldout` is a separate C8 experiment without T5 in training/validation; T5 remains in the test schedule. Key probes and calibration run with the measured stages.

## 5. Quota and recovery rules

- Prioritise one complete paired seed first. Finish seeds 1/2 and held-out T5 before calling the full study established. A single seed is preliminary, not three-seed evidence.
- The first tiny check must pass before committing long GPU time. It is not an accuracy target.
- Read epoch timings and current quota rather than assuming an unmeasured GPU runtime. Do not start a job near the account's remaining session limit.
- Checkpoints are saved **after completed epochs**. An interruption within an epoch repeats its unfinished work. Restore the previous outputs and rerun the same stage/seed to resume. This is not a mid-batch checkpoint implementation.
- Source/data/settings mismatch is a protective error. Do not delete `experiment.json` or edit receipts to bypass it. A new source revision, corpus, size, epoch count or width requires a new study name/output directory.
- Caches live under `/kaggle/temp` and are intentionally disposable. Evidence is rebuilt when no matching cache exists. Persisting full caches would consume storage; they are not included in result ZIPs.
- GPU determinism is best-effort with warnings for unsupported kernels, recorded in the environment receipt. Exact CPU/GPU or cross-version equality is not promised. CPU interrupted/resumed training is tested for equality.
- Restore only trusted project-generated Torch checkpoints.

## 6. Inspect the outputs for submission

Each saved output includes numerical receipts, verdict arrays, split manifests, source/data fingerprints, runtime package versions, logs, selected weights and resumable checkpoints. `summary.json` explicitly lists missing full-study jobs. “Complete” means files exist; it is **not** a blanket scientific pass.

Submission requirements:

- Quote tampered-only localisation IoU, TPR, FPR, denominators, balanced verdict accuracy, and paired C8−C0/C12−C8 differences with bootstrap intervals.
- Report all three training seeds and distinguish image-bootstrap uncertainty from seed variability.
- Preserve Carrier-B regressions, false claims, infeasible empirical abstention constraints, and rekeying/held-out failures. A confidence margin is not a calibrated posterior or population-risk guarantee.
- Disclose synthetic tamper generation, JPEG-as-tamper semantics, image-level grouping limitations and training subsampling.
- Compare to current papers only under aligned datasets, splits, attack definitions and metrics. This assembly is **not an exact verified PFF-WM reproduction**. Do not import a paper's CheXpert/LiTS headline scores into an ISIC table or promise superiority before measurement.

The notebook makes the implementation reproducible and quota-conscious; it cannot guarantee a best-in-class submission number.
