"""Development comparison on exact prepared sources; retains every decoder failure."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import sparse_refinement as S
from src.localization_comparison import operators
from src.persistence import source_digest
from experiment_grid_tradeoff import load_inputs


def run(preparation=None,n=1):
    key=Ed25519PrivateKey.generate();rows=[]
    for index,(ident,rgb) in enumerate(load_inputs(n,preparation)):
        for budget in (128,512,2048):
            started=time.perf_counter();packet=S.sign(rgb,key,index,budget);setup=time.perf_counter()-started
            for name,family,received in operators(rgb,100+index):
                started=time.perf_counter();v=S.verify(received,packet,key.public_key(),index)
                elapsed=time.perf_counter()-started
                pixels=np.any(rgb!=received,axis=2)
                truth=pixels.reshape(128,4,128,4).any(axis=(1,3))
                available=v.failed_blocks is not None
                matched=bool(np.array_equal(truth,v.failed_blocks)) if available else None
                if matched is False or v.verdict!=('FAILED_INTEGRITY' if pixels.any() else 'VERIFIED'):
                    raise AssertionError('unsafe verification or exposed map')
                prediction=v.failed_blocks.repeat(4,0).repeat(4,1) if available else None
                union=int((prediction|pixels).sum()) if available else None
                rows.append({'source_id':ident,'source_rgb_sha256':hashlib.sha256(rgb.tobytes()).hexdigest(),
                    'case':name,'family':family,'source_operator_seed':100+index,'buckets':budget,
                    'sidecar_bytes':len(packet),'setup_seconds':setup,'verification_seconds':elapsed,
                    'embedding_mse':0,'changed_tiles':int(truth.sum()),'changed_pixels':int(pixels.sum()),
                    'verdict':v.verdict,'reason':v.reason,'fine_map_available':available,'map_matches_truth':matched,
                    'pixel_iou':float((prediction&pixels).sum()/union) if available and union else None,
                    'missed_pixels':int((~prediction&pixels).sum()) if available else None,
                    'extra_pixels':int((prediction&~pixels).sum()) if available else None})
    return {'schema':'sparse-real-development-v1','synthetic':preparation is None,'source_sha256':source_digest(ROOT),
        'preparation_file_sha256':hashlib.sha256(Path(preparation).read_bytes()).hexdigest() if preparation else None,
        'rows':rows,'limitations':['Standard signed IBLT-style composition, no novelty claim.',
            'Same32 development sources, not independent final evaluation.',
            'Unavailable localisation is not zero missed pixels or successful detection coverage.',
            'JPEG is a separate changed-pixel case, not benign-tolerance success.',
            'No watermark embedded; original RGB used only for evaluation truth, not verification.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--preparation',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('new output required')
    result=run(a.preparation)
    with a.out.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
    for budget in (128,512,2048):
        for case in ('intact','one-bit','brightness32','replace64','copy64','jpeg75'):
            rs=[r for r in result['rows'] if r['buckets']==budget and r['case']==case]
            print(budget,case,'fine maps',sum(r['fine_map_available'] for r in rs),'/',len(rs))
