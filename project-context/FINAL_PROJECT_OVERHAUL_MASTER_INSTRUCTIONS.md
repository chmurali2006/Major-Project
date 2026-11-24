# Coding Agent Execution Instructions — Final Project Overhaul

> **Status overlay — 2026-10-19 UTC:** This remains the user-provided master plan and its scientific/data-access safeguards remain controlling. T1 is now complete and ingested as a validation-only run; see `deliverables/T1_VALIDATION_RESULTS.md`. The reported run accessed TRAIN/validation only (`test_accessed:false`). T2/PH2 remains blocked as confirmatory because of prior PH2 use and incomplete exact membership/source lineage. Other unchecked tasks below remain planned or incomplete unless separate evidence says otherwise. Calendar/day estimates and target metrics are not results. Future-dated receipt/report timestamps after 2026-10-19 remain unauthenticated. The current later 500-image holdout is closed to further outcomes and is not a confirmatory TEST.

**Target:** Transform `chmurali2006/Major-Project` from a fragmented, audit-heavy prototype into a cohesive, domain-grounded, SOTA-compared B.Tech Major Project ready for an NIT Andhra Pradesh CSE faculty panel (including domain specialists in medical image watermarking, ROI/RONI tamper localisation, and image forensics).

**Read this first:** Every instruction below is mandatory unless explicitly marked `[OPTIONAL / TIME-PERMITTING]`. Execute in strict priority order. Do not invent new audit frameworks, do not expand unit-test bloat, and do not fabricate results.

---

## 0. Hard Operating Rules & Banned Agent Behaviors

Your previous iterations over-indexed on compliance memos and QA plumbing while leaving five major scientific and presentation holes open. **Follow these rules strictly:**

1. **STOP audit/QA bloat immediately.**
   - Do **not** write any new meta-audit memos, snapshot dossiers, or receipt-review essays unless explicitly required to parse a new Kaggle output ZIP.
   - Do **not** write new unit tests except lightweight sanity/smoke checks that prevent notebook crashes on Kaggle.
   - **NEVER** put unit-test counts (e.g., "540 passed"), JSON receipt schemas, or SHA-256 hash dumps in abstracts, slide headlines, executive summaries, or main report tables. Reproducibility goes in one concise paragraph under *Implementation Details*.
2. **BAN third-person AI/auditor prose from all student-facing deliverables.**
   - Remove every instance of `"the user reports"`, `"per the user"`, `"receipt-audited, not independently replayed from source pixels"`, and `"public-key issuer not independently authenticated"` from `README.md`, `PRESENTATION_DEFENSE_PACK.md`, `PROJECT_PRESENTATION_DRAFT.pptx`, and thesis tables.
   - Write all student-facing documents in **first-person academic voice** (`"we implemented"`, `"we evaluated"`, `"our benchmark shows"`). State execution provenance calmly in one sentence under *Experimental Protocol*.
3. **Maintain strict scientific honesty—without defensive self-sabotage.**
   - Keep real limits accurate: lesion-disjoint ISIC 2019 is not patient-independent; `EditGuard` (`clean.pth`) is an out-of-domain general-image checkpoint; `Full4`/`Full8`/`bounded289` are tile-expanded maps (not pixel-exact); the historical `isic-study-v2` run evaluated an unrecoverable 1,000-image test partition, so the later 500-image ISIC internal holdout is **permanently non-confirmatory** and must never be called "untouched TEST."
   - Put limitations in one clean **Scope & Limitations** section—never open a presentation or report with *"we claim no novelty, no SOTA, no clinical safety."*
4. **Respect environment boundaries cleanly.**
   - Because this local workspace lacks CUDA and raw medical image files, split every GPU/pixel task into:
     - **(a) Local agent code + self-contained Kaggle notebook** (with fail-closed input preflight and clean ZIP export), and
     - **(b) Local post-processing script** that ingests the returned Kaggle ZIP to build final CSV/LaTeX tables and 300-DPI figures.
5. **Respect dataset licensing and Git hygiene.**
   - **NEVER** commit raw ISIC 2019 or PH2 images, `.pth` weights, or private keys to Git.
   - Visual comparison figures containing actual medical pixels (needed for the thesis PDF and defense slides) must be exported by the Kaggle notebook into a **gitignored** folder (`deliverables/defense_visuals/`) for offline academic defense use only. Quantitative plots (no patient pixels) go into tracked `deliverables/figures/`.
6. **Do NOT break working imports or delete historical evidence.**
   - Never blindly delete legacy code/results. Label/quarantine historical prototypes (`PROTOCOL_V2`, `isic-study-v2`, `isic-full-v8`, failed learned refiners) cleanly in documentation and optional archive directories only after verifying active scripts/imports still pass.

---

## 1. Summary of Defects Being Fixed

| # | Current Defect (Panel Vulnerability) | Mandatory Fix |
|---|---|---|
| D1 | Both the `JPEG70` ($-19.64\text{ pp}$ MEL sensitivity) and `EditGuard` ($-25.0\text{ pp}$ MEL sensitivity) findings rely on **one un-augmented, epoch-3 DenseNet121** ($86.4\%$ clean acc $<$ $88.8\%$ majority baseline). Faculty will dismiss this as an undertrained-model artifact. | **Task T1:** Train `DenseNet121-Aug` + a second distinct architecture (`ResNet50-Aug` or `ConvNeXt-Tiny-Aug`) with standard geometric dermoscopy augmentations (NO JPEG augmentation) on the exact same 1,500 ISIC TRAIN split; re-evaluate all 500 VAL images across operators and `EditGuard`. |
| D2 | **Zero confirmatory held-out test set** (the 500-image ISIC holdout is permanently non-confirmatory due to `isic-study-v2`), plus **random background tampering** (`copy32`/`local_blur32` mostly hit healthy skin, causing only 4/1 flips). | **Task T2:** Add a guaranteed-disjoint **external test evaluation on PH2** ($N = 200$: 40 MEL, 160 nonMEL) using PH2's **official clinician lesion segmentation masks** for real anatomical ROI-targeted tampering (`roi_blur`, `roi_skin_cover`) and Grad-CAM attribution drift. |
| D3 | `bounded289` ($18.6\text{ KB}$) fails on **100% of global operations** ($0/3,500$ fine maps), leaving no working positive system improvement over `Full4`. | **Task T3:** Build and benchmark a **Zero-Distortion Multiresolution Adaptive Verifier (`bounded289` + `Full32` outer-signed coarse fallback, $\approx 27\text{ KB}$, $\text{MSE} = 0$)** that delivers $4\times 4$ tile maps for local edits and $100\%$ authenticated $32\times 32$ coarse coverage on global edits—plus run the real-image capacity sweep (`scripts/sweep_bounded_capacity_validation.py`). |
| D4 | `EditGuard` (`clean.pth`, in-band) is only compared against a detached $+524\text{ KB}$ `Signed4` sidecar—no in-band medical watermarking baseline exists to bridge into Dr. Prakash's ROI/RONI research area. | **Task T4:** Implement a clean **ROI-Preserving RONI Transform-Domain Watermark Baseline (`DWT-SVD` in RONI, $\text{ROI-MSE} = 0$ guaranteed)** evaluated on PH2 clinician lesion masks alongside Detached Cryptographic and `EditGuard`. |
| D5 | **Zero visual results** across 480 KB of text docs, missing standard forensics metrics (`PSNR`, `SSIM`, `Pixel Precision/Recall/F1`), and an unresolved row-count mismatch (`1,503` vs `1,500` `VERIFIED` due to `ISIC_0069696`). | **Task T5:** Compute complete domain metrics, fix the `1,503 / 13,497` count everywhere, and generate 4 publication-grade 300-DPI figures (including a visual dermoscopy ground-truth & Grad-CAM plate). |
| D6 | `README.md` still pitches abandoned `PROTOCOL_V2` HMAC-LSB as the main method; verified citations in `DESIGN_REVIEW.md` are missing from `LITERATURE.md`; hundreds of untracked files; no `LICENSE` or `ATTRIBUTION.md`; defense pack buries the `EditGuard` diagnostic crash and keeps auditor voice. | **Task T6 & T7:** Unify `README.md`, sync verified bibliography, add `LICENSE`/`ATTRIBUTION.md`, commit clean repo state, and rebuild the 12-slide presentation + Master Multi-Contract Comparison Table in clean first-person academic voice. |

---

## 2. Detailed Execution Tasks

---

### TASK T1 [CRITICAL — HIGHEST PRIORITY]: Multi-Architecture & Augmented Classifier Validation

**Objective:** Determine conclusively whether the Accuracy–Sensitivity Paradox under `JPEG70` and `EditGuard` (`clean.pth`) reproduces on properly regularized, data-augmented classifiers across two distinct architectures—or whether augmentation mitigates it. Either outcome is a publishable finding.

**Implementation Requirements:**
1. Create `src/multi_arch_classifier.py` and Kaggle notebook builder `scripts/build_multi_arch_validation_notebook.py` $\to$ `deliverables/kaggle_t1_multi_arch_validation.ipynb`.
2. Use the **exact fixed ISIC 2019 `adapted-isic2500` cohort** (`1,500` TRAIN / `500` VAL; strictly forbid TEST access; verify cohort SHA-256 `c524a43fce2951dbd68514a94d60610a8daa4f88fd40b8b93c53ee1f03f5aa42`).
3. Train **two frozen models** on the 1,500 TRAIN split (keep original un-augmented `DenseNet121` checkpoint `38d52ca8...` as Model 0 for direct ablation):
   - **Model 1 (`DenseNet121-Aug`):** `torchvision.models.densenet121(weights=IMAGENET1K_V1)`, binary `[nonMEL, MEL]` head.
   - **Model 2 (`ResNet50-Aug` or `ConvNeXt-Tiny-Aug`):** Distinct architecture (`torchvision.models.resnet50` or `convnext_tiny`, `IMAGENET1K_V1`/`V2`), binary `[nonMEL, MEL]` head.
4. **Frozen Training Recipe (Both Models):**
   - Input size: $512 \times 512$ RGB, ImageNet mean/std normalization.
   - **Standard geometric dermoscopy augmentations ONLY:** Random horizontal flip ($p = 0.5$), random vertical flip ($p = 0.5$), random 90-degree rotations, mild color jitter (`brightness=0.1, contrast=0.1, saturation=0.1`).
   - **FORBIDDEN augmentations:** Do **NOT** apply JPEG compression, Gaussian blur, or downscale-upscale during training (those are the test exposures under evaluation).
   - Loss: Weighted Cross-Entropy using exact TRAIN-only inverse-frequency class weights (`[0.56391, 4.41176]`).
   - Optimizer & Schedule: `AdamW` (`lr=1e-4` for backbone / `3e-4` for head, `weight_decay=1e-4`), `CosineAnnealingLR`, `epochs=20`, `batch_size=16` (or `8` with grad accumulation `2`), CUDA AMP, fixed seed `4101`.
   - Checkpoint selection: Highest validation Balanced Accuracy (record clean Acc, BA, MEL Sensitivity, Specificity, Macro-F1, ROC AUC, and fixed-90%-specificity MEL sensitivity).
5. **Frozen Evaluation on the 500 ISIC VAL Images (Both New Models):**
   - Evaluate each frozen checkpoint on:
     - **Original-image operators (10 cases):** `intact`, `copy32`, `local_blur32_surrogate`, `jpeg70`, `jpeg85`, `jpeg95`, `resize90_restore`, `contrast90`, `contrast110`, `gaussian05` (exact same deterministic seeds/settings as Track C).
     - **EditGuard-watermarked (`clean.pth`) paired contrasts (minimum 5 key cases, or all 10 if within GPU time):** `intact`, `copy32`, `jpeg70`, `jpeg85`, `gaussian05` — computing BOTH `marked_intact vs original_intact` AND `embedding_given_operator` (`operated_marked vs operated_original`).
   - Export per-image probabilities JSONL/CSV, paired class-stratified bootstrap 95% CIs (2,000 draws), and summary JSON.
   - **Also save exact SSIM** alongside PSNR/MSE for the 500 `EditGuard`-marked images (fixing the missing SSIM metric from the previous return!).
   - **Also export 6 authorized visual case panels** (for Task T5) directly from the same Kaggle run into `defense_visuals/` inside the returned ZIP (excluded from Git!).
6. Create local ingestion script `scripts/ingest_t1_multi_arch.py` producing:
   - `deliverables/tables/table_multi_arch_diagnostic_drift.csv` (3-model comparison: `DenseNet121-Base` vs `DenseNet121-Aug` vs `ResNet50/ConvNeXt-Aug`).
   - `deliverables/tables/table_editguard_ssim_and_multi_arch.csv`.

**Acceptance Criteria for T1:**
- Both augmented models beat the majority baseline on Balanced Accuracy ($> 0.75$) and show non-trivial clean melanoma sensitivity.
- Complete 3-model side-by-side table proves clearly whether `JPEG70` and `EditGuard` minority-class drops persist or shrink across augmentation and architecture change.

---

### TASK T2 [CRITICAL]: External Held-Out Test on PH2 ($N = 200$) + Real Clinician-ROI Tampering & Grad-CAM Shift

**Objective:** Solve three structural weaknesses in one clean external benchmark:
1. Establish a **guaranteed-clean external test cohort** (zero overlap with `isic-study-v2`).
2. Replace random background patches with **clinically grounded lesion-ROI tampering** using PH2's official manual expert lesion segmentation masks.
3. Measure **Grad-CAM explainability shift** under `JPEG70`, `EditGuard`, and lesion tampering.

**Implementation Requirements:**
1. Create `src/ph2_dataset.py` and `src/roi_tampering.py` + Kaggle notebook builder `scripts/build_ph2_external_eval_notebook.py` $\to$ `deliverables/kaggle_t2_ph2_external_test.ipynb`.
2. **Dataset & Leakage Check (PH2 — Mendonça et al., EMBC 2013):**
   - Load all 200 PH2 dermoscopy images (`IMDxxx.bmp`) and their official binary clinician lesion masks (`IMDxxx_lesion.bmp`).
   - Map labels deterministically to binary `[nonMEL, MEL]`: Common Nevus (80) + Atypical Nevus (80) $\to$ `nonMEL` (160); Melanoma (40) $\to$ `MEL` (40).
   - Preprocessing: Explicit RGB conversion and Pillow bicubic resize to $512 \times 512$ (matching ISIC 2019); resize binary lesion mask using **nearest-neighbor** (`PIL.Image.NEAREST`) to preserve exact binary values $\{0, 1\}$.
   - **Cross-Dataset Deduplication Check:** Compute exact SHA-256 and 64-bit `dHash`/`pHash` for all 200 PH2 images and verify zero exact matches (and log any Hamming distance $\le 4$ near-matches) against the 2,500 ISIC 2019 prepared hashes.
3. **Clinically Grounded Anatomical ROI Tampering Operators (`src/roi_tampering.py`):**
   - Use **ONLY** PH2's clinician lesion mask (NEVER classifier Grad-CAM!) to place attacks:
     - `rand_copy32` / `rand_blur32`: Existing random $32 \times 32$ patches (for direct contrast with ROI attacks).
     - `roi_blur32` / `roi_blur64`: Gaussian blur ($\sigma = 4.0$) centered on the clinician lesion mask centroid (clipped inside image bounds).
     - `roi_skin_cover32` / `roi_skin_cover64`: Copy-move a healthy skin patch sampled from the **RONI** (outside the dilated lesion mask, away from dark vignette corners) directly over the lesion centroid—simulating realistic melanoma concealment.
     - Global operators: `jpeg70`, `jpeg85`, `jpeg95`, `gaussian05`, `resize90_restore`.
4. **Frozen External Evaluation on All 200 PH2 Images:**
   - **Detached Cryptographic Methods:** `Full4`, `Full8`, `bounded289`, and the new **`bounded289 + Full32` Adaptive Fallback** (from Task T3) — measure exact integrity verdicts, local & global Pixel Precision / Recall / F1 / IoU, map coverage, sidecar bytes, and latency.
   - **Proactive Deep Baseline (`EditGuard clean.pth`):** Measure PSNR, SSIM, ROI-MSE, intact false-positive rate, local/ROI/global Pixel Precision / Recall / F1 / IoU, and complete target misses.
   - **ROI/RONI Transform Baseline (`DWT-SVD` from Task T4):** Measure whole-image PSNR, SSIM, exact ROI-MSE ($= 0.0$), JPEG70/85/95 payload Bit Accuracy, ROI-tamper detection rate, and diagnostic impact.
   - **Frozen Cross-Dataset Diagnostic Impact:** Evaluate all three frozen ISIC-trained classifiers (`DenseNet121-Base`, `DenseNet121-Aug`, `ResNet50/ConvNeXt-Aug`) on PH2 across `intact`, random edits, ROI lesion-concealment edits, `jpeg70`, `EditGuard`, and `ROI/RONI DWT-SVD`.
     - *Critical calibration note:* Because PH2 is an external acquisition domain, report **ROC AUC** and **MEL Sensitivity at Fixed $90\%$ Specificity** (calibrated on intact PH2 scores) alongside raw argmax metrics so cross-domain threshold shift does not obscure real discriminative impact.
   - **Grad-CAM Attribution Shift (`src/gradcam_metrics.py`):**
     - Compute Grad-CAM from the final convolutional block on all 40 PH2 melanomas (+ 40 stratified non-melanomas) under `intact`, `jpeg70`, `roi_skin_cover64`, `EditGuard`, and `ROI/RONI DWT-SVD`.
     - Report: (a) Grad-CAM Cosine Similarity vs. intact, (b) Top-20% Activation Map IoU vs. intact, and (c) **ROI Attribution Mass** (fraction of Grad-CAM energy inside PH2's official clinician lesion mask).
5. Create local ingestion script `scripts/ingest_t2_ph2_external.py` $\to$ `deliverables/tables/table_ph2_external_benchmark.csv`, `deliverables/tables/table_ph2_roi_tampering_and_gradcam.csv`.

---

### TASK T3 [HIGH VALUE]: Zero-Distortion Adaptive Fallback (`bounded289 + Full32`) & Real-Image Capacity Sweep

**Objective:** Fix `bounded289`'s biggest engineering weakness ($0/3,500$ global maps) while preserving **exact zero pixel distortion ($\text{MSE} = 0$)** and $\approx 94.8\%$ storage savings vs. `Full4`, and map `bounded289`'s real-image capacity cliff.

**Implementation Requirements:**
1. **Implement `src/adaptive_signed_evidence.py` (`bounded289_plus_full32`):**
   - **Construction:** Generate both a `bounded289` packet ($18,620\text{ B}$) and a `Full32` coarse grid packet ($32 \times 32$ tiles $\to 256$ tiles $\to 8,282\text{ B}$), bound together under a single outer Ed25519 signature over `(version, image_id, geometry, sha256(bounded289_body), sha256(full32_body))`.
   - Total serialized size: $\approx 27\text{ KB}$ ($\approx 94.8\%$ smaller than `Full4`'s $524,378\text{ B}$, and $79\%$ smaller than `Full8`'s $131,162\text{ B}$).
   - **Verification Contract (Strictly Fail-Closed):**
     - Invalid signature, wrong key, wrong image ID, or truncated packet $\to$ `CANNOT_AUTHENTICATE` (no map).
     - Exact full-root match $\to$ `VERIFIED` (0 changed pixels, $\approx 50\text{ ms}$).
     - Local tampering ($\le 289$ altered $4\times 4$ tiles) $\to$ `FAILED_INTEGRITY`, `resolution_mode = "FINE_4x4"`, outputs exact $4\times 4$ tile map (identical to `Full4`).
     - Global or large tampering ($> 289$ altered $4\times 4$ tiles) $\to$ `FAILED_INTEGRITY`, `resolution_mode = "COARSE_32x32_FALLBACK"`, outputs authenticated $32\times 32$ coarse map instead of abstaining ($100\%$ map availability!).
   - **Honest labeling:** Never call this a "novel cryptographic primitive." Frame it accurately as a **zero-distortion multiresolution authenticated coding construction** solving `bounded289`'s global abstention cliff.
2. **Real-Image Evaluation & Capacity Sweep:**
   - Include `bounded289_plus_full32` inside `deliverables/kaggle_t2_ph2_external_test.ipynb` (200 PH2 images) AND run it + the existing `scripts/sweep_bounded_capacity_validation.py` (50 fixed ISIC VAL images across $16^2, 32^2, 48^2, 64^2, 80^2$ and $1..4$ disjoint $32^2$ patches) inside a fast CPU/Kaggle runner cell.
   - Output `deliverables/tables/table_adaptive_fallback_and_capacity.csv` reporting exact bytes, `FINE_4x4` rate, `COARSE_32x32` fallback rate, Pixel F1/IoU, and sign/verify latency breakdown.

---

### TASK T4 [HIGH VALUE — DIRECT FACULTY DOMAIN BRIDGE]: ROI-Preserving RONI Transform-Domain Watermark Baseline (`DWT-SVD`)

**Objective:** Add a true **in-band medical watermarking paradigm** directly relevant to Dr. Prakash's ROI/RONI research area so your Master Comparison Table evaluates all three major paradigms side-by-side on identical medical images:
- **Paradigm 1:** Detached Zero-Distortion Cryptographic (`Full4`, `Full8`, `bounded289`, `bounded289+Full32`) — $\text{MSE} = 0$ everywhere, out-of-band.
- **Paradigm 2:** In-Band ROI-Preserving Transform Watermarking (`ROI/RONI DWT-SVD`) — **$\text{ROI-MSE} = 0.0$ strictly inside the clinician lesion mask**, semi-robust in-band payload in RONI.
- **Paradigm 3:** In-Band Full-Image Proactive Deep Watermarking (`EditGuard clean.pth`) — full-image distortion ($\approx 29.6\text{ dB}$), learned pixel localisation.

**Implementation Requirements (`src/roi_roni_dwt_svd.py`):**
1. **Strict Labeling Rule:** Name and describe this explicitly as **"ROI-Preserving RONI DWT-SVD Reference Baseline (Standard Medical Paradigm)"**. **NEVER** call it an exact reproduction of Prakash et al. (2025) or PFF-WM.
2. **Algorithm Design (Clean, Deterministic, Verifiable):**
   - **Input:** $512 \times 512$ uint8 RGB image $I$, binary clinician lesion ROI mask $M_{\text{ROI}}$ (dilated by 8 pixels for border safety), secret/signing key.
   - **Hard ROI Lock:** Every pixel with $M_{\text{ROI}}^{\text{dilated}}(i,j) = 1$ MUST remain bitwise identical in $I_w$ (assert `np.array_equal(I_w[roi], I[roi])`, guaranteeing exact $\text{ROI-MSE} = 0.0$).
   - **Authenticated ROI Digest:** Compute a 128-bit truncated HMAC-SHA256 (keyed with image ID + dimensions + canonical ROI pixel bytes) over the untouched ROI, plus optional ECC repetition coding (e.g., $3\times$ or $5\times$ majority vote) to survive JPEG85/70.
   - **RONI Transform Embedding:** Partition non-overlapping $16 \times 16$ (or $8 \times 8$) blocks lying strictly inside the RONI ($M_{\text{ROI}}^{\text{dilated}} == 0$, excluding pure-black vignette blocks where mean luminance $< 15$ to avoid clipping). Apply 1-level 2D Haar DWT (`pywt.dwt2`) on the luminance ($Y$) channel of each valid RONI block, apply SVD to the $LL$ (or $LH/HL$) subband, and embed 1 bit per block via QIM on the largest singular value $\sigma_1$ with quantization step $\Delta$ calibrated on a tiny synthetic/TRAIN tuning check (e.g., 5 images) to target whole-image $\text{PSNR} \ge 40\text{ dB}$ while surviving JPEG85/70 cleanly.
   - **Verification & Tamper Detection:** Extract RONI payload bits (with majority voting), recompute the keyed HMAC over the received ROI pixels, and compare against the extracted ROI digest. Any change inside the lesion ROI triggers an immediate `ROI_TAMPER_DETECTED` verdict; RONI block-level fragility/hash bits (or block check) flag RONI tampering.
   - **Document exact trust limits honestly:** State clearly that the receiver requires the shared key and an expected ROI mask/version contract (if an attacker alters the mask boundary without external binding, the verifier cannot trust the mask).
3. **Evaluate on all 200 PH2 images** inside `deliverables/kaggle_t2_ph2_external_test.ipynb`:
   - Report Whole-Image PSNR (dB), SSIM, **Exact ROI-MSE (verify $= 0.0$)**, Clean & Post-JPEG95/85/70 Bit Accuracy ($1 - \text{BER}$), ROI-Tamper Detection Rate on `roi_blur32/64` and `roi_skin_cover32/64`, and **Diagnostic Impact on all 3 frozen classifiers** (demonstrating directly whether keeping $\text{ROI-MSE} = 0$ eliminates `EditGuard`'s $-25\text{ pp}$ melanoma sensitivity collapse!).

---

### TASK T5 [CRITICAL]: Forensics Metrics Repair & Publication-Grade Visual Figures

**Objective:** Fix every metric/count inconsistency in existing results and produce the mandatory visual figures that image-processing faculty expect.

**Implementation Requirements:**
1. **Unified Forensics Metrics Script (`scripts/compute_forensics_metrics.py`):**
   - Read existing Track A (`adapted-validation500-v1/rows.jsonl` / `analysis.json`), Matched EditGuard (`matched-editguard-validation-return-v3`), Track C (`classifier-impact-return-v1`), and Track D (`diagnostic-embedding-train12-return-v1`) receipts.
   - Compute and export **Pixel Precision, Pixel Recall, Pixel F1-Score, Pixel IoU, Intact Image FPR, Intact Pixel FPR, Map Coverage, Sidecar Bytes/KB, Mean/Median Latency (ms), PSNR (dB), SSIM (where available), Bit Accuracy ($1-\text{BER}$), and Payload Capacity (bpp)**.
   - **Fix the Track A count bug permanently:** Report **`1,503 VERIFIED` and `13,497 FAILED_INTEGRITY`** across all active tables and docs, explicitly documenting `ISIC_0069696` (`local_blur32_surrogate` produced $0$ changed integer RGB pixels, so all 3 methods correctly returned `VERIFIED`).
   - **Fix Track D PSNR estimands explicitly:** Report per-image PSNR for `ISIC_0061070` (`MSE 0.07644` $\to$ **$59.30\text{ dB}$**; `MSE 5.81810` $\to$ **$40.48\text{ dB}$**) distinctly from aggregate-mean PSNR (`0.06660` $\to 59.90\text{ dB}$).
2. **Generate Four 300-DPI Publication Figures (`scripts/build_publication_figures.py`):**
   - **Figure 1 (`deliverables/defense_visuals/fig1_visual_qualitative_plate.png` — GITIGNORED, exported by Kaggle notebook T1/T2):**
     - 4–6 real dermoscopy cases (2 ISIC `MEL` + 2 PH2 `MEL` + 1–2 `nonMEL`), crisp columns:
       `Original RGB` | `EditGuard Marked (~29.6 dB)` | `Amplified Diff (|Iw - I| x 15)` | `Intact EditGuard FP Map vs. bounded289 VERIFIED` | `ROI/Local Tamper GT Mask` | `bounded289 (+Full32) Map` | `EditGuard Map` | `ROI/RONI DWT-SVD (ROI-MSE=0)`.
     - Overlay exact PSNR, IoU, and Pixel F1 on each tile.
   - **Figure 2 (`deliverables/defense_visuals/fig2_gradcam_and_roi_concealment.png` — GITIGNORED, exported by Kaggle notebook T2):**
     - 3 PH2 melanoma cases showing clinician lesion mask, `roi_skin_cover64` concealment attack, `JPEG70`, `EditGuard`, and `ROI/RONI DWT-SVD` with Grad-CAM heatmaps overlaid and exact $P(\text{MEL})$ + predicted label underneath each image.
   - **Figure 3 (`deliverables/figures/fig3_storage_latency_coverage_pareto.png` — TRACKED):**
     - Two-panel quantitative figure:
       - (a) Storage (KB, log scale) vs. Local Pixel F1/IoU vs. Global Map Coverage (comparing `Full4`, `Full8`, `bounded289`, `bounded289+Full32`, `EditGuard`, `ROI/RONI DWT-SVD`).
       - (b) Real-image `bounded289` Capacity Cliff curve (Altered $4\times 4$ Tile Count vs. Fine Map Recovery % and Verify Latency).
   - **Figure 4 (`deliverables/figures/fig4_multi_arch_diagnostic_drift.png` — TRACKED):**
     - Two-panel quantitative figure:
       - (a) **Dual Accuracy–Sensitivity Paradox Plot:** $\Delta\text{Accuracy (pp)}$ vs. $\Delta\text{MEL Sensitivity (pp)}$ across `JPEG95`, `JPEG85`, `JPEG70`, `Gaussian05`, `Resize90`, `EditGuard`, and `ROI/RONI DWT-SVD` across all 3 classifiers (`DenseNet121-Base`, `DenseNet121-Aug`, `ResNet50/ConvNeXt-Aug`), highlighting the deceptive $\Delta\text{Acc} > 0, \Delta\text{MEL Sens} < 0$ quadrant.
       - (b) Compact Track D Negative Ablation inset: Spatial QIM JPEG95/85/70 BER collapse ($\approx 50\%$) + `ISIC_0061070` $76.1\times$ MSE spike.

---

### TASK T6 [CRITICAL]: Repository Cleanup, Bibliography Sync, Licensing & Voice Overhaul

**Objective:** Eliminate every contradiction a faculty panel member would see when opening GitHub or reading your documentation.

**Implementation Requirements:**
1. **Rewrite Root `README.md`:**
   - Present the unified thesis cleanly in first-person academic voice:
     - **Project Title:** *Contract-Aware Authentication, Multiresolution Tamper Localisation, and Class-Sensitive Diagnostic Stability in Dermoscopic Medical Imaging*.
     - **3-Stage Engineering Evolution:** (1) Early Prototypes (`PROTOCOL_V2` HMAC-LSB & Learned Refiners — why we pivoted), (2) Detached Cryptographic & Multiresolution Coding (`Full4`/`Full8`/`bounded289`/`bounded289+Full32` — including the 2-tile stopping-set break of index peeling and GF($2^{16}$) Berlekamp–Massey fix), (3) Multi-Contract SOTA & Medical Benchmark (`EditGuard` CVPR '24 vs. `ROI/RONI DWT-SVD` vs. Detached Signed Evidence + Multi-Architecture Diagnostic & Grad-CAM Impact on ISIC 2019 & PH2 + Closed Track D Negative Ablation).
   - Explicitly label `PROTOCOL_V2.md`, `RUNNING.md` (old 7-image diagnostic), `results/isic-study-v2/`, and `runs/isic-full-v8/` under a clear **"Historical Phase-1 Prototypes (Archived / Excluded from Final Results)"** section. Do not delete them or break imports.
2. **Sync Verified Bibliography (`docs/LITERATURE.md` + `deliverables/references.bib`):**
   - Move ALL already-verified primary citations from `docs/DESIGN_REVIEW.md` into `docs/LITERATURE.md` and a clean BibTeX file `deliverables/references.bib`:
     - Prakash et al., *Ensuring integrity and security of medical image transmission in IoMT using highly imperceptible and robust watermarking approach*, Scientific Reports (2025), DOI `10.1038/s41598-025-11023-9`.
     - Khaldi et al. (PFF-WM), *Explainable and proactive fragile watermarking for medical Deepfake detection*, Intelligent Systems with Applications 31 (2026) 200684, DOI `10.1016/j.iswa.2026.200684`.
     - Arham et al., *Reversible watermarking for medical images using ROI-based tamper localization and recovery*, Franklin Open 15 (2026) 100545, DOI `10.1016/j.fraope.2026.100545`.
     - MedSign, *Pathology-Aware Adaptive Watermarking for Text-Driven Medical Image Synthesis*, arXiv:2503.08346 (2025).
     - Zhang et al., *EditGuard*, CVPR 2024, pp. 11964–11974.
     - Zhang et al., *OmniGuard*, CVPR 2025, pp. 3008–3018.
     - Sander et al., *Watermark Anything With Localized Messages (WAM)*, ICLR 2025.
     - Lefevre et al., *Signal Processing* 190 (2022) 108342, DOI `10.1016/j.sigpro.2021.108342`.
     - Lin, Varodayan & Girod, MMSP 2007.
     - Eppstein et al. (SIGCOMM 2011) & Goodrich & Mitzenmacher (Allerton 2011).
     - Mendonça et al., *PH2 — A Dermoscopic Image Database for Research and Benchmarking*, IEEE EMBC 2013.
     - ISIC 2019 Challenge (Tschandl et al. 2018; Codella et al. 2018; Combalia et al. 2019).
     - Huang et al. (DenseNet, CVPR 2017); He et al. (ResNet, CVPR 2016); Liu et al. (ConvNeXt, CVPR 2022).
     - RFC 8032 (EdDSA/Ed25519) & DICOM PS3.15 Annex C.
   - Remove the stale warning that PFF-WM citations are unverified.
3. **Add Missing Legal & Attribution Files:**
   - Root `LICENSE` (MIT License applying strictly to original student-authored code in `src/`, `scripts/`, `tests/`, explicitly excluding third-party datasets and model checkpoints).
   - Root `ATTRIBUTION.md` documenting ISIC 2019 CC BY-NC 4.0 terms + mandatory BCN20000 / HAM10000 / MSK acknowledgements, PH2 academic research terms, torchvision pretrained weight credits, and EditGuard upstream commit `174778fb` credit.
4. **Fix `docs/DESIGN_REVIEW.md` Discrepancy & `.gitignore`:**
   - Append a crisp erratum note correcting `"All 13,500 manipulated rows FAILED_INTEGRITY"` to `1,503 VERIFIED / 13,497 FAILED_INTEGRITY` (`ISIC_0069696` zero-byte-change blur).
   - Update `.gitignore` to ensure `deliverables/defense_visuals/`, `*.pth`, `*.pt`, raw `.jpg`/`.bmp`/`.png` medical image caches, and transient multi-hundred-MB ZIP parts are never tracked.
   - Stage and verify a clean tracked file list so a fresh `git clone` of the branch contains every active source file, notebook, table, figure, and doc.

---

### TASK T7 [FINAL]: Master Multi-Contract Table & Upgraded 12-Slide Defense Deck

**Objective:** Replace the defensive 9-slide text-only draft (`PROJECT_PRESENTATION_DRAFT.pptx`) and auditor-toned `PRESENTATION_DEFENSE_PACK.md` with a sharp, visual, 12-slide academic presentation and LaTeX/CSV Master Comparison Table.

**Implementation Requirements:**
1. **Generate `deliverables/tables/table_master_comparison.csv` and `.tex`** with exact measured columns (marking any unrun optional row clearly as omitted rather than `"To measure"`):
   - Rows: `Full4 Ed25519`, `Full8 Ed25519`, `bounded289`, `bounded289 + Full32 (Adaptive)`, `ROI/RONI DWT-SVD (PH2)`, `EditGuard (CVPR '24 clean.pth)`, `Spatial QIM + KL Corr. (Track D Negative Ablation)`.
   - Columns: `Contract`, `PSNR (dB)`, `SSIM`, `ROI-MSE`, `Sidecar (KB)`, `Intact FPR`, `Local/ROI F1 & IoU`, `Global Coverage`, `JPEG70 Bit Acc`, `Verify (ms)`, `MEL Sens Shift (pp) [Multi-Arch]`.
2. **Update `scripts/build_presentation_draft.py` $\to$ `deliverables/PROJECT_PRESENTATION_FINAL.pptx` (12 Slides + 4 Backup Slides):**
   - **Slide 1:** Title & 3-Contract Hook (Integrity · Localisation · Diagnostic Stability).
   - **Slide 2:** Problem Statement, Security Contracts & Related Work (explicitly citing Prakash et al. 2025 ROI/RONI, PFF-WM, MedSign, EditGuard, OmniGuard, DICOM PS3.15).
   - **Slide 3:** Engineering Evolution — Stage 1 Early Prototypes (`PROTOCOL_V2` HMAC-LSB $87.5\%$ altered pixels / $51.14\text{ dB}$; failed learned refiners $0.0$ IoU & $112$–$1,157$ intact FPs) $\to$ Why we pivoted to detached contracts and multi-contract benchmarking.
   - **Slide 4:** Datasets & Protocol (ISIC 2019 $N=500$ validation benchmark + PH2 $N=200$ external clinician-masked test set; random vs. anatomical ROI tampering operators; clean 1-line note on lesion-disjoint scope and archived legacy splits).
   - **Slide 5:** Algorithmic Depth — From IBLT to `bounded289` & Adaptive Fallback (show the 2-tile stopping-set break of fixed-layout peeling in $0.0006\text{ s}$ $\to$ $\text{GF}(2^{16})$ Berlekamp–Massey/Chien/Vandermonde power-syndrome decoding $\to$ `bounded289 + Full32` outer-signed multiresolution fallback).
   - **Slide 6:** Zero-Distortion Pareto Frontier & Capacity Cliff (embed **Figure 3** + Track A & Adaptive Fallback table with exact `1,503 / 13,497` counts and Pixel F1/IoU/latency).
   - **Slide 7:** Multi-Architecture Diagnostic Drift — The Dual Accuracy–Sensitivity Paradox (embed **Figure 4a** showing `JPEG70` & `EditGuard` across `DenseNet121-Base`, `DenseNet121-Aug`, and `ResNet50/ConvNeXt-Aug`, plus fixed-specificity sensitivity).
   - **Slide 8:** External PH2 Evaluation — Clinician-ROI Concealment & Grad-CAM Drift (embed **Figure 2** contrasting random patches vs. `roi_skin_cover64` + Grad-CAM cosine/ROI-mass stability).
   - **Slide 9:** Visual Ground-Truth Proof Plate (embed **Figure 1**: real dermoscopy cases showing `EditGuard`'s $29.60\text{ dB}$ noise, $62\%$ intact false positives, and `Copy32` misses vs. `bounded289` and `ROI/RONI DWT-SVD`).
   - **Slide 10:** Master Multi-Contract Comparison (Detached vs. ROI/RONI DWT-SVD vs. Proactive Deep `EditGuard` CVPR '24 — putting `EditGuard`'s $29.60\text{ dB}$ PSNR, $62\%$ FPR, $128/500$ `Copy32` misses, $-25\text{ pp}$ intact MEL crash, and $10/10$ negative paired BA contrasts front and centre alongside ROI/RONI's $\text{ROI-MSE}=0$ protection!).
   - **Slide 11:** Track D Negative Ablation (Pythagorean distortion equation $\|y-x\|_2^2 = \|b-x\|_2^2 + \|(y-x)_{\setminus C}\|_2^2$, synthetic unseen-model transfer counterexample, `ISIC_0061070` $76.1\times$ MSE spike, and **Figure 4b** showing $\approx 50\%$ JPEG95/85/70 BER collapse).
   - **Slide 12:** Key Conclusions, Scope Boundaries, Future Research Offshoots & Complete References (3 crisp contributions, 2-line scope note, 3 concrete next-batch offshoots, and verified IEEE bibliography).
   - **Backup Slides (13–16):** (B1) Legacy HMAC-LSB & 8-bit collision probe, (B2) Learned refiner synthetic diagnostic table, (B3) Full 12-operator Track C table incl. FGSM4/PGD4, (B4) Reproducibility & Cohort Provenance summary.
3. **Rewrite `deliverables/PRESENTATION_DEFENSE_PACK.md`** in confident first-person student voice aligned 1-to-1 with the 12 slides, including crisp Q&A answers for:
   - *Why `bounded289` uses Berlekamp–Massey over $\text{GF}(2^{16})$ and how `Full32` fallback fixes global abstention.*
   - *What happened when we added data augmentation and a second architecture (T1 results).*
   - *Why `EditGuard clean.pth` suffered domain-transfer FPR and MEL recall drops, and how ROI/RONI DWT-SVD compares.*
   - *Why we used PH2 as an external clinician-masked test set instead of reusing the historical ISIC split.*
   - *Why Track D stopped cleanly at 12 images.*

---

## 3. Time-Boxed Execution Schedule

Execute tasks in strict dependency order depending on remaining days before defense:

### Path A — Standard Full Finish (7–10 Days Available, Recommended)
1. **Day 1:** Implement **T3** (`bounded289 + Full32` adaptive fallback locally) + **T4** (`src/roi_roni_dwt_svd.py` locally with tiny synthetic smoke test) + **T5.1** (`compute_forensics_metrics.py`).
2. **Day 2:** Build and launch Kaggle Notebook **T1** (`DenseNet121-Aug` + `ResNet50/ConvNeXt-Aug` + EditGuard SSIM + ISIC visual panels).
3. **Day 3–4:** Build and launch Kaggle Notebook **T2** (PH2 external test: Detached + Adaptive Fallback + EditGuard + ROI/RONI DWT-SVD + Clinician-ROI tampering + Grad-CAM + PH2 visual panels + 50-image ISIC capacity sweep).
4. **Day 5:** Ingest T1 & T2 returns locally; generate all 4 300-DPI figures (**T5.2**).
5. **Day 6:** Execute **T6** (`README.md`, `LITERATURE.md`, `references.bib`, `LICENSE`, `ATTRIBUTION.md`, `DESIGN_REVIEW.md` erratum, clean Git commit).
6. **Day 7:** Execute **T7** (Master Comparison Table, final 12-slide PPTX, rewritten Defense Pack, offline demo check).

### Path B — Emergency Crunch Mode ($\le 4$ Days Available)
- Execute **T1 (Multi-Arch Augmented Classifiers + EditGuard SSIM + ISIC Visuals)** + **T3 (`bounded289 + Full32`)** + **T5 (Forensics Metrics + 300-DPI Figures)** + **T6 (Repo/Bibliography/Voice Cleanup)** + **T7 (Final 12-Slide Deck)**.
- Defer **T2 (PH2)** and **T4 (ROI/RONI DWT-SVD)** explicitly to *Future Work* on Slide 12 (never pretend they were run).

---

## 4. Strict Definition of Done (Final Verification Gate)

Do **not** report completion until every item below passes:

- [ ] **Zero AI/auditor voice** (`grep -iE "the user reports|per the user|issuer not authenticated|not independently replayed" README.md deliverables/PRESENTATION_DEFENSE_PACK.md` returns 0 matches).
- [ ] **Zero unit-test headlines** in `README.md` top summary, slides, or Master Comparison Table.
- [ ] **Exact Track A counts fixed** (`1,503 VERIFIED` / `13,497 FAILED_INTEGRITY` with `ISIC_0069696` noted).
- [x] **T1 completed & ingested (validation-only):** 3-model diagnostic comparison table (`DenseNet121-Base` vs `DenseNet121-Aug` vs `ResNet50-Aug`) and EditGuard SSIM populated from the returned Kaggle run; validation results and caveats documented in `deliverables/T1_VALIDATION_RESULTS.md`. No TEST access.
- [ ] **T2 & T4 completed & ingested (Path A):** PH2 external test ($N = 200$) with clinician-masked ROI tampering, Grad-CAM shift, and ROI/RONI DWT-SVD ($\text{ROI-MSE} = 0.0$ verified).
- [ ] **T3 completed:** `bounded289 + Full32` adaptive fallback ($100\%$ global map coverage, $\text{MSE} = 0$) benchmarked alongside `Full4`/`Full8`/`bounded289`.
- [ ] **All 4 publication figures rendered at 300 DPI** (visual medical plates in gitignored `deliverables/defense_visuals/`, quantitative plots in tracked `deliverables/figures/`).
- [ ] **Clean repository state:** `README.md` unified, `docs/LITERATURE.md` + `deliverables/references.bib` synced (including Prakash et al. 2025, PFF-WM 2026, EditGuard 2024, OmniGuard 2025, WAM 2025, Lefevre et al. 2022, PH2 2013), `LICENSE` & `ATTRIBUTION.md` added, raw pixels/weights excluded via `.gitignore`, active code/docs committed cleanly.
- [ ] **Final 12-slide PPTX (`deliverables/PROJECT_PRESENTATION_FINAL.pptx`)** visually inspected with zero overlapping text, zero `"To measure"` placeholders, and zero `"Final TEST untouched"` claims on the legacy ISIC split.