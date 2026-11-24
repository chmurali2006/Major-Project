"""Compact detached baseline: synthetic or existing hash-bound prepared inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import binary_signed_grid as B
from src.localization_comparison import evaluate
from src.persistence import source_digest
from experiment_grid_tradeoff import load_inputs


def run(preparation=None,n=4):
    inputs=load_inputs(n,preparation)
    key=Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b'PUBLIC binary-grid benchmark seed').digest())
    rows=[]
    for i,(ident,rgb) in enumerate(inputs):
        for block in (8,4):
            started=time.perf_counter();packet=B.sign(rgb,key,i,block);setup=time.perf_counter()-started
            def localize(x):
                result=B.verify(x,packet,key.public_key(),i,block)
                if result.failed_blocks is None:raise RuntimeError('evidence rejected in controlled benchmark')
                mask=result.failed_blocks.repeat(block,0).repeat(block,1)
                return mask.astype(float),mask
            result,_=evaluate(rgb,rgb.copy(),localize,100+i)
            rows.append({'sample':i,'source_id':ident,'block':block,'sidecar_bytes':len(packet),
                         'digest_bits':256,'signature_bytes':64,'header_bytes':B.HEADER.size,
                         'setup_seconds':setup,**result})
    return {'schema':'binary-signed-grid-experiment-v1','synthetic':preparation is None,
            'source_sha256':source_digest(ROOT),'rows':rows,
            'preparation_file_sha256':hashlib.sha256(Path(preparation).read_bytes()).hexdigest() if preparation else None,
            'limitations':['Detached evidence required; public key/version trusted externally.',
                'No embedding distortion, but evidence size includes digests/header/signature, excludes key distribution.',
                'Standard signed-grid control, no novelty/security-proof/clinical claim.',
                'Different deployment from embedded authentication; JPEG is separate, not tolerated as identical pixels.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--preparation',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('new output required')
    result=run(a.preparation)
    with a.out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    for block in (8,4):
        rows=[r for r in result['rows'] if r['block']==block]
        print('block',block,'sidecar bytes',rows[0]['sidecar_bytes'],'max embedding MSE',max(r['embedding_mse'] for r in rows),
              'missed edit pixels',sum(c['confusion']['fn'] for r in rows for c in r['cases'] if c['family']=='edit'))
