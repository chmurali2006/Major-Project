"""Measure fixed192-bit tag grid controls on fixtures or hash-bound prepared inputs."""
import argparse
import json
import hashlib
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from src import authentication_grid as G
from src.localization_comparison import evaluate
from src.persistence import source_digest


def load_inputs(n=4,preparation=None):
    inputs=[]
    if preparation is None:
        from src.fixtures import phantom
        for i in range(n):
            rgb,_=phantom(seed=500+i)
            inputs.append((str(i),rgb))
    else:
        from PIL import Image
        preparation=Path(preparation).resolve()
        receipt=json.loads(preparation.read_text())
        if receipt.get('complete') is not True or not 1<=len(receipt['selected'])<=32:
            raise ValueError('complete bounded preparation required')
        for entry in receipt['selected']:
            ident=entry['image_id']
            if Path(ident).name!=ident or '/' in ident or '\\' in ident:raise ValueError('unsafe image ID')
            path=(preparation.parent/'prepared'/(ident+'.png')).resolve()
            if not path.is_relative_to(preparation.parent):raise ValueError('unsafe prepared path')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['prepared_file_sha256']:raise ValueError('prepared file hash mismatch')
            with Image.open(path) as im:
                if im.mode!='RGB' or im.size!=(512,512):raise ValueError('prepared512RGB required')
                rgb=np.array(im)
            if hashlib.sha256(rgb.tobytes()).hexdigest()!=entry['prepared_rgb_sha256']:raise ValueError('prepared RGB hash mismatch')
            inputs.append((ident,rgb))
    return inputs


def run(n=4,preparation=None):
    rows=[]
    inputs=load_inputs(n,preparation)
    for i,(ident,rgb) in enumerate(inputs):
        for block in (8,4):
            reference=G.embed(rgb,b'PUBLIC experimental key',i,block)
            def localize(x):
                mask=G.failures(x,b'PUBLIC experimental key',i,block).repeat(block,0).repeat(block,1)
                return mask.astype(float),mask
            receipt,_=evaluate(rgb,reference,localize,seed=100+i)
            rows.append({'sample':i,'source_id':ident,'block':block,'tag_bits':192,'lsbs_per_channel':192//(block*block*3),**receipt})
    return {'schema':'fixed-tag-grid-experiment-v1','synthetic':preparation is None,'source_sha256':source_digest(ROOT),
            'scope':'engineering control; no clinical, held-out or novelty claim',
            'preparation_file_sha256':hashlib.sha256(Path(preparation).read_bytes()).hexdigest() if preparation else None,'rows':rows,
            'limitations':['Method-specific protected references differ; identical edit operators/seeds, not identical received pixels.',
                          '4x4 requires four LSBs per channel; do not hide the distortion cost.',
                          'Nominal192-bit HMAC tags, no formal security proof or freshness guarantee.',
                          'Simple grid control, not a proposed new research contribution.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--preparation',type=Path,help='existing preparation.json with hash-bound prepared PNGs; no EditGuard rerun');a=p.parse_args()
    result=run(preparation=a.preparation)
    with a.out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    for b in (8,4):
        rows=[r for r in result['rows'] if r['block']==b]
        print('block',b,'meanPSNR',np.mean([r['embedding_psnr_db'] for r in rows]))
        for case in ('one-bit','brightness32','replace64','copy64'):
            cases=[c for r in rows for c in r['cases'] if c['case']==case]
            print(case,'IoU',np.mean([c['pixel_iou'] for c in cases]),'missed',sum(c['confusion']['fn'] for c in cases))
