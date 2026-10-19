# A Fragile Watermarking for Medical Image Tamper Detection

Position-bound, zero-training, keyed dual watermarking for medical images, with
designed abstention. Primary corpus: ISIC 2018 Task 1. Secondary: LiTS.
Validation: PH2.

The design authority is the context package in `project-context/`. Where this
code departs from it, the departure is recorded with its measurement in
`docs/AMENDMENTS.md`.

## Status

Mid-project review checkpoint, measured on real tissue (PH2, n=200, 22 frozen
conditions). All five operating-point bars are met on the mean: detection
99.90%, IoU 0.9421, benign claims 0.00%, PSNR 38.27 dB, verify 38.60 ms, and
zero false claims on the 200 untouched images. The known weaknesses — worst-case
PSNR 35.52 dB, burned-in text as an alarm rather than a localiser — are stated
with their numbers in
[`docs/MID_PROJECT_REVIEW.md`](docs/MID_PROJECT_REVIEW.md) §5 and
[`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) §3.

Start with the review document; the measured tables are generated from the
receipt by `scripts/make_tables.py`.

## Layout

```
src/            config, transform, binder, carriers, container, pipeline, ladder, metrics
src/battery/    the frozen conditions, one function each
scripts/        dataset preparation, benchmark harness, local runner
tests/          39 tests, including the six pre-flight checks
docs/           MID_PROJECT_REVIEW, BENCHMARKS, AMENDMENTS, REPRODUCE, figures/
project-context/ reference material only — never imported by code
```

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                                    # 39 tests, no data needed

# prepare a corpus (the public PH2 mirror needs no registration)
git clone https://github.com/vikaschouhan/PH2-dataset /tmp/ph2src
python scripts/prepare_ph2_public.py --src /tmp/ph2src --out datasets/ph2

# run the battery, leave a receipt
python scripts/bench.py --data datasets/ph2 --limit 200 \
                        --receipt runs/<utc>/receipt.json
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
