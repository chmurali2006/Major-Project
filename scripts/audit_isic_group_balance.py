"""Audit cohort ID-range balance/exact RGB duplicates; optional pixel pHash audit.

ID ranges are descriptive proxies, not authoritative publisher provenance.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]


def source_group(image_id):
    digits=image_id.split('_')[1][:4]
    n=int(digits)
    if 12<=n<=14:return '0012-0014 range (MSK/downsampled family; ID-range proxy)'
    if 24<=n<=34:return '0024-0034 range (HAM-family ID-range proxy)'
    if 53<=n<=73:return '0053-0073 range (BCN-family ID-range proxy)'
    return 'other/unclassified'


def phash(path):
    from scipy.fft import dctn
    with Image.open(path) as im:
        x=np.asarray(im.convert('L').resize((32,32),Image.Resampling.LANCZOS),dtype=np.float64)
    coeff=dctn(x,norm='ortho')[:8,:8].ravel();median=np.median(coeff[1:])
    value=0
    for bit in (coeff>median):value=(value<<1)|int(bit)
    return value


def audit(cohort_path,prep_path,images=None,expected_count=2500):
    cohort=json.loads(Path(cohort_path).read_text());prep=json.loads(Path(prep_path).read_text())
    rows=cohort['selected'];prepared=prep['selected']
    if len(rows)!=expected_count or len(prepared)!=expected_count:raise ValueError(f'expected frozen {expected_count} manifest and preparation receipt')
    if [(r['image_id'],r['split'],r['lesion_id']) for r in rows]!=[(r['image_id'],r['split'],r['lesion_id']) for r in prepared]:raise ValueError('cohort/preparation ordering mismatch')
    counts={s:Counter(source_group(r['image_id']) for r in rows if r['split']==s) for s in ('train','validation','test')}
    decoded=defaultdict(list);prepared_hash=defaultdict(list)
    for r in prepared:
        if not r.get('source_decoded_rgb_sha256') or not r.get('prepared_rgb_sha256'):raise ValueError('missing exact RGB receipts')
        decoded[r['source_decoded_rgb_sha256']].append(r);prepared_hash[r['prepared_rgb_sha256']].append(r)
    dup=lambda groups:[{'sha256':h,'images':[{'id':r['image_id'],'split':r['split']} for r in values]} for h,values in groups.items() if len(values)>1]
    exact_source=dup(decoded);exact_prepared=dup(prepared_hash)
    result={'schema':'isic-cohort-source-balance-and-duplicate-audit-v1','cohort_sha256':hashlib.sha256(Path(cohort_path).read_bytes()).hexdigest(),
        'preparation_sha256':hashlib.sha256(Path(prep_path).read_bytes()).hexdigest(),'counts':{s:dict(c) for s,c in counts.items()},
        'exact_rgb':{'source_decoded_cross_split_duplicate_groups':sum(len({v['split'] for v in q['images']})>1 for q in exact_source),
            'source_decoded_duplicate_groups_any_split':len(exact_source),'prepared_cross_split_duplicate_groups':sum(len({v['split'] for v in q['images']})>1 for q in exact_prepared),
            'unique_source_decoded_hashes':len(decoded),'unique_prepared_hashes':len(prepared_hash),'n':len(prepared)},
        'pHash':{'status':'not_run_no_source_images_supplied','method':'32x32 grayscale Lanczos, orthonormal DCT, top-left8x8, AC median threshold, 64-bit Hamming distance',
                 'cross_split_pairs_within_hamming4':None,'minimum_cross_split_distance':None}}
    if images is not None:
        images=Path(images);hashes={}
        for r in rows:
            ident=r['image_id'];matches=[p for p in images.rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png') and p.stem==ident]
            if len(matches)!=1:raise ValueError(f'{ident}: expected one source image, got {len(matches)}')
            hashes[ident]=phash(matches[0])
        train=[r for r in rows if r['split']=='train'];evals=[r for r in rows if r['split']!='train']
        close=[];minimum=64
        for a in train:
            for b in evals:
                distance=(hashes[a['image_id']]^hashes[b['image_id']]).bit_count();minimum=min(minimum,distance)
                if distance<=4:close.append({'a':a['image_id'],'split_a':a['split'],'b':b['image_id'],'split_b':b['split'],'hamming':distance})
        result['pHash']={'status':'completed','method':'32x32 grayscale Lanczos, orthonormal DCT, top-left8x8, AC median threshold, 64-bit Hamming distance',
            'cross_split_pairs_within_hamming4':len(close),'minimum_cross_split_distance':minimum,'pairs':close,
            'caveat':'Perceptual similarity shortlist only; not proof of same lesion or patient.'}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--cohort',type=Path,default=ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json');p.add_argument('--preparation',type=Path,default=ROOT/'deliverables/verification-evidence/adapted-isic2500-preparation-v2/preparation.json');p.add_argument('--images',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('new output required')
    result=audit(a.cohort,a.preparation,a.images);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
