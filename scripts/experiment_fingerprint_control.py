"""Test shortened-reference costs/collisions; not equal-security improvement claim."""
import json
from pathlib import Path
import sys
import zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import fingerprint_grid as F
from src import binary_signed_grid as B
from src.fixtures import phantom
from src.localization_comparison import operators
from src.persistence import source_digest
from src.sparse_refinement import leaves


def run():
    key=Ed25519PrivateKey.generate();rows=[];storage=[]
    for seed in (91,92,93):
        x,_=phantom(seed=seed)
        full=B.sign(x,key,seed,4)
        storage.append({'seed':seed,'full_grid_bytes':len(full),'zlib_full_grid_bytes':len(zlib.compress(full,9))})
        for width in (1,4,8,16,32):
            packet=F.sign(x,key,seed,width)
            for case,family,y in operators(x,100+seed):
                r=F.verify(y,packet,key.public_key(),seed,width)
                truth=np.any(x!=y,axis=2).reshape(128,4,128,4).any(axis=(1,3))
                if r.verdict!=('FAILED_INTEGRITY' if truth.any() else 'VERIFIED'):raise AssertionError('incorrect verdict')
                rows.append({'seed':seed,'case':case,'family':family,'fingerprint_bits':width*8,'sidecar_bytes':len(packet),
                    'verdict':r.verdict,'changed_tiles':int(truth.sum()),'missed_tiles':int((truth&~r.estimated_blocks).sum()),
                    'extra_tiles':int((~truth&r.estimated_blocks).sum()),'localisation_certified_complete':r.localisation_certified_complete})
    # Deliberately insecure8bit fixture makes the distinction directly observable.
    x=np.zeros((32,32,3),np.uint8);packet=F.sign(x,key,9,1);target=leaves(x,9,4)[0][:1]
    for counter in range(1,10001):
        y=x.copy();y[0,:2,:].flat[:4]=np.frombuffer(counter.to_bytes(4,'big'),np.uint8)
        if leaves(y,9,4)[0][:1]==target:break
    else:raise AssertionError('fixture collision not found')
    r=F.verify(y,packet,key.public_key(),9,1)
    return {'schema':'truncated-fingerprint-control-v1','synthetic':True,'source_sha256':source_digest(ROOT),
        'rows':rows,'storage':storage,'constructed_8bit_collision':{'attempt':counter,'verdict':r.verdict,
        'highlighted_tiles':int(r.estimated_blocks.sum()),'changed_tiles':1},
        'limits':['Shorter fingerprints weaken adversarial localisation; savings not an equal-security improvement.',
            'Full commitment preserves integrity decision under assumed SHA256/Ed25519 security, not fine-map completeness.',
            'Zero observed misses on finite ordinary edits does not establish adaptive attack resistance.',
            '8bit configuration is intentionally insecure demonstration, not a deployment recommendation.',
            'No novel mechanism or real-image benchmark claim.']}


if __name__=='__main__':
    p=ROOT/'deliverables/verification-evidence/fingerprint-control-v1.json'
    if p.exists():raise ValueError('new output required')
    result=run();p.write_text(json.dumps(result,indent=2)+'\n')
    for width in (8,32,64,128,256):
        rows=[r for r in result['rows'] if r['fingerprint_bits']==width]
        print(width,'bits','bytes',rows[0]['sidecar_bytes'],'missed tiles',sum(r['missed_tiles'] for r in rows))
    print('storage',result['storage']);print('collision',result['constructed_8bit_collision'])
