# Run locally or on Kaggle

**This audited recipe requires a fresh study directory and current source.** Pre-audit weights/receipts are not results for this corrected training protocol. See `VERIFICATION.md` for findings and limits.

## Which should you choose?

- **Local NVIDIA GPU available:** local is the best persistence/control option. Verify with `preflight.py --require-gpu`; GPU model, VRAM and drivers determine feasibility. This project has not been GPU-tested in Arena.
- **No usable local NVIDIA GPU:** use Kaggle GPU for training; keep downloaded results and matching source on your local disk. CPU execution is supported, but the full suite can take many hours. No GPU speed/runtime claim has been measured here.
- Reference development/test environment: Python 3.11. Use one GPU, not distributed/multi-GPU training.

## Local setup (Windows, Linux or macOS)

Extract `keyswm-project.zip` into a project directory, or use the repository. Create a virtual environment:

```sh
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS, or `.venv\Scripts\Activate.ps1` in Windows PowerShell. Then:

```sh
python -m pip install --upgrade pip
python -m pip install -r requirements-training.txt
python -m pytest -q
python scripts/preflight.py
```

For a local GPU, install a PyTorch build compatible with your GPU/driver (use the official PyTorch installation selector), then verify `python scripts/preflight.py --require-gpu`. A CUDA version label on the wheel alone does not prove CUDA is usable. Apple MPS is not supported by this runner; use CPU or Kaggle.

## Data

Use actual ISIC 2019 training JPEGs and their ground-truth CSV. Do **not** put pixels or caches in the repository. Example layout:

```text
project/                       # source only
isic2019/                      # external dataset directory
  images/ISIC_....jpg
  ISIC_2019_Training_GroundTruth.csv
keyswm-cache/                  # external, disposable cache
experiments/                   # persistent results/checkpoints
```

`--data` searches recursively for `*.jpg`. `--metadata` must point to the one-hot ground truth or recognised diagnosis CSV, not an unrelated metadata file. Only labelled, resolving images enter the study. Duplicate image ids are rejected. The current runner uses image-level splits and refuses a supplied metadata file with repeated lesion grouping; it does not claim patient/lesion separation where identifiers are absent.

Optional public-mirror acquisition requires **Git and an already authenticated `gh` CLI**, as well as network access:

```sh
python scripts/acquire_isic.py --destination ../isic2019
```

This merges the mirror's five overlapping label files with conflict checks (20,455 unique labels resolve among 25,331 JPEGs). It is not a substitute for the official complete ground truth. Using a different labelled corpus changes the partition and requires a new output directory. On Kaggle, attach the images and CSV as input datasets instead; no GitHub credentials are needed by the notebook.

Check the paths before training:

```sh
python scripts/preflight.py --data ../isic2019 --metadata ../isic2019/ISIC_2019_GroundTruth_deduplicated.csv
```

For your own downloaded dataset, replace the CSV filename in every command below.

## First: an explicitly non-claimable wiring run

```sh
python scripts/run_suite.py --data ../isic2019 --metadata ../isic2019/ISIC_2019_GroundTruth_deduplicated.csv --out ../experiments/wiring --cache ../keyswm-cache --device auto --seeds 0 --train-n 7 --val-n 7 --test-n 7 --epochs 1 --width 4 --sanity
```

The tiny run tests both models and controls, not accuracy. Receipts are marked unusable as scientific results. `summary.json` will show the unexecuted full-study jobs as missing.

## Full study

```sh
python scripts/run_suite.py --data ../isic2019 --metadata ../isic2019/ISIC_2019_GroundTruth_deduplicated.csv --out ../experiments/isic-v3 --cache ../keyswm-cache --device cuda --seeds 0,1,2 --train-n 2000 --val-n 150 --test-n 1000 --epochs 3 --width 16 --probes --heldout-run
```

Use `--device cpu` or `--device auto` if you intentionally accept CPU execution. `cuda` fails rather than silently falling back. Plan for roughly **15–20 GB free storage**, plus the environment/dataset; actual use depends on selected sizes and cached probes. Epoch progress, logs and checkpoints are retained. Authentic reconstruction runs for 2 epochs on intact TRAIN cases and is frozen before localisation training. The suite runs sequentially: two controls, C8/C12 for each seed, key probes when requested, then C8 trained without T5. Seeds share fixed corpus partitions and attack realisations. Changing sizes changes which selected images are evaluated; never mix protocols or splits in one comparison.

## Interrupt and resume

Keep the **same source bundle**, dataset bytes, split sizes, seeds, epochs, configurations and attack settings. Repeat the exact command with `--resume` added. Outputs/cache may move to a different disk or host. Resume validates source/data/settings fingerprints, restores optimizer + latest completed-epoch model + best validation weights + Torch RNG, skips complete configurations, and reuses valid matching cache entries.

**Checkpoint granularity is one completed epoch.** Interrupting during an epoch loses that epoch's unfinished work. After training, interruption during evaluation reruns evaluation from the saved checkpoint. Moving between CPU/GPU or changing Torch/CUDA versions can change numerical behaviour; exact cross-hardware equality is not promised. GPU runs request deterministic kernels where supported but warn on unsupported deterministic operations; logs and the environment receipt record this best-effort mode. CPU mode is strict. Checkpoints use Torch serialization: restore only trusted project-generated files.

Do not change `--epochs` to extend an existing run: that is a new experiment. Source or data changes require a new output directory. A single-writer lock prevents two processes from writing the same experiment. Caches are content-namespaced and atomically written. The cache is disposable; output checkpoints are not.

## What to save

```text
isic-v3/
  logs/
  seed-0/ (also seed-1, seed-2)
    experiment.json, manifest.json
    C8_checkpoint.pt, C12_checkpoint.pt   # optimizer, epoch, best state, RNG
    C8_state.pt, C12_state.pt             # selected weights
    C0_count.json, C0_B.json, C8.json, C12.json
    *_verdicts.npz, *_validation.npz
    *_vs_*.json                           # paired image-bootstrap intervals
  heldout-T5/
  summary.json
```

Archive results **after stopping training** (not while checkpoint files are changing):

```sh
python scripts/export_results.py --runs ../experiments/isic-v3 --out ../isic-v3-results.zip
```

Retain that ZIP and the matching `keyswm-project.zip` on a persistent local disk. Extraction of the results ZIP restores the run-directory contents; point `--out` there and add `--resume`. Neither ZIP contains dataset pixels. The result ZIP includes checkpoints and checksums, not the external cache. `summary.json` records missing runs explicitly; a completed execution does not mean its scientific gates passed. Carrier-B regression, failed abstention constraints, and rekeying failures must remain in the report. Bootstrap CIs quantify test-image sampling, not training-seed uncertainty.

## Kaggle

Use **[KAGGLE_SETUP.md](KAGGLE_SETUP.md)** for the current staged notebook workflow.
The notebook audits actual attachments, requires the full ISIC 2019 count/class
profile unless a subset is explicitly allowed, and runs one model/seed per saved
version. `STAGE='check'` is the non-claimable wiring check. Full stages are `main-model`,
`attention-enhanced` and `heldout`; the first two share a frozen main/attention experiment and can run
in separate sessions without retraining the completed model. Restore prior saved
outputs to preserve all seeds. No dataset is attached to your Kaggle account by
Arena; you must attach the images/CSV and previous outputs in Kaggle.

## Validate/build the deliverables

```sh
python scripts/build_notebook.py
python scripts/validate_notebook.py
python scripts/validate_notebook.py --execute-wiring
```

The last command executes the extracted, Git-free source ZIP end-to-end on **synthetic disk images**, then tests no-op resume; these are wiring checks, not ISIC results. The notebook's GPU session still needs to be verified on Kaggle.
