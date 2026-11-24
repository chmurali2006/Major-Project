"""Build a validation-only matched EditGuard + frozen-DenseNet handoff.

This notebook requires the full fixed image inputs and an enabled external GPU.
It never accesses TEST, trains, tunes thresholds or claims clinical benefit.
"""
import base64
import hashlib
import io
import json
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['src/__init__.py','src/persistence.py','src/diagnostic_impact.py','src/isic_classifier_training.py',
       'src/paper_aligned_operators.py','src/signed_manifest.py','src/binary_signed_grid.py','src/editguard_adapter.py',
       'scripts/prepare_adapted_isic_cohort.py','scripts/experiment_matched_editguard_validation.py']
COHORT='deliverables/verification-evidence/adapted-isic2019-cohort-v1.json'
GUIDE='deliverables/verification-evidence/adapted-classifier-return-v1/review.json'
EDITGUARD_MD5='fd8c6987d67071d3e629133499b44765'
EDITGUARD_COMMIT='174778fb371640bb31b32fcb9f7bfd440c88766b'

def build():
    guide=json.loads((ROOT/GUIDE).read_text());guide_hash=guide['checkpoint_sha256']
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for n in FILES:z.writestr(n,(ROOT/n).read_bytes())
        z.writestr('cohort.json',(ROOT/COHORT).read_bytes())
    raw=buf.getvalue();bundle_sha=hashlib.sha256(raw).hexdigest();cells=[]
    def cell(kind,text):cells.append({'cell_type':kind,'metadata':{},'source':text.splitlines(True),**({'execution_count':None,'outputs':[]} if kind=='code' else {})})
    cell('markdown','''# Matched EditGuard + frozen DenseNet — validation development only

This is a bounded **validation-only** comparison, not a final test. It measures 500 fixed validation images, one official clean EditGuard checkpoint, and the already-reviewed frozen adapted DenseNet121 checkpoint. No model training or threshold tuning. The image preparation recreates all 2,500 fixed cohort rows from original inputs; only validation images enter evaluation.

For each of 10 image operations, matched original vs EditGuard-marked image predictions are evaluated by the exact same operation/seed. The predeclared bridge reports: `operator_without_embedding` (operated original vs original), `embedding_given_operator` (operated marked vs operated original), and `total_embedding_plus_operator` (operated marked vs original). Clean marking is also measured. This paired contrast avoids attributing operator harm to the watermark. Metrics are still only a limited imperfect classifier probe, not clinical safety.

Signed4 is applied to the same marked reference as a localization reader. It adds 524,378 bytes per image (about262 MB/500) and is NOT an equal-storage or end-to-end treatment. EditGuard native weights/in-band message cost and full sidecar costs are reported separately. This tests a published baseline under an adapted local protocol, not author-score reproduction or SOTA superiority.

**Must have:** GPU runtime; original fixed ISIC image files for all 2,500 IDs; the reviewed classifier results ZIP; and the official EditGuard `clean.pth`. Pixels/checkpoints are not included in this notebook. Ensure dataset access/licence is authorised. Internet required to fetch the pinned upstream EditGuard code. Estimates are not promised; check accelerator quota. If any prerequisite is absent, stop before run. Never connect or evaluate TEST here.

The results ZIP contains hashes, probabilities, masks, signed packets and code but no medical source pixels. Split output parts are each <90 MiB for upload limits. Preserve all parts and upload them for audit; do not upload weights/images into the result archive.
''')
    cell('code',f'''import os
os.environ['OMP_NUM_THREADS']='2';os.environ['MKL_NUM_THREADS']='2'
import base64,hashlib,io,json,shutil,subprocess,sys,zipfile
from pathlib import Path
import torch
WORK=Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()
INPUT=Path('/kaggle/input') if Path('/kaggle/input').exists() else Path('/content')
# Configure these ONLY if unique automatic discovery is ambiguous.
IMAGE_ROOT=None
TRAINING_ZIP=None  # accepts the full results ZIP OR a Kaggle input folder containing best.pt, summary.json, protocol.json
EDITGUARD_CHECKPOINT=None  # clean.pth and clean (1).pth are both discoverable
PREPARATION=WORK/'matched-editguard-preparation-v1'
TRAINING=WORK/'reviewed-classifier-v1'
CHECKOUT=WORK/'EditGuard-reviewed'
OUT=WORK/'matched-editguard-validation-v1'
PACKAGE=WORK/'matched-editguard-validation-v1-results.zip'
GUIDE_SHA256={guide_hash!r}
EXPECTED_EDITGUARD_MD5={EDITGUARD_MD5!r}
PINNED_EDITGUARD_COMMIT={EDITGUARD_COMMIT!r}
BUNDLE_B64={base64.b64encode(raw).decode()!r}
BUNDLE_SHA256={bundle_sha!r}
assert torch.cuda.is_available(), 'Enable a GPU; this protocol has no CPU fallback.'
assert not OUT.exists() and not PREPARATION.exists() and not TRAINING.exists() and not PACKAGE.exists(), 'Choose fresh output directories; nothing is overwritten.'
print('GPU:',torch.cuda.get_device_name(0),'input root:',INPUT)
''')
    cell('code',f'''bundle=base64.b64decode(BUNDLE_B64)
assert hashlib.sha256(bundle).hexdigest()==BUNDLE_SHA256
CODE=WORK/('matched-editguard-code-'+BUNDLE_SHA256[:12]);CODE.mkdir(exist_ok=False)
with zipfile.ZipFile(io.BytesIO(bundle)) as z:
    for info in z.infolist():
        target=(CODE/info.filename).resolve()
        assert target.is_relative_to(CODE.resolve()) and not info.is_dir()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(info))
COHORT=CODE/'cohort.json'
# Locate exact approved inputs; fail on ambiguity. Set explicit paths in cell 1 if needed.
def one(candidates,name):
    unique=sorted({{str(p.resolve()):p.resolve() for p in candidates if p.is_file()}}.values())
    if len(unique)!=1:raise RuntimeError(f'Expected exactly one {{name}}, found {{len(unique)}}; set its explicit path in cell 1.')
    return unique[0]
if IMAGE_ROOT is None:
    IMAGE_ROOT=INPUT
if TRAINING_ZIP is None:
    archives=[p for p in INPUT.rglob('adapted-isic2500-classifier-v1-results.zip') if p.is_file()]
    checkpoint_dirs=[]
    for best in INPUT.rglob('best.pt'):
        d=best.parent
        if (d/'summary.json').is_file() and (d/'protocol.json').is_file():checkpoint_dirs.append(d)
    candidates=archives+checkpoint_dirs
    unique=sorted({{str(p.resolve()):p.resolve() for p in candidates}}.values())
    if len(unique)!=1:raise RuntimeError(f'Expected one classifier ZIP or folder with best.pt/summary.json/protocol.json, found {{len(unique)}}. Set TRAINING_ZIP in cell 1.')
    TRAINING_ZIP=unique[0]
if EDITGUARD_CHECKPOINT is None:
    EDITGUARD_CHECKPOINT=one([p for p in INPUT.rglob('*') if p.is_file() and p.name.lower().startswith('clean') and p.suffix.lower()=='.pth'],'EditGuard clean checkpoint (clean.pth or clean (1).pth)')
TRAINING.mkdir()
if Path(TRAINING_ZIP).is_dir():
    source=Path(TRAINING_ZIP)
    for name in ('best.pt','summary.json','protocol.json'):
        if not (source/name).is_file():raise RuntimeError(f'Missing {{name}} in classifier checkpoint folder: {{source}}')
        shutil.copy2(source/name,TRAINING/name)
else:
    with zipfile.ZipFile(TRAINING_ZIP) as z:
        assert z.testzip() is None and 'best.pt' in z.namelist() and 'summary.json' in z.namelist()
        summary=json.loads(z.read('summary.json'))
        assert summary.get('checkpoint_sha256')==GUIDE_SHA256 and summary.get('completed') is True
        for name in ('best.pt','summary.json','protocol.json'):
            (TRAINING/name).write_bytes(z.read(name))
summary=json.loads((TRAINING/'summary.json').read_text())
assert summary.get('checkpoint_sha256')==GUIDE_SHA256 and summary.get('completed') is True
assert hashlib.sha256((TRAINING/'best.pt').read_bytes()).hexdigest()==GUIDE_SHA256
assert __import__('hashlib').md5(EDITGUARD_CHECKPOINT.read_bytes()).hexdigest()==EXPECTED_EDITGUARD_MD5
print('Classifier and EditGuard checkpoint bytes verified. Classifier source:',TRAINING_ZIP,'EditGuard:',EDITGUARD_CHECKPOINT)
print('Original images will be preflighted against the fixed 2,500-ID manifest before evaluation.')''')
    cell('code', '''# Prepare fixed inputs if needed; exact IDs only, no substitutions. No TEST predictions are run.
sys.path.insert(0,str(CODE))
from scripts.prepare_adapted_isic_cohort import prepare
if PREPARATION.exists():raise RuntimeError('Use fresh PREPARATION directory; this cell will not overwrite.')
prepare(COHORT,IMAGE_ROOT,PREPARATION)
print('Fixed preparation complete:',json.loads((PREPARATION/'preparation.json').read_text())['split_counts'])
''')
    cell('code',f'''# Clone only pinned public code, verify commit; user should inspect upstream licensing separately.
import importlib.util
if importlib.util.find_spec('einops') is None or importlib.util.find_spec('yaml') is None:
    subprocess.run([sys.executable,'-m','pip','install','einops==0.8.0','PyYAML>=6,<7'],check=True)
if not CHECKOUT.exists():
    subprocess.run(['git','clone','--filter=blob:none','--sparse','https://github.com/xuanyuzhang21/EditGuard.git',str(CHECKOUT)],check=True)
    subprocess.run(['git','-C',str(CHECKOUT),'fetch','origin',PINNED_EDITGUARD_COMMIT],check=True)
    subprocess.run(['git','-C',str(CHECKOUT),'checkout','--detach',PINNED_EDITGUARD_COMMIT],check=True)
    subprocess.run(['git','-C',str(CHECKOUT),'sparse-checkout','set','code'],check=True)
assert subprocess.check_output(['git','-C',str(CHECKOUT),'rev-parse','HEAD'],text=True).strip()==PINNED_EDITGUARD_COMMIT
import numpy as np
from src.editguard_adapter import EditGuard
from src.isic_classifier_training import load_frozen_densenet
adapter=EditGuard(CHECKOUT,EDITGUARD_CHECKPOINT,'cuda')
adapter.provenance['checkpoint_bytes']=EDITGUARD_CHECKPOINT.stat().st_size
cohort_sha=hashlib.sha256(COHORT.read_bytes()).hexdigest()
classifier,identity=load_frozen_densenet(TRAINING/'best.pt',GUIDE_SHA256,cohort_sha,'cuda')
manifest=json.loads(COHORT.read_text())
for split in ('train','validation'):
    assert set(identity['protocol'][split+'_ids'])=={{r['image_id'] for r in manifest['selected'] if r['split']==split}},'Frozen checkpoint membership differs'
print('Exact pinned models loaded; guide:',identity['selected_epoch'],'EditGuard:',adapter.provenance['checkpoint_sha256'])''')
    cell('code','''from scripts.experiment_matched_editguard_validation import run
summary=run(adapter,PREPARATION,COHORT,OUT,synchronize=torch.cuda.synchronize,
            classifier=classifier,classifier_identity=identity,repetitions=2000)
assert summary['completed'] and summary['images']==500 and summary['rows']==10000 and not summary['test_evaluated']
assert summary['diagnostic_rows']==5000
print('Validation only complete. Inspect summary; any failure means incomplete, not a result.')
''')
    cell('code','''# Auditable ZIP plus upload-sized parts. Do not include image inputs or model weights.
assert OUT.exists() and json.loads((OUT/'summary.json').read_text()).get('completed') is True
assert not PACKAGE.exists()
with zipfile.ZipFile(PACKAGE,'x',zipfile.ZIP_DEFLATED) as z:
    for name in ('protocol.json','rows.jsonl','setup.jsonl','diagnostic-predictions.jsonl','diagnostic-summary.json','summary.json'):
        if (OUT/name).is_file():z.write(OUT/name,name)
    for path in sorted((OUT/'artifacts').rglob('*')):
        if path.is_file():z.write(path,'artifacts/'+path.name)
    z.write(COHORT,'cohort.json');z.write(PREPARATION/'preparation.json','preparation.json')
    for path in sorted(CODE.rglob('*.py')):z.write(path,'code/'+str(path.relative_to(CODE)))
    z.writestr('editguard-checkout.json',json.dumps(adapter.provenance,indent=2))
print('ZIP bytes:',PACKAGE.stat().st_size)
PART=90*1024*1024;parts=[]
with PACKAGE.open('rb') as f:
    i=1
    while True:
        data=f.read(PART)
        if not data:break
        p=WORK/f'matched-editguard-validation-v1-results-part{i:03d}.bin';p.write_bytes(data);parts.append(p);i+=1
print('Upload all parts:',[(p.name,p.stat().st_size) for p in parts])
from IPython.display import FileLink,display
for p in parts:display(FileLink(str(p)))
''')
    return {'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5}

if __name__=='__main__':
    out=ROOT/'deliverables/matched_editguard_validation_v1.ipynb'
    out.write_text(json.dumps(build(),indent=1)+'\n');print(out)
