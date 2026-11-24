"""Export independent ZIP parts below connector limits; never include source pixels."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def package(out,code,preparation,limit=90_000_000):
    out=Path(out);code=Path(code);preparation=Path(preparation)
    if not out.is_dir():raise ValueError('No run output; resolve preflight error')
    if list(out.parent.glob(out.name+'-results-part*.zip')):raise ValueError('Previous export exists; do not overwrite')
    files=[]
    for name in ('protocol.json','public-key.bin','rows.jsonl','setup.jsonl','summary.json'):
        p=out/name
        if p.is_file():files.append((p,name))
    for p in sorted((out/'artifacts').glob('*')):
        if p.is_file() and p.suffix in ('.bin','.npz'):files.append((p,'artifacts/'+p.name))
    files.extend([(code/'cohort.json','cohort.json'),(preparation/'preparation.json','preparation.json')])
    for p in sorted(code.rglob('*.py')):files.append((p,'code/'+str(p.relative_to(code))))
    # ZIP_STORED makes sizes predictable. NPZ is already compressed; signatures
    # and SHA256 digests are essentially incompressible.
    groups=[];group=[];used=22
    for path,name in files:
        cost=path.stat().st_size+2*len(name.encode('utf-8'))+128
        if cost+22>limit:raise ValueError('Single export member exceeds part limit: '+name)
        if group and used+cost>limit:groups.append(group);group=[];used=22
        group.append((path,name));used+=cost
    if group:groups.append(group)
    parts=[]
    for i,group in enumerate(groups,1):
        part=out.with_name(out.name+f'-results-part{i:03d}.zip')
        with zipfile.ZipFile(part,'x',zipfile.ZIP_STORED) as z:
            for path,name in group:z.write(path,name)
        if part.stat().st_size>=limit:raise ValueError('Unexpected oversized export')
        parts.append({'name':part.name,'bytes':part.stat().st_size,'sha256':hashlib.sha256(part.read_bytes()).hexdigest()})
    (out.parent/(out.name+'-export-index.json')).write_text(json.dumps({'parts':parts,'completed_summary_present':(out/'summary.json').exists()},indent=2))
    return parts

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for k in ('out','code','preparation'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(package(a.out,a.code,a.preparation),indent=2))
