"""Self-contained, offline CPU cohort preparation notebook with executable checks."""
import base64
import hashlib
import json
from build_editguard_pilot_notebook import cell,ROOT


def build(manifest_bytes=None):
    script=(ROOT/'scripts/prepare_adapted_isic_cohort.py').read_bytes()
    manifest=manifest_bytes if manifest_bytes is not None else (ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json').read_bytes()
    return {'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.11'}},'cells':[
        cell('markdown','''# ISIC 2019 — fixed 2,500-image preparation (v2)
**Purpose:** prepare the adapted cohort, not train or evaluate a model.

1. Import this notebook into Kaggle; select **Accelerator: None**. Internet is unnecessary.
2. Attach the **original ISIC 2019 images** using Add Input. Do not attach only the CSVs, a ZIP that remains unextracted, or a resized/re-encoded copy.
3. Set `INPUT` below to the attached image dataset folder. Run all cells in order.
4. Download the final receipts ZIP and upload it to Drive.

The cohort and preparation script are embedded and hash-checked. No clone, token, pip install or external download is needed. Requires the standard Kaggle NumPy/Pillow/IPython environment.

**Scope:** explicitly adapted selection and preprocessing, NOT the authors' exact PFF-WM reproduction. One known lesion per image, no patient-independence claim. No silent substitutions. Missing/ambiguous images stop execution. Several CPU minutes plus I/O is an estimate, not a measured full-cohort runtime.

**Output:** PNGs remain in the working directory; only JSON receipts enter the exported ZIP. Kaggle Save Version may retain other working outputs separately—do not publish dataset pixels unintentionally. Use a fresh output directory when rerunning.'''),
        cell('code','''from pathlib import Path
# Change INPUT to the specific ORIGINAL image dataset directory if multiple copies are attached.
WORK = Path(globals().get('WORK', '/kaggle/working' if Path('/kaggle/working').exists() else Path.cwd()))
INPUT = Path(globals().get('INPUT', '/kaggle/input'))
OUT = Path(globals().get('OUT', WORK / 'adapted-isic2500-preparation-v2'))
'''),
        cell('code',f'''import base64, hashlib, json, shutil, subprocess, sys, zipfile
import numpy as np
import PIL
from PIL import Image
if not INPUT.is_dir():
    raise ValueError('INPUT is missing: attach and extract the original ISIC 2019 image dataset, then set INPUT.')
WORK.mkdir(parents=True, exist_ok=True)
if OUT.exists():
    raise ValueError('OUT already exists. Choose a fresh OUT or a fresh Kaggle session; previous data will not be overwritten.')
code = base64.b64decode({base64.b64encode(script).decode()!r})
manifest = base64.b64decode({base64.b64encode(manifest).decode()!r})
if hashlib.sha256(code).hexdigest() != {hashlib.sha256(script).hexdigest()!r}:
    raise ValueError('Embedded preparation code checksum mismatch')
if hashlib.sha256(manifest).hexdigest() != {hashlib.sha256(manifest).hexdigest()!r}:
    raise ValueError('Embedded cohort checksum mismatch')
cohort = json.loads(manifest)
expected_counts = cohort['split_counts']
if len(cohort['selected']) != sum(expected_counts.values()):
    raise ValueError('Invalid embedded cohort counts')
# RGB PNG storage can approach raw pixel size. Conservative bound plus overhead.
required_bytes = len(cohort['selected']) * 512 * 512 * 3 * 1.3 + 100 * 1024**2
free_bytes = shutil.disk_usage(WORK).free
if free_bytes < required_bytes:
    raise ValueError('Insufficient free disk space for prepared images; use a clean working directory.')
BUNDLE = WORK / ('adapted-preparation-code-' + hashlib.sha256(code + manifest).hexdigest()[:12])
BUNDLE.mkdir(exist_ok=True)
SCRIPT = BUNDLE / 'prepare_adapted_isic_cohort.py'
MANIFEST = BUNDLE / 'cohort.json'
for path, value in ((SCRIPT, code), (MANIFEST, manifest)):
    if path.exists() and path.read_bytes() != value:
        raise ValueError('Existing embedded file differs: ' + str(path))
    path.write_bytes(value)
print('Python:', sys.version.split()[0], 'NumPy:', np.__version__, 'Pillow:', PIL.__version__)
print('Images:', len(cohort['selected']), 'Splits:', expected_counts)
print('Input:', INPUT, 'Output:', OUT, 'Free GiB:', round(free_bytes / 1024**3, 2))
'''),
        cell('markdown','''## Prepare and verify images
Progress is printed every 100 images. No model is loaded and no test performance is computed.
Missing or duplicate filenames fail before output creation. Unreadable files stop the run; use a fresh output after correcting the source. Identical decoded images across splits produce a receipt but block successful completion. A passing receipt is only a data-preparation check—not research or clinical approval.'''),
        cell('code','''import time
started = time.perf_counter()
subprocess.run([sys.executable, '-u', str(SCRIPT), '--manifest', str(MANIFEST),
                '--images', str(INPUT), '--out', str(OUT)], check=True)
result = json.loads((OUT / 'preparation.json').read_text())
if result['split_counts'] != expected_counts or len(result['selected']) != len(cohort['selected']):
    raise ValueError('Returned source/split counts do not match the fixed cohort')
if result['cohort_sha256'] != hashlib.sha256(manifest).hexdigest():
    raise ValueError('Preparation used a different cohort')
if result['ready_for_training'] is not True:
    raise ValueError('Preparation checks failed; do not train')
print('Preparation finished in', round(time.perf_counter() - started, 1), 'seconds')
print('Verified fixed cohort:', result['split_counts'])
'''),
        cell('markdown','''## Export receipts only
Download the link below. Keep the prepared directory in this Kaggle session for follow-up work; the small ZIP cannot reconstruct images without the original dataset. No private keys, source pixels or model results are included.'''),
        cell('code','''PACKAGE = OUT.parent / (OUT.name + '-results.zip')
with zipfile.ZipFile(PACKAGE, 'x', zipfile.ZIP_DEFLATED) as z:
    z.write(OUT / 'preparation.json', 'preparation.json')
    z.write(MANIFEST, 'cohort.json')
with zipfile.ZipFile(PACKAGE) as z:
    if set(z.namelist()) != {'preparation.json', 'cohort.json'} or z.testzip() is not None:
        raise ValueError('Invalid receipt package')
print('Upload this ZIP to Drive:', PACKAGE.name)
print('Package SHA256:', hashlib.sha256(PACKAGE.read_bytes()).hexdigest())
try:
    from IPython.display import display, FileLink
except ImportError:
    print('Receipt file:', PACKAGE)
else:
    display(FileLink(str(PACKAGE)))
''')]}


if __name__=='__main__':
    path=ROOT/'deliverables/adapted_isic2500_preparation.ipynb'
    path.write_text(json.dumps(build(),indent=1)+'\n');print(path)
