# Matched EditGuard validation return — audit and results

**Audit date:** 2026-11-24 UTC  
**Status:** **receipt and signed-packet audit passed using the subsequently uploaded public key.** This is validation/development evidence only.

## What was received and checked

The three named Google Drive parts were downloaded and concatenated in order. The 277,001,270-byte ZIP passed the ZIP CRC test and contained 1,019 entries / 289,685,056 uncompressed bytes. All 10,000 localisation rows, all 5,000 paired diagnostic rows, all 500 map archives, all 500 signed4 packets’ lengths/headers, the exact cohort, returned Python source files, row-to-map confusion arithmetic, paired probability summaries and completion counts passed the existing return reviewer.

The exact Drive notebook was downloaded and supplied to the audit (`SHA-256 9107ca9bead8b9770a562a9375ba990f432e3b96dfb524696847f318e1193b9e`). The returned source bundle’s Python files match the notebook bundle, fixed cohort and the local reviewed protocol. The archive hash is `33ac519371e373081ae60ddd7f44ff8c55168e6fea43458c6a395297764997a9`. Part-level Drive IDs, sizes and hashes are recorded in `deliverables/verification-evidence/matched-editguard-validation-return-v2/input-manifest.json`.

**The ZIP omitted `public-key.bin`** because the executed notebook’s packaging cell did not include it, although the experiment runner writes it to the output directory. The user uploaded the raw 32-byte Ed25519 public key separately. I reran the strict audit with that file supplied externally: **all 500 packet signatures verified**, in addition to the structural, map and probability checks. The key is bound to the returned packets by those signatures, but its issuer identity is not independently authenticated. I also patched the local notebook copy’s packaging cell to include `OUT/'public-key.bin'` for future returns; the exact Drive notebook used for this audit remains preserved separately. The earlier partial audit is retained at `deliverables/verification-evidence/matched-editguard-validation-return-v2/`; the completed strict audit is at `deliverables/verification-evidence/matched-editguard-validation-return-v3/`.

## Headline results from the returned receipts

The CSV tables are the source for complete per-case values: [`table_editguard_metrics.csv`](tables/table_editguard_metrics.csv) and [`table_editguard_diagnostic_impact.csv`](tables/table_editguard_diagnostic_impact.csv). The final summary and strict row-to-map/signature review are in [`tables/summary.json`](tables/summary.json) and [`verification-evidence/matched-editguard-validation-return-v3/review.json`](verification-evidence/matched-editguard-validation-return-v3/review.json).

| Case | EditGuard pixel precision | EditGuard pixel recall | EditGuard pixel IoU | EditGuard image-positive rate / misses | Signed4 pixel precision | Signed4 pixel recall |
|---|---:|---:|---:|---:|---:|---:|
| Intact | 0.000 (no positive pixels) | — | 0.000 | **62.0% false-positive images** (310/500) | no positive pixels | — |
| Copy32 | 0.871 | 0.714 | 0.646 | 90.4% positive; 128 targets have zero pixel overlap | 0.835 | 1.000 |
| Local blur32 surrogate | 0.971 | 0.865 | 0.843 | 100% positive | 0.835 | 1.000 |
| JPEG quality 70 | 0.999 | 1.000 | 0.999 | 100% positive | 0.999 | 1.000 |
| JPEG quality 85 | 0.998 | 1.000 | 0.998 | 100% positive | 0.998 | 1.000 |
| JPEG quality 95 | 0.991 | **0.010** | **0.010** | 100% positive, but very poor localization | 0.992 | 1.000 |
| Resize 90% then restore | 0.990 | 1.000 | 0.990 | 100% positive | 0.990 | 1.000 |
| Contrast 90% | 0.999 | **<0.001** | **<0.001** | 94.6% positive; 27 targets have zero overlap | 0.999 | 1.000 |
| Contrast 110% | 1.000 | **0.049** | **0.049** | 61.0% positive; 195 targets have zero overlap | 0.996 | 1.000 |
| Gaussian noise 0.05 | 0.981 | 0.811 | 0.798 | 100% positive | 0.983 | 1.000 |

Image-positive means only that a map contains at least one predicted pixel; it is **not** a claim of useful localization. Likewise, a positive image with near-zero recall does not constitute successful localization. Signed4 expands failed 4×4 tiles to pixels, so its apparent full recall comes with false-highlight area (for example, precision about 0.835 on the two local-edit cases), and it adds 524,378 bytes per image—about 262 MB decimal across this 500-image validation set—on top of the EditGuard-marked container. This is not a cost-matched end-to-end comparison.

For intact images, EditGuard marked at least one pixel on 310/500 images. The clean checkpoint therefore has a substantial false-alarm issue under this protocol. The local blur is explicitly a synthetic surrogate, not semantic lesion removal. These are ten predeclared cases—not twelve.

## Distortion and diagnostic-classifier contrasts

The returned per-image setup receipts give mean PSNR **29.60 dB** (median 30.91 dB), with mean per-image MSE 170.97 (median 52.74); all 500 marked images have nonzero MSE. These values are receipt-checked, **not recomputed from retained source/marked pixels**. The embedding is therefore not zero-distortion relative to the original image. It is inappropriate to describe it as imperceptible without a separately justified perceptual evaluation.

For the frozen adapted DenseNet on this validation cohort, the intact comparison (marked vs original) reports:

- Accuracy: 86.4% → 88.4% (+2.0 percentage points).
- Balanced accuracy: 74.4% → 64.6% (−9.8 points; paired class-stratified image-bootstrap 95% interval for the change: −16.2 to −3.8 points).
- Melanoma sensitivity: 58.9% → 33.9% (−25.0 points).
- 40/500 predicted labels flip.

The most relevant control is the **embedding-given-operator** contrast: operated marked vs the same operation applied to the original, with paired seeds/parameters. Across the ten cases, the observed balanced-accuracy change ranges from −4.8 to −11.1 points; all ten unadjusted descriptive paired bootstrap intervals are below zero. Melanoma sensitivity drops by 10.7–28.6 points across those cases. These comparisons suggest a consistent class-sensitive shift in this one imperfect classifier, not a clinical outcome or proof of patient harm. Validation was used for checkpoint selection; the image bootstrap is not patient-level, has no multiplicity adjustment, and does not establish calibration or clinical safety.

## Limits and next action

This is a careful audit of returned records, not source-pixel or model replay. We did **not** independently re-run EditGuard, the image operations, the classifier, or compute SSIM. The 500-image set is validation/development data, not a final independent test. None of these findings resolve the separate old-test membership/overlap question.

**Packaging fix for future returns:** update the notebook’s archive creation cell to include `OUT/'public-key.bin'` alongside the other root metadata files. For this completed run, the detached key was verified without editing the original archive or rerunning the GPU job. The uploaded public-key file SHA-256 is `eb896a22b9129d19bb50d4da64073b396265ab512d88b5092b3334e4951bf741`.

### Audit artifacts

- Completed strict reviewer output and full input/hash manifest: `deliverables/verification-evidence/matched-editguard-validation-return-v3/`
- Earlier partial reviewer output (superseded): `deliverables/verification-evidence/matched-editguard-validation-return-v2/`
- Per-case masks and timing: `deliverables/tables/table_editguard_metrics.csv`
- Paired diagnostic effects: `deliverables/tables/table_editguard_diagnostic_impact.csv`
- Summary with caveats and provenance hash: `deliverables/tables/summary.json`
- The original result parts and public key remain in Google Drive; local downloaded result parts and assembled ZIP were removed after the audit to avoid retaining large transient copies in the repository workspace.
