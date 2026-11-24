"""Self-contained fixed validation run; no repository/network downloads at runtime."""
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
FILES=['src/__init__.py','src/signed_manifest.py','src/binary_signed_grid.py','src/index_syndrome.py',
       'src/sparse_refinement.py','src/bounded_syndrome.py','src/bounded_acceleration.py',
       'src/paper_aligned_operators.py','scripts/experiment_adapted_validation.py',
       'scripts/prepare_adapted_isic_cohort.py','scripts/package_validation_results.py']

def build():
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
        for name in FILES:z.writestr(name,(ROOT/name).read_bytes())
        z.writestr('cohort.json',(ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json').read_bytes())
    raw=buffer.getvalue();cells=[]
    def cell(kind,text):cells.append({'cell_type':kind,'metadata':{},'source':text.splitlines(True),**({'outputs':[],'execution_count':None} if kind=='code' else {})})
    cell('markdown', '# Adapted ISIC2500 — validation classical controls\nCPU only. Attach the original ISIC2019 dataset (andrewmvd/isic-2019). Missing preparation is rebuilt automatically using the identical fixed cohort; existing preparation can also be reused. No test images are evaluated. This is NOT PFF-WM reproduction or a learned-model comparison.\n\n500 images × 10 operations × 3 controls = 15,000 verification rows. Full signed grids at 4/8 pixels and bounded radius289. Exact RGB truth, not semantic truth. Paper-benign operations remain integrity changes for these exact-pixel controls. Local blur is a surrogate, not lesion removal.\n\nAllow several CPU hours (provisional 2–5 hours, not measured on Kaggle); no GPU quota needed. Results stream per image; completed is written only at the end. Keep all failures. No source pixels/private key exported.\n')
    cell('code', '''import os
os.environ['OMP_NUM_THREADS']='2'
os.environ['MKL_NUM_THREADS']='2'
from pathlib import Path
# Change only this path if preparation output was saved/attached elsewhere.
PREPARATION=Path('/kaggle/working/adapted-isic2500-preparation-v2')
OUT=Path('/kaggle/working/adapted-isic2500-validation-v1')
INPUT=Path('/kaggle/input') # Attach one copy of the original ISIC2019 dataset
assert not OUT.exists(), 'Choose a fresh OUT; never overwrite previous results'
import numpy, PIL, cryptography
print('Dependencies:', numpy.__version__, PIL.__version__, cryptography.__version__)
''')
    cell('code',f'''import base64, hashlib, io, zipfile, subprocess, sys, json
raw=base64.b64decode({base64.b64encode(raw).decode()!r})
assert hashlib.sha256(raw).hexdigest()=={hashlib.sha256(raw).hexdigest()!r}
CODE=Path('/kaggle/working/adapted-validation-code-'+hashlib.sha256(raw).hexdigest()[:12])
CODE.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(io.BytesIO(raw)) as z:z.extractall(CODE)
# A new Kaggle runtime does not contain earlier working files.
if not (PREPARATION/'preparation.json').is_file():
    import shutil
    assert not PREPARATION.exists(), 'Incomplete preparation directory exists; choose a fresh PREPARATION path'
    assert INPUT.is_dir(), 'Attach original ISIC2019 dataset under /kaggle/input'
    assert shutil.disk_usage(PREPARATION.parent).free > 4*1024**3, 'Need at least 4 GiB free for preparation and run evidence'
    print('Rebuilding the identical fixed2500 cohort; no replacements or split changes.',flush=True)
    subprocess.run([sys.executable,str(CODE/'scripts/prepare_adapted_isic_cohort.py'),
        '--manifest',str(CODE/'cohort.json'),'--images',str(INPUT),'--out',str(PREPARATION)],check=True)
process=subprocess.run([sys.executable,str(CODE/'scripts/experiment_adapted_validation.py'),
    '--preparation',str(PREPARATION),'--cohort',str(CODE/'cohort.json'),'--out',str(OUT)])
print('Exit code:',process.returncode, '(nonzero means incomplete run or invariant failure; retain outputs)')
''')
    cell('code', """# Independent ZIP parts, each below 90 MB; upload ALL parts to Drive.
# Partial runs are exported too, but lack a completed summary.
subprocess.run([sys.executable,str(CODE/'scripts/package_validation_results.py'),
    '--out',str(OUT),'--code',str(CODE),'--preparation',str(PREPARATION)],check=True)
print('Completed summary:', (OUT/'summary.json').read_text() if (OUT/'summary.json').exists() else 'INCOMPLETE')
try:
    from IPython.display import FileLink,display
except ImportError:
    FileLink=str
    display=print
for part in sorted(OUT.parent.glob(OUT.name+'-results-part*.zip')):
    print(part.name, part.stat().st_size, 'bytes');display(FileLink(str(part)))
print('Use Save Version / Save & Run All to retain Kaggle outputs. Upload ALL ZIP parts, not prepared pixels.')
""")
    return {'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},'nbformat':4,'nbformat_minor':5}

if __name__=='__main__':
    (ROOT/'deliverables/adapted_isic2500_validation.ipynb').write_text(json.dumps(build(),indent=1)+'\n')
