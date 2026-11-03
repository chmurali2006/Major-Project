"""Archive completed AND partial outputs/checkpoints for persistence/resume."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.persistence import atomic_write


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--runs',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    root=args.runs.resolve()
    if not root.is_dir(): raise SystemExit('--runs is not a directory')
    if args.out.resolve()==root or root in args.out.resolve().parents:
        raise SystemExit('archive must be outside the runs directory')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    hashes={}
    def write_archive(fh):
        with zipfile.ZipFile(fh,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(root.rglob('*')):
                if p.is_file() and not p.name.endswith(('.tmp','.lock')):
                    name=p.relative_to(root).as_posix()
                    hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
                    z.write(p,name)
            z.writestr('ARTIFACT_MANIFEST.json',json.dumps(hashes,indent=2)+'\n')
    atomic_write(args.out, write_archive)
    print(f'{args.out}: {len(hashes)} files. Retain the matching source ZIP too.')


if __name__=='__main__':
    main()
