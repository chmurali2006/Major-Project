"""Fetch ONLY a deterministic small unverified-mirror pilot, outside the repo.

Not official ISIC verification; class labels come from another public mirror.
Pixel preparation is explicit nearest512 RGB to match EditGuard test geometry.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PIL import Image
from src.dataset_audit import label_rows,CLASSES
from src.isic_pilot_selection import select
from src.persistence import atomic_json,source_digest
IMAGE_REPO='Sushma7890creator/ISIC-2019-dataset'
IMAGE_COMMIT='b9a0b64d02f9d4893fe63b5dd7379f3e0491ec70'
LABEL_REPO='UdaykiranReddy-1/FedExBC'
LABEL_COMMIT='58db7e4c35a9236a3bdd42093cd3f3d87c81e333'


def api(path):
    return json.loads(subprocess.check_output(['gh','api',path],text=True))


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--destination',type=Path,required=True)
    ap.add_argument('--per-class',type=int,default=1)
    ap.add_argument('--seed',type=int,default=29)
    args=ap.parse_args();dest=args.destination.resolve()
    if dest==ROOT or ROOT in dest.parents or dest.exists():ap.error('new destination OUTSIDE the repository required')
    tree=api(f'repos/{IMAGE_REPO}/git/trees/{IMAGE_COMMIT}?recursive=1')
    if tree.get('truncated'):raise ValueError('refuse truncated image inventory')
    available={}
    for item in tree['tree']:
        if item['path'].lower().endswith('.jpg'):
            ident=Path(item['path']).stem
            if ident in available:raise ValueError('ambiguous duplicate image ID in mirror')
            available[ident]=item
    rows={};total=0;sources=[]
    # Metadata only until the complete deterministic selection is fixed.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        for part in range(1,6):
            path=f'Dataset/ISIC_2019_Training_Input/split_part_{part}.csv'
            obj=api(f'repos/{LABEL_REPO}/contents/{path}?ref={LABEL_COMMIT}')
            raw=base64.b64decode(obj['content'])
            csvpath=Path(tmp)/f'{part}.csv';csvpath.write_bytes(raw)
            labels,n=label_rows(csvpath);total+=n
            for ident,value in labels.items():
                if ident in rows and rows[ident]!=value:raise ValueError('conflicting label duplicates')
                rows[ident]=value
            sources.append({'path':path,'git_blob':obj['sha'],'sha256':hashlib.sha256(raw).hexdigest(),'rows':n})
    selected=select(rows,available,args.per_class,args.seed)
    dest.mkdir(parents=True);(dest/'prepared').mkdir();(dest/'original').mkdir()
    report={'schema':'isic-mirror-pilot-preparation-v1','scope':'unverified-mirror engineering pilot, not held-out ISIC study',
            'selection':'per diagnosis, hash-order SHA256(seed/image_id), no model/pixel access',
            'seed':args.seed,'per_class':args.per_class,'class_order':list(CLASSES),
            'image_source':{'repository':IMAGE_REPO,'commit':IMAGE_COMMIT,'files':len(available)},
            'label_source':{'repository':LABEL_REPO,'commit':LABEL_COMMIT,'parts':sources,
                            'rows':total,'unique_ids':len(rows),'duplicate_rows':total-len(rows)},
            'source_sha256':source_digest(ROOT),'selected':[],
            'official_identity_verified':False,'grouping_available':False,
            'limitations':['Matching filenames and label consistency do not authenticate original ISIC pixels.',
                           'Image mirror may already have resized/compressed images; dimensions/hashes are recorded.',
                           'Labels are partial overlapping mirror partitions, not full official ground truth.',
                           'One image per class is a smoke pilot, not class-wise performance evidence.',
                           'No lesion/patient grouping or population uncertainty claim; no test-set status.']}
    atomic_json(dest/'preparation.json',report)
    for row in selected:
        item=available[row['image_id']]
        blob=api(f'repos/{IMAGE_REPO}/git/blobs/{item["sha"]}')
        raw=base64.b64decode(blob['content'])
        # Independently check Git object identity, not merely transfer success.
        if hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!=item['sha']:raise ValueError('Git blob hash mismatch')
        original=dest/'original'/f'{row["image_id"]}.jpg';original.write_bytes(raw)
        with Image.open(io.BytesIO(raw)) as im:
            if getattr(im,'n_frames',1)!=1:raise ValueError('single-frame input required')
            original_mode=im.mode;original_size=list(im.size)
            prepared=im.convert('RGB').resize((512,512),Image.Resampling.NEAREST)
            target=dest/'prepared'/f'{row["image_id"]}.png';prepared.save(target)
        entry={**row,'mirror_path':item['path'],'mirror_git_blob':item['sha'],
               'original_file_sha256':hashlib.sha256(raw).hexdigest(),'mirror_decoded_size':original_size,
               'mirror_decoded_mode':original_mode,'prepared_file_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
               'prepared_rgb_sha256':hashlib.sha256(prepared.tobytes()).hexdigest(),
               'preparation':'explicit RGB conversion and nearest-neighbour square resize to 512x512; not native originals'}
        report['selected'].append(entry);atomic_json(dest/'preparation.json',report)
        print(row['diagnosis'],row['image_id'],original_size,flush=True)
    with (dest/'manifest.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['image_id','path','label'])
        for r in selected:writer.writerow([r['image_id'],'prepared/'+r['image_id']+'.png',r['label']])
    report['complete']=True;atomic_json(dest/'preparation.json',report)
    print(dest)


if __name__=='__main__':main()
