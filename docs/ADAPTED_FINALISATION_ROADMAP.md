# Adapted finalisation roadmap — evidence-first, presentation-ready

**Status date:** 2026-10-19 UTC. **Scope:** adapt the earlier roadmap to evidence retained in this checkout. Current branch: `arena/a9fb47a3-major-project`. A former 2026-11-24 date on this note is future-dated relative to the current status and is not accepted chronology. An earlier `isic-study-v2` receipt reports 1,000 test evaluations; exact IDs are unrecoverable from retained evidence, and overlap with the later 500-image cohort is unknown. That cohort is non-confirmatory and closed to further outcome analysis. The old freeze is revoked; future confirmation requires a new provenance-audited cohort. T1 is now complete on TRAIN/validation only; see `deliverables/T1_VALIDATION_RESULTS.md`.

## Executive decision

The proposed organising frame is sound: keep **integrity**, **localisation**, and **diagnostic impact** as separate contracts, compare their costs/limits, and retain failed experiments as bounded negative results. Do not claim the thesis has established an exact global Pareto frontier, causal smoothing mechanism, clinical utility, SOTA status, or publication readiness. The existing comparative work is the defensible centre; the medical QIM pilot is a limited TRAIN feasibility/stop-gate result.

**Do not spend time or compute scaling the unchanged QIM correction.** Its fixed-carrier distortion barrier and TRAIN12 result are sufficient to close that candidate, not to establish performance on unseen patients/models.

## Status of roadmap items

| Item | Status | Evidence / remaining boundary |
|---|---|---|
| Track A detached signed evidence | **Completed on VAL** | 15,000 rows, exact RGB integrity; compact method saves bytes but trades coverage/latency. Not a DICOM workflow or PKI deployment claim. |
| Track B learned localisation | **Synthetic diagnostics only** | Failure modes retained. Do not imply medical-image training/validation. |
| Track C original frozen DenseNet impact | **Completed on VAL** | 6,000 operator rows; validation is development data because checkpoint selection used VAL. Adapted model/operators, not author reproduction or clinical model. |
| T1 multi-architecture classifier validation | **Returned and ingested on TRAIN/VAL** | Three models and 10 operators; both augmented models exceed validation BA 0.75. JPEG70 accuracy rose while MEL sensitivity fell across all three; augmentation effect is architecture-dependent. No TEST access or external/confirmatory claim. See `deliverables/T1_VALIDATION_RESULTS.md`. |
| Track D correction | **Closed as a TRAIN stop-gate** | 12 TRAIN images (2 MEL), 72 variant rows, 720 operator-recovery entries and 72 packet signatures checked. No independent evaluator, no pixel replay, no class flips; one costly changed output. See pilot addendum. |
| Class-specific probability shift / fixed clean threshold | **Completed exploratory analysis** | `deliverables/verification-evidence/class-sensitive-drift-v2/`; plot and JSON saved. Post-hoc VAL analysis, not preregistered operating point or causal diagnosis. |
| Cohort source-range/exact-hash audit | **Completed from receipts** | 2,500 source-decoded/prepared RGB hashes unique; no cross-split exact duplicates. Source attribution uses ID-range proxies only. `pHash` not run because source pixels are absent. |
| `bounded289` capacity curve on 50 VAL images | **Blocked** | Original/prepared pixels are not in this workspace. Existing VAL rows cover the pinned operators, not a capacity sweep. Do not substitute synthetic measurements as an ISIC result. |
| `bounded289` cProfile | **Synthetic profile only** | `bounded289-cprofile-synthetic-v1.json`, random RGB and clustered 64×64 edit (256 changed 4×4 tiles); not medical or directly comparable to prior timings. Python locator/moment recovery dominated profile. |
| 10-image deterministic Track A + C replay | **Blocked** | Requires prepared RGB pixels and the validated per-image replay inputs; saved probability receipts alone cannot replay image transforms/model predictions. |
| Matched EditGuard + frozen DenseNet on VAL | **Receipt-audited validation return** | Structural, row-arithmetic, map-comparison and 500/500 Signed4 signature checks passed. No source pixels or models were replayed; see `deliverables/MATCHED_EDITGUARD_VALIDATION_RETURN_REVIEW.md`. |
| Later 500-image internal holdout | **Non-confirmatory development evidence; closed to further outcome analysis** | Earlier v2 evaluated 1,000 test images; exact IDs are unrecoverable and overlap is unknown. Recovery is closed under `deliverables/TEST_SPLIT_RECOVERY_DECISION.md`. Do not describe as untouched or confirmatory. |
| Literature/pHash, final matrix, licensing | **Open/partial** | Literature matrix needs final cited-source review; pHash needs pixels; master table must mark unmeasured fields N/A/pending. Confirm ISIC and upstream licensing before redistribution. |

### Newly completed exploratory VAL analysis

A single probability threshold was selected from intact VAL probabilities to target at least 90% empirical nonMEL specificity, then held fixed for all operations. It is a post-hoc descriptive operating point. Threshold is **0.506985545158**; actual intact specificity is **90.09%** due to discrete counts. At that threshold, MEL sensitivity is intact **58.93%**, JPEG70 **39.29%**, JPEG85 **51.79%**, Gaussian05 **48.21%**, resize90-restore **50.00%**, contrast110 **62.50%**. Actual specificity changes by operation and is reported, not refitted.

Mean change in MEL probability for true MEL / true nonMEL: JPEG70 **−0.11360 / −0.03939**; Gaussian05 **−0.06967 / −0.03461**; JPEG85 **−0.06573 / −0.02538**. These are scores from the same adapted classifier, not evidence that a specific feature was destroyed or that calibration caused the shift. The paired class-conditional bootstrap intervals are in `analysis.json`; they are image-level, conditional on VAL class counts.

Source-range proxy counts (not an authoritative source label):

| Split | 0012–0014 ID range | 0024–0034 ID range | 0053–0073 ID range |
|---|---:|---:|---:|
| TRAIN | 102 (6.8%) | 963 (64.2%) | 435 (29.0%) |
| VAL | 38 (7.6%) | 314 (62.8%) | 148 (29.6%) |
| TEST | 36 (7.2%) | 291 (58.2%) | 173 (34.6%) |

This confirms representation across approximate acquisition ID families, not balance of institutions or acquisition conditions. There are **zero exact source-decoded RGB hash duplicates across the three splits** in the preparation receipts. Perceptual-hash similarity and patient identity remain unverified.

## Corrected central thesis and title

**Working thesis:** *An audited comparison of detached exact-integrity evidence, compact tamper localisation, and class-sensitive diagnostic effects on an adapted ISIC2019 cohort, with a bounded feasibility analysis of a diagnostic-constrained embedding extension.*

Possible concise title: **“Integrity, Tamper Localisation, and Diagnostic Impact in Dermoscopic Image Protection: An Audited Comparative Study.”** This does not imply all methods were compared at equal storage/compute, nor that the adaptation is a clinical benchmark.

## Presentation-safe findings (with claim boundaries)

1. **Exact evidence is a systems tradeoff, not a universal winner.** In the VAL protocol, bounded289 reduces additional storage versus full4 while exact RGB remains unchanged; it gives useful fine maps for tested local edits but abstains on global changes. Quantify latency and abstention beside storage. State that these are pinned deterministic operators and a Python implementation, not a universal optimum.
2. **Accuracy alone concealed class-specific validation changes.** JPEG70 accuracy rose from 86.4% to 89.2% while MEL sensitivity fell from 58.93% to 39.29% and balanced accuracy fell by 7.01 points. The exploratory frozen-threshold analysis confirms lower MEL scores/sensitivity for several operators. Do not say the experiment proves a biological or feature-level mechanism.
3. **The QIM extension is a negative feasibility result.** On 12 already-classified guide-TRAIN images, all variants kept the same predicted classes; guided correction changed 1/12 images and sharply raised MSE there. The strict fixed-carrier gate returned baseline output. JPEG70 BER is around 50%. This closes the candidate, not the broader field of diagnostic-aware robust watermarking.

## Immediate path to presentation

1. **Use existing validation evidence.** Build slides around the three findings above, fixed protocols, and limits. The matched EditGuard return is receipt-audited; label it validation-only and distinguish receipt checks from independent source-pixel/model replay.
2. **Propagate the split decision.** State that the old v2 test IDs are unrecoverable, overlap with the later 500-image cohort is unknown, and that cohort is non-confirmatory. Do not make untouched/pristine or confirmatory-generalization claims and do not inspect it for additional outcomes.
3. **Plan any future confirmatory study as a new study.** Use a new provenance-audited cohort with frozen membership, endpoints, code/checkpoint hashes, and documented authorization. The current cohort cannot be rehabilitated into confirmatory TEST by protocol freeze.
4. **No repository cleanup by moving “legacy” code now.** Existing imports/tests depend on a broad research workspace; archiving is cosmetic and risks breaking reproducibility. Instead label active vs historical code in documentation.
5. **Final package:** verify full tests; add a one-page claim/evidence/limit table, bibliography, reproducibility/version list and dataset/repository licences. Do not tag a final release or use “publishable-grade” until those are actually complete.

## Suggested 8-slide structure

1. Research question and the three contracts (integrity / localisation / diagnostic effects).
2. Protocol/cohort and adaptation boundary (lesion-disjoint; patient-disjoint not established).
3. Track A storage–latency–coverage table, including abstentions.
4. Track C baseline and JPEG70/Gaussian sensitivity; paired VAL examples, not clinical claims.
5. Exploratory fixed-threshold / score-shift chart (clearly labelled post-hoc validation).
6. Track B and D as bounded failed/limited experiments; one structural equation + TRAIN12 row.
7. Integrated comparison matrix: measured vs pending, unequal costs explicit, literature-only rows separated.
8. Conclusions, limitations, exact next gate, and project future work.

Detailed evidence is in the snapshot dossier plus the TRAIN12 addendum; this roadmap is not a replacement for either. Current full software regression after these additions: **539 passed, 1 CUDA-dependent test skipped in 73.08 s**. `git diff --check` is clean. Tests support code integrity only, not efficacy. The editable eight-slide draft is `deliverables/PROJECT_PRESENTATION_DRAFT.pptx`; reproducibility helpers are in `scripts/build_presentation_draft.py` and optional dependencies in `requirements-presentation.txt`.

## Follow-up: execution tooling and final-test gate

A deterministic 50-image VAL `bounded289` empirical capacity sweep is now implemented at `scripts/sweep_bounded_capacity_validation.py`; test fixture passes. It is intentionally not reported as an ISIC finding until run against all required real prepared VAL pixels. The exact final TEST protocol has been drafted in root `FREEZE_PROTOCOL.md`, with Track A's 15,000-row matrix, Track C's 5,000-row matrix, an EditGuard inclusion switch, and a strict one-time return audit policy. It requires explicit sign-off and final data/compute access; no test predictions have been made.

The Google Drive/repository search found no original fixed ISIC image files (only metadata, labels, and returned hash/preparation receipts), and local PyTorch reports CUDA unavailable. Thus no amount of parallel code edits can validly produce the held-out results in this runtime. To close the actual empirical items, provide the exact original 2,500 selected images via an accessible Drive folder/archive and an authorized GPU runtime for the EditGuard handoff. After the matched VAL return is audited, record the user's A/B decision in the frozen protocol and run TEST once. Do not replace missing pixels with similarly named mirrors or manufacture a pass from receipts.

Current complete regression after capacity-sweep tests and protocol docs: **540 passed, 1 CUDA-dependent skipped in 93.20 s**; `git diff --check` clean. The capacity sweep and notebook are ready; they are not experiment results.
