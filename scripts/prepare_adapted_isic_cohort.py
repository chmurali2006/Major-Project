"""Verify fixed cohort against attached original images, record hashes; no evaluation.

RGB conversion and bicubic512resize are explicit adaptation choices, not verified
identical author preprocessing. Missing/duplicate sources fail without substitutions.
Prepared pixels stay local on Kaggle and are never exported in receipt ZIP.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image,__version__ as PILLOW_VERSION


def prepare(manifest,images,out):
    manifest=Path(manifest);images=Path(images);out=Path(out)
    if out.exists():raise ValueError('new output directory required')
    cohort=json.loads(manifest.read_text());selected=cohort['selected']
    ids=[r['image_id'] for r in selected];lesions=[r['lesion_id'] for r in selected]
    if len(set(ids))!=len(ids) or len(set(lesions))!=len(lesions) or not all(lesions):raise ValueError('unique images and known lesions required')
    if cohort.get('exact_paper_reproduction') is not False:raise ValueError('explicit adapted manifest required')
    matches={ident:[] for ident in ids}
    for path in images.rglob('*'):
        if path.is_file() and path.suffix.lower() in ('.jpg','.jpeg','.png') and path.stem in matches:matches[path.stem].append(path)
    failures={ident:len(paths) for ident,paths in matches.items() if len(paths)!=1}
    if failures:raise ValueError('missing/ambiguous fixed IDs; no substitution: '+str(failures))
    out.mkdir(parents=True);(out/'prepared').mkdir();rows=[]
    for index,entry in enumerate(selected):
        path=matches[entry['image_id']][0];raw=path.read_bytes()
        with Image.open(path) as source:
            source.load();mode=source.mode;dimensions=list(source.size)
            rgb=source.convert('RGB');decoded=hashlib.sha256(rgb.tobytes()).hexdigest()
            prepared=rgb.resize((512,512),Image.Resampling.BICUBIC)
        target=out/'prepared'/(entry['image_id']+'.png');prepared.save(target)
        rows.append({**entry,'source_file_sha256':hashlib.sha256(raw).hexdigest(),'source_mode':mode,
            'source_dimensions':dimensions,'source_decoded_rgb_sha256':decoded,
            'prepared_rgb_sha256':hashlib.sha256(prepared.tobytes()).hexdigest(),
            'prepared_file_sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
        if (index+1)%100==0:print('Prepared',index+1,'/',len(selected),flush=True)
    counts={}
    for r in rows:counts[r['split']]=counts.get(r['split'],0)+1
    hashes={}
    for row in rows:hashes.setdefault(row['source_decoded_rgb_sha256'],set()).add(row['split'])
    cross=[h for h,splits in hashes.items() if len(splits)>1]
    result={'schema':'adapted-isic2019-preparation-v1','cohort_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
        'exact_paper_reproduction':False,'selected':rows,'split_counts':counts,'pillow_version':PILLOW_VERSION,
        'preprocessing':'convertRGB then direct bicubic square512; no implicit EXIF orientation or normalization',
        'cross_split_identical_decoded_rgb_groups':len(cross),
        'ready_for_training':not cross,
        'limits':['Source hashes recorded, not compared against an official publisher checksum manifest.',
            'No patient independence or original author split claim.',
            'No train/evaluation/model/attack execution in this preparation step.',
            'Cross-split identical decoded pixels block training; no silent replacement.']}
    (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    if cross:raise ValueError('cross-split duplicate decoded images: receipt saved; do not train')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for field in ('manifest','images','out'):p.add_argument('--'+field,type=Path,required=True)
    a=p.parse_args();r=prepare(a.manifest,a.images,a.out);print(r['split_counts'])
