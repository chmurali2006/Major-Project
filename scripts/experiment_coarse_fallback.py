"""Development experiment: composite fallback versus plain coarse signed grid."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import binary_signed_grid as B
from src import coarse_fallback as C
from src.fixtures import phantom
from src.localization_comparison import operators
from src.persistence import source_digest


def metrics(mask,truth):
    union=int((mask|truth).sum())
    return {'iou':int((mask&truth).sum())/union if union else None,
            'missed_pixels':int((truth&~mask).sum()),'extra_pixels':int((mask&~truth).sum())}


def run():
    rows=[];key=Ed25519PrivateKey.generate()
    for seed in (111,112,113):
        x,_=phantom(seed=seed)
        for coarse in (16,32):
            baseline=B.sign(x,key,seed,coarse)
            for budget in (512,2048):
                packet=C.sign(x,key,seed,budget,coarse)
                for name,family,y in operators(x,seed):
                    result=C.verify(y,packet,key.public_key(),seed,coarse)
                    reference=B.verify(y,baseline,key.public_key(),seed,coarse)
                    if result.failed_blocks is None:raise AssertionError('unexpected missing fallback')
                    truth=np.any(x!=y,axis=2)
                    mask=result.failed_blocks.repeat(result.resolution,0).repeat(result.resolution,1)
                    rough=reference.failed_blocks.repeat(coarse,0).repeat(coarse,1)
                    measured=metrics(mask,truth)
                    if measured['missed_pixels']!=0:raise AssertionError('incomplete exposed region')
                    rows.append({'seed':seed,'case':name,'family':family,'coarse':coarse,'buckets':budget,
                        'sidecar_bytes':len(packet),'plain_coarse_bytes':len(baseline),'resolution_used':result.resolution,
                        'verdict':result.verdict,'embedding_mse':0,'composite':measured,'plain_coarse':metrics(rough,truth)})
    return {'schema':'coarse-fallback-control-v1','synthetic':True,'source_sha256':source_digest(ROOT),'rows':rows,
            'limits':['Standard multiresolution composition, not a novel method.',
            'All coarse+fine+outer signatures included in storage, no hidden online evidence.',
            'Fallback map covers coarse blocks, not exact edited pixels.',
            'Zero misses in fixtures is not universal/adaptive-adversary security proof.',
            'Development evidence only; no patient/clinical or real-image comparison.']}


if __name__=='__main__':
    out=ROOT/'deliverables/verification-evidence/coarse-fallback-control-v1.json'
    if out.exists():raise ValueError('new output required')
    result=run();out.write_text(json.dumps(result,indent=2)+'\n')
    for coarse in (16,32):
        for budget in (512,2048):
            rs=[r for r in result['rows'] if r['coarse']==coarse and r['buckets']==budget]
            print('coarse',coarse,'buckets',budget,'bytes',rs[0]['sidecar_bytes'],'plain bytes',rs[0]['plain_coarse_bytes'])
            for case in ('one-bit','brightness32','replace64','copy64','jpeg75'):
                selected=[r for r in rs if r['case']==case]
                print(case,'fine',sum(r['resolution_used']==4 for r in selected),'/',len(selected),
                      'IoU',np.mean([r['composite']['iou'] for r in selected]),'coarse IoU',np.mean([r['plain_coarse']['iou'] for r in selected]))
