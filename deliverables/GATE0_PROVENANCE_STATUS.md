# Gate 0 provenance and evaluation-state check

**Status reviewed:** 2026-10-19 UTC  
**Scope:** retained provenance audit of relevant local receipts, cohort manifests, Git objects, Drive return artifacts and review outputs. No source images or models were replayed in that audit. The separate T1 Kaggle validation return is summarized in `deliverables/T1_VALIDATION_RESULTS.md`; it did not access TEST. Dates later than 2026-10-19 appearing in retained receipts or older addenda are future-dated relative to this status and must be treated as unauthenticated, not silently accepted as chronology.

## Status: RECOVERY CLOSED; confirmatory testing on current holdout blocked

The local artifacts confirm that an earlier ISIC-study-v2 run evaluated a 1,000-item `test` split. The uploaded seed-0 evidence ZIP contains only the two aggregate receipts and a collection manifest—no per-image membership manifest or verdict NPZ—so overlap with the later adapted 2,500-image cohort cannot be determined. Per the decision in `deliverables/TEST_SPLIT_RECOVERY_DECISION.md`, stop recovery attempts against available artifacts and treat exact membership as unrecoverable unless original evidence later appears. The current 500-image holdout is non-confirmatory; do not call it untouched or open it for additional outcome analysis. Separately, the matched EditGuard return was audited, and its uploaded public key verified all 500 Signed4 signatures.

## Findings

| Check | Observation | Status |
|---|---|---|
| Historical test access | `results/isic-study-v2/seed-0/C0_count.json` reports `n=1000`, `test_n=1000`; parameters include `test_n=1000`. The project runner has a normal path that scores test controls/models. | **Confirmed accessed** |
| Old test membership | Both the local `results/isic-study-v2/seed-0` directory and the uploaded collection ZIP contain aggregate JSON receipts only. No exact per-image verdict archive or test manifest was provided; recovery is closed by decision. | **Unrecoverable from available evidence; overlap unknown** |
| Later cohort | `adapted-isic2019-cohort-v1.json` specifies 1,500 train / 500 validation / 500 test and says 48 previous images were excluded. The preparation review checks exact duplicate/group membership within this cohort, but lacks old v2 membership and does not establish patient independence. | **Cohort receipt consistent; historical overlap unresolved** |
| Source revisions | Git cannot resolve v2 commit `6dc18a4` or v8 commit `28e4e6ec66fbe3ff720c03cc4d506f158e88798d` in this checkout. | **Not source-reproducible here** |
| Receipt dates | v2 records `2026-11-03T10:42:53`; v8 records `2026-10-20T23:46:07+00:00`. Both are later than the authoritative status date 2026-10-19 UTC. | **Future-dated relative to this status; timestamp authenticity and chronology unverified. Do not present as proven execution times.** |
| v8 dataset identity | v8 receipt says `datasets\\isic2018` while `dataset_is_primary=true`, despite the current ISIC2019 primary-study framing. | **Scope mismatch; separate from timestamp issue** |
| Matched EditGuard return | Three Drive parts were assembled (archive SHA-256 `33ac519371e373081ae60ddd7f44ff8c55168e6fea43458c6a395297764997a9`) and the exact Drive notebook was audited. All 10,000 localization rows, 5,000 diagnostic rows and 10,000 packed masks passed structural/arithmetic checks. The separately uploaded raw key verified all 500 Ed25519 signatures. | **Receipt and signature audit passed; issuer identity not independently authenticated** |
| v2 membership collection ZIP | Uploaded ZIP hash `8cc66bad8fe9e75bfccb1e02b3c5432bfd5f79d8747482350b0bdf0793d26315`; CRC passed. It includes `C0_count.json`, `C0_B.json`, and `collection_manifest.json`. Included-file hashes match that manifest, and both JSON receipts semantically match local copies; they provide no `manifest.json` or verdict `image_id` array. | **Archive/receipt consistency checked; test membership still unavailable** |

## Local artifact hashes

These hashes identify the exact files inspected in this check; they do not authenticate the underlying historical run.

- `results/isic-study-v2/seed-0/C0_count.json`: `25cd7f71567721a4aa7949f05cf7fb5933bd5ffd568b027a6d3dd59826a8482c`
- `runs/isic-full-v8/receipt.json`: `54f6f849ecf57768755bd9a739edf38309a6ed659a057c93144868969bf9ec9d`
- Uploaded membership-evidence ZIP: `8cc66bad8fe9e75bfccb1e02b3c5432bfd5f79d8747482350b0bdf0793d26315` (retained at `deliverables/verification-evidence/isic-study-v2-seed-0-membership-evidence.zip`)
- `deliverables/verification-evidence/adapted-isic2019-cohort-v1.json`: `c524a43fce2951dbd68514a94d60610a8daa4f88fd40b8b93c53ee1f03f5aa42`
- `deliverables/verification-evidence/adapted-isic2500-preparation-v2/review.json`: `3bdc015ba88df9733fe27c80304647929ed5fb4ce852734539647acf94b5cca3`
- Executed Drive notebook copy `google_drive/matched_editguard_validation_v1.ipynb`: `9107ca9bead8b9770a562a9375ba990f432e3b96dfb524696847f318e1193b9e`
- Updated local notebook package-cell copy `deliverables/matched_editguard_validation_v1.ipynb`: `d3eea3aeb3969145d264a75ecfc0d880daa2e4405be13a2b1752f941693842c3`
- Current return reviewer `scripts/review_matched_editguard_validation.py`: `9783ee3ac229bb8dfe431400279a81079a03c598ea224f97206e760ca4b61333`

## Required next inputs/actions

1. Recovery is closed under `deliverables/TEST_SPLIT_RECOVERY_DECISION.md`; reopen only if the actual original manifest/verdict archive or a source/input bundle that reproduces the exact recorded manifest hash appears.
2. Recover source bundles for the cited commits and original run logs/metadata. If not recoverable, retain and label these receipts as legacy/unverified, outside headline results.
3. For future runs, fix the notebook packaging cell to include `public-key.bin`; this completed return's separately uploaded key has now verified all 500 signatures.
4. Keep the later 500-image split closed to further outcome analysis and classify it as non-confirmatory development evidence. A future confirmatory study requires a new cohort and frozen protocol. No new GPU job was launched in this audit.

## Gate decision

**Gate 0 disposition: recovery closed; confirmatory TEST blocked for the current cohort.** The old test access is confirmed, but its membership cannot be recovered from the available artifacts. The later 500-image holdout may or may not overlap it; no overlap claim is justified. Treat that split as non-confirmatory development evidence. The matched EditGuard return passed structural, arithmetic and packet-signature checks with the uploaded key; no independent pixel/model replay was performed.
