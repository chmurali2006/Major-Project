"""Deterministic development sweep; empirical decoding coverage, not security bound."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import sparse_refinement as S
from src.persistence import source_digest


def locations(seed,count,pattern,tiles=128):
    rng=np.random.default_rng(seed)
    if pattern=='distributed':return rng.choice(tiles*tiles,count,replace=False)
    if pattern!='clustered':raise ValueError('unsupported pattern')
    width=int(np.ceil(np.sqrt(count)));y=int(rng.integers(0,tiles-width+1));x=int(rng.integers(0,tiles-width+1))
    return np.array([(y+j//width)*tiles+x+j%width for j in range(count)])


def summarise(rows):
    groups={}
    for r in rows:groups.setdefault((r['buckets'],r['changed_tiles'],r['pattern']),[]).append(r)
    result=[]
    for (m,count,pattern),rs in sorted(groups.items()):
        result.append({'buckets':m,'sidecar_bytes':rs[0]['sidecar_bytes'],'changed_tiles':count,'pattern':pattern,
                       'trials':len(rs),'fine_maps':sum(r['fine_map_available'] for r in rs),
                       'unavailable':sum(not r['fine_map_available'] for r in rs),
                       'false_acceptances':sum(r['verdict']=='VERIFIED' for r in rs),
                       'incorrect_exposed_maps':sum(r['map_matches_truth'] is False for r in rs)})
    return result


def run(seeds=range(5),counts=(16,32,64,128,256,512),budgets=(128,512,2048)):
    key=Ed25519PrivateKey.generate();rows=[]
    for seed in seeds:
        # Random RGB intentionally removes any dependence on medical-looking texture.
        original=np.random.default_rng(2000+seed).integers(0,256,(512,512,3),dtype=np.uint8)
        for m in budgets:
            packet=S.sign(original,key,seed,m)
            for count in counts:
                for pattern in ('clustered','distributed'):
                    indices=locations(3000+seed,count,pattern)
                    received=original.copy()
                    for index in indices:received[(index//128)*4,(index%128)*4,0]^=1
                    started=time.perf_counter();r=S.verify(received,packet,key.public_key(),seed)
                    truth=np.zeros(128*128,bool);truth[indices]=True
                    matched=bool(np.array_equal(r.failed_blocks,truth.reshape(128,128))) if r.failed_blocks is not None else None
                    row={'seed':seed,'buckets':m,'sidecar_bytes':len(packet),'changed_tiles':count,
                         'pattern':pattern,'symmetric_difference_entries':2*count,
                         'verification_seconds':time.perf_counter()-started,'verdict':r.verdict,
                         'fine_map_available':r.failed_blocks is not None,'map_matches_truth':matched}
                    rows.append(row)
                    if r.verdict!='FAILED_INTEGRITY' or matched is False:raise AssertionError('unsafe result in sweep')
    return {'schema':'sparse-capacity-development-v1','synthetic':True,'source_sha256':source_digest(ROOT),
            'rows':rows,'summary':summarise(rows),
            'limitations':['Five selected development seeds do not establish a guaranteed capacity or failure probability.',
                           'Changes replace old index/hash entries with new ones: symmetric difference is twice changed tiles.',
                           'Hash placement can be content-dependent; no adaptive-adversary robustness claim.',
                           'Standard IBLT-style decoder; no novelty claim or real-image validation.',
                           'All unavailable fine maps remain in trial denominators; no successful-only IoU.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('new output required')
    result=run();a.out.write_text(json.dumps(result,indent=2)+'\n')
    for r in result['summary']:print(r['buckets'],r['changed_tiles'],r['pattern'],str(r['fine_maps'])+'/'+str(r['trials']))
