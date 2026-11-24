"""Local sparse-sketch feasibility probe, not real-image or novelty evidence."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src.fixtures import phantom
from src import sparse_refinement as S
from src.persistence import source_digest


def run():
    rows=[];key=Ed25519PrivateKey.generate()
    for seed in (81,82,83):
        x,_=phantom(seed=seed)
        cases={'intact':x.copy()}
        y=x.copy();y[129,133,0]^=1;cases['one-bit']=y
        for size in (16,64):
            y=x.copy();y[129:129+size,133:133+size,0]^=1;cases['patch'+str(size)]=y
        for count in (64,1024):
            y=x.copy();indices=np.random.default_rng(seed).choice(128*128,count,replace=False)
            for index in indices:y[(index//128)*4,(index%128)*4,0]^=1
            cases['distributed'+str(count)]=y
        cases['whole-image']=x^np.uint8(1)
        for m in (128,512,2048):
            start=time.perf_counter();packet=S.sign(x,key,seed,m);setup=time.perf_counter()-start
            for name,y in cases.items():
                start=time.perf_counter();r=S.verify(y,packet,key.public_key(),seed);seconds=time.perf_counter()-start
                truth=np.any(x!=y,axis=2).reshape(128,4,128,4).any(axis=(1,3))
                matched=bool(np.array_equal(truth,r.failed_blocks)) if r.failed_blocks is not None else None
                if matched is False:raise AssertionError('incorrect exposed fine map')
                rows.append({'seed':seed,'case':name,'buckets':m,'sidecar_bytes':len(packet),'setup_seconds':setup,
                             'verification_seconds':seconds,'changed_tiles':int(truth.sum()),'verdict':r.verdict,
                             'fine_map_available':r.failed_blocks is not None,'map_matches_truth':matched})
    return {'schema':'sparse-sketch-feasibility-v1','synthetic':True,'source_sha256':source_digest(ROOT),'rows':rows,
            'limits':['IBLT-style reconciliation is prior art; no novelty claim.',
                      'Root-checked decoding tested, not a formal cryptographic/security proof.',
                      'Finite sketch can fail decoding; unavailable maps must not be excluded from coverage.',
                      'Sketch sizes/attacks are development probes, not final tuned test results.']}


if __name__=='__main__':
    out=ROOT/'deliverables/verification-evidence/sparse-sketch-feasibility-v1.json'
    if out.exists():raise ValueError('new output required')
    result=run();out.write_text(json.dumps(result,indent=2)+'\n')
    for m in (128,512,2048):
        rs=[r for r in result['rows'] if r['buckets']==m]
        print('buckets',m,'bytes',rs[0]['sidecar_bytes'])
        for name in dict.fromkeys(r['case'] for r in rs):
            cs=[r for r in rs if r['case']==name]
            print(name,'maps',sum(r['fine_map_available'] for r in cs),'/',len(cs),'changed tiles',cs[0]['changed_tiles'])
