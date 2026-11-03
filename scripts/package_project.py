"""Create a portable source ZIP, without Git history, pixels or run outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def build(destination):
    files=[]
    for pattern in ('src/**/*.py','scripts/*.py','tests/*.py','requirements*.txt','README.md','RUNNING.md','PROTOCOL_V2.md','docs/DESIGN_REVIEW.md','docs/LITERATURE.md','project-context/README.md'):
        files.extend(ROOT.glob(pattern))
    files=sorted(set(files))
    manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p,p.relative_to(ROOT).as_posix())
        z.writestr('SOURCE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    return destination


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--out',type=Path,default=ROOT/'deliverables'/'keyswm-project.zip')
    args=ap.parse_args()
    print(build(args.out))


if __name__=='__main__':
    main()
