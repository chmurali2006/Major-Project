# Independent technical review of Major-Project

**Original review date recorded:** 2026-10-19 (UTC). The report contains a later-dated addendum that must be read with the correction below.  
**Scope:** current checkout source, retained run artifacts, and selected validation-return rows. This review treats summaries as claims to check, not ground truth.  
**Not performed:** no original ISIC pixels were available in this audit environment; no full source-pixel/model replay or security certification was performed. Re-parsing rows/recomputing metrics checks artifact arithmetic, not that the claimed source images or predictions were genuinely produced by the stated run.

## Current date/provenance correction (2026-10-19 UTC)

The addendum below is headed 2026-11-24 and states that 2026-10-20 / 2026-11-03 receipt timestamps were not future-dated. That chronology is impossible relative to the authoritative current date 2026-10-19 UTC. Treat the 2026-11-24 addendum/date claim as invalid for current status; the retained receipt timestamps are future-dated and unauthenticated, and do not establish execution times. This does not by itself prove artifact fabrication; it means chronology/source identity remain unresolved pending primary logs. A later-reviewed T1 Kaggle return is documented separately in `deliverables/T1_VALIDATION_RESULTS.md`; it is validation-only and does not resolve other provenance issues.

## Test-membership disposition (current status 2026-10-19)

The uploaded `isic-study-v2-seed-0-membership-evidence.zip` was checked (SHA-256 `8cc66bad8fe9e75bfccb1e02b3c5432bfd5f79d8747482350b0bdf0793d26315`). It contains the matching aggregate `C0_count.json` and `C0_B.json` receipts plus a collection manifest, but no test-ID manifest or per-image verdict NPZ. The exact 1,000-image membership therefore cannot be recovered from the retained evidence. The project disposition is to stop recovery attempts against available artifacts and treat the old membership as unrecoverable unless an original archive later appears. Overlap with the later 500-image cohort remains unknown; that cohort is non-confirmatory and must not be described as an untouched final TEST. See `deliverables/TEST_SPLIT_RECOVERY_DECISION.md`.

## Bottom line

**The work is a substantial engineering prototype plus several carefully scoped comparative experiments. It is not a completed demonstration of a novel, clinically reliable tamper-localisation method.** Since the original review, T1 added a receipt-ingested three-model TRAIN/validation comparison; see `deliverables/T1_VALIDATION_RESULTS.md`. It strengthens the classifier-impact discussion but does not constitute independent source-pixel/model replay, a new external cohort, or confirmatory test performance. The strongest defensible story remains a measured engineering tradeoff plus validation-stage classifier impact, accompanied by a small negative embedding-feasibility pilot. The central learned HMAC-guided localiser has not been shown to outperform its controls in a complete, independently auditable medical-image study.

My recommendation is **major revision and scope reduction**, not abandonment. A defensible B.Tech project can be built from the existing work, but only if the primary contribution is stated narrowly, test-set history is reconciled, and provenance issues below are resolved before reporting results as final.

## What I checked independently

- Read the actual active runner and core RGB authentication code (`scripts/run_isic_study.py`, `scripts/run_suite.py`, `src/authentication.py`, `src/isic_classifier_training.py`) instead of taking prose descriptions as evidence.
- Parsed all 15,000 records in `deliverables/verification-evidence/adapted-validation500-v1/rows.jsonl`; recomputed method-level map coverage, IoU, and timing means.
- Parsed all 6,000 rows in `deliverables/verification-evidence/classifier-impact-return-v1/predictions.jsonl.gz`; recomputed intact/JPEG70 accuracy, melanoma sensitivity, balanced accuracy and AUC from probabilities.
- Ran a fresh deterministic synthetic 512×512 RGB input through `src.authentication.embed` and checked the resulting pixel distortion and verification. This is an implementation check, not medical evidence.
- Inspected the checked-in result receipts and the files actually retained beside them. I did not run returned code or infer missing image pixels from hashes.

## Findings, by severity

### Critical: “TEST untouched” is not true for every study in this checkout

The current `scripts/run_isic_study.py` constructs `test` and evaluates the `C0_count` and `C0_B` controls on it in the ordinary run path (lines 272–307); it also predicts and scores learned models on `test` (lines 329–333). There is no explicit one-time approval/freeze gate protecting those code paths. `scripts/run_suite.py` defaults to three seeds and `test_n=1000`, so the same test partition is available to repeated study runs.

Consistent with that code, `results/isic-study-v2/seed-0/C0_count.json` is a stored test evaluation: it reports `n=1000`, `test_n=1000`, and metrics. This means the **ISIC-study-v2 test split has already been evaluated**. A different, later 500-image cohort protocol may have a separate holdout, but I cannot verify that it is disjoint from the earlier test images: the retained results and subsequently uploaded collection ZIP lack the per-image verdict archive and test manifest needed to compare IDs. At the original review date, the slide wording “Final TEST untouched” was therefore too broad. The current disposition treats the old membership as unrecoverable and the later holdout as non-confirmatory development evidence; see `deliverables/TEST_SPLIT_RECOVERY_DECISION.md`. This does not prove overlap, only that disjointness cannot be established.

### Critical: run provenance has unresolved timestamp and code-identity questions

- The retained `C0_count.json` records `provenance.started = 2026-11-03T10:42:53` and split seed `20261103`. Both dates are later than the current 2026-10-19 status date. Treat them as future-dated and unauthenticated; a split seed is not proof of when an evaluation ran. The contrary 2026-11-24 addendum is invalid for current chronology.
- `runs/isic-full-v8/receipt.json` records `created_utc = 2026-10-20T23:46:07Z`; this is later than the current 2026-10-19 status date and is future-dated, with chronology unverified. Check original run logs and source records before accepting it as an execution timestamp. It names its dataset `datasets\isic2018` while marking `dataset_is_primary=true`; that conflicts with the current checkout’s ISIC2019 primary-study framing and should be labelled as a separate legacy ISIC2018 run, not used as ISIC2019 evidence.
- The v2 result says it came from commit `6dc18a4`, but that commit object is not available in the current Git object database. The v8 receipt cites `28e4e6e`; its tree is marked dirty. These are not independently source-reproducible from this checkout.
- The v2 results directory retains aggregate JSON/interval files but not the per-image verdict NPZ or manifest that the runner says it writes. The aggregate values cannot be independently re-analysed at the image level or used to recover the evaluated membership here.

Until the timestamp and source-identity questions are checked against source archives, hashes, logs, and run records, **quarantine those run numbers from headline claims**. The unavailable commits, dirty tree, and missing membership artifacts independently prevent full reproduction. This is a reproducibility/provenance concern, not proof of misconduct.

### Major: the main learned-method result is missing

The repository’s main `isic-rgb-auth-v2` program is a keyed LSB authentication channel with classical controls and learned C8/C12 localisation variants. The only retained `results/isic-study-v2/seed-0` results are `C0_count` and `C0_B` controls and their aggregate comparison; there are no C8/C12 trained outputs there. The full three-seed/ablation study described in the protocol is not evidenced by those files.

Therefore the core claim that the learned model adds value over the classical/control system is **unanswered**, not negative and not positive. The 540 passing software tests (one CUDA-only test skipped in the recorded full run) are a real engineering strength, but tests establish implementation checks, not medical efficacy or learned superiority.

### Major: the embedded RGB HMAC changes the image and is fragile by design

`src/authentication.py` clears each 8×8 RGB block’s 192 LSBs, computes a 192-bit HMAC over the upper seven bits plus geometry, version ID and block address, and writes the tag into those cleared bits. A deterministic fresh synthetic check found approximately **50% of channel samples changed by ±1**, approximately **87.5% of RGB pixels changed in at least one channel**, MSE 0.5000 and PSNR 51.14 dB; the embedded output verified successfully. This agrees with the construction, but it means the method is **not zero-distortion and does not preserve the exact original RGB values**. The overwritten source LSBs cannot be recovered from this marked image alone.

That can be an acceptable fragile watermark design, but its contract must be stated as integrity of the marked representation, not exact preservation of the source. Lossy JPEG/re-encoding is expected to fail the MAC. The runner also uses the literal public benchmark key `b'isic-study-key'` (`scripts/run_isic_study.py`), so its scores do not demonstrate resistance to an adversary who knows or obtains the key. The implementation comments acknowledge this; any security claims must retain that limitation. Signed sidecar baselines are the necessary zero-distortion comparator.

### Major: one published aggregate statement disagrees with the raw validation rows

My row-level count found **501 `VERIFIED` records per method**, not 500, because one `local_blur32_surrogate` application to `ISIC_0069696` is a no-op (`changed_pixels=0`, unchanged RGB hash). Repeated across three methods, the raw rows contain 1,503 verified and 13,497 failed records. `docs/DESIGN_REVIEW.md` says “All 13,500 manipulated rows FAILED_INTEGRITY.” The three rows labelled as a blur condition are in fact unchanged inputs. This is a small, explainable reporting discrepancy, not a failure of the cryptographic methods; fix the denominator/wording and report the no-op explicitly.

### Moderate: the auxiliary validation evidence is numerically coherent, but not replay evidence

The validation rows support a useful and reproducible **receipt-level** storage/coverage/latency comparison. My independent arithmetic reproduces:

- `bounded289` vs `Full4`: 18,620 vs 524,378 bytes/image (96.45% lower); copy/blur IoU 0.8373/0.7946 for both; mean copy verification 1.8695 s vs 0.05674 s.
- `Full8`: copy/blur IoU 0.6797/0.6436; copy verification 0.02135 s.
- `bounded289` has fine maps on 1,500 total rows (intact and the two local cases) and abstains on the 3,500 global-operation rows.

I also recomputed the classifier impact directly from stored probabilities. On 500 validation images, intact accuracy/sensitivity/BA/AUC are 86.40% / 58.93% / 74.40% / 0.8454; JPEG70 is 89.20% / 39.29% / 67.39% / 0.8045. This is a sound example of why accuracy alone can mislead under class imbalance. It is **not** evidence that an embedding caused the change, and it is not a clinical endpoint.

For both studies, the raw rows/probabilities let me check arithmetic and internal pairing, but no original source images were available to replay transformations or predictions. The strongest defensible wording is “independently recomputed from returned receipts,” not “independently reproduced from pixels.”

### Moderate: the QIM extension is a negative pilot, not a demonstrated contribution

The 12-image guide-TRAIN receipt reports that guided correction changed only one image, substantially increasing its distortion, with no predicted-class changes; JPEG70 message errors are near chance. That is useful negative feasibility evidence if described honestly. It does not establish diagnostic benefit, independent-model transfer, clinical preservation, robustness, or novelty. The returned receipt has no original/received pixels for replay, so its MSE and pixel claims remain receipt-checked rather than independently image-verified.

### Moderate: the work is too broad and the public-facing scope is inconsistent

The workspace contains separable lines: (1) HMAC-LSB plus learned-localiser work, (2) detached signed/compact evidence, (3) classifier operator impact including the now-ingested T1 three-model validation return, (4) the small QIM pilot, and (5) matched EditGuard validation. These are related but not one validated end-to-end system. T1 and matched EditGuard returns are validation evidence, not confirmatory or clinical findings. The project needs one explicit thesis question and a clear map of which tracks answer it; otherwise it risks appearing as many prototypes rather than one completed study.

### Moderate: the thesis/report release is not ready on citations and permissions

The local literature file itself says that the PFF-WM citation needs full bibliographic verification and that dataset licences need formal review. This checkout has no root `LICENSE` file. ISIC 2019’s non-commercial terms and required source acknowledgements must be followed, and upstream EditGuard code/checkpoint redistribution terms remain unresolved in the project notes. Do not publicly package their data/weights or claim a complete related-work review until the exact permissions and references are checked. I did not independently verify the papers online in this review.

### Moderate: the Git branch does not yet contain the whole deliverable set

`git status --short` shows many central source additions, notebooks, evidence artifacts, and deliverables as untracked in this checkout. They are present in the shared workspace, but a normal GitHub clone/PR from the branch would omit untracked files. Before claiming the branch is a complete reproducibility package, explicitly curate and commit the intended source/evidence/docs (excluding caches, data and model weights), then verify a clean clone can run the documented checks.

## Strengths worth preserving

- Good separation between strict integrity outcomes and learned scores; learned decisions do not silently override a failed MAC.
- Clear threat-model caveats around key secrecy, version freshness, lossy operations and clinical limits.
- Negative experiments are retained instead of being hidden; the QIM stop-gate is appropriately conservative.
- The sidecar/compact-evidence validation and classifier-impact returns contain row-level data that allowed me to independently recompute key metrics.
- Strong software test discipline and numerous fail-closed input/checkpoint checks. This supports confidence in plumbing, not in efficacy.

## Required next actions, in order

1. **Freeze claims, not just slides.** Relabel `isic-study-v2` test metrics as already-accessed development/prototype results. Locate the exact old split membership from the original archive/logs, or state that membership cannot be recovered. Reconcile overlap with the later 500-image cohort before describing that holdout as untouched.
2. **Make test access impossible by default.** Split the runner into validation/development and a distinct, explicitly authorised final-evaluation command; no baseline/model/test scoring in default study runs. Hash and approve the evaluation protocol before opening any genuinely fresh holdout.
3. **Repair provenance.** Verify receipt timestamps against original run records; as of 2026-10-19, the 2026-10-20 and 2026-11-03 receipt timestamps are future-dated and unauthenticated. Preserve source bundles for cited commits and label ISIC2018 separately. Historical test membership is unrecoverable from retained evidence; do not create a synthetic replacement and represent it as original.
4. **Choose the primary contribution.** Either present a careful comparison of integrity-evidence cost/coverage and diagnostic operator effects, or complete a rigorous learned-localisation study against classical block expansion and image-only controls. Do not market the current code combination as a novel method without that discriminating result.
5. **For a learned-method claim:** use a defensible lesion/patient grouping policy, source-verified inputs, prespecified thresholds and metrics, multiple training seeds, a frozen independent evaluation, and a complete auditable per-image return. The T1 and matched EditGuard records add validation comparisons, but receipt audits cannot repair test contamination or provenance gaps and do not substitute for source-pixel/model replay.
6. **Finish bibliography, licensing, authorship and reproducibility packaging.** Include a project licence, dependency/model/data attribution, exact non-commercial restrictions, and one authoritative protocol/version table. Keep patient images and model weights out of public links unless explicitly permitted.

## Final assessment

**Current status: promising and unusually self-critical prototype; not yet a trustworthy final research result or a demonstrated novel/clinical system.** The best near-term presentation is a bounded engineering comparison with transparent negative findings, after the test/provenance contradictions are resolved. If presented as “a new clinically reliable AI medical-image tamper detector,” the evidence does not support it. If presented as “an audited prototype study of integrity/localisation tradeoffs, with a limited classifier-impact analysis and a negative embedding feasibility pilot,” it can be credible—provided the test split history and timestamp/source provenance questions are handled openly.
