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
seven controlled scenarios, and links the numerical receipt and protected PNG.

This is the **classical RGB authentication path**, not a demonstration of learned
pixel segmentation. Red overlays mean failed 8×8 blocks. The measured pixel
change mask is shown separately and is never supplied to verification. Wrong-key,
wrong-identifier and JPEG examples explain why failure does not establish intent.
`scripts/demo.py` is historical and does not demonstrate this current method.

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
