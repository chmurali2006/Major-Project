# Running the project

Read [PROTOCOL_V2.md](PROTOCOL_V2.md) before a measured study. Start with a wiring
check; CPU checks do not establish GPU readiness or scientific performance.

## Local setup

Use Python 3.11 and a virtual environment:

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-training.txt
python -m pytest -q
python scripts/preflight.py
```

For NVIDIA training, install a compatible PyTorch/CUDA build and run
`python scripts/preflight.py --require-gpu`. The runner supports CPU or one CUDA
device, not distributed training or Apple MPS.

## Inputs

Keep pixels and caches outside the repository. Supply authorised ISIC 2019 training
JPEGs and the eight-class ground-truth CSV (`image,MEL,NV,BCC,AK,BKL,DF,VASC,SCC`).
The notebook requires 25,331 images and the official class/count profile by default.
A labelled subset requires explicit opt-in and is not a complete-corpus result.
Counts do not prove source authenticity or patient independence. Known shared
patient/lesion IDs are refused by the current image-level split implementation.

## Kaggle: one saved job at a time

1. Upload `notebooks/keyswm_isic2019.ipynb` (or its copy in `deliverables/`).
2. Attach training images and ground truth through **Add Input / Add Data**.
3. Enable one available GPU. Preserve Kaggle's supplied Torch/CUDA installation.
4. Set `STAGE='check'`, `SEED=0`, `RESTORE_FROM=None`. Leave `DATA` and `METADATA`
   as `None` only when discovery is unambiguous; otherwise use the actual listed
   paths. Set `IMAGE_ZIP` only if extraction is necessary.
5. **Save Version → Save & Run All**. Check logs and saved outputs. This tiny
   7/7/7 run is non-claimable. Avoid paying for both an interactive and saved run.
6. After the GPU check and protocol review, set
   `ACKNOWLEDGE_EXPERIMENTAL_PROTOCOL_V2=True` for measured jobs. This is consent
   to an experiment, not approval of its results.

Use a fresh `STUDY_NAME='isic2019-rgb-auth-v2'`. Run main model and attention-enhanced
model for seeds 0,1,2. For constituent jobs use `STAGE='ablation'` and one `ABLATION`
from [the variant list](PROTOCOL_V2.md#runnable-constituent-removals), per seed.
Use `STAGE='heldout'`, seed 0, for the planned main-model held-out test.

For every continuation, attach the preceding saved output and set `RESTORE_FROM`
to its **whole study directory**, not a seed folder. Keep source, input bytes and
training settings fixed. Advance only stage/seed/ablation. Do not restore tiny or
old-protocol checkpoints into a measured study.

Download the result ZIP and retain the matching source bundle. GPU runtime, VRAM,
session limits and remaining quota must be checked on the account, not assumed.

## Local CLI

Example wiring run (replace paths):

```sh
python scripts/run_suite.py --data ../images --metadata ../labels.csv --out ../runs/check-v2 --cache ../cache --device cpu --seeds 0 --train-n 7 --val-n 7 --test-n 7 --epochs 1 --width 4 --sanity
```

For measured jobs use default frozen settings, a new output directory, `--probes`
and `--ablations` from the first job. Select the main model with
`--execute-configs C8`, attention with `C12`, or a descriptive ablation argument.
Continue with `--resume`; use `--only-heldout` for the held-out job. Internal IDs
are artifact compatibility names. See the protocol for exact commands and scope.

## Recovery and checks

Completed epochs save model, optimizer and RNG state atomically. An interrupted
epoch repeats. Source/data/settings changes are rejected on resume. Hard platform
shutdown can still prevent export; retain the entire study, not just final weights.

```sh
python scripts/validate_notebook.py --execute-wiring --exercise-ablations
python scripts/review_from_source.py --exercise-crash --out /tmp/review.json
```

Use another temporary path on Windows. On high-core CPU hosts, limiting
`OMP_NUM_THREADS` and `MKL_NUM_THREADS` to 2 can reduce diagnostic overhead.
These commands use synthetic CPU checks, not a completed ISIC/GPU study.
