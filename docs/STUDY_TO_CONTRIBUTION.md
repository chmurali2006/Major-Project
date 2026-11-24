# Study to implemented candidate: evidence review

**Current status correction (2026-10-19 UTC):** The former 2026-11-24 date in this document is later than the current date and is not accepted as valid chronology. Later-dated receipts/addenda in this project are future-dated and their timestamps are unauthenticated. This long-form note includes older planning snapshots; read this correction and `PROJECT_CONTEXT_MASTER.md` first. T1 classifier validation is now returned/ingested on TRAIN and validation only; see `deliverables/T1_VALIDATION_RESULTS.md`. The matched EditGuard return is receipt-audited only (no source-pixel/model replay). Historical `isic-study-v2` test IDs are unrecoverable from retained evidence; overlap with the later 500-image cohort is unknown. That later cohort is non-confirmatory and closed to additional outcome analysis. PH2 is not treated as a clean external cohort. Any confirmatory work requires a new provenance-audited cohort.

## What is complete

The 500-image classical validation was reanalysed from five returned archives (15,000 records). Compact evidence uses 18,620 bytes versus 524,378 for full4. Both provided maps for all 500 copy and all 500 local-blur cases, with matching localisation maps. Compact evidence supplied no maps for the seven global operators, and verification was approximately 1.81 seconds slower per local manipulation. These are storage/coverage/latency tradeoffs, not an overall superiority result. Receipt consistency is not an independent full pixel/operator replay.

Refiner failure diagnostics did not rescue the learned models: selected shared-rule outputs remained all-background on seven synthetic fixtures. Training-only threshold changes introduced intact-image false positives. This motivates stronger controls and explicit failure reporting, not a claim that attention solves localisation.

Neither result measures the clinical effect of watermark embedding. In particular, the compact authenticated method does not modify the image. A defensible narrative is: these studies identified competing engineering requirements and insufficient evidence for learned claims; we consequently implemented a separately testable, payload-constrained diagnostic correction hypothesis. It is not defensible to say that a measured clinical failure caused this design.

## Implemented candidate

`src/diagnostic_constrained_embedding.py` embeds a binary message using pair-difference QIM in fixed red-channel carrier samples. A frozen classifier guides bounded integer-RGB corrections on **non-carrier samples only**. The decoder and carrier values remain fixed. This is a research prototype, not a secure or novel watermark claim.

The pilot runner `scripts/experiment_diagnostic_embedding.py` compares fixed QIM, weaker uniform QIM, diagnostic correction and energy-matched random-direction correction. It restricts exploration to the first bounded number of TRAIN images, records source/checkpoint hashes and predictions, and evaluates recovery separately from full signed RGB authentication. An independent evaluator is optional in code but necessary for meaningful transfer evidence. The later 12-image guide-TRAIN pilot was executed and is summarized below; it is a receipt-reviewed feasibility pilot, not transfer evidence.

## Executed mechanism check

`deliverables/verification-evidence/diagnostic-embedding-mechanism-v1.json` records an explicitly synthetic 8×8 example:

| Variant | MSE | Guide KL | Unseen-model KL | Clean bit errors |
|---|---:|---:|---:|---:|
| Fixed | 0.166667 | 0.048425 | 0.048425 | 0 |
| Weaker | 0.041667 | 0.012253 | 0.012253 | 0 |
| Correction | 0.25 | 0 | 0.185144 | 0 |
| Energy-matched random | 0.25 | 0 | 0.185144 | 0 |

The correction successfully preserves carriers and improves its guide objective, **but worsens the unseen model**. The random control ties it in this fixture. Thus this demonstrates mechanism feasibility and an explicit transfer failure, not efficacy. Correction also increases distortion. A non-carrier edit preserves message recovery but fails separate signed authentication: message recovery alone cannot authenticate the image.

## Prior art and claim boundary

- PFF-WM: https://www.sciencedirect.com/science/article/pii/S2667305326000591 — local extracted paper `project-context/papers/pff-wm.txt`, saliency embedding around lines 505–526 and classifier-explanation alignment around 820–850. Generic diagnostic-aware watermarking is already covered.
- MedSign: https://arxiv.org/html/2503.08346v1 — primary page reviewed; pathology localization, adaptive watermark strength and diagnostic-region preservation for generated medical images already exist. Its generation setting differs, but that does not establish our novelty.

The narrower fixed-carrier correction formulation is an implemented candidate for further comparison, not established differentiation from all prior work. No SOTA, clinical safety or novelty claim is currently supported.

## Verification and remaining gates

Historical local regression counts in this section refer to the earlier implementation snapshot, not a current full-suite run. Unit and fixture integration tests do not establish medical performance. The original sent classifier notebook remains unchanged. The later 500-image holdout is not a valid untouched test: historical `isic-study-v2` test access is confirmed, exact IDs are unavailable, overlap is unknown, and no further holdout outcome analysis is allowed.

Classifier impact return review: the original DenseNet121 checkpoint selected epoch 3 with validation BA 0.7440, ROC-AUC 0.8454, and MEL sensitivity 0.5893 (33/56). Stored prediction arithmetic/source-protocol consistency were checked; no local source-image/model replay was performed. The earlier statement that the operator-impact notebook was still running is superseded: Track C and T1 results are available. T1’s two additional models and validation-only results are summarized in `deliverables/T1_VALIDATION_RESULTS.md`; do not blend its separate protocol/intervals with Track C without naming the source.

Before claiming a useful contribution: run the bounded training pilot; obtain independent-model evaluation; account for all distortion, payload margin, compute and authentication costs; freeze a validation/final-test protocol; execute actual matched baseline comparisons. Report failures and null results. Clinical fidelity requires evidence beyond guide confidence or KL. `REVIEW_READINESS_PLAN.md` ranks the gaps, fair controls and go/no-go criteria.

Machine-readable claim status and artifact SHA-256 hashes: `deliverables/verification-evidence/study-to-candidate-evidence-ledger-v1.json`. Rebuild with `.venv/bin/python scripts/build_research_evidence_ledger.py`; rerun the mechanism with `OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 .venv/bin/python scripts/smoke_diagnostic_embedding.py --out deliverables/verification-evidence/diagnostic-embedding-mechanism-v1.json`.

## Stronger controls and structural finding (v2)

Implemented `src/diagnostic_correction_controls.py` and upgraded the unexecuted TRAIN pilot to protocol v2 with six variants. Existing sent/running notebooks are unchanged. New controls are forward-query-matched best-of-K random search and a strict pixel-distortion gate. The pilot records query counts, random search traces and rejection reasons. Forward-query matching is **not** wall-clock/gradient-compute matching: guided search additionally uses backward passes. The conservative gate reuses the already computed guided candidate and therefore does not avoid optimisation cost.

A structural limit is now explicit. Let C be the locked carrier set, b the fixed embedding and x the original. Since b equals x outside C, any corrected y with y[C]=b[C] satisfies:

`||y-x||² = ||b-x||² + ||(y-x)[outside C]||²`.

Therefore every nonzero non-carrier correction strictly increases total squared distortion. The equal-distortion gate must return the baseline for every such correction; it is a limitation detector, not an efficacy method. Any future useful claim must explicitly justify a diagnostic/distortion tradeoff, or investigate a separately versioned formulation allowing carrier adjustments within decoding constraints. The latter is not implemented, proven robust or established novel here; it must not replace fixed-carrier results silently.

Executed receipt: `deliverables/verification-evidence/correction-controls-v2.json`. The synthetic comparison used 19 forward queries in each search; guided also used 8 backward passes. Random and guided both reached guide KL zero. The gate rejected the guided candidate (squared error 48 versus baseline 32). All returned clean payloads decoded. No medical efficacy follows. Regression after v2: **509 passed, 1 skipped**, 65.72 seconds; diff checks passed.

This changes the recommendation: keep the candidate experimental rather than advertising an equal-distortion improvement. A medical pilot may measure a tradeoff; it cannot overturn the algebraic constraint.

## Actual TRAIN12 pilot return reviewed (supersedes pending-pilot statements)

`diagnostic-embedding-train12-v2-results.zip` SHA256 `2ac8e65a9f1703ec186a2acbf744f5d0290c7bb5da5a5d11b51ed254fa81ae71`: 12 TRAIN images (10 nonMEL/2 MEL), 72 rows, 720 recovery entries, 72 signatures checked, exact sent-source/preparation/cohort identity and recomputed summary checks passed. All variants retain all12 guide labels; these TRAIN examples were already correctly classified. Guided correction returns fixed outputs on11/12, changes one image with increased distortion, and demonstrates no class-decision benefit. Mean MSE fixed .0665994, weaker .0163891, guided .545071, query-matched random2.768288. Mean guide KL fixed .000544013, weaker .0000469812, guided .000466016, query-random .000407102. Gate rejects the sole nonzero guided correction. JPEG70 payload BER is about50% across variants; clean decoding is not JPEG robustness.

Decision: **do not scale this unchanged candidate to validation/test**. Preserve as an evaluated experimental extension with negative/limited findings; prioritise independent review and pending matched baseline evidence. Any redesign requires a new protocol and prior-art/constraint review first. Independent evaluator still absent. These are receipt/signature checks, NOT independent image or attack replay: pixels were not returned. Full text addendum: `deliverables/DIAGNOSTIC_EMBEDDING_PILOT_REVIEW_ADDENDUM.txt`; evidence in `deliverables/verification-evidence/diagnostic-embedding-train12-return-v1/`. The earlier independent-review dossier remains a historical snapshot and should be shared with this addendum.

## Additional finalisation review (2026-10-19)

Adapted checklist and evidence boundaries are consolidated in `docs/ADAPTED_FINALISATION_ROADMAP.md`. Post-hoc VAL class-score shifts and a clean-derived fixed threshold are in `deliverables/verification-evidence/class-sensitive-drift-v2/`; this is descriptive, not causal or preregistered. Cohort ID-range proxies and exact decoded/prepared RGB-hash uniqueness are in `deliverables/verification-evidence/isic-group-balance-v1.json`; pHash still awaits pixels. A cProfile run is explicitly synthetic in `deliverables/verification-evidence/bounded289-cprofile-synthetic-v1.json`, not substituted for the missing 50-VAL-image capacity/latency study.

The matched EditGuard validation handoff later produced a return that is receipt/signature audited in `deliverables/MATCHED_EDITGUARD_VALIDATION_RETURN_REVIEW.md`; this does not imply source-pixel/model replay. The T1 return separately included paired EditGuard classifier contrasts and marking-fidelity metrics. Both are validation-only. No TEST access is authorized.

## Execution tooling and held-out-test gate (2026-10-19)

The exploratory source-group/exact-hash receipts and synthetic-only capacity profile remain as described in the adapted roadmap. A predeclared 50-image empirical validation capacity curve runner exists at `scripts/sweep_bounded_capacity_validation.py` and passed a synthetic fixture; it has not been run on medical pixels. `FREEZE_PROTOCOL.md` is now a revocation/tombstone notice; its former test switches and test-running instructions were removed because the current holdout is non-confirmatory. T1's separate Kaggle run did not access TEST. This document's earlier test-status wording is superseded. The local sandbox lacks source pixels and CUDA, so it cannot independently replay returned medical-image outputs. Historical test timestamps are not authenticated; see `deliverables/GATE0_PROVENANCE_STATUS.md`.
