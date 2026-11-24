# Complete project context package — read me first

**Snapshot date:** 2026-10-19 UTC  
**Repository:** `chmurali2006/Major-Project`  
**Branch:** `arena/a9fb47a3-major-project`

This is a curated, integrity-manifested context snapshot of the project: authoritative project status, study protocols, source code, tests, sanitized notebooks, key narrative documents, derived result tables, and retained text/JSON audit receipts. It is designed so a reviewer can understand the whole project and inspect implementation/evidence boundaries without receiving restricted or unnecessary medical data.

## Start here

1. `PROJECT_CONTEXT_MASTER.md` — authoritative cross-strand status, results summary, restrictions, and document index.
2. `deliverables/MIDREVIEW_POSTER_TRANSITION_RECORD.md` — historical reported results and the current-vs-historical transition narrative; original PDFs remain at linked source locations because their embedded pixels are unscreened.
3. `deliverables/PROJECT_FULL_OVERVIEW_AND_GAPS.md` — detailed study/evidence inventory.
4. `deliverables/CLAIMS_EVIDENCE_LIMITS.md` — claim language and caveats.
5. `deliverables/T1_VALIDATION_RESULTS.md` — completed validation-only multi-architecture results.
6. `deliverables/TEST_SPLIT_RECOVERY_DECISION.md` and `deliverables/GATE0_PROVENANCE_STATUS.md` — historical TEST access, unresolved membership, and provenance/chronology limits.
7. `RUNNING.md` — safe usage; no holdout commands are authorized.

## Scope and important exclusions

This package deliberately excludes original medical-image pixels and metadata spreadsheets that could expose source records, model/checkpoint weights, private keys/credentials, the 40 MB T1 return ZIP containing visual panels, result ZIP archives whose contents were not individually reviewed for redistribution, opaque NPZ/map binaries, image and media files, third-party full-text papers/PDFs, `.git` history, local environments, caches, and build products. The source mid-review and poster PDFs are also not embedded: their presentation graphics have not been screened for image pixels or redistribution rights; the transition record preserves extracted text, reported results, source links, and the date/provenance caveat. Historical claims are not current results. Generated notebooks are included as source-only copies with outputs and cell execution state stripped.

Therefore this is a **complete project context + source + text/derived-evidence package within privacy, licensing, and scope safeguards**, not a byte-for-byte clone of the workspace or a full data/model reproducibility kit. The generated `PACKAGE_MANIFEST.csv` lists included paths, byte sizes, and SHA-256 hashes; excluded categories are recorded in `PACKAGE_EXCLUSIONS.md`.

## Evidence boundaries

- T1 is validation-only on 1,500 TRAIN / 500 validation images and reports `test_accessed:false`. No T1 result is a TEST result.
- Historical `isic-study-v2` test access is recorded; exact membership is unrecoverable from retained artifacts, and overlap with the later 500-image holdout is unknown. The later holdout is closed to further outcome analysis and is non-confirmatory.
- PH2 has prior project use and incomplete exact membership/source lineage. Do not call it a clean confirmatory external cohort.
- Receipt/metric/hash checks are not source-pixel/model replay, security certification, clinical validation, or proof of authorship.
- Dates in retained run receipts that are later than 2026-10-19 are future-dated and unauthenticated in this snapshot; do not present them as proven execution timestamps.
- Verify dataset, upstream-code, model, paper, and image licenses before any public redistribution.

The package builder is `scripts/build_context_package.py`. Build and re-run its inventory check before re-uploading after any material source changes.