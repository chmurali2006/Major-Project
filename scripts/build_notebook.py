"""Generate a staged, audited Kaggle notebook from the canonical tested source."""
import base64
import hashlib
import json
from pathlib import Path
from package_project import build

ROOT = Path(__file__).resolve().parents[1]


def cell(kind, text):
    d = {'cell_type': kind, 'metadata': {}, 'source': text.strip().splitlines(True)}
    if kind == 'code':
        d.update(execution_count=None, outputs=[])
    return d


def main():
    archive = build(ROOT / 'deliverables' / 'keyswm-project.zip')
    payload = base64.b64encode(archive.read_bytes()).decode()
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    cells = [cell('markdown', '''# ISIC 2019: audited, staged watermarking study
**Protocol v2 — incompatible with all earlier checkpoints/results.**
The fragile verifier now checks a block-local RGB HMAC carried in RGB low bits;
it no longer relies on the periodic luma code for authentication. Read
`PROTOCOL_V2.md` for capacity, fidelity, lossless-storage and replay/key limitations.
The earlier brightness/colour failures are retained as legacy regression cases.

Main model, attention-enhanced model and constituent removals share the same
protected inputs, measured masks and validation decision objective. The AE is
pretrained on authentic TRAIN samples then frozen. Abstention is empirical, not
a clinical guarantee. Corrected code is not yet a full measured ISIC study.

**Before running:** attach ISIC 2019 training images and the eight-class ground-truth
CSV with **Add Input / Add Data**, enable a GPU, and read `RUNNING.md` supplied
with this notebook. No private GitHub login or API token is required.

For engineering checks only, start with `STAGE='check'`. Do not advance to the full study
until the new GPU wiring check passes and the amended protocol has been reviewed. Restore the preceding saved
output each time. Do not change training settings based on test results.
The method is a research prototype, not a clinically validated medical system.
'''), cell('code', f'''# 1. Verify/extract the exact project source. No separate notebook model implementation.
import base64, hashlib, io, json, zipfile, sys, subprocess, os, shutil
from pathlib import Path
PROJECT = Path('/kaggle/working/keyswm-project')
# Byte verification cannot invalidate Python's already-imported module cache.
# A different/unknown project version needs a fresh kernel before extraction.
loaded_project_modules = [name for name in sys.modules if name == 'src' or name.startswith('src.') or name in ('run_matrix','run_isic_study')]
if loaded_project_modules and globals().get('_KEYSWM_SOURCE_BUNDLE_SHA256') != {sha!r}:
    raise RuntimeError('Project modules are already loaded from an unknown/different source. Restart the kernel, then run from the top.')
PROJECT.mkdir(parents=True, exist_ok=True)
raw = base64.b64decode({payload!r})
assert hashlib.sha256(raw).hexdigest() == {sha!r}
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    for name in z.namelist():
        if not (PROJECT / name).resolve().is_relative_to(PROJECT.resolve()):
            raise ValueError('unsafe source archive entry')
    z.extractall(PROJECT)
for name, expected in json.loads((PROJECT / 'SOURCE_MANIFEST.json').read_text()).items():
    assert hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() == expected
sys.path.insert(0, str(PROJECT))
_KEYSWM_SOURCE_BUNDLE_SHA256 = {sha!r}
print('Verified source bundle:', {sha!r})
'''), cell('markdown', '''## 2. Configuration — edit only this cell
Leave paths as `None` for unambiguous auto-discovery. If more than one image root
or ground truth is attached, the notebook lists candidates and stops; enter the
correct paths explicitly. Attaching only a CSV is not sufficient.

`diagnostic` is the default next step: seven TRAIN images, two authentic epochs and
20 localisation epochs per model, with no validation/test evaluation. It is an
in-sample learning diagnostic, never a study receipt. It reports the shared-rule
result alongside a clearly separate pixel-only TRAIN operating point.

`STAGE` chooses work, **not a different scientific protocol**. main model and attention-enhanced model use the
same frozen model list/settings so they can be executed in separate sessions.
Full-profile count checks are strict by default. A count/profile match is an audit,
not cryptographic proof that a third-party mirror is authentic.
'''), cell('code', '''ACKNOWLEDGE_EXPERIMENTAL_PROTOCOL_V2 = False  # See PROTOCOL_V2.md; engineering fixes are not measured submission results.
STAGE = 'diagnostic'         # 'diagnostic', 'check', 'main-model', 'attention-enhanced', 'ablation', 'heldout'
ABLATION = 'without-ae'       # one registered removal per saved job; see PROTOCOL_V2.md
SEED = 0                     # use 0, then 1, then 2; heldout uses seed 0
STUDY_NAME = 'isic2019-rgb-auth-v2'    # new name if changing source, data or training settings

INPUT_ROOT = Path('/kaggle/input')
DATA = None                  # e.g. Path('/kaggle/input/<your-input>/training-images')
METADATA = None              # actual ISIC_2019_Training_GroundTruth.csv
IMAGE_ZIP = None             # optional: Path to attached training-image ZIP, if not extracted
ALLOW_LABELLED_SUBSET = False # explicit exception; clearly labelled as a subset in the audit
INSTALL_MISSING = False      # only if imports fail; enable Internet for that setup run

# Attach the PREVIOUS saved notebook output as an input for later stages/sessions.
# This must be its whole study directory, not a seed folder or a checkpoint file.
RESTORE_FROM = None           # e.g. Path('/kaggle/input/<previous-output>/isic-runs/isic2019-v4')

# Freeze these BEFORE the first full run. Never extend epochs inside an existing run.
TRAIN_N, VAL_N, TEST_N, EPOCHS, WIDTH = 2000, 150, 1000, 3, 16
AUTHENTIC_EPOCHS = 2
DIAGNOSTIC_EPOCHS = 20  # TRAIN-only memorisation, not part of the full-study protocol
DIAGNOSTIC = STAGE == 'diagnostic'
if STAGE not in ('diagnostic', 'check', 'main-model', 'attention-enhanced', 'ablation', 'heldout') or SEED not in (0, 1, 2):
    raise ValueError('invalid stage or seed')
if STAGE not in ('check', 'diagnostic') and not ACKNOWLEDGE_EXPERIMENTAL_PROTOCOL_V2:
    raise RuntimeError('Full run blocked: acknowledge the new experimental RGB-authentication protocol after checking PROTOCOL_V2.md and the GPU wiring check. This does not certify accuracy or clinical/security validity.')
if STAGE == 'heldout' and SEED != 0:
    raise ValueError('the planned held-out run uses seed 0')
SANITY = STAGE in ('check', 'diagnostic')
if SANITY:
    TRAIN_N, VAL_N, TEST_N, EPOCHS, WIDTH = 7, 7, 7, 1, 4
RUN_NAME = 'learning-diagnostic-v2' if DIAGNOSTIC else ('wiring-check-v2' if SANITY else STUDY_NAME)
RUNS = Path('/kaggle/working/isic-runs') / RUN_NAME
CACHE = Path('/kaggle/temp/keyswm-cache')  # disposable, not copied into saved results
print(dict(stage=STAGE, seed=SEED, output=str(RUNS), sanity=SANITY))
'''), cell('markdown', '''## 3. Dependencies — preserve Kaggle's supplied Torch/CUDA
Do not blindly upgrade Torch or the entire Kaggle environment. Missing non-Torch
packages may be installed explicitly. If numerical libraries were already imported
before changing them, restart the kernel and run from the top. No package installation
is needed if these imports pass. Runtime versions are recorded with every experiment.
'''), cell('code', '''import importlib.util
required = {'numpy':'numpy', 'scipy':'scipy', 'cv2':'opencv-python-headless==4.10.0.84',
            'PIL':'Pillow', 'filelock':'filelock'}
missing = [package for module, package in required.items() if importlib.util.find_spec(module) is None]
if importlib.util.find_spec('torch') is None:
    raise RuntimeError('Use Kaggle Python with a GPU/PyTorch image; do not install an arbitrary CPU Torch wheel.')
if missing:
    if not INSTALL_MISSING:
        raise RuntimeError(f'Missing {missing}. Enable Internet and INSTALL_MISSING for setup, then rerun.')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-deps', *missing], check=True)
import numpy as np, scipy, cv2, torch, filelock
print('Python', sys.version.split()[0], 'Torch', torch.__version__, 'NumPy', np.__version__)
if not torch.cuda.is_available():
    raise RuntimeError('No usable CUDA GPU. Enable an available GPU accelerator in notebook settings.')
print('GPU:', torch.cuda.get_device_name(0), '| CUDA:', torch.version.cuda)
print('Multiple GPUs are not used by this single-device runner.')
'''), cell('markdown', '''## 4. Find and verify the attached data
The audit requires all 25,331 labelled training images with the official eight-class
count profile unless you explicitly allow a subset. It rejects missing images,
ambiguous inputs, conflicting duplicate labels, invalid one-hot labels and duplicate
image identifiers. A small image sample is decoded here; selected experiment images
are decoded and fingerprinted by the runner. Image-level splitting is a limitation
where lesion/patient identifiers are unavailable.
'''), cell('code', '''from src.dataset_audit import discover, audit
candidates = discover(INPUT_ROOT)
print(json.dumps(candidates, indent=2))
if IMAGE_ZIP is not None:
    IMAGE_ZIP = Path(IMAGE_ZIP)
    extracted = Path('/kaggle/temp/isic2019-extracted')
    with zipfile.ZipFile(IMAGE_ZIP) as z:
        needed = sum(i.file_size for i in z.infolist())
        if needed + 4 * 2**30 > shutil.disk_usage('/kaggle/working').free:
            raise RuntimeError('Not enough free space to extract images and prepare samples. Attach extracted images instead.')
        extracted.mkdir(parents=True, exist_ok=True)
        for member in z.infolist():
            if not (extracted / member.filename).resolve().is_relative_to(extracted.resolve()):
                raise ValueError('unsafe dataset ZIP entry')
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('symlink in dataset ZIP')
        z.extractall(extracted)
    DATA = extracted
    candidates['ground_truth_csvs'] = sorted(set(candidates['ground_truth_csvs'] + discover(extracted)['ground_truth_csvs']))
if DATA is None:
    if len(candidates['image_roots']) != 1:
        raise ValueError('Choose DATA explicitly from the listed image roots. If images are zipped, set IMAGE_ZIP.')
    DATA = Path(candidates['image_roots'][0])
if METADATA is None:
    if len(candidates['ground_truth_csvs']) != 1:
        raise ValueError('Choose METADATA explicitly from the listed ground-truth CSVs.')
    METADATA = Path(candidates['ground_truth_csvs'][0])
CANONICAL_CSV = Path('/kaggle/working/verified-isic-ground-truth.csv')
dataset_audit = audit(DATA, METADATA, CANONICAL_CSV, allow_subset=ALLOW_LABELLED_SUBSET)
Path('/kaggle/working/dataset_audit.json').write_text(json.dumps(dataset_audit, indent=2))
print(json.dumps(dataset_audit, indent=2))
subprocess.run([sys.executable, str(PROJECT/'scripts/preflight.py'), '--require-gpu',
                '--data', str(DATA), '--metadata', str(CANONICAL_CSV)], check=True)
'''), cell('markdown', '''## 5. Restore the preceding saved output, if continuing
Use the **same notebook/source version**, image bytes and frozen settings. Only stage
and seed advance. Checkpoints are trusted Torch files: restore only your own outputs.
If the working output already exists, it is resumed rather than merged with another
experiment. To start a different study, use a new name. Do not delete results to bypass
a fingerprint mismatch.
'''), cell('code', '''if RESTORE_FROM is not None:
    restore = Path(RESTORE_FROM)
    if not restore.is_dir():
        raise ValueError('RESTORE_FROM must be a study directory in an attached previous output')
    if RUNS.exists():
        raise ValueError('Restore target already exists. Do not merge two experiments.')
    shutil.copytree(restore, RUNS)
if STAGE in ('attention-enhanced','ablation') and not (RUNS / f'seed-{SEED}' / 'C8.json').exists():
    raise ValueError('attention/ablation continuation requires the preceding main model output for this seed. Attach it and set RESTORE_FROM.')
RESUME = RUNS.exists()
RUNS.mkdir(parents=True, exist_ok=True)
shutil.copy2('/kaggle/working/dataset_audit.json', RUNS/'dataset_audit.json')
shutil.copy2(CANONICAL_CSV, RUNS/'ground-truth-used.csv')
print('Resume existing study:', RESUME)
print('Free space (GiB):', round(shutil.disk_usage('/kaggle/working').free / 2**30, 1))
'''), cell('markdown', '''## 6. Execute one bounded job; export outputs even if it fails
This runs CPU evidence preparation followed by GPU training/evaluation. GPU time is
still consumed while a GPU-enabled session prepares data. The wiring check measures
plumbing, **not scientific accuracy**; its receipts are non-claimable.

Training checkpoints are atomic, once per completed epoch. An unfinished epoch must
be repeated. There is no guarantee of surviving a forced platform shutdown before
outputs are saved. Logs stream progress; no fixed GPU runtime is claimed in advance.
If you must interrupt, stop the training subprocess before archiving.
'''), cell('code', '''cmd = [sys.executable, '-u', str(PROJECT/'scripts/run_suite.py'),
       '--data', str(DATA), '--metadata', str(CANONICAL_CSV), '--out', str(RUNS),
       '--cache', str(CACHE), '--device', 'cuda', '--seeds', str(SEED),
       '--configs', 'C8,C12', '--ablations', '--train-n', str(TRAIN_N), '--val-n', str(VAL_N),
       '--test-n', str(TEST_N), '--epochs', str(EPOCHS), '--ae-epochs', str(AUTHENTIC_EPOCHS), '--width', str(WIDTH)]
if RESUME: cmd.append('--resume')
if SANITY:
    cmd.extend(['--sanity','--execute-configs','C8,C12'])
elif STAGE == 'heldout':
    cmd.extend(['--only-heldout', '--probes'])
else:
    from src.names import STAGE_MODELS
    from src.ablations import ABLATIONS
    if STAGE == 'ablation' and ABLATION not in ABLATIONS:
        raise ValueError('unknown constituent ablation')
    cmd.extend(['--execute-configs', ABLATION if STAGE == 'ablation' else STAGE_MODELS[STAGE], '--probes'])
if DIAGNOSTIC:
    cmd = [sys.executable, '-u', str(PROJECT/'scripts/diagnose_learning.py'),
           '--data', str(DATA), '--metadata', str(CANONICAL_CSV),
           '--out', str(RUNS/'training-only'), '--epochs', str(DIAGNOSTIC_EPOCHS),
           '--n', '7', '--width', '4', '--seed', str(SEED), '--device', 'cuda']
print('Executing:', STAGE, 'seed', SEED, '| output:', RUNS)
# Popen + finally prevents a failed child from skipping the export step.
child = None
failure = None
try:
    child = subprocess.Popen(cmd, start_new_session=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
    with (RUNS/'execution.log').open('a') as execution_log:
        execution_log.write('COMMAND ' + json.dumps(cmd) + '\\n')
        for line in child.stdout:
            print(line, end='', flush=True)
            execution_log.write(line)
            execution_log.flush()
    if child.wait() != 0:
        raise RuntimeError('Study failed: inspect logs; outputs will still be exported.')
except BaseException as exc:
    failure = exc
    if child is not None and child.poll() is None:
        import signal
        try:
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            pass
        except BaseException as cleanup_error:
            print('CHILD STOP WARNING:', repr(cleanup_error))
        finally:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except BaseException as cleanup_error:
                print('CHILD KILL WARNING:', repr(cleanup_error))
            try:
                child.wait(timeout=10)
            except BaseException as cleanup_error:
                print('CHILD WAIT WARNING:', repr(cleanup_error))
finally:
    # Independent attempts: neither a bad summary nor its launch failure may
    # prevent exporting raw checkpoints. Do not mask the original study error.
    finalization_errors = []
    try:
        if not DIAGNOSTIC:
            subprocess.run([sys.executable, str(PROJECT/'scripts/summarize_isic_study.py'),
                            '--root', str(RUNS), '--out', str(RUNS/'summary.json')], check=True)
    except BaseException as exc:
        finalization_errors.append(('summary', exc))
        print('SUMMARY FAILED:', repr(exc))
    archive = Path('/kaggle/working') / (RUN_NAME + '-results.zip')
    try:
        subprocess.run([sys.executable, str(PROJECT/'scripts/export_results.py'),
                        '--runs', str(RUNS), '--out', str(archive)], check=True)
        shutil.copy2(PROJECT/'SOURCE_MANIFEST.json', '/kaggle/working/SOURCE_MANIFEST.json')
        print('SAVE/DOWNLOAD:', archive)
    except BaseException as exc:
        finalization_errors.append(('export', exc))
        print('EXPORT FAILED: save the raw study folder if possible:', repr(exc))
if failure is not None:
    raise failure
if finalization_errors:
    raise RuntimeError('Finalization failed: ' + ', '.join(name for name, _ in finalization_errors)) from finalization_errors[0][1]
'''), cell('markdown', '''## 7. Inspect results, then Save Version
A successful job is not the same as a successful scientific gate. Carrier-B losses,
false claims, infeasible abstention and rekeying drops remain visible. Confidence
margins are not posterior probabilities. IoU is reported over tampered images only;
TPR/FPR and denominators accompany verdict accuracy. Bootstrap CIs represent image
sampling, while the three seeds measure training variability.

For submission, finish all seeds and the held-out run, keep the manifests, runtime
versions and checksummed artifacts. PFF-WM results on other datasets/protocols must
not be placed beside these numbers as if directly comparable. This assembled
implementation is not an exact verified reproduction of PFF-WM.
'''), cell('code', '''if DIAGNOSTIC:
    diagnostic = json.loads((RUNS/'training-only'/'diagnostic.json').read_text())
    print('TRAIN-only diagnostic. Not a benchmark result; usable:', diagnostic['usable'])
    for name, result in diagnostic['models'].items():
        for phase in ('before', 'after'):
            row = result[phase]
            print(name, phase, 'joint-rule TRAIN IoU', row['metrics']['iou_tampered_mean'],
                  'pixel-only TRAIN IoU', row['pixel_only_training_iou'], 'collapse', row['collapse'])
else:
    summary = json.loads((RUNS/'summary.json').read_text())
    for row in summary['runs']:
        print(row['model'], 'seed', row['seed'], 'usable', row['usable'],
              'IoU(tampered)', round(row['iou_tampered'], 4),
              'balanced', round(row['balanced_accuracy'], 4),
              'FPR', round(row['fpr'], 4))
    print('Artifact suite complete (NOT security approval):', summary['complete'])
    print('Malformed receipts:', summary['invalid_receipts'])
    print('Comparison failures:', summary['comparison_failures'])
    print('Missing full-suite receipts:', len(summary['missing']))
from IPython.display import FileLink, display
display(FileLink(str(archive)))
print('For the next job: configure its stage/seed, attach this saved output, then Save Version -> Save & Run All.')
print('Do not accidentally pay for an interactive run and a second fresh run of the same job.')
print('Download the result ZIP; verify saved output files exist before ending the session.')
''')]
    for i, c in enumerate(cells):
        c['id'] = f'keyswm-{i:02d}'
    nb = {'cells': cells, 'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
          'language_info': {'name': 'python', 'version': '3.11'}}, 'nbformat': 4, 'nbformat_minor': 5}
    dest = ROOT / 'notebooks' / 'keyswm_isic2019.ipynb'
    dest.write_text(json.dumps(nb, indent=1) + '\n')
    print(dest)


if __name__ == '__main__':
    main()
