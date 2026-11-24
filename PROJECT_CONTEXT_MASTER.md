# Major Project — authoritative context and status

**Status snapshot:** 2026-10-19 UTC  
**Repository:** `chmurali2006/Major-Project`  
**Active branch:** `arena/a9fb47a3-major-project`  
**Purpose:** give a single, evidence-bounded map of the project's methods, results, limitations, and current-safe actions. This is a synthesis of repository and returned artifacts, not a new experiment, independent reproduction, security certification, clinical assessment, or complete literature review.

## Executive status

The project is a set of related but distinct research/engineering strands in dermoscopic-image integrity, tamper localization, and classifier impact. They do **not** form one validated end-to-end system and their row counts or scores must not be pooled into one benchmark.

**Completed T1:** three classifiers (DenseNet121-Base, DenseNet121-Aug, ResNet50-Aug) were evaluated on the fixed 1,500 TRAIN / 500 validation cohort and the returned validation records were ingested. Source/operator identity checks passed against retained references; the run reports `test_accessed:false`. The augmented classifiers reached validation BA 0.7927 and 0.7573, respectively. JPEG70 raised accuracy but reduced MEL sensitivity for all three architectures. This is validation/development evidence; validation participated in checkpoint selection and no independent source-pixel/model replay or confirmatory generalization was established. Details: [`deliverables/T1_VALIDATION_RESULTS.md`](deliverables/T1_VALIDATION_RESULTS.md).

**No confirmatory TEST result is available for the current project.** A historical `isic-study-v2` run receipt reports that 1,000 test items were evaluated, but exact membership is unrecoverable from retained evidence; overlap with the later 500-image holdout is unknown. The later holdout is non-confirmatory development evidence, closed to further outcome analysis, and must not be described as untouched, pristine, disjoint, or final TEST. PH2 likewise has historical project use and incomplete membership/source lineage; it is not treated as a clean confirmatory external cohort.

## Historical mid-review/poster and transition boundary

The earlier mid-review deck and poster describe a separate ISIC 2018 fragile-watermarking study; their headline figures are historical reports, not current T1 results. The source PDFs and receipt chronology have unresolved provenance/date issues, and the PDFs are not included in the public package because embedded image pixels have not been screened. Use [`deliverables/MIDREVIEW_POSTER_TRANSITION_RECORD.md`](deliverables/MIDREVIEW_POSTER_TRANSITION_RECORD.md) for the reported numbers, limitations, source links, date caveat, and an evidence-bounded transition script. Do not present the Drive metadata dates as presentation dates: they are later than this status snapshot.

## Research framing

A cautious working framing is: **an evidence-bounded comparison of integrity, localization, and diagnostic-model impact under specified image changes**. Keep these contracts distinct:

1. **Integrity:** does decoded content match trusted evidence?
2. **Localization:** where are changes indicated, at what map resolution/coverage, with what false positives and cost?
3. **Classifier impact:** how do specified operations or marking alter a frozen research classifier's outputs?

Do not claim a new clinically reliable method, clinical benefit/safety, patient-level independence, production deployment, DICOM compliance, SOTA, novelty, or universal robustness. Integrity failure does not prove malicious intent. Classifier changes do not establish clinical harm or mechanism.

## Workstream map and evidence

| Workstream | Current evidence | Appropriate interpretation / limit |
|---|---|---|
| **Track A: detached integrity/localization** | 500-image validation receipts; 15,000 records. `bounded289` sidecar 18,620 B/image vs Full4 524,378 B (96.45% less). Reported copy/blur IoU: bounded289 0.837/0.795; Full4 0.837/0.795; Full8 0.680/0.644. Compact maps available for 0/3,500 tested global-operation rows. | Protocol-specific storage/coverage/latency tradeoff. Returned records were audited; transformations were not replayed from source pixels in this environment. Expanded tile maps are not pixel-exact. Not a universal optimum or deployed PKI claim. Evidence: `deliverables/verification-evidence/adapted-validation500-v1/`. |
| **Track C: original frozen DenseNet impact** | 500 validation images × 12 cases (6,000 rows). JPEG70: accuracy 86.4%→89.2%, MEL sensitivity 33/56 (58.93%)→22/56 (39.29%), BA 74.40%→67.39% (−7.006 pp). | One validation-selected adapted DenseNet and specified operators, not a clinical model or embedding-effect study. Original narrative CI [−13.144, −1.311] pp; the later T1 ingester's baseline interval [−13.042, −1.413] pp uses its recorded bootstrap procedure; keep analysis-specific intervals tied to their source artifacts. |
| **T1: multi-architecture classifier validation** | Shared 1,500 TRAIN / 500 validation cohort; 30 standard operator rows and 48 EditGuard contrast rows in ingested tables. Intact BA / MEL sensitivity: Base .7440/.5893; DenseNet-Aug .7927/.7679; ResNet-Aug .7573/.6250. Under JPEG70 accuracy rose +2.80/+2.40/+3.60 pp, while MEL sensitivity shifted −19.64/−7.14/−21.43 pp. DenseNet-Aug ΔBA −1.77 pp [−6.80,+3.04]; ResNet-Aug −7.34 pp [−13.03,−1.87]. | Paradox persists in this validation cohort. Its severity is architecture-dependent; attenuation appears for DenseNet-Aug but not ResNet-Aug. No test access, clinical interpretation, or independent replication. Source hash matched `src/multi_arch_classifier.py` (`510b94df1e79ce1d894ed9643edf3d89c78b95aed84af190633a6a167ee8d587`). Tables: `deliverables/tables/`. |
| **T1 EditGuard paired validation** | `marked_intact` vs each model's own unmarked intact: DenseNet base ΔBA −9.80 pp [−16.06,−3.21], ΔMEL sensitivity −25.00 pp; DenseNet-Aug −4.46 [−9.15,−0.11], −8.93 pp; ResNet-Aug +1.79 [−2.22,+6.03], +1.79 pp. Marking fidelity mean MSE 170.9716, PSNR 29.5999 dB, SSIM .8701. | Architecture-specific validation contrasts; these do not show a clinical benefit or harm. The CSV contains distinct operator-only, embedding-given-operator, and combined contrasts for five key conditions. |
| **Separate matched EditGuard + DenseNet validation** | Return audit checked archive/rows/maps/paired summaries and 500 Signed4 signatures under a separately supplied public key. EditGuard had positive maps on 310/500 intact images (62%); operation-specific performance varied. | Receipt and signature consistency only; no original-pixel/model replay, issuer identity proof, or equal-storage comparison. See `deliverables/MATCHED_EDITGUARD_VALIDATION_RETURN_REVIEW.md`. This return is separate from T1's own paired outputs. |
| **Track D: diagnostic-constrained QIM** | 12-image guide-TRAIN feasibility return (10 nonMEL/2 MEL), 72 rows, receipt/signature checks. One corrected MEL example increased MSE .0764→5.8181; no class-decision benefit; JPEG70 payload BER about 50%. | Unchanged candidate's small feasibility stop-gate is closed. Do not scale unchanged design or generalize failure to the field. No independent image/operator replay. See `deliverables/DIAGNOSTIC_EMBEDDING_PILOT_REVIEW_ADDENDUM.txt`. |
| **Protocol-v2 RGB-HMAC / learned localization** | Separate fragile per-block RGB-HMAC protocol, tests, synthetic TRAIN-only diagnostic (7 examples), and an incomplete real-image sanity trace (4/12 receipts; `complete=false`). | Not T1. No complete multi-seed ISIC learned-localization result is established. Synthetic learning metrics are not ISIC results; incomplete sanity trace is not full-ISIC performance. Legacy `heldout` commands are revoked. See `PROTOCOL_V2.md`. |
| **Historical `isic-study-v2`** | Retained receipt reports `test_n=1000`; expected manifest hash cannot be recomputed because membership/per-image verdict artifacts are absent. | Test access occurred; exact historical IDs and overlap with the later cohort are unknown. Recovery against available artifacts is closed unless genuine original evidence appears. |
| **PH2** | Historical project notes describe a 120-image stand-in split by lesion, 24 held out/opened once; exact source/membership lineage is unavailable. | Not a clean confirmatory external cohort. Do not claim guaranteed disjointness or treat a proposed PH2 N=200 evaluation as clean without new provenance evidence. |

## Provenance, chronology, and reproducibility

- The adapted cohort manifest SHA-256 is `c524a43fce2951dbd68514a94d60610a8daa4f88fd40b8b93c53ee1f03f5aa42`.
- The T1 results archive ZIP passed integrity check; its summary/protocol records report no test access; the returned classifier module SHA matched the checked-in module. Ingestion also checked membership/source/operator references and prediction structure. These checks support artifact consistency, not proof of the original environment or an independent replay.
- Historical receipts contain timestamps `2026-10-20T23:46:07+00:00` and `2026-11-03T10:42:53`, both later than this 2026-10-19 status date. Older docs include a 2026-11-24 addendum claiming those timestamps were not future-dated. That chronology is invalid relative to the authoritative date; treat the run timestamps/addendum as future-dated and unauthenticated. This is a provenance concern, not proof of fabrication.
- The local sandbox previously lacked Torch, authorized source-image inputs, and reviewed weights; do not claim independent source-pixel or model replay from the local audit. T1 used an external Kaggle run; no TEST access was part of it.
- This active branch contains a large untracked/modified working set. It is not a clean release snapshot or evidence that a normal clone contains all workspace files. Do not bulk-add/delete or claim release readiness without curation and clean-clone checks.
- Literature details, data/source licenses, upstream code/checkpoint redistribution rights, and project attribution require formal review. Keep raw medical pixels, restricted model weights, credentials, and private keys out of public/package uploads.

## Safe current actions and hard boundaries

- Start with [RUNNING.md](RUNNING.md) for synthetic demonstrations, test commands, and T1 ingestion. Its prior holdout instructions were replaced with safe guidance.
- `FREEZE_PROTOCOL.md` is a revocation notice, not an active test protocol.
- Do not access the later 500-image holdout for additional performance analysis. Do not construct a substitute membership manifest and claim it is historical.
- PH2 is not clean confirmation by default. A future external evaluation must audit source and prior membership first.
- T1 results are validation-only and must never be labelled TEST results.
- Before any confirmatory study, obtain a new authorized cohort, audit source identity and exact/perceptual duplicates against all recoverable prior data, use verified lesion/patient grouping where available, prespecify metrics/thresholds, and freeze artifacts before outcome access.

## Controlling document index

### Start and status
- [`README.md`](README.md) — repository landing page and fast evidence summary.
- [`PROJECT_CONTEXT_MASTER.md`](PROJECT_CONTEXT_MASTER.md) — current source of truth and crosswalk (this document).
- [`deliverables/PROJECT_FULL_OVERVIEW_AND_GAPS.md`](deliverables/PROJECT_FULL_OVERVIEW_AND_GAPS.md) — detailed study-line/evidence inventory and research plan.
- [`deliverables/CLAIMS_EVIDENCE_LIMITS.md`](deliverables/CLAIMS_EVIDENCE_LIMITS.md) — presentation-safe claims and boundaries.

### Results and provenance
- [`deliverables/T1_VALIDATION_RESULTS.md`](deliverables/T1_VALIDATION_RESULTS.md) — T1 metrics and audit notes.
- [`deliverables/MIDREVIEW_POSTER_TRANSITION_RECORD.md`](deliverables/MIDREVIEW_POSTER_TRANSITION_RECORD.md) — historical presentation claims, current-vs-historical guardrails, and chronology limits.
- [`deliverables/TEST_SPLIT_RECOVERY_DECISION.md`](deliverables/TEST_SPLIT_RECOVERY_DECISION.md) — current historical holdout disposition.
- [`deliverables/GATE0_PROVENANCE_STATUS.md`](deliverables/GATE0_PROVENANCE_STATUS.md) — provenance checks and unresolved chronology.
- [`deliverables/MATCHED_EDITGUARD_VALIDATION_RETURN_REVIEW.md`](deliverables/MATCHED_EDITGUARD_VALIDATION_RETURN_REVIEW.md) — separate matched EditGuard return review.
- [`deliverables/DIAGNOSTIC_EMBEDDING_PILOT_REVIEW_ADDENDUM.txt`](deliverables/DIAGNOSTIC_EMBEDDING_PILOT_REVIEW_ADDENDUM.txt) — bounded negative QIM pilot.

### Methods and roadmap
- [`PROTOCOL_V2.md`](PROTOCOL_V2.md) — separate RGB-HMAC/learned-localization protocol; do not confuse it with T1.
- [`project-context/FINAL_PROJECT_OVERHAUL_MASTER_INSTRUCTIONS.md`](project-context/FINAL_PROJECT_OVERHAUL_MASTER_INSTRUCTIONS.md) — user's controlling proposal/targets; remaining unchecked work is not completed evidence.
- [`docs/LITERATURE.md`](docs/LITERATURE.md) — references, with bibliographic/licensing verification still required.
- [`deliverables/PRESENTATION_DEFENSE_PACK.md`](deliverables/PRESENTATION_DEFENSE_PACK.md) — oral-defense language aligned to current boundaries.
- [`deliverables/PROJECT_COMPLETE_DOCUMENT_COMPILATION.md`](deliverables/PROJECT_COMPLETE_DOCUMENT_COMPILATION.md) — compiled narrative snapshot; regenerate after source-doc updates.

## Context-package contents and exclusions

A curated project context package has been built at [`deliverables/PROJECT_CONTEXT_BUNDLE_2026-10-19.zip`](deliverables/PROJECT_CONTEXT_BUNDLE_2026-10-19.zip). It contains source, tests, protocols, current and historical status documents, source-only sanitized notebooks, and derived text/JSON/CSV audit records with a SHA-256 manifest. It intentionally excludes original medical pixels, restricted model weights, credentials/private keys, image-bearing/raw result ZIPs (including the T1 return archive with visual panels), opaque NPZ/map binaries, full-text papers, images, and Git internals. It is a complete **project-context and reproducibility-source package within privacy/licensing limits**, not a byte-for-byte clone or data/model package. Exact included paths/hashes are in `deliverables/PACKAGE_MANIFEST.csv`; exclusions are described in the archive-root `PACKAGE_EXCLUSIONS.md` and `deliverables/PROJECT_CONTEXT_PACKAGE_README.md`.