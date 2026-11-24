# Medical Image Tamper Detection

Research prototype for image integrity and tamper localisation, targeting ISIC2019.

**Research focus:** We study exact image integrity, tamper localization, and class-sensitive diagnostic-model impact as separate contracts in dermoscopic imaging. We do not assume that watermarking or deep learning is superior; comparisons must account for their different distortion, evidence, storage, and trust costs.

## Scope and experimental protocol

Our repository contains multiple study lines and their outcomes are not pooled as one benchmark. We evaluated an adapted ISIC 2019 cohort and checked returned validation records against the declared row/protocol structure; we did not rerun source-image transformations or classifier inference locally. A separate historical `isic-study-v2` run evaluated 1,000 test images, but its exact IDs cannot be recovered from retained evidence. Overlap with the later 500-image cohort is unknown, so we exclude that holdout from confirmatory claims and further outcome analysis. The recovery decision and claim limits are in [`deliverables/TEST_SPLIT_RECOVERY_DECISION.md`](deliverables/TEST_SPLIT_RECOVERY_DECISION.md), [`deliverables/GATE0_PROVENANCE_STATUS.md`](deliverables/GATE0_PROVENANCE_STATUS.md), and [`deliverables/CLAIMS_EVIDENCE_LIMITS.md`](deliverables/CLAIMS_EVIDENCE_LIMITS.md).

Historical PH2 work is also present in this repository; we do not describe PH2 as an unused external test cohort until its earlier membership/protocol history is reconciled.

**Project structure:** the repository contains a protocol-v2 embedded RGB-HMAC prototype, detached signed-evidence/localization studies, and separate classifier/embedding experiments. Their protocols and evidence levels differ; refer to the consolidated project overview before combining or comparing their results.

## Start here

**Authoritative project state (as of 2026-10-19 UTC):** [Project master context](PROJECT_CONTEXT_MASTER.md). It reconciles the separate experimental strands, evidence levels, critical limits, document map, and safe next steps. Detailed tables and caveats are in [Project overview](deliverables/PROJECT_FULL_OVERVIEW_AND_GAPS.md), [Claims/evidence limits](deliverables/CLAIMS_EVIDENCE_LIMITS.md), and the [T1 validation report](deliverables/T1_VALIDATION_RESULTS.md).

**T1 status:** the fixed 1,500 TRAIN / 500 validation multi-architecture study was returned and ingested. Results are validation-only; no TEST data were accessed. See the T1 report for metrics, audit checks, and limitations. This T1 classifier notebook is separate from the RGB-HMAC protocol-v2 runner below.

**Historical transition record:** the earlier mid-review/poster concerned a different ISIC 2018 fragile-watermarking study. Its reported figures are archived with limitations and unresolved date/provenance warnings in [the transition record](deliverables/MIDREVIEW_POSTER_TRANSITION_RECORD.md); do not mix them with current T1 results.

- [Current safe run instructions and boundaries](RUNNING.md)
- [Protocol-v2 method specification](PROTOCOL_V2.md) — separate research line; its historical stage plan is not authorization to access any holdout.
- [Open technical questions](docs/DESIGN_REVIEW.md#5-open-questions)
- [References and bibliography caveats](docs/LITERATURE.md)
- [Complete narrative compilation](deliverables/PROJECT_COMPLETE_DOCUMENT_COMPILATION.md) (documentation-only compilation).
- [Curated full project context/source bundle](deliverables/PROJECT_CONTEXT_BUNDLE_2026-10-19.zip) with included-file hashes and documented exclusions; not a raw-data or weights package. See [package guide](deliverables/PROJECT_CONTEXT_PACKAGE_README.md).

The current fragile verifier uses block-local RGB HMAC tags. The main learned
model estimates pixel localisation; the attention-enhanced model and seven
constituent controls are experiments, not demonstrated improvements.

## Simple current-method demonstration

**Protect → alter → verify**, on CPU without a neural checkpoint:

```sh
python -m pip install -r requirements.txt
python scripts/showcase.py --synthetic --out /tmp/keyswm-showcase
# Open /tmp/keyswm-showcase/index.html in your browser.
```

For your authorised, de-identified ISIC image, replace `--synthetic` with
`--image /outside/repo/ISIC.jpg --resize 512`. Resizing is explicit, recorded
preprocessing, not preservation of the original medical acquisition. Output
pixels must stay outside this repository. The HTML works offline, shows all
eight controlled scenarios, and links the numerical receipt and protected PNG.

This is the **classical RGB authentication path**, not a demonstration of learned
pixel segmentation. Red overlays mean failed 8×8 blocks. The measured pixel
change mask is shown separately and is never supplied to verification. Wrong-key,
wrong-identifier and JPEG examples explain why failure does not establish intent.
`scripts/demo.py` is historical and does not demonstrate this current method.

## Answering the signature objection with a measured comparison

```sh
python scripts/compare_integrity.py --synthetic --n 4 --out /tmp/integrity-tradeoffs.json
# Open /tmp/integrity-tradeoffs.html; retain the matching JSON receipt.
```

Use `--image /outside/repo/prepared-RGB.png` for one authorised image, or
`--data /outside/repo/images --n 4` for an explicitly nonrepresentative convenience
subset. Inputs are not silently resized. This is separate from the frozen ISIC
learned-model study and does not evaluate a trained model.

| Mechanism | Alters pixels? | Localises changes? | Required external trust/evidence |
| --- | --- | --- | --- |
| Whole-image Ed25519 signature | No | No map | Trusted public key, version ID, signed evidence |
| Signed tile-hash manifest | No | Failed 8×8 tiles | Trusted public key, version ID, signed manifest |
| Embedded HMAC watermark | Yes | Failed 8×8 blocks | Shared secret key, trusted version ID |

Signatures can localise when a tile manifest is signed. This baseline must not be
omitted to make watermarking look necessary. No blockchain is required for these
checks; freshness and key trust still need an external workflow. Reported sidecar sizes exclude key
distribution, certificates and trusted version-registry overhead for all methods. Invalid/missing
signed evidence means `CANNOT_AUTHENTICATE`, not an invented tamper map. Our
signature baseline covers decoded RGB, not DICOM metadata or a DICOM profile.

The candidate learning contribution is **better sub-block localisation than block
expansion**, compared against an image-only model. This is not established. A high
image detection score, extra attention layers or a favourable whole-image JPEG
mask cannot substitute for small-edit pixel localisation.

## Status

Targeted CPU checks cover authentication edits, checkpoint recovery and synthetic
training of all variants. A tiny ISIC T4 wiring run has executed, but learned
localisation failed there. Full ISIC three-seed results, strict GPU reproducibility
and clinical validity are not established. Raw check outputs are in `deliverables/*.json`;
historical performance receipts remain in `results/`. Neither is a paper-parity
claim. See each output's source fingerprint and scope before using its numbers.

## Files

- `src/`, `scripts/`, `tests/`: implementation, runners and tests.
- `notebooks/keyswm_isic2019.ipynb`: generated standalone Kaggle notebook.
- `deliverables/`: portable ZIPs, notebook copy and machine-readable checks.
- `project-context/`: concise project context and historical facts.

Use a fresh `isic2019-rgb-auth-v2` study. Old checkpoints are incompatible.
Protected images require lossless storage. Public benchmark keys are not
production secrets; learned predictions cannot override failed authentication.

Historical `src/pipeline.py` and `scripts/bench.py` retain the earlier classical
implementation through `legacy_carriers`/`legacy_metrics`; they are not v2 runners.
