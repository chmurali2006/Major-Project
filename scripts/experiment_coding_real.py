"""Matched coding controls on prepared development images; no training/novelty claim."""
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
from cryptography.hazmat.primitives import serialization
from src import bounded_syndrome as B,index_syndrome as I,sparse_refinement as S,binary_signed_grid as G
from src.localization_comparison import operators
from src.persistence import source_digest
from experiment_grid_tradeoff import load_inputs

CONFIGS=(('bounded289',B,289),('index288',I,288),('set330',S,330),('full4',G,4))


def run(preparation=None,n=1,artifacts=None):
    key=Ed25519PrivateKey.generate();pub=key.public_key();rows=[];setup=[]
    if artifacts is not None:
        artifacts=Path(artifacts);artifacts.mkdir(exist_ok=False)
        (artifacts/'public-key.bin').write_bytes(pub.public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
    for index,(ident,x) in enumerate(load_inputs(n,preparation)):
        packets={};maps={}
        for name,module,parameter in CONFIGS:
            kwargs={'backend':'accelerated'} if module is B else {}
            start=time.perf_counter();packet=module.sign(x,key,index,parameter,**kwargs)
            setup.append({'source_id':ident,'method':name,'sidecar_bytes':len(packet),'seconds':time.perf_counter()-start})
            packets[name]=packet
            if artifacts is not None:(artifacts/f'{index:03d}-{name}.bin').write_bytes(packet)
        for trial,(case,family,y) in enumerate(operators(x,100+index)):
            truth=np.any(x!=y,axis=2);tiles=truth.reshape(128,4,128,4).any(axis=(1,3))
            maps[case+'-truth']=tiles
            offset=trial%4
            for name,module,_ in CONFIGS[offset:]+CONFIGS[:offset]:
                kwargs={'backend':'accelerated'} if module is B else {}
                start=time.perf_counter();r=module.verify(y,packets[name],pub,index,**kwargs);elapsed=time.perf_counter()-start
                available=r.failed_blocks is not None
                matched=bool(np.array_equal(r.failed_blocks,tiles)) if available else None
                if matched is False or r.verdict!=('FAILED_INTEGRITY' if truth.any() else 'VERIFIED'):raise AssertionError('unsafe result')
                if module is B and tiles.sum()<=289 and not available:raise AssertionError('within-radius unavailable')
                mask=r.failed_blocks.repeat(4,0).repeat(4,1) if available else None
                union=int((mask|truth).sum()) if available else None
                if available:maps[case+'-'+name]=r.failed_blocks
                rows.append({'source_id':ident,'source_index':index,'source_rgb_sha256':hashlib.sha256(x.tobytes()).hexdigest(),
                    'received_rgb_sha256':hashlib.sha256(y.tobytes()).hexdigest(),'source_operator_seed':100+index,
                    'case':case,'family':family,'method':name,'sidecar_bytes':len(packets[name]),'embedding_mse':0,
                    'changed_tiles':int(tiles.sum()),'changed_pixels':int(truth.sum()),'verdict':r.verdict,'reason':r.reason,
                    'fine_map_available':available,'map_matches_truth':matched,'verification_seconds':elapsed,
                    'pixel_iou':int((mask&truth).sum())/union if available and union else None,
                    'missed_pixels':int((truth&~mask).sum()) if available else None,
                    'extra_pixels':int((mask&~truth).sum()) if available else None})
        if artifacts is not None:np.savez_compressed(artifacts/f'{index:03d}-maps.npz',**maps)
    return {'schema':'coding-real-development-v1','synthetic':preparation is None,'source_sha256':source_digest(ROOT),
        'preparation_file_sha256':hashlib.sha256(Path(preparation).read_bytes()).hexdigest() if preparation else None,
        'setup':setup,'rows':rows,'limitations':['Same32 development images, NOT independent final evaluation.',
        'Classical coding controls, no novel or reproduced published-method claim.',
        'Compact packets under18620bytes, full4 is larger coverage reference, not equal storage.',
        'No patient independence, diagnostic utility, clinical safety or SOTA claim.',
        'JPEG treated as exact-pixel change, not benign tolerance.',
        'Export contains signatures, public key and tile masks, no source pixels/private keys.',
        'Exported key is run evidence, not independently trusted production provenance.',
        'Single timing per case, rotated method order, not stable latency ranking.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--preparation',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--artifacts',type=Path,required=True);a=p.parse_args()
    if a.out.exists() or a.artifacts.exists():p.error('new outputs required')
    r=run(a.preparation,artifacts=a.artifacts);a.out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    for name,_,_ in CONFIGS:
        for case in ('intact','one-bit','brightness32','replace64','copy64','jpeg75'):
            rs=[row for row in r['rows'] if row['method']==name and row['case']==case]
            print(name,case,sum(row['fine_map_available'] for row in rs),'/',len(rs))
