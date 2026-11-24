"""Classical bounded-code capacity extended to historical patch operators."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import bounded_syndrome as B
from src.fixtures import phantom
from src.localization_comparison import operators
from src.persistence import source_digest


def run():
    key=Ed25519PrivateKey.generate();rows=[];setup=[]
    for seed in (1001,1002):
        x,_=phantom(seed=seed);start=time.perf_counter()
        packet=B.sign(x,key,seed,289,backend='accelerated')
        setup.append({'seed':seed,'radius':289,'sidecar_bytes':len(packet),'sign_seconds':time.perf_counter()-start})
        for case,family,y in operators(x,seed):
            start=time.perf_counter();r=B.verify(y,packet,key.public_key(),seed,backend='accelerated');elapsed=time.perf_counter()-start
            truth=np.any(x!=y,axis=2);tiles=truth.reshape(128,4,128,4).any(axis=(1,3))
            available=r.failed_blocks is not None
            matched=bool(np.array_equal(r.failed_blocks,tiles)) if available else None
            if matched is False:raise AssertionError('incorrect map')
            if int(tiles.sum())<=289 and not available:raise AssertionError('within-radius unavailable')
            if r.verdict!=('FAILED_INTEGRITY' if truth.any() else 'VERIFIED'):raise AssertionError('incorrect integrity')
            pixel=None
            if available:
                mask=r.failed_blocks.repeat(4,0).repeat(4,1);union=int((mask|truth).sum())
                pixel={'missed_pixels':int((truth&~mask).sum()),'extra_pixels':int((mask&~truth).sum()),
                    'iou':int((mask&truth).sum())/union if union else None}
            rows.append({'seed':seed,'case':case,'family':family,'radius':289,'sidecar_bytes':len(packet),
                'changed_tiles':int(tiles.sum()),'verdict':r.verdict,'fine_map_available':available,
                'map_matches_truth':matched,'pixel_metrics':pixel,'verification_seconds':elapsed})
    return {'schema':'bounded-patch-development-v1','synthetic':True,'source_sha256':source_digest(ROOT),
        'rows':rows,'setup':setup,'limits':['Two synthetic development images, not real-image or heldout validation.',
        'Standard bounded code extended in capacity; no novel method or coding-optimality claim.',
        'No embedding distortion; full signed commitment checked before maps.',
        'JPEG changes exact pixels and exceeds correction radius, not benign authentication tolerance.',
        'Single local timing per case; above-radius absence of map remains in results.']}


if __name__=='__main__':
    p=ROOT/'deliverables/verification-evidence/bounded-patch-development-v1.json'
    if p.exists():raise ValueError('new output required')
    r=run();p.write_text(json.dumps(r,indent=2)+'\n')
    for row in r['setup']:print(row)
    for row in r['rows']:print(row)
