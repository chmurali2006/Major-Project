# Kaggle handoff: validation return audited; current holdout is non-confirmatory

## 1. Original images (do not substitute or re-split)

The fixed 2,500-image cohort was drawn from the official ISIC 2019 **training** archive. Its later 500-image internal holdout is lesion-disjoint per its cohort receipt, but an earlier ISIC-study-v2 run evaluated 1,000 test images and their IDs are unrecoverable; overlap is unknown. By decision, the later holdout is non-confirmatory development evidence and must not be opened for further outcome analysis or called an untouched TEST. The official ISIC page lists 25,331 JPEG training images under CC BY-NC and provides the archive and CSVs [official ISIC dataset page](https://challenge.isic-archive.com/data/).

- [Official training images ZIP — 9.1 GB](https://isic-archive.s3.amazonaws.com/challenges/2019/ISIC_2019_Training_Input.zip)
- [Official training labels CSV](https://isic-archive.s3.amazonaws.com/challenges/2019/ISIC_2019_Training_GroundTruth.csv)
- [Official training metadata CSV](https://isic-archive.s3.amazonaws.com/challenges/2019/ISIC_2019_Training_Metadata.csv)
- Alternative Kaggle hosted data source: [ISIC 2019 / Skin Lesion Images for Melanoma Classification](https://www.kaggle.com/datasets/andrewmvd/isic-2019) (25,331 images, published under CC BY-NC 4.0) [Kaggle listing](https://www.kaggle.com/datasets/andrewmvd/isic-2019).

Use the exact source IDs selected in the supplied frozen cohort manifest. Do **not** use the official challenge TEST images as substitutes; do not download a different crop, resized copy, or 2020 release. If the Kaggle source is not byte/ID-compatible, preflight will stop before inference.

## 2. Required frozen models/files

Upload these as **private Kaggle datasets** and attach them to the notebook. The updated notebook automatically accepts either the original classifier results ZIP OR a Kaggle input folder containing `best.pt`, `summary.json`, and `protocol.json`; it also finds either `clean.pth` or `clean (1).pth` by its verified MD5.

- [Reviewed adapted-classifier results ZIP](https://drive.google.com/file/d/1wT9x3wyW5UfSEnIeTFjXVFxLx12DbDrB/view) — alternatively use your `classifier-checkpoint` Kaggle dataset containing the listed files. Expected checkpoint SHA256: `38d52ca825472cb525c4c2745f9f7e2e047ddcbc34a6fe6cdcbfbdc0786ba57e`.
- [Official EditGuard clean.pth checkpoint](https://drive.google.com/file/d/1w4e1gpdInAv7Lj_NQ7EGgmMuInyfUYgi/view) — your Kaggle dataset filename `clean (1).pth` is accepted. Expected MD5: `fd8c6987d67071d3e629133499b44765`. Your Kaggle dataset names `classifier-checkpoint`, `editguard-checkpoint`, and `Skin Lesion Images for Melanoma Classification` are fine; the image folder is discovered recursively.
- [Corrected matched EditGuard + frozen DenseNet notebook v3](https://drive.google.com/file/d/1HzpwoRnmZbCH5EPIs8dMcoiMispTGGM-/view) — detects the classifier folder and either `clean.pth` or `clean (1).pth`. Use this latest file for any new run; do not start a duplicate while an existing run is active.

Use an authorised Kaggle GPU, enable Internet for the pinned public EditGuard source/dependencies, and ensure enough scratch storage for the 2,500 prepared PNGs and result package. The notebook verifies cohort/checkpoint identities and refuses to access the held-out TEST during validation. It performs **validation only** and does not retrain or tune the classifier.

## 3. Run validation first

1. In Kaggle, create a private notebook and import/download **`matched_editguard_validation_v3.ipynb`**. Confirm its first markdown cell says it accepts folder inputs; do not use an older `v1` copy.
2. Attach the original ISIC2019 training-images dataset, the private classifier-results dataset, and the private EditGuard checkpoint dataset.
3. Select a GPU accelerator and turn Internet on. Use a fresh Kaggle session/output directories; do not reuse a partial run.
4. Run cells in order. If the notebook preflight reports missing/ambiguous inputs, set `IMAGE_ROOT`, `TRAINING_ZIP`, or `EDITGUARD_CHECKPOINT` explicitly; do not bypass hash checks.
5. Wait for the final assertion that all 500 validation images, 10,000 localization rows and 5,000 paired diagnostic rows completed. A nonzero/unfinished run is not evidence.
6. Download the full results ZIP if available. Otherwise download **every** `matched-editguard-validation-v1-results-partNNN.bin` part, preserve filenames/order, and upload all parts into one Drive folder. Send the folder link/IDs here. The original pixels and model weights are excluded from results.
7. We will combine/audit the return against the sent notebook, hashes, 500×10×2 maps and paired probabilities before interpreting it.

Do not rerun to improve a poor outcome; if a technical failure occurs before outcome inspection, preserve logs and the exact protocol for a documented recovery decision.

## 4. Test-split decision — current cohort is closed

`FREEZE_PROTOCOL.md` is superseded for the current 500-image cohort. The historical ISIC-study-v2 test split was evaluated, but its image IDs cannot be recovered from the retained receipts/archive. The later cohort’s overlap status is unknown. Do not evaluate, tune, or inspect the later 500-image holdout for confirmatory claims; describe it only as non-confirmatory development evidence. See `deliverables/TEST_SPLIT_RECOVERY_DECISION.md`.

If a confirmatory estimate is required, plan a **new** provenance-audited cohort and predeclare membership, lesion/patient grouping limits, endpoints, and code/checkpoint hashes before any outcome access. Do not call the new cohort patient-independent unless verified patient linkage supports that claim.

## 5. If Kaggle shows “Queued”

This notebook contains no queue/wait loop. Its first executed cell checks whether CUDA is available; image preparation and model inference happen only in later cells. If Kaggle says the **session/kernel is queued before any cell starts**, that is Kaggle waiting for an accelerator/runtime slot, not a loop in the notebook. I cannot see your Kaggle session from Drive; the shared Drive currently has the notebook and guide but no execution log/result.

- Don’t press Run All repeatedly or create multiple copies/sessions; that can leave duplicate jobs competing for quota.
- Confirm the notebook accelerator is set to GPU and Internet is on. Close other active Kaggle GPU sessions and check Kaggle’s accelerator quota/availability notice. If it offers another GPU type, selecting it is fine; this notebook uses one GPU.
- Wait for the kernel/session to start. Once it starts, cell output should progress normally; image preparation itself can take time.
- Do not switch to CPU: the notebook intentionally fails closed without CUDA and a full 500-image EditGuard + DenseNet run on CPU is not a practical substitute.
- If a cell has already started and is stuck, report the cell number, exact status text, and last visible output/error (or share a screenshot). That distinguishes accelerator queueing from a pip install, input-discovery, preparation, or code error.

## 6. Attribution

ISIC 2019 is CC BY-NC 4.0; cite ISIC and acknowledge the BCN20000, HAM10000 and MSK source datasets as specified on the [official ISIC page](https://challenge.isic-archive.com/data/). Non-commercial license terms apply. Do not republish the image files or include them in result ZIPs.
