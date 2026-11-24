"""Build a separate source-bound local-ISIC pilot notebook; frozen study untouched."""
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
FILES=['src/__init__.py','src/authentication.py','src/signed_manifest.py','src/showcase.py',
       'src/dataset_audit.py','src/persistence.py','src/local_isic_pilot.py','src/pilot_inputs.py',
       'src/editguard_adapter.py','src/localization_comparison.py',
       'scripts/run_local_isic_pilot.py','scripts/compare_editguard.py','scripts/report_editguard_comparison.py']


def cell(kind,text):
    result={'cell_type':kind,'metadata':{},'source':text.strip().splitlines(True)}
    if kind=='code':result.update(execution_count=None,outputs=[])
    return result


def build():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for filename in FILES:
            info=zipfile.ZipInfo(filename,date_time=(2026,10,19,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,(ROOT/filename).read_bytes())
    raw=buf.getvalue();digest=hashlib.sha256(raw).hexdigest()
    prep=ROOT/'deliverables/verification-evidence/editguard-isic-mirror-pilot-v1/preparation.json'
    prior=[x['image_id'] for x in json.loads(prep.read_text())['selected']] if prep.exists() else []
    cells=[cell('markdown','''# EditGuard paired local-ISIC feasibility pilot
Separate from the frozen study notebook. No training; CPU inference by default.
Unique image/label/checkpoint attachments are discovered and checked before setup.
Attach authorised images, matching ground truth, grouping metadata if available,
and the official EditGuard clean.pth checkpoint. Internet is needed for the pinned
upstream code and optional packages. No account token is requested.

This notebook does not establish official image identity, held-out status, clinical
safety or superiority. It records original dimensions/hashes before explicit nearest
512px preparation. The previous local 8-image mirror run took about five minutes
of CPU evaluation; Kaggle runtime is unmeasured. Start with one image per class.
Upstream code/weights are not redistributed here; licensing review remains needed.'''),
    cell('code',f'''import base64, hashlib, io, json, zipfile
from pathlib import Path
SOURCE_B64={base64.b64encode(raw).decode()!r}
EXPECTED_SOURCE_ARCHIVE_SHA256={digest!r}
archive=base64.b64decode(SOURCE_B64)
assert hashlib.sha256(archive).hexdigest()==EXPECTED_SOURCE_ARCHIVE_SHA256
WORK=Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()
CODE=WORK/('keyswm-editguard-pilot-code-'+EXPECTED_SOURCE_ARCHIVE_SHA256[:12])
CODE.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    for entry in z.infolist():
        target=(CODE/entry.filename).resolve()
        assert target.is_relative_to(CODE.resolve()) and not entry.is_dir()
        target.parent.mkdir(parents=True,exist_ok=True)
        content=z.read(entry)
        if target.exists():
            if target.read_bytes()!=content:raise RuntimeError('Existing extracted source differs; use a fresh location. Nothing was overwritten.')
        else:target.write_bytes(content)
print('Extracted verified project source bundle',EXPECTED_SOURCE_ARCHIVE_SHA256)'''),
    cell('code',f'''# None means discover ONLY a unique matching attachment. Set explicit paths if ambiguous.
INPUT_ROOT=Path('/kaggle/input')
DATA=None  # Path('/kaggle/input/your-attachment/ISIC_2019_Training_Input')
LABELS=None  # matching original one-hot ground-truth CSV
METADATA=None  # CSV with image and patient_id OR lesion_id
GROUP_FIELD=None  # 'patient_id' or 'lesion_id', exactly as documented
ALLOW_IMAGE_LEVEL_PILOT=False  # explicit weaker fallback, NEVER patient-independent evidence
CHECKPOINT=None  # Path('/kaggle/input/your-checkpoint/clean.pth')
PER_CLASS=1
SEED=73
INSTALL_OPTIONAL_PACKAGES=True
# Known preceding mirror-pilot images only. ADD other prior development IDs.
PRIOR_EVALUATION_IDS={prior!r}
OUT=WORK/'local-isic-editguard-pilot'
CHECKOUT=WORK/'EditGuard-reviewed'
print('Top-level input attachments:',[p.name for p in INPUT_ROOT.glob('*')])'''),
    cell('code', '''# Preflight runs BEFORE package installation, upstream clone or inference.
import sys
sys.path.insert(0,str(CODE))
from src.pilot_inputs import resolve_inputs
resolved=resolve_inputs(INPUT_ROOT,data=DATA,labels=LABELS,checkpoint=CHECKPOINT)
DATA,LABELS,CHECKPOINT=resolved['data'],resolved['labels'],resolved['checkpoint']
print('Resolved DATA:',DATA)
print('Resolved LABELS:',LABELS)
print('Resolved CHECKPOINT:',CHECKPOINT)
print('Labelled images:',resolved['labelled_image_ids'])
print(resolved['identity_limitation'])
if METADATA is not None or GROUP_FIELD is not None:
    if METADATA is None or GROUP_FIELD not in ('patient_id','lesion_id') or not Path(METADATA).is_file():
        raise ValueError('Set both an existing METADATA CSV and documented GROUP_FIELD patient_id/lesion_id.')
elif not ALLOW_IMAGE_LEVEL_PILOT:
    raise ValueError('No grouping was supplied. Supply documented METADATA/GROUP_FIELD, or explicitly set ALLOW_IMAGE_LEVEL_PILOT=True for the weaker image-level pilot only. This does not establish patient-independent results.')
if OUT.exists():raise ValueError('OUT already exists; select a NEW output directory. Previous results are never deleted.')'''),
    cell('code', '''import subprocess, sys
if INSTALL_OPTIONAL_PACKAGES:
    subprocess.run([sys.executable,'-m','pip','install','einops==0.8.0','PyYAML>=6,<7','cryptography>=43','Pillow>=11'],check=True)
import torch, torchvision, numpy, PIL
print({'torch':torch.__version__,'torchvision':torchvision.__version__,'numpy':numpy.__version__,'Pillow':PIL.__version__,'device':'cpu'})
# Upstream repository code is executable. Review it before running this cell.
PIN='174778fb371640bb31b32fcb9f7bfd440c88766b'
if not CHECKOUT.exists():
    subprocess.run(['git','clone','--filter=blob:none','--sparse','https://github.com/xuanyuzhang21/EditGuard.git',str(CHECKOUT)],check=True)
    subprocess.run(['git','-C',str(CHECKOUT),'fetch','origin',PIN],check=True)
    subprocess.run(['git','-C',str(CHECKOUT),'checkout','--detach',PIN],check=True)
    subprocess.run(['git','-C',str(CHECKOUT),'sparse-checkout','set','code'],check=True)
assert subprocess.check_output(['git','-C',str(CHECKOUT),'rev-parse','HEAD'],text=True).strip()==PIN'''),
    cell('code', '''import csv
for name,value in [('DATA',DATA),('LABELS',LABELS),('CHECKPOINT',CHECKPOINT)]:
    if value is None or not Path(value).exists():raise ValueError('Configure an existing '+name+' path first.')
if not ALLOW_IMAGE_LEVEL_PILOT and (METADATA is None or GROUP_FIELD is None):
    raise ValueError('Supply documented grouping metadata or explicitly acknowledge image-level pilot only.')
EXCLUDE=WORK/'prior-evaluation-ids.csv'
with EXCLUDE.open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['image_id']);writer.writerows([[x] for x in PRIOR_EVALUATION_IDS])
command=[sys.executable,str(CODE/'scripts/run_local_isic_pilot.py'),
 '--data',str(DATA),'--labels',str(LABELS),'--out',str(OUT),
 '--checkout',str(CHECKOUT),'--checkpoint',str(CHECKPOINT),
 '--per-class',str(PER_CLASS),'--seed',str(SEED),'--exclude-csv',str(EXCLUDE)]
if METADATA is not None:command+=['--metadata',str(METADATA),'--group-field',str(GROUP_FIELD)]
if ALLOW_IMAGE_LEVEL_PILOT:command+=['--allow-image-level-pilot']
subprocess.run(command,check=True)'''),
    cell('code', '''from IPython.display import display, HTML, FileLink
report=json.loads((OUT/'results/report.json').read_text())
assert report.get('complete') is True
# Export numeric receipts/maps only, never original/prepared input images.
package=WORK/'editguard-local-pilot-results.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
    z.write(OUT/'preparation.json','preparation.json')
    for path in sorted((OUT/'results').iterdir()):
        if path.is_file():z.write(path,'results/'+path.name)
print('Result ZIP SHA256:',hashlib.sha256(package.read_bytes()).hexdigest())
display(FileLink(str(package)))
display(HTML((OUT/'results/index.html').read_text()))''')]
    return {'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
           'language_info':{'name':'python'},'source_archive_sha256':digest},'nbformat':4,'nbformat_minor':5}


if __name__=='__main__':
    out=ROOT/'deliverables/editguard_local_isic_pilot.ipynb'
    out.write_text(json.dumps(build(),indent=1)+'\n');print(out)
