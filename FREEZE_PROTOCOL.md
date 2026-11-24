# Freeze-protocol status — revoked for this cohort

**Status as of 2026-10-19 UTC: NOT AUTHORIZED; DO NOT EXECUTE.** This file previously contained an operational plan to evaluate the adapted cohort's 500-image holdout. Those instructions are withdrawn. The historical `isic-study-v2` receipt records evaluation of 1,000 test items, but their exact membership is unavailable; overlap with this later cohort is unknown. The later 500-image split is non-confirmatory development evidence and is closed to further outcome analysis.

This file is retained as a status tombstone so an old link cannot be mistaken for an active test protocol. It deliberately contains no runnable TEST instructions or sign-off switches. A protocol freeze cannot restore a holdout's pristine status. Do not use the historical runner's `heldout` stage on the current cohort.

Controlling records:

- [`PROJECT_CONTEXT_MASTER.md`](PROJECT_CONTEXT_MASTER.md) — consolidated project status and operating boundaries.
- [`deliverables/TEST_SPLIT_RECOVERY_DECISION.md`](deliverables/TEST_SPLIT_RECOVERY_DECISION.md) — why historical test membership is unrecoverable and disposition.
- [`deliverables/GATE0_PROVENANCE_STATUS.md`](deliverables/GATE0_PROVENANCE_STATUS.md) — artifact/provenance audit and unresolved timestamp/source issues.
- [`deliverables/CLAIMS_EVIDENCE_LIMITS.md`](deliverables/CLAIMS_EVIDENCE_LIMITS.md) — allowed claims and limits.

The separate T1 classifier experiment is complete on TRAIN/validation only; it did not use the TEST split. See [`deliverables/T1_VALIDATION_RESULTS.md`](deliverables/T1_VALIDATION_RESULTS.md). T1 completion does not authorize a test run.

Any future confirmatory evaluation requires a genuinely new, authorized cohort with source provenance and membership audited before outcome access, a prespecified protocol, and appropriate review. PH2 is not assumed clean: historical project use and exact membership uncertainty remain documented. Never copy original medical pixels, restricted weights, credentials, or private keys into a project/Drive context package.
