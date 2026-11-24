# Test-split recovery and disposition decision

**Current disposition recorded:** 2026-10-19 UTC. An older header carried the future date 2026-11-24; that date is not accepted as a valid chronology as of this record.  
**Decision:** Treat exact membership of the historical `isic-study-v2` 1,000-image test evaluation as **unrecoverable from the retained project artifacts reviewed**. Stop attempting to recover it from the searched seed-0 folder and collection bundle. Reopen only if a genuine original run archive, manifest, verdict-ID artifact, or source/input bundle is later found.

## Evidence reviewed

- The retained `results/isic-study-v2/seed-0/C0_count.json` records `n=1000`, `test_n=1000`, protocol `isic-study-v2`, commit `6dc18a4`, and expected manifest hash `47cf4f949c3005556da3b06df28f90eeba8e0138efdf305ddd0ea9a7aac339c9`.
- `C0_B.json` carries the same run-identifying fields.
- The uploaded collection ZIP `isic-study-v2-seed-0-membership-evidence.zip` has SHA-256 `8cc66bad8fe9e75bfccb1e02b3c5432bfd5f79d8747482350b0bdf0793d26315`; its CRC passes. It contains only `C0_count.json`, `C0_B.json`, and `collection_manifest.json`. Those receipts are semantically consistent with the local copies.
- Neither the matching retained run folder nor the collection ZIP contains `manifest.json`, `experiment.json`, `C0_count_verdicts.npz`, `C0_B_verdicts.npz`, or a run-specific execution/source manifest. Therefore the expected manifest hash cannot be recomputed and the 1,000 test IDs cannot be extracted or matched against the later cohort from the available evidence.

This conclusion is an operational disposition of the available evidence, not a claim that no external backup could ever exist. The prior manifest hash inside a receipt is not a substitute for the missing manifest.

## Consequences for claims and evaluation

1. Record that the **ISIC-study-v2 test partition was evaluated**. Do not say that the project has never accessed test data.
2. Historical membership overlap between those 1,000 images and the later 500-image internal holdout is **unknown**—neither overlap nor disjointness has been established.
3. Retire “Final TEST untouched,” “pristine holdout,” and confirmatory/generalization claims based on the later 500-image holdout. For project reporting, classify it as **non-confirmatory development evidence with historical overlap unresolved**.
4. Do not open that 500-image split for additional performance analysis or model/threshold selection. Preserve existing artifacts unchanged and label their evidence status; do not delete or rewrite history.
5. If a confirmatory estimate is required, define a new evaluation cohort/protocol only after auditing it against recoverable historical image and lesion membership. Do not imply patient-level independence unless patient linkage is actually available and verified.

## Reopening condition

Reopen this decision only if new original evidence appears—for example, the actual v2 manifest or verdict NPZ from an archived run output, or a source/input bundle that regenerates the manifest with the receipt’s exact hash. A reconstructed candidate that fails the exact hash check is not the historical membership list.
