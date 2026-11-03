"""Generate the Kaggle entrypoint from the canonical portable source bundle."""
import base64
import hashlib
import json
from pathlib import Path
from package_project import build

ROOT=Path(__file__).resolve().parents[1]


def cell(kind,text):
    d={'cell_type':kind,'metadata':{},'source':text.strip().splitlines(True)}
    if kind=='code': d.update(execution_count=None,outputs=[])
    return d


def main():
    archive=build(ROOT/'deliverables'/'keyswm-project.zip')
    payload=base64.b64encode(archive.read_bytes()).decode()
    sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    cells=[cell('markdown', '''# ISIC 2019 — persistent, resumable study
Enable a GPU and attach the ISIC 2019 images and ground-truth CSV as Kaggle inputs.
This notebook runs the same code as the local CLI; it contains no separate model implementation.
Start with the small wiring run, then change only the configuration cell for a new full output directory.
Save **a notebook version with outputs**, and download the result ZIP after each session.
Working-directory files are not guaranteed to survive an unsaved/disconnected session.
The model and empirical abstention mechanism are research prototypes, not clinically validated software.
'''),cell('code',f'''# Extract the exact source bundle; no GitHub authentication required.
import base64, hashlib, io, json, zipfile, sys, subprocess, os
from pathlib import Path
PROJECT = Path('/kaggle/working/keyswm-project')
PROJECT.mkdir(parents=True, exist_ok=True)
raw = base64.b64decode({payload!r})
assert hashlib.sha256(raw).hexdigest() == {sha!r}
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    for name in z.namelist():
        if not (PROJECT / name).resolve().is_relative_to(PROJECT.resolve()):
            raise ValueError('unsafe archive entry')
    z.extractall(PROJECT)
manifest = json.loads((PROJECT / 'SOURCE_MANIFEST.json').read_text())
for name, expected in manifest.items():
    assert hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() == expected
print('Source verified:', PROJECT)
'''),cell('code','''# Set True only if required packages are missing. Keep Kaggle's supplied Torch/CUDA.
# If pip changes an already-imported numerical package, restart the kernel before continuing.
INSTALL_DEPENDENCIES = False
if INSTALL_DEPENDENCIES:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r',
                    str(PROJECT / 'requirements-training.txt')], check=True)
'''),cell('code','''# EDIT THESE TWO PATHS to match your attached Kaggle dataset.
DATA = Path('/kaggle/input/YOUR-ISIC-DATASET/ISIC_2019_Training_Input')
METADATA = Path('/kaggle/input/YOUR-ISIC-DATASET/ISIC_2019_Training_GroundTruth.csv')

# Start with wiring-check sizes; these do NOT establish performance.
# Full study: TRAIN_N=2000, VAL_N=150, TEST_N=1000, EPOCHS=3, WIDTH=16,
# SEEDS='0,1,2', PROBES=True, HELDOUT_RUN=True. Use a NEW RUN_NAME.
RUN_NAME = 'wiring-check'
TRAIN_N, VAL_N, TEST_N, EPOCHS, WIDTH = 7, 7, 7, 1, 4
SEEDS = '0'
PROBES = False
HELDOUT_RUN = False
RESUME = False
SANITY = True  # Set False for the full study; never quote wiring-check results.
RUNS = Path('/kaggle/working/isic-runs') / RUN_NAME
CACHE = Path('/kaggle/temp/keyswm-cache')

# To resume from an earlier SAVED notebook output, attach that output as an input,
# set RESTORE_FROM to its isic-runs/<RUN_NAME> directory, keep the same source and
# experiment settings, and set RESUME=True. Trusted checkpoints only.
RESTORE_FROM = None
if RESTORE_FROM is not None:
    import shutil
    if RUNS.exists():
        raise ValueError('restore target already exists; do not merge experiments')
    shutil.copytree(Path(RESTORE_FROM), RUNS)
'''),cell('code','''# Hardware/data checks. Fail before training if GPU or labels are missing.
subprocess.run([sys.executable, str(PROJECT/'scripts/preflight.py'),
                '--require-gpu', '--data', str(DATA), '--metadata', str(METADATA)], check=True)
'''),cell('code','''# Train with epoch checkpoints and streamed logs; failures are never hidden.
cmd = [sys.executable, '-u', str(PROJECT/'scripts/run_suite.py'),
       '--data', str(DATA), '--metadata', str(METADATA), '--out', str(RUNS),
       '--cache', str(CACHE), '--device', 'cuda', '--seeds', SEEDS,
       '--train-n', str(TRAIN_N), '--val-n', str(VAL_N), '--test-n', str(TEST_N),
       '--epochs', str(EPOCHS), '--width', str(WIDTH)]
if RESUME: cmd.append('--resume')
if SANITY: cmd.append('--sanity')
if PROBES: cmd.append('--probes')
if HELDOUT_RUN: cmd.append('--heldout-run')
subprocess.run(cmd, check=True)
'''),cell('code','''# Run this cell even after a manual interruption, once the training process stops.
# Download the ZIP AND save a notebook version including outputs.
archive = Path('/kaggle/working') / (RUN_NAME + '-results.zip')
subprocess.run([sys.executable, str(PROJECT/'scripts/export_results.py'),
                '--runs', str(RUNS), '--out', str(archive)], check=True)
# Matching source is necessary to pass the resume fingerprint check later.
import shutil
shutil.copy2(PROJECT/'SOURCE_MANIFEST.json', '/kaggle/working/SOURCE_MANIFEST.json')
from IPython.display import FileLink, display
display(FileLink(str(archive)))
''')]
    nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
        'language_info':{'name':'python','version':'3.11'}},'nbformat':4,'nbformat_minor':5}
    dest=ROOT/'notebooks'/'keyswm_isic2019.ipynb'
    dest.write_text(json.dumps(nb,indent=1)+'\n')
    print(dest)


if __name__=='__main__': main()
