"""Build standalone adapted classifier training notebook; test split forbidden."""
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
FILES=['src/__init__.py','src/isic_classifier_training.py','src/diagnostic_impact.py','src/persistence.py',
       'scripts/train_adapted_isic_classifier.py','scripts/prepare_adapted_isic_cohort.py']


def build():
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
        for n in FILES:z.writestr(n,(ROOT/n).read_bytes())
        z.writestr('cohort.json',(ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json').read_bytes())
    raw=buffer.getvalue();cells=[]
    def cell(kind,text):cells.append({'cell_type':kind,'metadata':{},'source':text.splitlines(True),**({'execution_count':None,'outputs':[]} if kind=='code' else {})})
    cell('markdown','''# Adapted ISIC diagnostic classifier — train and validation only
Attach one original ISIC2019 dataset: andrewmvd/isic-2019. Accelerator: single GPU (T4/P100), Internet ON for official torchvision ImageNet initialization. No CheXpert data/checkpoint, no claimed PFF-WM reproduction.

DenseNet121 binary MEL/rest, prepared512 RGB, ImageNet normalization, Adam1e-5, batch8, 20epochs, train-derived class weights, CUDA mixed precision, no augmentation. Adapted baseline settings, not recovered author settings. Validation selects best balanced accuracy; argmax threshold is not tuned. Test split is not evaluated.

Run after the classical-validation job finishes. Allow provisionally 2–6 GPU hours, not measured on Kaggle. Training has a six-hour elapsed-time guard (partial run is NOT completion); platform GPU accounting can differ. Confirm remaining weekly quota first. No automatic retries/tuning or fallback random initialization. If out-of-memory occurs, keep the error/output; do not silently change batch/size. Use Save Version / Save & Run All to retain artifacts.
''')
    cell('code', '''import os
os.environ['OMP_NUM_THREADS']='2';os.environ['MKL_NUM_THREADS']='2'
from pathlib import Path
import base64,hashlib,io,json,zipfile,subprocess,sys,shutil,time
import torch,torchvision,numpy,PIL
WORK=Path('/kaggle/working')
INPUT=Path('/kaggle/input')
PREPARATION=WORK/'adapted-isic2500-preparation-v2'
OUT=WORK/'adapted-isic2500-classifier-v1'
assert torch.cuda.is_available(), 'Enable single GPU; no silent CPU training fallback'
assert not OUT.exists(), 'Choose fresh OUT; never overwrite previous training'
assert shutil.disk_usage(WORK).free>5*1024**3, 'Need at least 5GiB free'
print('GPU:',torch.cuda.get_device_name(0))
print('Versions:',str(torch.__version__),torchvision.__version__,numpy.__version__,PIL.__version__)
''')
    cell('code',f'''raw=base64.b64decode({base64.b64encode(raw).decode()!r})
assert hashlib.sha256(raw).hexdigest()=={hashlib.sha256(raw).hexdigest()!r}
CODE=WORK/('adapted-classifier-code-'+hashlib.sha256(raw).hexdigest()[:12])
CODE.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(io.BytesIO(raw)) as z:z.extractall(CODE)
if not (PREPARATION/'preparation.json').is_file():
    assert not PREPARATION.exists(), 'Partial preparation exists; use fresh PREPARATION path'
    subprocess.run([sys.executable,str(CODE/'scripts/prepare_adapted_isic_cohort.py'),
        '--manifest',str(CODE/'cohort.json'),'--images',str(INPUT),'--out',str(PREPARATION)],check=True)
''')
    cell('code', '''# Official torchvision initialization only. Network failure is fatal, no random fallback.
from torchvision.models import densenet121,DenseNet121_Weights
weights=DenseNet121_Weights.IMAGENET1K_V1
initial=densenet121(weights=weights) # torchvision verifies published filename hash prefix
# Save normalized torchvision-compatible keys; original publisher file may use legacy keys.
WEIGHTS=WORK/'densenet121-imagenet-compatible.pt'
assert not WEIGHTS.exists(), 'Choose a fresh WEIGHTS filename; do not overwrite'
torch.save(initial.state_dict(),WEIGHTS)
WEIGHTS_SHA=hashlib.sha256(WEIGHTS.read_bytes()).hexdigest()
original=Path(torch.hub.get_dir())/'checkpoints'/weights.url.rsplit('/',1)[-1]
publisher_prefix=original.stem.rsplit('-',1)[-1]
original_sha=hashlib.sha256(original.read_bytes()).hexdigest()
assert original_sha.startswith(publisher_prefix), 'Cached original weights hash-prefix mismatch'
INITIALIZATION={'source_url':weights.url,'weights_enum':str(weights),'original_file_sha256':original_sha,
    'publisher_verification':'torchvision filename SHA256 prefix, not independently published full hash',
    'compatible_state_dict_sha256':WEIGHTS_SHA,'torchvision':torchvision.__version__}
(WORK/'classifier-initialization.json').write_text(json.dumps(INITIALIZATION,indent=2))
del initial
torch.cuda.empty_cache()
''')
    cell('code', '''process=subprocess.run([sys.executable,str(CODE/'scripts/train_adapted_isic_classifier.py'),
    '--preparation',str(PREPARATION),'--cohort',str(CODE/'cohort.json'),
    '--weights',str(WEIGHTS),'--weights-sha256',WEIGHTS_SHA,
    '--weights-source',json.dumps(INITIALIZATION,sort_keys=True),'--out',str(OUT),'--device','cuda'])
print('Training exit:',process.returncode,'; nonzero = incomplete/error, retain evidence')
''')
    cell('code', '''# Keep partial evidence too. Never export dataset pixels or initialization weights.
PACKAGE=WORK/(OUT.name+'-results.zip')
assert OUT.exists(), 'No training output; resolve preflight failure'
assert not PACKAGE.exists(), 'Do not overwrite existing package'
with zipfile.ZipFile(PACKAGE,'x',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name in ('protocol.json','history.jsonl','best.pt','selected-validation.json','summary.json'):
            z.write(path,path.name)
    z.write(PREPARATION/'preparation.json','preparation.json')
    z.write(CODE/'cohort.json','cohort.json')
    z.write(WORK/'classifier-initialization.json','initialization.json')
    for path in sorted(CODE.rglob('*.py')):z.write(path,'code/'+str(path.relative_to(CODE)))
assert PACKAGE.stat().st_size<90_000_000, 'Unexpected large package; retain it and report size'
print('Summary:',(OUT/'summary.json').read_text() if (OUT/'summary.json').exists() else 'INCOMPLETE')
print('Upload:',PACKAGE,PACKAGE.stat().st_size,'bytes')
try:
    from IPython.display import FileLink,display
except ImportError:
    FileLink=str
    display=print
display(FileLink(str(PACKAGE)))
''')
    return {'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5}

if __name__=='__main__':
    (ROOT/'deliverables/adapted_isic2500_classifier.ipynb').write_text(json.dumps(build(),indent=1)+'\n')
