"""Prepare validation-impact handoff only AFTER selecting a reviewed checkpoint.

Requires its actual SHA256 at build time; no placeholder/hash derived from an
unreviewed newly found checkpoint. Does not alter the current training notebook.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
ROOT=Path(__file__).resolve().parents[1]
FILES=['src/__init__.py','src/isic_classifier_training.py','src/persistence.py','src/diagnostic_impact.py',
       'src/adversarial_operators.py','src/paper_aligned_operators.py',
       'scripts/prepare_adapted_isic_cohort.py','scripts/evaluate_adapted_classifier.py']


def build(checkpoint_sha256,*,files=None):
    if not re.fullmatch('[0-9a-f]{64}',checkpoint_sha256):raise ValueError('actual reviewed checkpoint SHA256 required')
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for n in (FILES if files is None else files):z.writestr(n,(ROOT/n).read_bytes())
        z.writestr('cohort.json',(ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json').read_bytes())
    raw=buf.getvalue();cells=[]
    def cell(kind,text):cells.append({'cell_type':kind,'metadata':{},'source':text.splitlines(True),**({'execution_count':None,'outputs':[]} if kind=='code' else {})})
    cell('markdown','''# Frozen classifier impact — validation only
Run only after the classifier return has been reviewed and its checkpoint SHA256 selected. Attach the saved classifier notebook output (including best.pt), plus one original ISIC2019 dataset. GPU enabled; Internet is not needed. No model download, retraining, threshold tuning or test-split evaluation.

Ten existing operations + adapted untargeted FGSM4 / PGD4 (3 steps, step1). This is NOT the paper's exact classifier/attack reproduction. Clean and received balanced accuracy, macroF1, sensitivity, ROC AUC and prediction changes are paired on the same images. Validation selected the checkpoint; results remain development evidence, not clinical safety or final test results.

If prepared files disappeared, they are rebuilt using the identical cohort. Checkpoint discovery only accepts the preselected hash and completed summary. Model parameters remain frozen. GPU runtime provisional 0.5–2 hours, not measured on Kaggle; check quota. Save the notebook version to retain outputs.
''')
    cell('code',f'''import os
os.environ['OMP_NUM_THREADS']='2';os.environ['MKL_NUM_THREADS']='2'
import base64,hashlib,io,json,subprocess,sys,zipfile
from pathlib import Path
import torch
WORK=Path('/kaggle/working');INPUT=Path('/kaggle/input')
TRAINING=WORK/'adapted-isic2500-classifier-v1'
PREPARATION=WORK/'adapted-isic2500-preparation-v2'
OUT=WORK/'adapted-isic2500-classifier-impact-v1'
EXPECTED_CHECKPOINT_SHA256={checkpoint_sha256!r}
assert torch.cuda.is_available(), 'Enable GPU; no silent CPU fallback'
assert not OUT.exists(), 'Choose fresh OUT; previous results will not be overwritten'
def matches(directory):
    try:
        summary=json.loads((directory/'summary.json').read_text())
        return summary.get('completed') is True and summary.get('checkpoint_sha256')==EXPECTED_CHECKPOINT_SHA256 and (directory/'best.pt').is_file()
    except (OSError,ValueError):return False
if not matches(TRAINING):
    candidates=[p.parent for p in INPUT.rglob('summary.json') if matches(p.parent)]
    assert len(candidates)==1, 'Attach ONE saved classifier output including best.pt and completed summary, or set TRAINING to its directory'
    TRAINING=candidates[0]
assert hashlib.sha256((TRAINING/'best.pt').read_bytes()).hexdigest()==EXPECTED_CHECKPOINT_SHA256, 'Checkpoint bytes differ'
print('Reviewed classifier:',TRAINING,'GPU:',torch.cuda.get_device_name(0))
''')
    cell('code',f'''raw=base64.b64decode({base64.b64encode(raw).decode()!r})
assert hashlib.sha256(raw).hexdigest()=={hashlib.sha256(raw).hexdigest()!r}
CODE=WORK/('classifier-impact-code-'+hashlib.sha256(raw).hexdigest()[:12]);CODE.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(io.BytesIO(raw)) as z:z.extractall(CODE)
if not (PREPARATION/'preparation.json').is_file():
    assert not PREPARATION.exists(), 'Partial preparation exists: choose fresh PREPARATION directory'
    subprocess.run([sys.executable,str(CODE/'scripts/prepare_adapted_isic_cohort.py'),
        '--manifest',str(CODE/'cohort.json'),'--images',str(INPUT),'--out',str(PREPARATION)],check=True)
''')
    cell('code', '''process=subprocess.run([sys.executable,str(CODE/'scripts/evaluate_adapted_classifier.py'),
    '--preparation',str(PREPARATION),'--cohort',str(CODE/'cohort.json'),
    '--training',str(TRAINING),'--checkpoint-sha256',EXPECTED_CHECKPOINT_SHA256,'--out',str(OUT),'--device','cuda'])
print('Exit code:',process.returncode,'; nonzero = incomplete/error, not a completed experiment')
''')
    cell('code', '''PACKAGE=WORK/(OUT.name+'-results.zip')
assert OUT.exists(), 'No evaluation output: resolve preflight failure'
assert not PACKAGE.exists(), 'Do not overwrite prior export'
with zipfile.ZipFile(PACKAGE,'x',zipfile.ZIP_DEFLATED) as z:
    for name in ('protocol.json','predictions.jsonl','summary.json'):
        if (OUT/name).is_file():z.write(OUT/name,name)
    z.write(CODE/'cohort.json','cohort.json')
    z.write(PREPARATION/'preparation.json','preparation.json')
    for path in sorted(CODE.rglob('*.py')):z.write(path,'code/'+str(path.relative_to(CODE)))
print('Completed:',(OUT/'summary.json').exists(),'Upload:',PACKAGE,'Bytes:',PACKAGE.stat().st_size)
try:
    from IPython.display import FileLink,display
    display(FileLink(str(PACKAGE)))
except ImportError:print(PACKAGE)
''')
    return {'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5}

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--checkpoint-sha256',required=True);a=p.parse_args()
    (ROOT/'deliverables/adapted_classifier_impact.ipynb').write_text(json.dumps(build(a.checkpoint_sha256),indent=1)+'\n')
