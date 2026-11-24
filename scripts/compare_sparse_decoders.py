"""Equal-byte fixed-index syndrome versus set-reconciliation development sweep."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import index_syndrome as I
from src import sparse_refinement as S
from src.persistence import source_digest
from sweep_sparse_capacity import locations


def run():
    key=Ed25519PrivateKey.generate();rows=[]
    for seed in range(5):
        x=np.random.default_rng(2000+seed).integers(0,256,(512,512,3),dtype=np.uint8)
        for old_m,new_m in ((128,112),(512,448),(2048,1792)):
            old=S.sign(x,key,seed,old_m);new=I.sign(x,key,seed,new_m)
            assert len(old)==len(new)
            for count in (16,32,64,128,256,512):
                for pattern in ('clustered','distributed'):
                    indices=locations(3000+seed,count,pattern);y=x.copy()
                    for index in indices:y[(index//128)*4,(index%128)*4,0]^=1
                    truth=np.zeros(128*128,bool);truth[indices]=True
                    for method,packet,verify in (('set-reconciliation',old,S.verify),('index-syndrome',new,I.verify)):
                        start=time.perf_counter();r=verify(y,packet,key.public_key(),seed)
                        available=r.failed_blocks is not None
                        matched=bool(np.array_equal(truth.reshape(128,128),r.failed_blocks)) if available else None
                        if r.verdict!='FAILED_INTEGRITY' or matched is False:raise AssertionError('unsafe map/verdict')
                        rows.append({'seed':seed,'method':method,'sidecar_bytes':len(packet),'count':count,'pattern':pattern,
                                     'fine_map_available':available,'map_matches_truth':matched,
                                     'verification_seconds':time.perf_counter()-start})
    summary=[]
    for size in sorted({r['sidecar_bytes'] for r in rows}):
        for count in (16,32,64,128,256,512):
            result={'bytes':size,'changed_tiles':count}
            for method in ('set-reconciliation','index-syndrome'):
                selected=[r for r in rows if r['sidecar_bytes']==size and r['count']==count and r['method']==method]
                result[method]={'maps':sum(r['fine_map_available'] for r in selected),'trials':len(selected)}
            summary.append(result)
    return {'schema':'equal-byte-decoder-development-v1','synthetic':True,'source_sha256':source_digest(ROOT),'rows':rows,'summary':summary,
            'limits':['Known finite-field/XOR sparse recovery ingredients, not a novelty or coding-optimality claim.',
            'Both decoders reconstruct the full signed commitment before exposing maps.',
            'Five development seeds/two patterns, not guaranteed capacity or adaptive adversary proof.',
            'Tile positions are fixed and public; no assumption of semantic edit detection.',
            'No real-image result, patient independence or clinical claim.']}


if __name__=='__main__':
    out=ROOT/'deliverables/verification-evidence/equal-byte-decoder-development-v1.json'
    if out.exists():raise ValueError('new output required')
    r=run();out.write_text(json.dumps(r,indent=2)+'\n')
    for s in r['summary']:print(s)
