"""Matched local development comparison under one explicit evidence ceiling."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import bounded_syndrome as B,index_syndrome as I,sparse_refinement as S
from src.persistence import source_digest
from sweep_sparse_capacity import locations
from probe_index_stopping_sets import duplicate_neighbours

CEILING=4220
CONFIGS=(('bounded',B,64),('index-peeling',I,63),('set-peeling',S,73))


def cases(seed):
    result=[(pattern,locations(seed,count,pattern)) for count in (2,16,32,64,65,128)
            for pattern in ('clustered','distributed')]
    for budget in (112,448):result.append(('targeted-index-'+str(budget),duplicate_neighbours(budget)['indices']))
    # Attack the actual comparator layout too, not only historical layouts.
    attack=duplicate_neighbours(63)
    if attack is not None:result.append(('targeted-index-63',attack['indices']))
    return result


def summarise(rows):
    summary=[]
    for name,_,_ in CONFIGS:
        for targeted in (False,True):
            selected=[r for r in rows if r['method']==name and r['pattern'].startswith('targeted')==targeted]
            summary.append({'method':name,'targeted':targeted,'bytes':selected[0]['sidecar_bytes'],
                'trials':len(selected),'fine_maps':sum(r['fine_map_available'] for r in selected),
                'incorrect_maps':sum(r['map_matches_truth'] is False for r in selected),
                'false_acceptances':sum(r['verdict']=='VERIFIED' for r in selected),
                'mean_verify_seconds':float(np.mean([r['verification_seconds'] for r in selected]))})
    return summary


def run():
    rows=[];setup=[];key=Ed25519PrivateKey.generate();pub=key.public_key()
    for seed in (601,602,603):
        x=np.random.default_rng(seed).integers(0,256,(512,512,3),dtype=np.uint8)
        packets={}
        for name,module,parameter in CONFIGS:
            start=time.perf_counter();packet=module.sign(x,key,seed,parameter)
            setup.append({'seed':seed,'method':name,'sidecar_bytes':len(packet),'sign_seconds':time.perf_counter()-start})
            if len(packet)>CEILING:raise AssertionError('exceeded ceiling')
            packets[name]=packet
            # Warm each code path before timed cases.
            assert module.verify(x,packet,pub,seed).verdict=='VERIFIED'
        for trial,(pattern,indices) in enumerate(cases(seed)):
            y=x.copy();truth=np.zeros(16384,bool)
            for index in indices:y[(index//128)*4,(index%128)*4,0]^=1;truth[index]=True
            # Rotate order to avoid one method always running first.
            offset=trial%3;ordered=CONFIGS[offset:]+CONFIGS[:offset]
            for name,module,_ in ordered:
                start=time.perf_counter();r=module.verify(y,packets[name],pub,seed);elapsed=time.perf_counter()-start
                available=r.failed_blocks is not None
                matched=bool(np.array_equal(r.failed_blocks,truth.reshape(128,128))) if available else None
                if r.verdict!='FAILED_INTEGRITY' or matched is False:raise AssertionError('unsafe map or verdict')
                rows.append({'seed':seed,'method':name,'pattern':pattern,'changed_tiles':len(indices),
                    'sidecar_bytes':len(packets[name]),'fine_map_available':available,'map_matches_truth':matched,
                    'verdict':r.verdict,'verification_seconds':elapsed})
    return {'schema':'matched-budget-development-v1','synthetic':True,'ceiling_bytes':CEILING,
        'source_sha256':source_digest(ROOT),'setup':setup,'rows':rows,'summary':summarise(rows),
        'limitations':['Single local CPU run,3development inputs, not stable latency/throughput ranking.',
            'Same byte ceiling, not identical packet lengths or equivalent decoding guarantees.',
            'Bounded radius64 is standard algebraic correction; peeling capacities empirical only.',
            'Targeted attacks favour neither a universal security proof nor a probability estimate.',
            'Signed root gates maps in all3methods; outside-capacity unavailability is not authenticity.',
            'No novel algorithm, real medical-image benchmark, independent final test or SOTA claim.']}


if __name__=='__main__':
    out=ROOT/'deliverables/verification-evidence/matched-budget-development-v1.json'
    if out.exists():raise ValueError('new output required')
    result=run();out.write_text(json.dumps(result,indent=2)+'\n')
    for row in result['summary']:print(row)
    for name,_,_ in CONFIGS:
        selected=[r for r in result['setup'] if r['method']==name]
        print(name,'mean signing seconds',np.mean([r['sign_seconds'] for r in selected]))
