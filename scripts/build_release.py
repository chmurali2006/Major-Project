"""Build the local/Kaggle hand-off ZIP. Validation is a separate explicit step."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from build_notebook import main as notebook

ROOT=Path(__file__).resolve().parents[1]


def main():
    notebook()
    out=ROOT/'deliverables'
    shutil.copy2(ROOT/'notebooks/keyswm_isic2019.ipynb',out/'keyswm_isic2019.ipynb')
    shutil.copy2(ROOT/'RUNNING.md',out/'RUNNING.md')
    release=out/'keyswm-ready.zip'
    with zipfile.ZipFile(out/'keyswm-project.zip') as source, zipfile.ZipFile(release,'w',zipfile.ZIP_DEFLATED) as z:
        for name in source.namelist():
            z.writestr(name,source.read(name))
        z.write(ROOT/'notebooks/keyswm_isic2019.ipynb','notebooks/keyswm_isic2019.ipynb')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (release,out/'keyswm-project.zip',out/'keyswm_isic2019.ipynb')}
    (out/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print(release)


if __name__=='__main__': main()
