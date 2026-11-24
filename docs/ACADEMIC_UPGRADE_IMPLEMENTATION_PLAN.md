# Corrected academic upgrade implementation plan

**Purpose:** turn the independent review and the attached panel proposal into a safe, evidence-led execution plan. This plan is not itself evidence that any proposed experiment has run or that a panel has approved its claims.

**Current constraint (status 2026-10-19 UTC):** the former 2026-11-24 date on this note is future-dated and not accepted chronology. The matched EditGuard return passed structural/arithmetic/signature checks using a separately supplied public key; this remains receipt-level evidence, not independent pixel/model replay. T1 is now returned/ingested on fixed TRAIN/validation only and includes SSIM/MSE/PSNR for EditGuard-marked validation images; details are in `deliverables/T1_VALIDATION_RESULTS.md`. Historical `isic-study-v2` exact test membership is unrecoverable; overlap with the later 500-image cohort is unknown. That cohort is non-confirmatory and closed to further outcome analysis. See `deliverables/TEST_SPLIT_RECOVERY_DECISION.md` and `deliverables/GATE0_PROVENANCE_STATUS.md`. Future confirmation requires a new provenance-audited cohort and frozen protocol.

## Executive decision

Use the attached plan as a list of candidate upgrades, **not as an approved scientific conclusion**. The matched EditGuard return audit and T1 multi-architecture validation ingestion are complete at the receipt level. The historical split issue is dispositioned: old membership is unrecoverable, and the current 500-image cohort is non-confirmatory. The key status/claims/presentation documents now reflect this; keep any remaining unimplemented hybrid, anatomical attack, or ROI/RONI idea labelled as a conditional proposal, not a result.

The defensible short-term framing is a comparative study of distinct contracts—detached integrity/localisation, operator-associated classifier changes, and a bounded embedding feasibility pilot. The proposed hybrid and ROI/RONI method remain unimplemented hypotheses until their experiments succeed.

## Corrections required before implementation

1. **Keep four modes separate, but do not promise a hybrid win.** Signing an EditGuard-marked image with `bounded289` is not zero-distortion relative to the source image. It is zero additional distortion relative to that already-watermarked representation. A hybrid may improve some coverage cases; it does not “strictly dominate” either component until a matched experiment demonstrates that.
2. **Tile localisation is not pixel-exact localisation.** The full-grid baselines identify failed 4×4/8×8 tiles and expand them to pixels. Their maps include extra pixels: the returned local IoUs are below 1.0. State the exact tile-level guarantee, map availability, missed pixels and false highlights; do not call the expanded pixel maps exact.
3. **Fallback never upgrades authentication.** In a hybrid, a missing, invalid or stripped sidecar remains `UNAUTHENTICATED`/`FAILED_INTEGRITY`. EditGuard may supply a *probabilistic supplemental mask*, not a cryptographic verification or a `VERIFIED` decision. Preserve the Stage-1 result and report fallback confidence/coverage separately.
4. **Do not assume EditGuard payload BER is available.** The current adapter embeds a 64-bit message but its localization interface returns a residual-derived mask; it does not currently expose a tested message decoder/BER output. Add bit accuracy only if the exact decoder, payload protocol, and corresponding ground truth are implemented and validated. The present return can support mask metrics and recorded MSE/PSNR receipts; it does not contain source/marked images for independent visual replay or SSIM calculation.
5. **No “SOTA” or mechanism claims by aspiration.** A local adapted comparison is not SOTA. Track C reports the original one-DenseNet operator-associated shift; T1 now adds two architectures on the same fixed validation cohort, so it is a cross-architecture validation comparison but not an independent-cohort replication. Neither result establishes a causal smoothing mechanism, clinical effect, or Grad-CAM explanation fidelity.
6. **ROI masks need independent validation.** ISIC 2019 labels are diagnostic labels, not automatically lesion segmentation masks. A classical threshold mask plus visual review on 20 images is not enough to call every attack anatomically lesion-centred. If independently validated masks or annotators are unavailable, call the operation a synthetic central/ROI-proxy edit—not realistic melanoma concealment.
7. **A self-embedded ROI digest is not automatically trusted.** Any ROI hash/MAC used as an integrity claim needs a trusted key/signature binding and a stable ROI definition. A freely recomputable digest embedded in the same image is not an authentication guarantee. Do not promise 100% lesion-change detection before testing mask error, payload extraction error, and attack cases.
8. **Close the test-membership recovery attempt.** The original `isic-study-v2` runner evaluated 1,000 test images. The uploaded collection ZIP contains only aggregate receipts; no test-ID manifest/verdict array exists in the available evidence. By decision, treat exact membership as unrecoverable and overlap with the later holdout as unknown. The later 500-image cohort is non-confirmatory; do not call it pristine or inspect further outcomes.
9. **Resolve time/source anomalies before using legacy run results.** Future-dated receipts and unavailable source commits are provenance blockers. Preserve and hash them; do not erase or silently relabel them as false. If they cannot be resolved, mark them legacy/unverified and keep them out of headline tables.
10. **Keep evidence caveats, but write them for the audience.** Avoid conversational “the user reports” phrasing in academic prose. However, retain an accurate methodology/limitations sentence explaining what was recomputed from returned records versus replayed from pixels. Unit-test counts belong in a short implementation note, not the abstract or headline findings.

## Work packages and gates

### Gate 0 — Evaluation-state disposition (current status 2026-10-19; no new GPU job in this provenance audit)

**Completed**
- The matched EditGuard validation return was audited against the exact Drive notebook and passed receipt, map-arithmetic and 500/500 Signed4 signature checks. It remains receipt-level evidence; no pixels or models were replayed. See `deliverables/MATCHED_EDITGUARD_VALIDATION_RETURN_REVIEW.md`.
- The uploaded v2 seed-0 bundle was integrity-checked and found to contain only aggregate receipts and its collection manifest. The actual manifest and per-image verdict ID arrays are absent.
- The historical v2 `test_n=1000` evaluation is confirmed. Exact membership recovery is closed by decision; overlap with the later 500-image cohort remains unknown. The later cohort is classified as non-confirmatory development evidence and must not be accessed for further outcome analysis.

**Remaining provenance work**
- Keep unavailable source commits and run records labelled legacy/unverified; do not present them as source-reproducible.
- A future confirmatory evaluation requires a new cohort audited against recoverable prior image/lesion membership and a new frozen protocol. Do not repurpose the current internal holdout.

**Disposition record:** `deliverables/TEST_SPLIT_RECOVERY_DECISION.md`; detailed audit state: `deliverables/GATE0_PROVENANCE_STATUS.md`.

### WP1 — Matched EditGuard validation comparison (completed; no TEST)

**Status:** the separate 500-image × 10-case matched return was produced and receipt-audited; no additional run is required to fill that table. T1 also returned separate EditGuard-paired classifier contrasts and SSIM/MSE/PSNR. Neither return was independently replayed from original image pixels/models. Any old instruction below to run the matched validation notebook is historical; do not start another run solely to reproduce these receipts or touch TEST.

The earlier matched runner stores per-row mask confusion, map artifacts, same-seed pairing, and classifier probability contrasts when the classifier is attached.

**From a valid return, compute and report**
- Pixel precision, recall, F1 and IoU directly from returned TP/FP/FN; intact false-positive rate and image-positive rate; conditional localization metrics together with map coverage/abstention.
- Per-case latency and explicit byte costs. The existing reader comparison adds a **524,378-byte Full4 sidecar** to EditGuard; it is not equal-storage or native EditGuard cost parity.
- The separate matched EditGuard archive's fidelity fields are limited to its own recorded setup receipts; the T1 return reports marking-fidelity MSE/PSNR/SSIM over validation images. Do not conflate those two archives or claim independent recomputation from pixels. Do not claim payload BER unless the decoder is exposed and tested.
- Diagnostic contrasts already specified by the runner: original vs. marked, original vs. operated original, operated original vs. operated marked, and original vs. operated marked. Recompute the paired class-stratified intervals and report the imperfect classifier/validation-selection limits.

**Do not proceed to the hybrid until** the matched EditGuard return passes review and the hybrid decision states are frozen. For the hybrid, sign the EditGuard-marked image, `I_w`, with `bounded289`; track MSE/PSNR relative to the original `I` and relative to `I_w` separately. Use the same 500 inputs and operator seeds across pure EditGuard, pure `bounded289`, and hybrid. Stage-1 tile maps must be called tile-level; Stage-2 masks remain statistical. On sidecar loss or invalidity, Stage 2 may output a supplemental mask but never change the integrity status to verified. Report fallback rate, coverage, errors, storage, runtime, and distortion. Do not claim dominance unless paired results establish it.

**Deliverables if the run supports them**
- `deliverables/tables/table_editguard_metrics.csv`
- `deliverables/tables/table_editguard_diagnostic_impact.csv`
- `scripts/evaluate_hybrid_verifier.py` and `deliverables/tables/table_hybrid_vs_components.csv` only after the pure baseline audit and new protocol freeze.

### WP2 — Forensics metrics and existing validation analysis (CPU/local; no new model training)

1. Add one deterministic metrics script that reads the existing row-level files and writes CSV/JSON with definitions, denominators, missing-map coverage, and per-case values. For each method/case report TP/FP/FN/TN-derived pixel precision/recall/F1/IoU, intact FPR, map coverage, and image-level decision counts. Do not pool abstentions into zero error.
2. Correct the exact Track A count everywhere: the row files contain 1,503 verified and 13,497 failed records because `ISIC_0069696`’s `local_blur32_surrogate` changed zero RGB pixels; there is one verified no-op row per method. Preserve that case rather than relabelling it a successful manipulation.
3. For the QIM pilot, compute per-image PSNR from each image’s MSE before taking means/medians. For `ISIC_0061070`, MSE 0.0764401754 corresponds to about **59.30 dB**, and 5.8180987040 to about **40.48 dB**. The 59.90 dB value is the PSNR calculated from the *aggregate mean fixed-QIM MSE* 0.0665994, not the first image’s PSNR. Label these estimands clearly. Bit accuracy is reported only for the actual decoded 4,096-bit payload; the corresponding nominal capacity is 0.015625 bpp at 512×512.
4. Reuse the existing `scripts/sweep_bounded_capacity_validation.py` for the specified area sweep; do not create a second competing capacity runner. Run it only when exact prepared validation pixels are available, under a fresh output path, and keep it validation/development evidence. Existing synthetic profiling is not a real-image throughput result.
5. Reuse `scripts/analyse_class_sensitive_drift.py` and its fixed-threshold outputs where they answer the question. Label its 90%-specificity threshold as exploratory/post-hoc validation. Sub-source ID-range composition is a proxy, not an institution label. Run pHash only from the exact authorized source images; pHash does not establish patient independence. Do not inspect the unresolved TEST split for subgroup effects.

**Deliverables**
- `scripts/compute_forensics_metrics.py`
- `deliverables/tables/table_trackA_forensics_metrics.csv`
- `deliverables/tables/table_trackC_drift.csv`
- `deliverables/tables/table_trackD_psnr_payload.csv`
- `deliverables/tables/table_cohort_provenance_phash.csv` (only after exact source pixels are available; otherwise mark pHash unavailable).

### WP3 — Anatomical-ROI experiments and Grad-CAM (conditional, not a one-week blocker)

**Prerequisites:** authorized exact images, independently validated lesion masks, a frozen classifier checkpoint, and an evaluation split not selected using these outputs. First determine whether this fixed ISIC 2019 cohort actually has usable lesion masks. Diagnostic labels alone do not satisfy this prerequisite.

If verified masks/qualified annotation are available:
- Implement a deterministic ROI loader/validator and visually QA a preregistered sample; report agreement/coverage and fallback counts. A centered fallback box must be labelled a proxy, never an anatomical ground truth mask.
- Freeze lesion-centred blur/copy/inpaint operators and seeds before model evaluation. Describe these as controlled synthetic interventions, not observed clinical concealment events.
- Use ROI masks—not DenseNet gradients—to place edits or partition ROI/RONI. Grad-CAM may be measured after the fact using predeclared cosine/top-20%-IoU/ROI-mass metrics, with no claim that map stability equals clinical explanation fidelity.
- Keep this an exploratory validation analysis. No TEST-derived mask tuning or outcome inspection.

If masks or trustworthy annotation are not available, defer anatomical claims and omit this package rather than manufacturing lesion masks or calling central patches “clinical attacks.”

### WP4 — Figures and presentation after analysis freezes

Build figures only from audited tables and authorized image examples. Include four contract modes as *separate paradigms*, and label the hybrid/ROI-RONI cells pending until run. Show storage, distortion, coverage/abstention, runtime and class-sensitive changes together. Do not show “100% exact pixel map” for tile-expanded outputs. Do not show source ISIC pixels in public Drive/Git artifacts unless the license and permissions permit it. Use 300-DPI PNG/PDF as presentation formatting, not as evidence quality.

### WP5 — Stronger/multiple classifiers (next-level, after core gates)

This is a new exploratory study, not a patch to the existing DenseNet result. Keep the current frozen DenseNet as a baseline. If compute/data/licensing permit, train an augmented DenseNet121 and one distinct architecture on exactly the same TRAIN/VAL memberships. Freeze augmentations, class weighting, optimizer, checkpoint rule, class order and operator suite before fitting. Do **not** use JPEG augmentation if compression is the test exposure. Select only on VAL and report paired class-sensitive changes with intervals. This does not clean or reopen the old test. No new model runs while the active Kaggle job is using the available GPU.

### WP6 — ROI/RONI transform-domain reference (research extension, not a promised result)

Do not implement the full DWT-SVD method until the cited methods are verified and WP3 has a valid ROI definition. Start with a tiny synthetic engineering prototype; then predeclare a validation parameter sweep over payload, PSNR/SSIM, ROI-MSE, BER and localization. Do not tune against a target “BER < 15–20%” and then present that same validation value as independent performance; show the complete curve and use a genuinely independent evaluation only after split integrity is resolved.

If a digest binds untouched ROI pixels, authenticate the digest under a trusted signature/MAC and define how the exact ROI mask/version is trusted. Distinguish RONI embedding distortion from ROI-MSE. Do not claim 100% ROI tamper sensitivity, JPEG resilience, or reproduction of Prakash/PFF-WM before independent execution and source-level protocol comparison.

### WP7 — Repository provenance, attribution and release hygiene (after results freeze)

- Keep a hash manifest and provenance index for every retained run. Quarantine legacy evidence through explicit labels/status files first; only move files after all references, hashes, and links are updated. Do not delete evidence to make the repository look clean.
- Add a project-specific source/data/model attribution file. Verify every bibliography entry, publication year/DOI and upstream license. Do not grant an MIT licence to third-party files/data. Select a root code licence only with the author/owner’s approval and exclude restricted data/weights.
- Curate tracked source, tests, deliverables, and small audit receipts; exclude raw ISIC pixels, checkpoints, caches, and restricted upstream code. The current checkout has many untracked files, so a fresh clone/PR must be checked explicitly before calling it reproducible.
- Replace conversational status wording in academic prose with accurate study-state language. Keep audit limits in the methods/limitations appendix; do not remove them. Remove unqualified “SOTA,” “untouched TEST,” “causal smoothing,” “clinical preservation,” and “novel” claims unless new evidence earns them.
- Do not create a `v1.0-academic-final` tag until all mandatory gates pass, the chosen thesis scope is signed off, and the release snapshot is reproducible. Any commit/tag remains on the current active branch; never switch branches.

## Proposed order and realistic schedule

| Order | Work | Compute | Exit condition |
|---|---|---|---|
| 0 | Current Kaggle completion, archive preservation, return audit, old-test/provenance reconciliation | Existing job only; no duplicate GPU | Complete return reviewed; old test/overlap status explicit |
| 1 | Existing-row metrics, no-op correction, QIM PSNR and table repairs | CPU | Every published metric traces to a row/artifact and has the right denominator |
| 2 | Decide whether a fresh final holdout is defensible; otherwise declare no confirmatory TEST | Data/provenance work | No unsupported “untouched” statement; no test run before freeze |
| 3 | Finish EditGuard analysis and, only if justified, implement/run hybrid on matched IDs | One approved GPU or sufficient CPU; sequential | Full paired comparison, explicit trust/fallback states, all costs and limitations |
| 4 | ROI/mask feasibility and selected figures | CPU plus authorized images | ROI definition validated or ROI claims explicitly deferred |
| 5 | Stronger classifiers, then ROI/RONI research prototype if time remains | Additional GPU time; separate preregistration | New results are clearly exploratory and not mixed into previous tests |
| 6 | Attribution, source packaging, doc cleanup and final release snapshot | CPU | Clean reproducible clone; permissions confirmed; no unsupported headline claim |

A realistic first-week target is Gates 0–2, the already-running EditGuard audit, corrected metrics, and a transparent presentation. WP3/WP5/WP6 may require additional weeks, annotation, and GPU access; do not imply they are finished to meet a calendar target.

## Acceptance criteria for any final academic package

- Every result has a data split, method version, source/checkpoint hash, command/environment, per-image denominator, and a status label.
- TEST status and overlap are stated precisely; if old test membership cannot be recovered, no confirmatory claim uses an unverified overlapping holdout.
- Hybrid results never claim zero MSE relative to the unmarked source, never call tile maps pixel-exact, and never let a neural fallback authenticate an image.
- ROI/RONI results have a trusted ROI/reference contract and measured—not assumed—distortion/robustness.
- EditGuard, stronger classifiers, ROI, Grad-CAM and RONI entries stay “pending” until their own outputs exist and pass audit.
- The final thesis contribution is either a measured contract-aware comparison or a demonstrated learned-method improvement—not an unvalidated combination of every implemented module.
