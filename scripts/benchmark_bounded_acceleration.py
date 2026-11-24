"""Paired repeated CPU benchmark of byte-identical bounded-syndrome backends."""
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


def run():
    key=Ed25519PrivateKey.generate();rows=[];signing=[]
    for seed in (901,902):
        x=np.random.default_rng(seed).integers(0,256,(512,512,3),dtype=np.uint8)
        for t in (8,64):
            packets={}
            for backend in ('reference','accelerated'):
                # Warmup, then3measured sign calls; no persistent per-image cache.
                B.sign(x,key,seed,t,backend=backend)
            for repeat in range(3):
                order=('reference','accelerated') if repeat%2==0 else ('accelerated','reference')
                for backend in order:
                    start=time.perf_counter();packet=B.sign(x,key,seed,t,backend=backend)
                    signing.append({'seed':seed,'t':t,'repeat':repeat,'backend':backend,'seconds':time.perf_counter()-start})
                    packets[backend]=packet
                if packets['reference']!=packets['accelerated']:raise AssertionError('wire mismatch')
            for count in (0,2,t,t+1):
                y=x.copy();truth=np.zeros((128,128),bool)
                for index in locations(seed,count,'distributed'):
                    row,col=divmod(int(index),128);y[row*4,col*4,0]^=1;truth[row,col]=True
                for backend in ('reference','accelerated'):B.verify(y,packet,key.public_key(),seed,backend=backend)
                for repeat in range(3):
                    order=('reference','accelerated') if repeat%2==0 else ('accelerated','reference');results={}
                    for backend in order:
                        start=time.perf_counter();r=B.verify(y,packet,key.public_key(),seed,backend=backend)
                        elapsed=time.perf_counter()-start;results[backend]=r
                        matched=bool(np.array_equal(r.failed_blocks,truth)) if r.failed_blocks is not None else None
                        if matched is False:raise AssertionError('incorrect map')
                        if count<=t and not matched:raise AssertionError('within-radius unavailable')
                        if r.verdict!=('VERIFIED' if count==0 else 'FAILED_INTEGRITY'):raise AssertionError('wrong verdict')
                        rows.append({'seed':seed,'t':t,'count':count,'repeat':repeat,'backend':backend,
                            'seconds':elapsed,'bytes':len(packet),'verdict':r.verdict,'map_matches_truth':matched,
                            'fine_map_available':r.failed_blocks is not None})
                    a,b=results.values()
                    if (a.verdict,a.reason)!=(b.verdict,b.reason) or not np.array_equal(a.failed_blocks,b.failed_blocks):
                        raise AssertionError('backend mismatch')
    summary=[]
    for t in (8,64):
        for count in (0,2,t,t+1):
            group={'t':t,'count':count}
            for backend in ('reference','accelerated'):
                rs=[r for r in rows if r['t']==t and r['count']==count and r['backend']==backend]
                group[backend+'_median_seconds']=float(np.median([r['seconds'] for r in rs]))
            group['ratio_of_medians']=group['reference_median_seconds']/group['accelerated_median_seconds']
            summary.append(group)
    return {'schema':'bounded-acceleration-benchmark-v1','source_sha256':source_digest(ROOT),'synthetic':True,
        'rows':rows,'signing':signing,'summary':summary,'limits':[
            'Local CPU microbenchmark,2inputs x3repetitions; no cross-machine latency claim.',
            'Identical packets/correction budget/root check, no statistical/probabilistic localisation shortcut.',
            'NumPy engineering optimisation of classical code, NOT a new coding/research contribution.',
            'Warmup calls excluded; all timed repetitions retained.',
            'Reference remains default backend; no frozen study settings changed.']}


if __name__=='__main__':
    p=ROOT/'deliverables/verification-evidence/bounded-acceleration-benchmark-v1.json'
    if p.exists():raise ValueError('new output required')
    r=run();p.write_text(json.dumps(r,indent=2)+'\n')
    for row in r['summary']:print(row)
    for t in (8,64):
        for backend in ('reference','accelerated'):
            print('sign',t,backend,np.median([s['seconds'] for s in r['signing'] if s['t']==t and s['backend']==backend]))
