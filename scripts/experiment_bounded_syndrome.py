"""Classical bounded syndrome baseline on ordinary and targeted development edits."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import bounded_syndrome as B
from src.persistence import source_digest
from sweep_sparse_capacity import locations
from probe_index_stopping_sets import duplicate_neighbours


def run():
    key=Ed25519PrivateKey.generate();rows=[]
    for seed in (501,502,503):
        x=np.random.default_rng(seed).integers(0,256,(512,512,3),dtype=np.uint8)
        for t in (2,8,32,64):
            started=time.perf_counter();packet=B.sign(x,key,seed,t);setup=time.perf_counter()-started
            cases=[]
            for count in (1,t,t+1):
                for pattern in ('clustered','distributed'):cases.append((pattern,locations(seed,count,pattern)))
            if t==2:
                for m in (112,448):cases.append(('targeted-layout-'+str(m),duplicate_neighbours(m)['indices']))
            for pattern,indices in cases:
                y=x.copy();truth=np.zeros(16384,bool)
                for index in indices:y[(index//128)*4,(index%128)*4,0]^=1;truth[index]=True
                started=time.perf_counter();r=B.verify(y,packet,key.public_key(),seed);elapsed=time.perf_counter()-started
                available=r.failed_blocks is not None
                correct=bool(np.array_equal(r.failed_blocks,truth.reshape(128,128))) if available else None
                if correct is False or r.verdict!='FAILED_INTEGRITY':raise AssertionError('unsafe result')
                if len(indices)<=t and not available:raise AssertionError('within-radius decoding failed')
                rows.append({'seed':seed,'t':t,'changed_tiles':len(indices),'pattern':pattern,'sidecar_bytes':len(packet),
                    'setup_seconds':setup,'verification_seconds':elapsed,'fine_map_available':available,
                    'map_matches_truth':correct,'verdict':r.verdict})
    return {'schema':'bounded-syndrome-development-v1','synthetic':True,'source_sha256':source_digest(ROOT),
        'rows':rows,'limitations':['Classical algebraic sparse-error recovery, NOT a novel method.',
        '2t moments support standard <=t error model; finite tests are not a proof or implementation audit.',
        'Full signed commitment gates map release; above-radius cases may return no map.',
        'Encoding/decoding costs and field-length bound must be reported, not only evidence bytes.',
        'No real-image, patient-independent, diagnostic safety or SOTA result.']}


if __name__=='__main__':
    out=ROOT/'deliverables/verification-evidence/bounded-syndrome-development-v1.json'
    if out.exists():raise ValueError('new output required')
    result=run();out.write_text(json.dumps(result,indent=2)+'\n')
    for t in (2,8,32,64):
        rs=[r for r in result['rows'] if r['t']==t]
        within=[r for r in rs if r['changed_tiles']<=t];over=[r for r in rs if r['changed_tiles']>t]
        print('t',t,'bytes',rs[0]['sidecar_bytes'],'within',sum(r['fine_map_available'] for r in within),'/',len(within),
              'above',sum(r['fine_map_available'] for r in over),'/',len(over),
              'mean verify s',sum(r['verification_seconds'] for r in rs)/len(rs))
