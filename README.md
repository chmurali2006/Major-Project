# A Fragile Watermarking for Medical Image Tamper Detection

Position-bound, zero-training, keyed dual watermarking for medical images, with
designed abstention. Primary corpus: ISIC 2018 Task 1. Secondary: LiTS.
Validation: PH2.

The design authority is the context package in `project-context/`. Where this
code departs from it, the departure is recorded with its measurement in
`docs/AMENDMENTS.md`.

## Status

Phase One complete and measured on real tissue. Three of six operating-point
bars met; the remainder have named engineering fixes, not threshold tweaks.
See `docs/BENCHMARKS.md`.

## Layout

```
src/            config, transform, binder, carriers, container, pipeline, ladder, metrics
src/battery/    the frozen conditions, one function each
scripts/        dataset preparation, benchmark harness, local runner
tests/          34 tests, including the six pre-flight checks
docs/           BUILD_PLAN, AMENDMENTS, BENCHMARKS
project-context/ reference material only — never imported by code
```

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                                    # 34 tests, no data needed

# prepare a corpus (needs images and masks on disk)
python scripts/prepare_isic.py --images <dir> --masks <dir> --out datasets/isic2018

# run the battery, leave a receipt
./scripts/run_local.sh datasets/isic2018 40
```

`runs/<timestamp>/receipt.json` records the command, configuration, git commit,
environment and per-condition counts. A number without a receipt does not exist.

## Datasets

Never committed (Trap 29). `scripts/prepare_*` writes a per-file SHA-256
receipt into the dataset directory. ISIC 2018 and LiTS require registration and
are not downloadable from an automated environment; PH2 has a public mirror.

## Honest limitation

The container is PNG with metadata chunks. Stripping the metadata costs an
abstention (CANNOT SAY), not an accusation — but it does mean an attacker who
strips metadata can cost you coverage. Integrity of the pixel payload survives;
the claim to the image's identity does not.
