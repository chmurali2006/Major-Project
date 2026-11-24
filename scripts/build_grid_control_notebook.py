"""Reuse exact returned32-image selection for fixed-strength grid experiment."""
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile
from build_editguard_pilot_notebook import cell,ROOT

FILES=['src/__init__.py','src/authentication.py','src/authentication_grid.py','src/showcase.py',
       'src/localization_comparison.py','src/persistence.py','scripts/experiment_grid_tradeoff.py']


def build():
    selection=json.loads((ROOT/'deliverables/verification-evidence/followup32-v1/preparation.json').read_text())
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            entry=zipfile.ZipInfo(name,(2026,10,19,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(entry,(ROOT/name).read_bytes())
    raw=buf.getvalue();digest=hashlib.sha256(raw).hexdigest()
    cells=[cell('markdown','''# Fixed-strength grid control — same32 images
CPU only. No training, checkpoint, upstream clone or EditGuard rerun.
Attach the SAME image dataset used in followup32. Selection, source file hashes,
prepared RGB hashes and order are fixed from that returned run. No substitutions.
This is an engineering control, not a new method or independent held-out study.
4×4 uses four LSBs/channel versus one at8×8; both carry192-bit tags.
Expected runtime: several minutes on CPU (estimate, not a measured32-image run).
If original followup prepared files are still present you can instead run the
experiment script with --preparation pointing to that preparation.json.'''),
    cell('code',f'''import base64,hashlib,io,json,zipfile,sys,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
WORK=Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()
INPUT=Path('/kaggle/input')  # set explicitly if running elsewhere
OUT=WORK/'grid-control32-v1'  # new directory; never overwrite
SOURCE_SHA256={digest!r}
raw=base64.b64decode({base64.b64encode(raw).decode()!r})
assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA256
CODE=WORK/('grid-control-code-'+SOURCE_SHA256[:12]);CODE.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    for entry in z.infolist():
        target=(CODE/entry.filename).resolve()
        assert target.is_relative_to(CODE.resolve())
        target.parent.mkdir(parents=True,exist_ok=True)
        value=z.read(entry)
        if target.exists() and target.read_bytes()!=value:raise ValueError('changed extracted source')
        target.write_bytes(value)
PREPARATION=json.loads({json.dumps(selection,separators=(',',':'))!r})'''),
    cell('code','''# Reconstruct exact preparation without trusting filenames alone.
if OUT.exists():raise ValueError('Use a new OUT; previous results are never overwritten')
paths={}
for path in INPUT.rglob('*'):
    if path.is_file() and path.suffix.lower() in ('.jpg','.jpeg','.png'):
        paths.setdefault(path.stem,[]).append(path)
selected_paths=[]
for entry in PREPARATION['selected']:
    matches=paths.get(entry['image_id'],[])
    matches=[p for p in matches if hashlib.sha256(p.read_bytes()).hexdigest()==entry['source_file_sha256']]
    if len(matches)!=1:raise ValueError('Need exactly one hash-matching source for '+entry['image_id'])
    selected_paths.append(matches[0])
OUT.mkdir();(OUT/'prepared').mkdir()
for entry,path in zip(PREPARATION['selected'],selected_paths):
    with Image.open(path) as im:
        if im.mode!='RGB' or list(im.size)!=entry['source_dimensions']:raise ValueError('source geometry/mode mismatch')
        if hashlib.sha256(np.array(im).tobytes()).hexdigest()!=entry['source_decoded_rgb_sha256']:raise ValueError('source decoded hash mismatch')
        prepared=im.resize((512,512),Image.Resampling.NEAREST)
    if hashlib.sha256(prepared.tobytes()).hexdigest()!=entry['prepared_rgb_sha256']:raise ValueError('prepared RGB mismatch')
    target=OUT/'prepared'/(entry['image_id']+'.png');prepared.save(target)
    # PNG encoder versions may differ; RGB must match, record actual new file hash.
    entry['prepared_file_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
(OUT/'preparation.json').write_text(json.dumps(PREPARATION,indent=2))
print('Reconstructed exact32-source order and RGB hashes; no source substitutions.')'''),
    cell('code','''subprocess.run([sys.executable,str(CODE/'scripts/experiment_grid_tradeoff.py'),
 '--preparation',str(OUT/'preparation.json'),'--out',str(OUT/'grid-results.json')],check=True)
result=json.loads((OUT/'grid-results.json').read_text())
assert result['synthetic'] is False and len(result['rows'])==64
# Only numeric receipts exported, never input/prepared pixels.
package=WORK/'grid-control32-results.zip'
with zipfile.ZipFile(package,'x',zipfile.ZIP_DEFLATED) as z:
    z.write(OUT/'grid-results.json','grid-results.json')
    z.write(OUT/'preparation.json','preparation.json')
from IPython.display import display,FileLink
display(FileLink(str(package)))''')]
    return {'cells':cells,'metadata':{'kernelspec':{'display_name':'Python3','language':'python','name':'python3'},'language_info':{'name':'python'},'source_archive_sha256':digest},'nbformat':4,'nbformat_minor':5}


if __name__=='__main__':
    out=ROOT/'deliverables/grid_control32.ipynb';out.write_text(json.dumps(build(),indent=1)+'\n');print(out)
