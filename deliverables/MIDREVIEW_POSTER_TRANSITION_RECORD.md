# Historical mid-review and poster record — transition evidence, not current status

**Prepared:** 2026-10-19 UTC  
**Purpose:** preserve what the project reported at mid-review/poster stage so the later change in scope can be explained without mixing historical and current results. This is an archival synthesis, not a new experiment or verification of the old image-level results.

> **Read this before quoting the mid-review or poster.** Their metrics belong to an earlier fragile-watermarking system and an ISIC 2018 Task 1 evaluation. They are not results from current T1 classifier validation, the detached-signature/localization comparison, or the current RGB-HMAC protocol-v2 study. Keep the studies, datasets, metrics, and evidence levels separate.

## Historical source artifacts

The source PDFs are retained in their original Google Drive locations. Text was extracted for this record, but the PDFs themselves are not copied into the public context folder or ZIP because their embedded visual content has not been screened for medical-image pixels, source licensing, or redistribution permission.

| Stage artifact | Original Drive file | Original Drive link | Size | Drive created/modified metadata returned |
|---|---|---|---:|---|
| Mid-review | `Major_Project_MidReview_PPT - Murali Cherapaka.pdf` | [Open original mid-review PDF](https://drive.google.com/file/d/1sC0mhoLs7VRvLcfPmuhtvVkZUJeHymAq/view?usp=drivesdk) | 432,031 bytes | 2026-10-21 08:36:44 UTC |
| Poster | `Team06-Final-Poster - Murali Cherapaka.pdf` | [Open original poster PDF](https://drive.google.com/file/d/1GB5OCnoylz-htXmQJsNwEL6lg6zwmM6x/view?usp=drivesdk) | 1,510,060 bytes | 2026-10-25 10:27:35 UTC |

Drive search also found same-size copies named `Major_Project_MidReview_PPT.pdf` and `Team06-Final-Poster.pdf`; their extracted text matched the author-labelled versions. This record cites the author-labelled copies as the chosen references, not as proof that they are the only or final presentation files.

**Date/provenance warning:** both Drive timestamps fall after the authoritative project snapshot date and after today's date (2026-10-19 UTC). They cannot establish when the presentations actually occurred. Treat them as returned metadata anomalies; do not put those dates on a presentation timeline as event dates. No verified event date/time, agenda, or presentation schedule was recovered from these files. Confirm the actual dates with the team/course records before describing when the mid-review or poster presentation happened.

## What the mid-review reported

The deck framed the project as **“Diagnosis-Safe Watermarking for Medical Image Tamper Localization”** and described a keyed, position-bound fragile mark on 8×8 blocks, using two-level integer Haar detail coefficients and a 60-bit QIM tag. The receiver used the returned PNG and key to produce `INTACT`, `TAMPERED`, or `CANNOT_SAY` block-level decisions. The deck explicitly said the system checks post-protection changes, not whether the original image was truthful; it was not a disease-diagnosis system.

The deck reported a primary ISIC 2018 Task 1 evaluation (`n=2,594`, 22 conditions) and cited `runs/isic-full-v8/receipt.json`, code commit `28e4e6e`, and a dataset receipt. Its headline reported values were:

- Copy-move detection: **12,969 / 12,970** cases, reported as 99.99%, at detection IoU threshold ≥0.10 for conditions 1–5.
- Mean localization IoU: **0.9936** for conditions 1–6.
- Benign handling false claims: **0 / 12,970**; clean images claimed tampered: **0 / 2,594**.
- Mean PSNR: **40.47 dB**; mean coverage: **98.7%**.

The deck also retained important failures and trade-offs, which must travel with any use of those numbers:

- Burned-in text (condition 21): mean IoU **0.272**; detection at IoU ≥0.50 **0.0%**; reported silent failures in 98.9% of images and 16.8% of blocks. Detection at a lenient threshold was not precise localization.
- Telea inpainting (condition 22): mean IoU **0.907**, with 6.4% silent changed blocks.
- JPEG Q90 certified only about 0.1% of blocks; Q75/Q50 certified none. Zero false claims did not mean useful coverage under those transformations.
- A separate 300-image JPEG-envelope result reported **2/300 (0.67%)** false claims at Q100, above the stated ≤0.50% ceiling. This was a separate probe, not part of the frozen 22-condition battery.
- The deck's own ablations documented changes to the reader, block-scale claim, content binding, scattered-mismatch abstention, and disabling Carrier B. Their denominators differed and should not be pooled.

These figures are **what the historical deck reported**. Although corresponding receipt files are present in the workspace, their timestamps are later than the 2026-10-19 status date; source pixels and the original execution environment are not available here for replay. The current project record flags those timestamps as future-dated/unauthenticated. Therefore do not present the figures as independently reproduced or as current validated performance. Use the original receipt and protocol only after provenance and chronology are resolved.

## What the poster condensed

The author-labelled poster used the same diagnosis-safe watermarking title and team identity. Its extracted abstract repeated the **99.99% detection** and **0.9936 localization IoU** headline on ISIC 2018 Task 1 (`n=2,594`) and the separate **2/300 false claims at JPEG Q100** result. It also said a learned refinement stage was planned but not yet validated. This is a historical poster statement, not current project status or authorization to claim that the refinement was completed.

The poster is not a new independent result: it is a presentation artifact summarizing that earlier work. Its extracted text is shorter than the mid-review deck, so refer to the deck/receipts for limitations and denominators.

## Transition to the current evidence record

A defensible transition narrative is:

1. **Earlier emphasis:** build and report a fragile-watermark verifier for local tamper evidence. The mid-review deck made the method concrete and reported strong results on its declared ISIC 2018 battery, while also exposing a Q100 false-claim ceiling miss, weak burned-text localization, and near-zero coverage for several JPEG transformations.
2. **Refinement of the research question:** separate integrity, localization, and classifier impact rather than treating them as one end-to-end claim. Compare trust/evidence, distortion, localization coverage, storage, latency, and diagnostic-model effects explicitly.
3. **Current state (2026-10-19 snapshot):** the repository contains multiple distinct strands, not a single successor system. Current T1 is a three-architecture classifier validation study on TRAIN/validation only; detached integrity/localization comparisons and the separate RGB-HMAC protocol have their own protocols and evidence. The unchanged small diagnostic-constrained QIM candidate was evaluated at a 12-image TRAIN feasibility stop-gate and was not scaled.
4. **Current headline from T1:** on the shared validation cohort, JPEG70 increased accuracy while reducing MEL sensitivity across all three architectures. For DenseNet121-Aug, intact validation balanced accuracy was 0.792712 and MEL sensitivity 0.7679; JPEG70 paired BA change was −1.77 pp [−6.80, +3.04]. This is a validation-only classifier-impact result, not a tamper-localization score and not a TEST result.

The transition above is a **safe synthesis of the documented research strands**, not proof that a particular historical failure caused a later design choice. The retained files do not establish a complete dated decision trail from presentation feedback to each subsequent experiment. Avoid claiming causal continuity unless meeting notes, dated commits, or supervisor feedback substantiate it.

## Current-vs-historical claim guardrails

| Topic | Historical mid-review/poster | Current controlling interpretation |
|---|---|---|
| Project unity | One fragile-watermarking story | Multiple distinct study lines; do not pool cohorts or scores as one end-to-end system. |
| Main data/result | ISIC 2018 Task 1, `n=2,594`, v8 receipt claims | T1 is a separate classifier validation on fixed 1,500 TRAIN / 500 validation; it did not access TEST. Historical ISIC 2018 performance is not T1 evidence. |
| Headline metric | Detection 99.99%, mean IoU 0.9936 | Historical reported numbers with unresolved receipt chronology and no independent pixel/model replay in this workspace. Not a current validated claim. |
| Known weakness | Q100 0.67% false claims; poor text localization; coverage failures | Keep these limitations visible whenever the old headline is shown. Do not use only its strongest number. |
| Learned refinement | Poster says planned, not validated | Do not imply completion from the old poster. Current candidate work is separate, narrowly scoped, and stopped at its feasibility gate. |
| Presentation dates | PDF names indicate stages; Drive metadata returns future dates | Actual event dates/times remain unverified. Confirm with course/team records. |

## Recommended short oral transition (evidence-bounded)

“At mid-review, we presented a fragile block-watermarking verifier for detecting and localizing image edits, with reported ISIC 2018 results. The deeper record showed that its headline detection did not remove important limitations: the separate JPEG-Q100 probe exceeded our false-claim ceiling, burned-in text localization was weak, and some benign JPEG settings had almost no committed coverage. We then organized the work into separate integrity/localization and classifier-impact questions. Our current T1 evidence is a distinct validation-only three-model study: JPEG70 increased accuracy but reduced melanoma sensitivity across architectures. We are careful not to present that as a TEST result, as a replication of the old watermark study, or as proof of clinical harm. The historical deck and poster are retained as stage evidence, while their dates and original image-level receipts still need provenance confirmation.”

## Archival handling

- This text record is included in the curated context package and is the safe portable summary for transition discussion.
- The source PDFs remain linked above in their original Drive folders. Do not copy them into the public context folder until embedded image pixels, licenses, and permissions are screened.
- Keep the mid-review/poster metrics in a **historical** section only. They must not overwrite the current master status or be silently relabelled as current T1 results.
