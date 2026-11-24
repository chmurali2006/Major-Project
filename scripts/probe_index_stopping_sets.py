"""Target public fixed-index hash placement; no secret key used for location search.

A duplicate3-bucket neighbourhood is a2-tile stopping set for singleton peeling.
This attacks fine-localisation availability, NOT signed integrity acceptance.
"""
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
from src import binary_signed_grid as B
from src.persistence import source_digest


def duplicate_neighbours(buckets,n=16384):
    seen={}
    for index in range(n):
        neighbours=tuple(sorted(I.addresses(index,buckets)))
        if neighbours in seen:return {'indices':[seen[neighbours],index],'buckets':list(neighbours),'positions_examined':index+1}
        seen[neighbours]=index
    return None


def run():
    searches=[];rows=[];key=Ed25519PrivateKey.generate()
    for m,old_m in ((112,128),(448,512),(1792,2048)):
        started=time.perf_counter();attack=duplicate_neighbours(m)
        searches.append({'index_buckets':m,'search_seconds':time.perf_counter()-started,'attack':attack})
        if attack is None:continue
        for seed in (401,402,403):
            x=np.random.default_rng(seed).integers(0,256,(512,512,3),dtype=np.uint8)
            y=x.copy();truth=np.zeros((128,128),bool)
            for index in attack['indices']:
                row,col=divmod(index,128);y[row*4,col*4,0]^=1;truth[row,col]=True
            packets=[('index-syndrome',I.sign(x,key,seed,m),I.verify),
                     ('set-reconciliation',S.sign(x,key,seed,old_m),S.verify),
                     ('full-signed-grid',B.sign(x,key,seed,4),B.verify)]
            for method,packet,verify in packets:
                result=verify(y,packet,key.public_key(),seed)
                available=result.failed_blocks is not None
                exact=bool(np.array_equal(truth,result.failed_blocks)) if available else None
                if result.verdict!='FAILED_INTEGRITY' or exact is False:raise AssertionError('unsafe result')
                rows.append({'seed':seed,'index_budget':m,'method':method,'bytes':len(packet),'changed_pixels':2,
                    'changed_tiles':2,'verdict':result.verdict,'fine_map_available':available,'map_matches_truth':exact})
    return {'schema':'index-stopping-set-probe-v1','synthetic':True,'source_sha256':source_digest(ROOT),
        'searches':searches,'rows':rows,'conclusions':[
        'Public fixed-index placement permits targeted low-cardinality stopping sets when duplicate neighbourhoods exist.',
        'Only fine localisation availability is attacked; all modified images still fail signed integrity.',
        'No duplicate at1792buckets is NOT proof there are no larger stopping sets or robust availability guarantees.',
        'Ordinary edit coverage does not justify adaptive-adversary localisation guarantees.',
        'Randomised public layout needs separate analysis; a public seed alone does not eliminate targeted stopping sets.']}


if __name__=='__main__':
    out=ROOT/'deliverables/verification-evidence/index-stopping-set-probe-v1.json'
    if out.exists():raise ValueError('new output required')
    result=run();out.write_text(json.dumps(result,indent=2)+'\n')
    for search in result['searches']:print(search)
    for row in result['rows']:print(row)
