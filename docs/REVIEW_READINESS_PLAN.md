# Review-readiness assessment and execution priorities

**Current status: 2026-10-19 UTC.** This file retains an older planning log; later pending/running statements are historical and superseded by `PROJECT_CONTEXT_MASTER.md`, `deliverables/T1_VALIDATION_RESULTS.md`, and the return reviews. T1 is now returned/ingested on TRAIN/validation only; matched EditGuard is receipt-audited; the 12-image diagnostic-correction pilot is complete and negative/limited. No TEST access is authorized. The former 2026-11-24 dated notes are future-dated relative to this status, so their timestamp assertions are not accepted.

## Executive decision

The best defensible project today is an **evidence-backed comparative study with an implemented experimental extension**, not a demonstrated new SOTA watermark. Present the measured evidence-budget tradeoff as the main completed finding; present payload-locked diagnostic correction as an implemented but limited/negative experimental result. T1 adds validation-stage multi-architecture classifier-impact evidence; it does not close the embedding-efficacy gap, establish clinical utility, or provide confirmatory testing.

A strong review needs a coherent question and fair comparisons more than additional model names. Do not hide null outcomes, retrofit a clinical motivation, or spend the final test repeatedly trying to obtain a positive result.

## One coherent research question

**What can we guarantee about image integrity, what can we localise under an evidence budget, and what diagnostic effects remain when we modify protected images?**

Three separate outputs answer different parts:

1. Signed integrity verification: exact RGB consistency with a signed reference under a trusted public key, not proof of patient identity, acquisition authenticity or freshness.
2. Localisation: exact/expanded block evidence versus learned estimates, with coverage and abstention reported separately.
3. Diagnostic impact: paired predictions and label-based performance from a frozen, imperfect research classifier; not a clinical guarantee.

The diagnostic-correction extension is **not required** for the zero-distortion signed method. It is an additional embedding experiment. Do not draw one pipeline diagram that falsely makes it part of every completed experiment.

## Current evidence and how far it supports us

| Component | Evidence available | Defensible statement | Missing before stronger claim |
|---|---|---|---|
| Compact signed evidence | 500 validation images, 15,000 records; returned archive review | 96.45% smaller than full4; matching maps on copy/blur; slower verification; no compact maps on seven global operators | Independent operator/pixel replay; final frozen test; deployment key trust |
| Learned refiners | Development failures and seven-fixture synthetic diagnostic | Current selected rule fails; attention has not solved localisation | Actual revised training and independent validation, only under a new versioned protocol |
| EditGuard | Matched validation return and T1 paired validation contrasts; receipt structure/arithmetic and supplied-key signatures audited | Operation-dependent localization and architecture-dependent classifier contrasts are reported in validation returns | Source-pixel/model replay, issuer identity, equal-cost end-to-end comparison, new confirmatory cohort |
| Original DenseNet121 | Reviewed 20-epoch return, epoch 3 selected; used in Track C and T1 comparisons | Baseline validation BA .74397, AUC .84540, MEL sensitivity .58929 | Independent prediction replay; external cohort; no test access to later holdout |
| T1 multi-architecture | Returned/ingested 500-image validation, 3 models × 10 operators plus paired EditGuard cases | DenseNet121-Aug BA .7927; ResNet50-Aug BA .7573; JPEG70 accuracy rose while MEL sensitivity fell across all three | Shared validation cohort, validation-based checkpoint selection, no independent replay or confirmatory generalization |
| Diagnostic correction | Synthetic mechanism checks and receipt-reviewed 12-image TRAIN pilot; stop-gate closed for unchanged candidate | Carrier preservation works in tested settings; pilot shows no useful demonstrated class benefit and one distortion-increasing change | Do not scale unchanged candidate; independent evaluator/generalization not established. A redesign needs new protocol and prior-art review. |

Evidence paths: `adapted-validation500-v1/analysis.json`, `adapted-classifier-return-v1/review.json`, `diagnostic-embedding-mechanism-v1.json`, and `refiner-failure-diagnostic-v3/` under `deliverables/verification-evidence/`.

## Most consequential weaknesses, ranked

### P0: Claims must match actual experiment contracts

**Risk:** Calling message recovery authentication, calling absent maps zero error, or claiming diagnostic preservation from one guide confidence.

**Action:** Put an explicit contract next to every result. A decoded payload may survive non-carrier edits. A signature detects changes but does not guarantee diagnosis or legitimate origin without key/identity infrastructure. Global exact-pixel changes are integrity violations even when visually benign. Report compact map coverage as 0/3500, not successful tolerance.

**Review-ready condition:** Every headline has evidence provenance and a scope statement; no unsupported novelty, clinical safety or universal robustness language.

### P0: The new extension needs a genuinely discriminating experiment

**Risk:** Guide KL improvement is partly guaranteed by candidate selection; it is not a useful discovery alone. Our synthetic random control ties the guided correction and the unseen model deteriorates.

**Action:** First run the bounded first-N TRAIN pilot without modifying the running notebook. Record fixed and weaker QIM, energy-matched random and guided outputs, failures, added distortion and full authentication packet cost. If the guide barely changes under fixed QIM, report a floor effect rather than enlarge the perturbation until it produces a dramatic result.

**Go/no-go:** Carrier invariants and clean recovery must hold. If the candidate produces no change, fails recovery, or buys guide agreement only with greater distortion and no advantage over random, do not headline efficacy. An independent evaluator is required before a transfer-preservation claim. A second seed of the same architecture is useful but weaker than architecture/dataset shift.

**Fairness improvement required before final claims:** Add best-of-K random candidates with the same guide-query budget and selection rule, plus a distortion-constrained comparison. Current random control is energy matched but not compute/query matched. The weaker baseline changes recovery margin and is not robustness matched. Added corrections can alter robustness under subsequent attacks even when clean carriers match.

### P0: Main method versus signed-manifest baseline

**Risk:** A standard signed full tile manifest may already be the practical winner: no image distortion, faster verification and complete coverage, at larger storage cost.

**Action:** Present a Pareto analysis, not a winner score. Compare packet bytes, signing/verification time, localisation quality conditional on availability, unconditional changed-pixel coverage, and whether an external reference is needed. Keep image dimensions, tile sizes and threat model explicit. An equal-container comparison isolates the reader; it does not establish equal cost or end-to-end superiority.

**Review-ready condition:** Include the inconvenient latency and global-coverage results beside storage savings.

### P1: Clinical probe quality and interpretation

The classifier misses 23/56 melanomas on validation. Its raw accuracy (.864) is below always-nonMEL (.888), while balanced accuracy is much better (.744 vs .5). Show all of those together. Validation selected the checkpoint: bootstrap intervals are descriptive and selection-biased.

The running notebook evaluates original-image operator effects. It does not show that the watermark caused those effects. For causal embedding attribution, compare original, watermarked, operated original and operated watermarked images using the same operator parameters. Partition images by whether clean predictions were originally correct; count wrong-to-right and right-to-wrong changes separately. This is a future protocol requirement, not a completed experiment. Do not tune thresholds after observing validation changes and then call them frozen.

### P1: Close prior-art overlap before naming a new method

Known overlap: faculty coauthored ROI/RONI DWT-SVD protection, PFF-WM saliency/explanation alignment, and MedSign pathology-aware preservation. Fixed carriers plus classifier-guided correction may be a narrower engineering formulation, but constrained optimisation and classifier-preserving watermarking require further primary-source review.

Additional search leads, **not established novelty conclusions**:
- *Adversarial Watermarking for Face Recognition*, https://arxiv.org/pdf/2409.16056 — search excerpt describes watermark/perturbation interaction and recognition failures; different task and adversarial objective. Full methods not reviewed here.
- *Conceptwm: A Diffusion Model Watermark for Concept Protection*, https://arxiv.org/html/2411.11688v1 — search excerpt describes fidelity-preserving perturbation modulation balancing watermarking and adversarial objectives; generated/concept setting differs. Full methods not reviewed here.

Search results are leads only, not reproduced evidence. Avoid “first”, “unique” and “novel” until a feature-by-feature primary-source comparison supports the exact claim. Do not train another architecture solely to make the system look complex.

## Execution sequence while the impact notebook runs

1. Complete this claim audit and review narrative; do not change sent notebook sources.
2. Prepare a return reviewer for the impact ZIP before inspecting outcomes: source/cohort/hash checks, exact 500-image × declared-case matrix, same labels/order, complete summary, finite probabilities and independently recomputed paired metrics. This is the next highest-value implementation task.
3. Review the returned impact evidence, including sensitivity, not only prediction agreement. Report failure/completion status explicitly.
4. Execute the bounded TRAIN embedding pilot on the existing reviewed guide when original prepared images/GPU capacity are available; no concurrent unrequested Kaggle workload.
5. Add matched-query and distortion controls before an efficacy study; obtain independent evaluator evidence.
6. Run actual matched baseline validation. Freeze all methods and reporting choices before opening the held-out test.

Do not delay review preparation waiting for a positive extension result. A well-explained negative extension is acceptable evidence; it is not proof of a useful new method.

## Suggested eight-slide technical story

1. **Problem and contracts:** authentication, localisation and diagnostic effects are distinct.
2. **Prior work:** faculty ROI/RONI paper, PFF-WM, MedSign, EditGuard and signed-manifest control; specify reproduced versus literature-only.
3. **Protocol:** cohort 1500/500/500, lesion-disjoint not proven patient-independent; frozen operator definitions and model selection.
4. **Completed tradeoff study:** evidence bytes, latency, map coverage and local IoU on the same slide. Include abstentions.
5. **Failed approaches:** refiner failure, threshold false positives and concrete lessons; no invented rescue.
6. **Implemented extension:** fixed carriers, bounded non-carrier correction, blind recovery and separate signatures. Label synthetic evidence visibly.
7. **Diagnostic evidence:** reviewed baseline first; add impact results only after ZIP review. Show unseen-guide counterexample, not merely lower guide KL.
8. **Conclusion:** demonstrated findings, candidate status, unresolved novelty, and exact next verification gates. Do not end with a generic “future work” list that implies undone experiments are completed.

## Concise answers for a critical review

**What is new?** “We have implemented a fixed-carrier, diagnostic-constrained correction prototype and controlled tests. Its useful advantage and novelty are not yet established. Our completed contribution so far is the audited comparative tradeoff study.”

**Why not use signatures alone?** “Full signed evidence is a strong zero-distortion baseline. Compact evidence saves bytes but costs latency and localisation coverage. Our results do not establish that embedding is always preferable.”

**Did your studies lead to this design?** “They motivated separating integrity from localisation and testing diagnostic constraints explicitly. They did not measure clinical harm from embedding; that motivation remains a prospective hypothesis.”

**Does high PSNR prove diagnostic preservation?** “No. Neither does guide agreement. We report label-based effects and independent-model checks where available, and do not claim clinical safety.”

**Can you claim SOTA?** “No. Published and adapted experiments differ; a matched, complete-cost comparison is still required.”

## Deliverable standard

The strongest final package contains: a one-page claims table, versioned protocols, reviewed result receipts with hashes, per-image paired data, reproducible analysis code, a brief demo of both success and failure, and a short limitations slide. Software test counts support implementation reliability only; they do not substitute for medical, security or novelty evidence.

## Implemented follow-through: impact return audit

`scripts/review_classifier_impact_return.py` now reviews the external notebook's ZIP without executing returned code. It checks ZIP membership/CRC, bundled Python source bytes against the actual sent impact notebook, cohort/preparation membership, reviewed checkpoint identity/protocol, declared operator and attack settings, the 500×12 matrix, labels, probabilities, seeds, hash/change-count consistency and attack Linf bounds. It independently recomputes all summary metrics and paired bootstrap intervals from the stored probabilities and compares them with the returned summary. It also flags clean-probability differences versus the training receipt for investigation rather than silently treating environments as identical.

This is still **receipt validation, not image/attack replay**: it cannot independently prove that claimed output pixels, transforms, or probabilities came from the declared model. Fine-grained per-row transform parameters are not regenerated. Source identity does not provide third-party trust. Eleven new tests cover malformed/missing/duplicate rows, probabilities, labels, attack bounds, forged summary values, a complete synthetic 500×12 return and altered returned source rejection. The synthetic return is a test fixture, not a new medical result.

**Historical pre-return note (superseded):** the prior draft said the notebook was still running and no return had been reviewed. That statement is no longer current. The completed Track C return review is documented immediately below; T1's separate validation return is documented in `deliverables/T1_VALIDATION_RESULTS.md`. Historical test counts in this plan are not a current full-suite result.

## Impact return is now reviewed (supersedes pending-impact notes above)

Downloaded Drive `1YF8N-hbbx_oQURalTj4_BYHge_ezwdja`, 1,001,846-byte ZIP; SHA256 `ab49421ea76a2d193be4d7e0cdf79f835ce2d4bc1f76e70680c298d913cc1e20`. Review passed on 500 images ×12 cases, all summary metrics/intervals recomputed. Maximum clean probability discrepancy from training receipt: 9.5367431640625e-07. Evidence: `deliverables/verification-evidence/classifier-impact-return-v1/`. Human-readable report: `deliverables/classifier-impact-validation500-review.html`.

JPEG70 drops BA 74.40%→67.39% and melanoma sensitivity 33/56→22/56, despite accuracy increasing 86.4%→89.2%. Thus raw accuracy is demonstrably misleading in this comparison. The local copy and blur surrogate cause 4 and 1 prediction flips; these are not verified lesion-removal operators. White-box adapted PGD makes 430/432 initially correct images incorrect (99.54%); recorded overall errors are 498/500. These are results of a ground-truth-label, model-gradient-access attack, not black-box robustness or embedding-effect results. This analysis used validation only; however, a historical ISIC-study-v2 test evaluation exists, and membership overlap with the later holdout is unrecoverable. The later holdout is non-confirmatory under the current disposition in `deliverables/TEST_SPLIT_RECOVERY_DECISION.md`. Do not retrospectively claim this experiment originally motivated code implemented earlier.

The TRAIN12 embedding feasibility pilot is complete and the unchanged candidate is closed at its stop-gate; see `deliverables/DIAGNOSTIC_EMBEDDING_PILOT_REVIEW_ADDENDUM.txt`. T1 multi-architecture validation is also complete on TRAIN/validation only; see `deliverables/T1_VALIDATION_RESULTS.md`. Remaining research priority is provenance/licensing cleanup and a genuinely new confirmatory cohort, not another analysis of the closed holdout. Medical benefit, novelty and SOTA superiority remain unestablished.
