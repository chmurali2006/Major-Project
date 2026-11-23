# Medical Image Tamper Detection

Research prototype for image integrity and tamper localisation, targeting ISIC2019.

**Current research focus:** establish when embedded authentication is justified
against image-preserving digital signatures, then test whether learning adds finer
localisation. We do not assume watermarking or deep learning is the better choice.

## Start here

**Next manual step:** [run the prepared Kaggle diagnostic](RUNNING.md#next-action-one-manual-kaggle-diagnostic).
The standalone notebook needs no token or local installation. Return the exported
ZIP; execution completion is not a scientific quality approval.

- [Run locally or on Kaggle](RUNNING.md)
- [Current method and protocol](PROTOCOL_V2.md)
- [Open questions](docs/DESIGN_REVIEW.md#5-open-questions)
- [References](docs/LITERATURE.md)

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
