# Presentation defense pack — evidence-led version

**Status date: 2026-10-19 UTC.** T1 multi-architecture validation has been ingested on the fixed 1,500 TRAIN / 500 validation cohort; it reports `test_accessed:false`. The separate matched EditGuard validation return was also audited. Neither return was independently replayed from original image pixels/models in this environment. An earlier `isic-study-v2` receipt reports 1,000 TEST items, but exact membership is unavailable; overlap with the later 500-image holdout is unknown. The holdout is non-confirmatory development evidence and closed to further outcome analysis. `FREEZE_PROTOCOL.md` is now a revocation notice, not a usable TEST plan. Historical records with dates after 2026-10-19 are future-dated and not validated timestamps.

## Historical transition framing — use before current results

The earlier mid-review and poster describe a **different ISIC 2018 fragile-watermarking study**. The mid-review reported 99.99% copy-move detection and mean localization IoU .9936, but it also documented 2/300 (0.67%) false claims in a separate JPEG-Q100 probe, weak burned-text localization (mean IoU .272; 0% at IoU ≥.50), and near-zero JPEG Q75/Q50 coverage. Present those only as historical reported results with their limitations, not as current T1 metrics. Their source PDF metadata dates are future-dated relative to this 2026-10-19 snapshot, and the receipt timestamps are not authenticated; the actual event date remains unverified. See `deliverables/MIDREVIEW_POSTER_TRANSITION_RECORD.md` for citations and the full transition script.

## 60-second opening

“At mid-review we presented a fragile watermark verifier for local tamper evidence. Its reported headline results came with a Q100 false-claim miss and weak text localization. We then organized the project around separate integrity, localization, and classifier-impact questions. Our current validation evidence is not a replication of that earlier study. We compare three contracts in dermoscopic image protection: exact integrity, tamper localization, and diagnostic-model impact. In validation-only studies, compact signed evidence reduced storage while trading off localization coverage and latency. T1 evaluated three classifiers on the same 500-image validation cohort: under JPEG70, accuracy rose for all three while melanoma sensitivity fell; the drop was smaller for DenseNet121-Aug than the baseline but not for ResNet50-Aug. EditGuard localization varied by operation and had positive maps on 62% of intact images in a separate returned validation study. These findings remain specific to the methods and validation protocols studied and require a new provenance-audited cohort for confirmation.”

## Experimental protocol and provenance

We checked the returned validation records against the declared cohort, operation settings, row arithmetic, and packet signatures; this environment did not rerun the original image transformations or classifier inference. The historical v2 test membership remains unidentified, so the later ISIC holdout is excluded from confirmatory analysis. PH2 also has prior development use in this repository and is not a clean external test until that history is reconciled.

## Slide-by-slide speaking cues

1. **Title and status:** We frame the work as a dermoscopy-focused controlled comparison and name the three technical contracts.
2. **Transition (historical vs current):** distinguish the old ISIC 2018 QIM watermark report from current studies; pair headline results with Q100/text/JPEG-coverage failures; state that date and receipt chronology are unresolved. Do not imply the old numbers are T1 or that historical failures caused later changes without a dated decision record.
3. **Research question and contracts:** We separate exact integrity, localization, and diagnostic impact. A failed signature does not establish intent; a localization map is not authentication; a classifier shift is not clinical harm.
4. **Cohort and protocol:** We report the TRAIN pilot pool and validation cohort used by the analyses. We explain that earlier test IDs are unavailable and the later holdout is excluded from confirmatory claims. Lesion-disjoint selection does not establish patient-level independence.
5. **Track A:** We report both sides of the tradeoff: 18,620 versus 524,378 bytes per image (96.45% less), local-edit IoU matching Full4 in the two tested local cases, 0/3,500 fine maps on seven global cases, and approximately 1.87 s versus 0.057 s verification for copy. Full8 has copy/blur IoU .680/.644 and about .021 s verification. We count abstentions separately from successful maps.
6. **Classifier impact (Track C + T1):** Keep the original single-model Track C result distinct from T1. Track C's original DenseNet121 JPEG70 comparison: accuracy 86.4%→89.2%, MEL sensitivity 58.93% (33/56)→39.29% (22/56), and BA change −7.01 pp. T1 intact validation BA/sensitivity were 0.7440/0.5893 (base), 0.7927/0.7679 (DenseNet121-Aug), and 0.7573/0.6250 (ResNet50-Aug). JPEG70 accuracy rose for all three (+2.80/+2.40/+3.60 pp), while MEL sensitivity fell (−19.64/−7.14/−21.43 pp). This shows the paradox persisted on this shared validation cohort, with augmentation architecture-dependent; it does not establish test or clinical performance. Report source-image/model replay as not independently performed.
7. **Matched EditGuard validation:** We report positive maps on 310/500 intact images (62%) and operation-specific recall. Signed4 reported full recall on tested tampered cases but adds 524,378 bytes/image and expands tiles; our comparison is not equal-cost. We describe these as results checked from returned records.
8. **Evidence matrix:** We use the matrix to distinguish contracts and costs, not to claim a leaderboard or matched-cost SOTA comparison. We keep the small QIM feasibility result in the appendix.
9. **Close:** We summarize the measured storage/coverage/latency tradeoff, operation-dependent localization, and class-sensitive classifier result. We identify a new, provenance-audited cohort as a requirement for future confirmation.
10. **References:** We use DICOM/EdDSA and prior watermarking papers as context, not as reproduced results. We verify bibliography details and permissions before public release.
11. **Backup appendix:** We describe the 12-image QIM pilot as a bounded negative feasibility result, not as the main contribution or evidence against the broader field.

## Likely questions and concise, defensible answers

**What is the main contribution?**  
“The strongest completed contribution is an audited comparison of exact signed-integrity/localisation methods under explicit storage, latency, coverage, and diagnostic-impact reporting. The embedding extension is implemented and experimentally bounded, but we do not claim it is advantageous or novel.”

**Why not just use the full signed manifest?**  
“It is a strong zero-distortion baseline with dense coverage and faster verification in our measured implementation. Compact evidence uses much less storage, but is slower and abstains on several global changes. The results support a tradeoff, not a universal winner.”

**Does JPEG70 show that watermarking harms melanoma diagnosis?**  
“No. That study applied JPEG to original validation images; it measures operator-associated changes in one adapted classifier. It does not isolate an embedding effect or establish clinical harm.”

**Why did accuracy improve when sensitivity worsened?**  
“The validation set is imbalanced (444 nonMEL, 56 MEL). More correct nonMEL predictions can raise overall accuracy while melanoma recall falls. That is why we report sensitivity and balanced accuracy alongside accuracy.”

**Is your cohort patient-independent?**  
“We established lesion-disjoint selection and found no exact cross-split RGB hash duplicates in the preparation receipts. We did not establish patient-level independence, perceptual-hash separation, or source institution balance.”

**Is your method novel or state of the art?**  
“We do not claim either. The cryptographic primitives and fixed-carrier QIM are established components; prior-art overlap needs a feature-by-feature review. We report what our adapted experiments actually measured.”

**Why include a negative embedding result?**  
“It documents a predeclared feasibility boundary: the unchanged candidate did not provide a useful demonstrated advantage under this small TRAIN pilot. Keeping that result prevents us from presenting only favourable cases.”

**How did we verify the matched EditGuard results?**  
“We checked the returned records for completeness, metric arithmetic, map consistency, and valid Signed4 signatures under the supplied key. We did not rerun the image transformations or classifier inference, and we have not established who controlled the signing key.”

**What is the status of the final-test evidence?**  
“An earlier ISIC-study-v2 run evaluated 1,000 test images, but the exact IDs are no longer available in the retained run files or uploaded collection. We cannot determine whether those IDs overlap the later 500-image holdout. We therefore do not call that holdout untouched, do not use it for confirmatory claims, and will not inspect it further. A confirmatory result would require a new cohort and frozen protocol.”

**Can we use all 200 PH2 images as a fresh external test?**  
“Not on the current record. Earlier project files document PH2 development and a held-out evaluation, but the original membership is not present here. We must reconcile prior image exposure before treating any PH2 subset as external confirmation; threshold selection cannot be performed on the final test set.”

**Is this clinically safe or deployment-ready?**  
“No. The classifier is a limited research probe, not a clinical model. The work does not establish patient-level generalisation, clinical utility, trusted key infrastructure, or a DICOM deployment workflow.”

## Claim guardrails for the final slides and report

| Safe wording | Avoid |
|---|---|
| “96.45% less sidecar storage than Full4 in this protocol” | “96% more efficient overall” |
| “No fine map available for 3,500 global-operation rows” | “Robust to benign global changes” |
| “MEL sensitivity fell on this validation comparison” | “JPEG/watermarking causes melanoma misses in practice” |
| “Small TRAIN feasibility pilot; no useful advantage demonstrated” | “Our novel method failed universally” or “clinical preservation achieved” |
| “Lesion-disjoint; patient independence unverified” | “Patient-independent cohort” |
| “We checked the returned records against the declared validation protocol; we did not rerun image transformations or model inference locally” | “EditGuard independently reproduced” / “clinically validated” |
| “Historical v2 test was evaluated; later holdout overlap is unknown and non-confirmatory” | “Final test untouched” / “Final test confirms generalisation” |

## Test-split disposition and next study

We preserved the matched EditGuard return and checked its records against the declared protocol. The separate v2 recovery bundle contains aggregate records but no per-image test membership. We have closed recovery against the available artifacts, classified the later 500-image holdout as non-confirmatory development evidence, and will not inspect it for further outcomes. The draft in `FREEZE_PROTOCOL.md` does not authorize evaluation of this cohort. A future confirmatory study requires a new cohort with auditable provenance and a protocol frozen before outcome access.
