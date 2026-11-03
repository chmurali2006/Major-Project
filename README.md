# Medical Image Tamper Detection

Experimental fragile watermarking and learned tamper localisation on ISIC 2019.

## Start here

- [Run locally or on Kaggle](RUNNING.md)
- [Current method and protocol](PROTOCOL_V2.md)
- [Open questions](docs/DESIGN_REVIEW.md#5-open-questions)
- [References](docs/LITERATURE.md)

The current fragile verifier uses block-local RGB HMAC tags. The main learned
model estimates pixel localisation; the attention-enhanced model and seven
constituent controls are experiments, not demonstrated improvements.

## Status

Targeted CPU checks cover authentication edits, checkpoint recovery and synthetic
training of all variants. Full ISIC three-seed results, CUDA operation and clinical
validity are not established. Raw check outputs are in `deliverables/*.json`;
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
