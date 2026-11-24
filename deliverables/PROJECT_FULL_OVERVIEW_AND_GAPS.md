# Project overview, evidence inventory, and next research plan

**Purpose:** one consolidated view of the research project as represented in this checkout: what the project is trying to do, which experimental strands exist, what results are presently defensible, what remains unverified or missing, and what would be required for a strong academic submission.

**Scope note:** this is a synthesis of repository documentation, retained receipts, code/protocol descriptions, and the documented audit decisions. It is not a new experiment, independent reproduction, security certification, clinical assessment, or external literature review. Receipt checks and software tests are not treated as scientific outcome evidence.

**Status date:** 2026-10-19 UTC. **Current branch:** `arena/a9fb47a3-major-project` (active). This report describes the working tree as it stands; it does not imply that every file is tracked, released, or reproducible from a clean clone. Use [`PROJECT_CONTEXT_MASTER.md`](../PROJECT_CONTEXT_MASTER.md) as the current document index and cross-strand status. A few retained historical records contain dates later than this status date; those timestamps are future-dated/unverified and are not accepted as proof of when a run occurred.

---

## 1. Executive summary

This repository contains a broad medical-image integrity and tamper-localization research effort with **multiple related but distinct study lines**. The coherent domain is dermoscopic imagery, especially ISIC 2019, but the work should not be reported as one unified experiment or one proven new method.

The most defensible present story is a **controlled, validation-stage comparison of distinct protection contracts**:

1. **Exact integrity:** can a receiver establish that decoded image content still matches trusted evidence?
2. **Localization:** where did image content change, with what storage, latency, map-coverage, and false-positive costs?
3. **Diagnostic-model impact:** how do specified image operations or an embedding change a frozen classifier’s class-sensitive outputs?

The strongest completed evidence is currently **receipt-audited validation evidence**, not a complete independent replay from original pixels and model weights. The adapted ISIC cohort’s later 500-image holdout is **not confirmatory**: a different historical `isic-study-v2` run evaluated a 1,000-image test partition, its exact IDs cannot be recovered from the retained evidence, and overlap with the later holdout is unknown. Do not call the later holdout untouched, analyze it further for outcomes, or use it for confirmatory claims. Reopen recovery only if authentic original membership evidence appears. Any future confirmatory evaluation needs a new provenance-audited cohort and a frozen protocol.

**No SOTA, clinical-safety, patient-independence, universal robustness, or new-algorithm novelty claim is supported by the current record.** The academic opportunity is to make a careful domain-specific comparative study—or, after substantially stronger evidence, a new-method paper. More unit tests, model names, or methods do not by themselves close the scientific gaps.

---

## 2. Project identity and the main scope problem

### Recommended research framing

A defensible working title is:

> **Integrity and Tamper Localization in Dermoscopy: A Controlled Evaluation of Cryptographic, Compact, and Learned Methods**

A suitable central question is:

> **How do image-integrity and localization methods trade off exactness, map coverage, storage, and latency under specified image changes, and what class-sensitive classifier changes accompany those operations?**

This frames the contribution as an **audited, domain-specific evaluation**. It does not claim that the project has invented the cryptographic primitives, watermarking, segmentation, or medical image signatures it uses. If a new-method contribution is later pursued, novelty must be established feature-by-feature against relevant literature and through matched experiments.

### Why the repository can be confusing

The checkout includes, among other things:

- a protocol-v2 RGB HMAC authentication and learned-localization line documented in `PROTOCOL_V2.md` and `RUNNING.md`;
- an adapted 2,500-image ISIC cohort used for detached-signature/localization and classifier studies;
- EditGuard adapter, pilot, and matched validation work;
- a small diagnostic-constrained QIM embedding pilot;
- historical `isic-study-v2` receipts and older experimental artifacts.

These lines have different protocols, cohorts, methods, and evidence levels. **Do not combine their counts or scores as if they came from one matched benchmark.** In particular, the RGB-HMAC protocol and the detached Ed25519 tile-manifest baselines are different systems with different key/trust models and pixel costs.

---

## 2.1 Historical mid-review/poster and transition story

The earlier mid-review deck and poster describe an ISIC 2018 fragile-watermarking experiment, not the current T1 classifier-impact study. They report headline detection/localization figures but also document poor burned-text localization, JPEG coverage failures, and a separate JPEG-Q100 false-claim rate above the stated ceiling. The source artifacts' Drive timestamps postdate the authoritative 2026-10-19 snapshot, and their claimed receipt timestamps are not independently authenticated here. The source PDFs are not redistributed in the public context package because embedded image pixels and licenses have not been screened. See [`MIDREVIEW_POSTER_TRANSITION_RECORD.md`](MIDREVIEW_POSTER_TRANSITION_RECORD.md) for exact historical claims, current-vs-historical guardrails, source links, chronology caveats, and an oral transition script. Treat the old values only as historical reported results, never as current T1 metrics.

---

## 3. Research strands and current status

| Strand | What it studies | Current status | Defensible boundary |
|---|---|---|---|
| **Protocol-v2 RGB HMAC authentication** | A fragile embedded per-block authenticator plus diagnostic/learned localization pipeline for 8-bit RGB images. | Protocol and implementation are documented; engineering/wiring diagnostics exist. A complete multi-seed ISIC study, full ablations, and a valid confirmatory evaluation are not established here. | The HMAC carrier modifies RGB low bits, requires a secret key and trusted version context, and breaks under loss-changing codecs. It is not encryption, a DICOM signature profile, or a clinical deployment. |
| **Detached integrity/localization (Track A)** | Ed25519-signed evidence at Full4/Full8 grids and compact `bounded289`, evaluated on a fixed validation cohort and controlled operators. | 500-image validation receipts reviewed across 15,000 records. Useful measured storage/coverage/latency tradeoffs. No full pixel/operator replay from original images in this runtime. | A tile failure expanded to pixels is not pixel-exact localization. Abstention is not a successful map. This is not a universal Pareto result or a deployed PKI system. |
| **Frozen classifier/operator impact (Track C)** | Class-sensitive changes in the original adapted DenseNet121 under a fixed set of image operations. | 500-image validation return reviewed; 6,000 stored condition rows. Its checkpoint was selected using validation. T1 later added two architectures in a separate 10-operator analysis; see next row. | Operator-associated changes for the stated model/cohort only—not clinical harm, causal biology, robust generalization, or a watermark effect. Stored outputs were not rerun on source pixels here. | 
| **T1 multi-architecture validation** | Original DenseNet121 baseline plus DenseNet121-Aug and ResNet50-Aug on fixed TRAIN/validation; ten standard operators and paired EditGuard conditions. | Returned Kaggle archive passed ZIP integrity and ingestion checks; 30 standard-condition summaries and 48 EditGuard contrast rows. Model source hash matched checked-in code; source/operator hashes, seeds, labels and received-image hashes matched retained references. `test_accessed:false` reported. | Validation-only, same validation cohort used in checkpoint selection; no TEST access, independent source-pixel/model replay, external cohort, or confirmatory generalization. Full metrics/caveats: `deliverables/T1_VALIDATION_RESULTS.md`. |
| **Matched EditGuard + classifier validation** | Operation-by-operation localization and paired classifier contrasts for EditGuard and a Signed4 reader. | Archive structure, row arithmetic, maps, paired summaries, and 500/500 Signed4 signatures passed the documented return audit using a separately supplied raw public key. | Receipt/signature audit only. Source pixels and models were not independently replayed; the public-key issuer is not independently authenticated. Signed4 adds a large sidecar and is not a cost-matched comparison. |
| **Diagnostic-constrained QIM (Track D)** | A small guide-TRAIN pilot of fixed-carrier embedding and non-carrier correction. | 12-image pilot reviewed; unchanged candidate’s stop-gate is closed. | A small negative feasibility result, not a successful method and not evidence that the broader field fails. Do not scale the unchanged candidate or present it as a core result. |
| **Learned refiner and other pilots** | Synthetic diagnostics, small image pilots, capacity/profiling and implementation studies. | Mixed exploratory/engineering artifacts are retained. Some are synthetic-only or use mirror data with non-official provenance/preprocessing. | Keep out of headline efficacy claims unless a specific artifact is independently validated under a declared protocol. |
| **Historical `isic-study-v2` evaluation** | An older run whose receipt reports a 1,000-image test evaluation. | Test access is confirmed; exact membership is unrecoverable from the retained run directory and uploaded collection ZIP. | Later holdout overlap is unknown. The recovery attempt is closed unless authentic original membership evidence appears. |

### 3.1 Protocol-v2 RGB authentication line

`PROTOCOL_V2.md` specifies an 8×8 RGB fragile carrier. In outline, the method canonicalizes 192 RGB sample low bits, computes a 24-byte truncated HMAC-SHA256 over versioned context, an image/version identifier, dimensions, block coordinates, and canonicalized block content, then embeds the tag in low bits. Verification is strict: any block failure rejects the image-level integrity check. The standard profile also includes a semi-robust DCT carrier; the legacy Haar profiles remain historical.

Important limitations encoded in the protocol:

- any JPEG/re-encoding/resizing breaks exact RGB integrity and is reported as content change, not automatically malicious intent;
- embedded low bits change the image and must be measured for fidelity;
- benchmark keys are not production secrets; the receiver needs trusted key and image/version identity handling to prevent replay;
- inputs are 8-bit RGB, not 16-bit or DICOM-native;
- neural scores/counts do not override failed cryptographic authentication;
- the method is explicitly not a reproduction of a published paper.

The protocol-v2 runner documentation belongs to this separate RGB-HMAC/learned-localization line. Its earlier small TRAIN-only diagnostic and incomplete real-image sanity trace do not establish completion of the full multi-seed study. Any legacy `heldout` instructions are withdrawn by the current safe-run guide and `FREEZE_PROTOCOL.md`; do not execute them on the current cohort. This protocol-v2 status is unrelated to completed T1 classifier validation, which used a separate runner and did not access TEST.

### 3.2 Track A: detached exact-integrity evidence and localization

The adapted validation work compares `Full4`, `Full8`, and `bounded289` on 500 validation images with deterministic operators. The retained review reports:

| Method | Additional evidence / image | Local copy / blur IoU | Fine maps on global-operation rows | Copy verification time (approx.) |
|---|---:|---:|---:|---:|
| Full4 | 524,378 B | 0.837 / 0.795 | Available on tested rows | 0.0567 s |
| Full8 | 131,162 B | 0.680 / 0.644 | Available on tested rows | 0.0214 s |
| `bounded289` | 18,620 B (96.45% below Full4) | 0.837 / 0.795 | 0 / 3,500 rows | 1.869 s |

These numbers support a **protocol-specific tradeoff**: the compact method sharply reduces sidecar size and matches Full4 on the two reported local cases, while taking longer and abstaining on the tested global operations. They do not establish that it is the best method overall. The receipts include 15,000 rows; an unchanged blur-surrogate no-op on one image generated one verified no-op row per method. Preserve and describe that case as a no-op, not as successful manipulation detection.

### 3.3 Track C: classifier impact under operators

The returned analysis covers a 500-image validation cohort and 12 conditions (6,000 rows). The central illustrative result is JPEG70 on one frozen adapted DenseNet121:

- Accuracy: **86.40% → 89.20%**.
- Melanoma sensitivity: **58.93% (33/56) → 39.29% (22/56)**.
- Balanced accuracy: **74.40% → 67.39%**, change **−7.006 percentage points**; reported paired image-bootstrap 95% interval **[−13.144, −1.311] points**.
- Always-nonMEL reference: **88.8% accuracy, 50% balanced accuracy, 0% MEL sensitivity**.

The finding is that overall accuracy can conceal class-sensitive changes on this validation comparison. This is the original single-model Track C analysis; T1 is a later, separate three-model validation analysis, summarized in `deliverables/T1_VALIDATION_RESULTS.md`. The correct boundary is the stated models and same validation cohort; no patient-level inference, independent model replay, clinical endpoint, biological mechanism, or causal embedding effect is established. Validation participated in checkpoint selection. The original Track C narrative reports a paired interval of [−13.144, −1.311] points; the later T1 ingestion reports [−13.042, −1.413] for the same rounded baseline JPEG70 point estimate using its recorded bootstrap procedure. Do not silently combine these analysis-specific intervals. White-box FGSM/PGD records, where cited, are adapted development attacks with label/model-gradient access, not black-box robustness evidence.

### 3.4 Matched EditGuard validation return

The completed return contained 500 images × 10 cases and two readers, with 10,000 localization rows, 5,000 paired diagnostic rows, 10,000 map comparisons, and 500 signed packets. The reviewer checked archive structure and CRC, notebook/source identity, row uniqueness and arithmetic, map comparisons, paired summaries, and signatures. All 500 Signed4 packet signatures verified using the separately provided 32-byte public key.

Selected receipt-reported findings:

| Condition | EditGuard pixel recall |
|---|---:|
| Copy32 | 0.714 |
| Local-blur32 surrogate | 0.865 |
| JPEG70 / JPEG85 | 1.000 / 1.000 |
| JPEG95 | 0.010 |
| Resize90 then restore | 1.000 |
| Contrast90 / Contrast110 | <0.001 / 0.049 |
| Gaussian noise 0.05 | 0.811 |
| Intact images | 310/500 positive maps (62% image-level false-positive rate) |

A positive map is not necessarily useful localization: some operation cases have very low recall despite frequent positive maps. Signed4 reported full pixel recall on the tested tampered cases by expanding failed 4×4 tiles, but incurs false-highlight area and adds **524,378 bytes per image** on top of the marked image. It is therefore not an equal-storage end-to-end comparison.

For the intact marked-vs-original classifier contrast, the return reports accuracy 86.4%→88.4%, balanced accuracy 74.4%→64.6% (−9.8 points; paired class-stratified image-bootstrap interval −16.2 to −3.8), MEL sensitivity 58.9%→33.9%, and 40/500 label flips. In the paired embedding-given-operator contrasts, the reported balanced-accuracy changes range from −4.8 to −11.1 points, with unadjusted descriptive bootstrap intervals below zero for all ten conditions. Treat these as receipt-checked contrasts for one validation-selected classifier, not clinical harm or independent replication; there is no multiplicity adjustment or patient-level inference.

**Provenance boundary:** the return audit proves consistency of the received artifacts with the audited protocol and verifies signatures relative to the supplied key. It does not prove the identity of the key issuer, recreate the original pixel inputs, rerun the models/operators, or establish that the returned predictions are independently reproducible.

### 3.5 Track D: QIM stop-gate

The small pilot used 12 guide-TRAIN images (10 nonMEL, 2 MEL). Guided correction matched the fixed output on 11/12. The one changed MEL image’s reported RGB-level MSE rose from approximately **0.0764 to 5.8181**; compared variants did not change predicted classes. A strict equal-distortion gate returned the baseline for all examples. JPEG70 payload bit error was about 50%, so clean decoding does not imply codec robustness.

The fixed-carrier geometry gives a structural bound: if the carrier samples are locked, any nonzero correction outside the carriers adds squared distortion to the fixed baseline. This candidate is closed as a small negative/limited feasibility result. It is not an argument that all diagnostic-aware watermarking fails.

---

## 4. Evidence quality: what is known and what is not

| Evidence class | What is present | What it establishes | What it does not establish |
|---|---|---|---|
| **Implementation/unit tests** | Many repository tests and fixture checks across cryptography, data handling, metrics, notebooks and models. A focused review-test subset recently passed. | Specific code paths satisfy stated test assertions. | Medical performance, effectiveness, novelty, security certification, data provenance or generalization. Do not headline test counts to faculty. |
| **Synthetic/wiring checks** | Synthetic authentication, model wiring, refiner and pilot fixtures; a small T4 wiring execution is reported in the v2 notes. | Some execution paths run on designed fixtures; selected engineering failures can be detected. | Real-image clinical evidence, full GPU reproducibility, SOTA comparison, or test-set validity. |
| **Receipt/metric audits** | Row counts, arithmetic, hashes, map consistency, stored metrics and paired summaries for validation returns. | Internal consistency of the retained records against the audit code and supplied files. | Independent replay from original images/models, trustworthy source execution, issuer identity, or causal interpretation. |
| **Signed-packet verification** | 500/500 packet signatures verify against an externally supplied raw public key. | Packets are cryptographically consistent with that public key. | Who owns the key or whether its issuer is trusted. |
| **Source/data replay** | Original ISIC image pixels and frozen weights were not available in this runtime for the current audits. | Nothing beyond documented receipt-level results. | Reproduction of image operators, inference, or independent numerical confirmation. |
| **Confirmatory evaluation** | No valid independent final evaluation for the current later holdout. Historical v2 test use is confirmed, but membership is unavailable. | The current project must not claim untouched-test generalization. | Disjointness between historical v2 IDs and later holdout, or patient independence. |

The available reviewer scripts and artifact paths are important, but tool consistency does not turn a receipt into a replay. All paper/presentation tables should label the evidence class explicitly.

---

## 5. Data, split, provenance, licensing, and security

### Cohort and split decision

- The adapted cohort manifest contains 2,500 selected records, partitioned as 1,500 TRAIN, 500 validation, and 500 later internal holdout. Preparation receipts report unique source-decoded and prepared RGB hashes with no exact cross-split duplicates **within that cohort**.
- The reported selection is lesion-disjoint, but patient-level linkage/independence is not established. Source-ID ranges are proxies, not verified institutions.
- The separate old `isic-study-v2` receipt reports `test_n=1000`. Its membership manifest/verdict array is missing from both the retained seed-0 run directory and the uploaded membership-evidence ZIP. The ZIP has only aggregate receipts and a collection manifest; the receipt’s expected manifest hash cannot substitute for the absent manifest.
- Exact overlap with the later 500-image holdout is unknown—not proven to overlap, and not proven disjoint. Recovery attempts against the available artifacts are closed. Reopen only if genuine original membership evidence or a source/input bundle that regenerates the exact recorded manifest hash appears.
- Keep the later holdout closed to additional outcome analysis and classify it as non-confirmatory development evidence. A protocol freeze cannot restore its pristine status.

### Source and model provenance

The repository contains some unavailable legacy commit identifiers, receipts whose execution identity cannot be independently validated, and at least one scope mismatch noted in the Gate 0 provenance report. Do not silently repair those historical records. Label unresolved records legacy/unverified and exclude them from headline findings unless original source bundles and run metadata become available.

**PH2 is not a clean unused external test by default.** Historical project files describe PH2 as an earlier pilot/instrument-validation corpus; `scripts/prepare_ph2.py` describes a third-party mirror rather than an official download, and `scripts/build_results.py` describes a lesion-grouped 60/20/20 PH2 split whose heldout portion was opened once. The corresponding `runs/ph2-v1` directory and exact prior membership are not present in the current tree. This is evidence of prior PH2 use, but it does not identify every prior image or establish which of the 200 images were exposed. Therefore the proposed PH2 N=200 external test in the uploaded overhaul plan is **blocked as confirmatory** until genuine prior-use membership and source provenance are reconciled. Do not call PH2 guaranteed-disjoint, and do not calibrate a threshold on all PH2 images and then report those same images as test data.

The uploaded `project-context/FINAL_PROJECT_OVERHAUL_MASTER_INSTRUCTIONS.md` is retained as a user-provided proposal, not a scientific protocol or evidence record. Its prospective model thresholds, PH2 assumptions, capacity claims, and promised outcomes must be treated as hypotheses until independently checked and, where applicable, experimentally observed.

The matched EditGuard return’s exact Drive notebook/archive hashes, key provenance caveat, and audit outputs are recorded in `deliverables/MATCHED_EDITGUARD_VALIDATION_RETURN_REVIEW.md` and the v3 verification-evidence directory. The classifier checkpoint and cohort hashes are recorded in their respective returns. Those hashes identify artifacts; they do not, by themselves, prove who generated them or that source pixels were used as claimed.

### Licensing and privacy

The project uses ISIC 2019 and acknowledges source datasets. The relevant dataset terms are non-commercial and attribution obligations apply. Verify ISIC and upstream method/checkpoint licences before public release or redistribution. Do not put original medical pixels, restricted checkpoints, private keys, or credentials in Git/Drive deliverables. Existing audit returns intentionally exclude original pixels and model weights.

### Security and clinical boundaries

- HMAC-on-image and detached Ed25519 signatures are distinct trust constructions; neither should be described as a DICOM-compliant workflow here.
- A public benchmark key is not a production secret. Freshness, key distribution, signer identity, and trusted image/version identifiers require an external workflow.
- Integrity failure means a mismatch to expected authenticated content; it does not establish malicious intent.
- Distortion/perceptual receipts are not clinical equivalence. The classifier is a research probe, not a clinical system.

---

## 6. What the project can safely claim now

1. **Engineering tradeoff:** on the retained validation protocol, `bounded289` sharply reduces detached sidecar bytes versus Full4 while trading verification time and global-operation fine-map availability.
2. **Class-sensitive evaluation lesson:** in the original single-model Track C and the later three-model T1 validation analysis, JPEG70 increased overall accuracy while reducing MEL sensitivity and BA. T1 also shows architecture-dependent attenuation; all claims remain specific to the validation cohort and are not clinical or test-performance claims.
3. **EditGuard validation observation:** in the returned validation records, intact images had a high positive-map rate and localization recall varied substantially by operation; the Signed4 comparison reported full recall at a large additional-storage cost.
4. **Bounded negative result:** the unchanged QIM correction did not demonstrate a useful advantage in a 12-image TRAIN feasibility pilot; this closes that candidate, not the research area.
5. **Evidence practice:** the project has distinguished receipt consistency, signature verification, and independent pixel/model replay rather than treating them as equivalent.

Every claim above must be labeled by dataset split, method, denominator, and evidence status. Use “reported in the returned receipts” where appropriate.

## 7. Claims that are not supported

Do **not** claim:

- SOTA, novelty, superiority, a universal optimum, or a completed matched benchmark against EditGuard/WAM/OmniGuard;
- that EditGuard, the classifier, or any method was independently reproduced from source pixels/models in this audit;
- untouched, pristine, disjoint, final-test, or confirmatory generalization for the later holdout;
- patient-independent data, verified institutional balance, or cohort representativeness;
- clinical harm, clinical safety, preserved diagnosis, patient benefit, or biological mechanism;
- robust authentication through JPEG/re-encoding for the fragile RGB HMAC protocol;
- DICOM 16-bit support, DICOM-standard compliance, production PKI/key management, or replay prevention;
- exact pixel localization from expanded tile maps;
- claims based only on unit-test counts, synthetic fixtures, the 8-image mirror pilot, or cross-paper scores from incompatible protocols.

---

## 8. Gaps and risks that still matter

### Scientific gaps

- **No valid confirmatory cohort:** the later holdout cannot serve; no new external/prospective cohort is documented here.
- **No independent full replay:** source ISIC pixels and pinned model weights were absent from this audit environment; returned metrics remain receipt-level.
- **T1 multi-architecture validation:** completed and ingested on the fixed TRAIN/validation cohort, with no TEST access. The validation results and per-architecture EditGuard contrasts are summarized in `deliverables/T1_VALIDATION_RESULTS.md` and the two CSV tables. They are validation/development evidence, not confirmatory generalization or independent pixel/model replay.
- **Narrow model evidence:** T1 adds two more architectures, but all three share one fixed validation cohort and validation-based checkpoint selection. No source-pixel/model replay, institution-level external cohort, or confirmatory generalization is established.
- **No verified patient grouping:** lesion-disjoint/exact-hash checks do not prove patient-level independence.
- **No matched-cost SOTA comparison:** methods use different storage, model/checkpoint, runtime and trust costs. Cross-paper reported numbers are not comparable baselines.
- **Threat-model distinction:** exact integrity, benign re-encoding, localized edits, and malicious manipulation must have separately defined expected outcomes. JPEG/contrast changes are not automatically malicious.
- **Multiplicity and uncertainty:** future analyses should predeclare primary metrics and comparisons, account for repeated conditions and group dependence, and preserve failures/abstentions in denominators.
- **No established clinical endpoint:** no prospective workflow, clinician reader study, patient outcome, or clinical utility assessment is documented.
- **Novelty review incomplete:** relevant prior work includes fragile authentication, DICOM signatures, EditGuard, WAM, OmniGuard, medical image watermarking and non-embedding authentication. The literature file itself warns that several bibliography details need verification.

### Reproducibility and project-management gaps

- **Parallel narratives remain by design:** the root RGB-HMAC/protocol-v2 line and the adapted-cohort validation studies are different workstreams. `PROJECT_CONTEXT_MASTER.md` now serves as the current crosswalk; do not merge protocols or results. Some append-only/historical notes retain older planning language and must be read under their dated status corrections.
- **Execution boundary corrected:** `RUNNING.md` now gives safe current instructions, and `FREEZE_PROTOCOL.md` has been replaced by a revocation notice with no runnable TEST switches. Older protocols/notebooks remain historical artifacts; their presence does not authorize executing a holdout stage.
- **Untracked working tree:** the snapshot currently contains hundreds of untracked project files and modified files. A clean-clone build, tracked-file manifest, attribution audit and reproducible release snapshot are not established. Do not bulk-add or delete artifacts without an explicit curation/ownership review.
- **Full regression not verified in this runtime:** a focused audit/documentation subset passed, but the complete Torch-backed suite was not collected because Torch was unavailable. Historical full-suite counts in old documents are not current claims.
- **Packaging and citations:** verify source/checkpoint licenses, DOI/publication metadata, dataset attribution, artifact hashes, and exclusion of sensitive pixels/weights before release.

---

## 9. Recommended next plan, in order

### Phase 0 — Lock the evidence boundary (now)

- Keep the old membership recovery closed; do not inspect the later 500-image holdout for outcomes.
- Treat the decision report and Gate 0 status as controlling; mark older instructions clearly historical or superseded.
- Keep the revised faculty deck focused on integrity/localization/class-sensitive impact. Keep software test counts in engineering QA material only.

**Exit condition:** no slide, abstract, README, or execution guide calls the current cohort untouched or authorizes new analysis on it.

### Phase 1 — Reproducibility and provenance audit

- Build a single inventory of each study line: cohort/protocol, code hash, checkpoint hash, returned artifact hash, evidence class, and allowed claim.
- Recover authentic source commits/logs where possible; otherwise label records legacy/unverified.
- Resolve bibliography and licensing before any public release.
- Curate a clean, tracked source/release snapshot without data pixels, keys, restricted weights, or duplicate stale artifacts.

**Exit condition:** a clean clone can identify which protocol produced every headline number and reproduce the non-data packaging/audit steps.

### Phase 2 — New confirmatory data design

- Obtain a genuinely new authorized cohort, preferably independently sourced or prospectively collected. A new random split of previously used images is not enough.
- Preflight source identity and exact/perceptual duplicates against recoverable development images; if patient/lesion IDs exist, split by verified groups and describe missing linkage honestly.
- Freeze inclusion/exclusion, operations/threat model, methods, primary metrics, sample-size rationale, subgroup plan, confidence intervals, and stop/failure handling before outcome access.

**Exit condition:** a signed, immutable protocol and auditable cohort manifest exist before test outcomes are generated.

### Phase 3 — Independent matched benchmark

- Re-run methods on source pixels and frozen checkpoints, with pinned environments and logs. Verify all numerical metrics from per-image outputs.
- Include strong non-embedding controls (whole-image signature and signed tile-hash manifest) and appropriate learned baselines only when implementations/protocols can be made comparable. Treat incompatible published scores as literature context.
- Compare at declared storage/compute budgets, report pixel/tile localization, map availability, false-positive maps on intact images, per-operation recall/precision/IoU, latency, bytes, and distortion.
- Repeat classifier-impact evaluation with at least one independent architecture and, if possible, another external cohort. Use paired/group-aware uncertainty and distinguish natural image operations from intentional edits.

**Exit condition:** independent source/model replay, complete denominators, uncertainty estimates, costs, failures, and provenance are all auditable.

### Phase 4 — Academic paper and defense package

- Write around the question, protocol, data lineage, matched baselines, primary findings, failure cases, uncertainty, and limitations—not code/test volume.
- State the narrow contribution that the evidence earns. Claim a new method only if prior-art comparison and matched experiments establish a distinct advantage.
- Put unit/integration test details in a short reproducibility appendix. Keep the 12-image QIM result as a bounded negative appendix unless a redesigned study earns a main-text role.
- Release only permitted code/receipts, include environment/source manifests, and obtain supervisor/owner approval for the final scope and licensing.

---

## 10. Project file map and controlling records

| File/location | Role |
|---|---|
| `PROJECT_CONTEXT_MASTER.md` | Authoritative crosswalk/status snapshot; start here. |
| `deliverables/PROJECT_CONTEXT_BUNDLE_2026-10-19.zip` and `deliverables/PACKAGE_MANIFEST.csv` | Curated source/context/evidence package with per-file SHA-256 inventory; raw pixels, weights and unscreened archives excluded. |
| `README.md`, `RUNNING.md`, `PROTOCOL_V2.md` | Root project entry point, safe current run guidance, and the separate RGB-HMAC v2 protocol. Legacy `heldout` workflow is revoked. |
| `src/`, `scripts/`, `tests/` | Implementation, runners, audits and software verification. Tests are engineering evidence, not research outcomes. |
| `deliverables/TEST_SPLIT_RECOVERY_DECISION.md` | Controlling recovery-closed decision and condition for reopening. |
| `deliverables/GATE0_PROVENANCE_STATUS.md` | Split/provenance status, receipt hashes and unresolved source items. |
| `deliverables/CLAIMS_EVIDENCE_LIMITS.md` | Compact claim/evidence/boundary table for academic reuse. |
| `deliverables/T1_VALIDATION_RESULTS.md` and `deliverables/tables/` | T1 three-model validation results, paired EditGuard contrasts, and ingested CSV tables. |
| `deliverables/MATCHED_EDITGUARD_VALIDATION_RETURN_REVIEW.md` | Detailed returned-record metrics and their audit limits. |
| `deliverables/PRESENTATION_DEFENSE_PACK.md` | Faculty-safe opening, slide cues, Q&A, and claim guardrails. |
| `deliverables/PROJECT_PRESENTATION_DRAFT.pptx` and `scripts/build_presentation_draft.py` | Current editable faculty presentation and reproducible generator. |
| `deliverables/verification-evidence/` | Hashes, reviewed receipts, cohort/preparation artifacts and return-audit outputs. These are not source pixels or independent model replays. |
| `docs/ADAPTED_FINALISATION_ROADMAP.md`, `docs/REVIEW_READINESS_PLAN.md`, `docs/STUDY_TO_CONTRIBUTION.md` | Planning/history with current status corrections. Historical pending/running statements are superseded by this overview and the master context. |
| `FREEZE_PROTOCOL.md` | Revocation/tombstone notice only; former TEST commands/switches have been removed. |
| `results/isic-study-v2/seed-0/` and retained membership-evidence ZIP | Aggregate evidence for old `test_n=1000`; insufficient to recover individual IDs. |

---

## 11. Bottom line

The project is not empty and it is not made stronger by inflating claims. It has meaningful implementation, controlled validation receipts, informative failure cases, and a useful domain-specific problem. Its academic strength will come from **one coherent research question, trustworthy data lineage, independent replay, fair matched baselines, patient/group-aware evaluation where possible, transparent uncertainty, and disciplined claims**.

For now, present the completed work as an evidence-calibrated validation study. Keep the later holdout closed. Do not claim SOTA. The decisive next scientific investment is a new provenance-audited cohort and an independently reproducible benchmark—not another software-test headline or a duplicate GPU run.
