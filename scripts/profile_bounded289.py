"""Profile bounded289 on seeded synthetic RGB; not an ISIC timing result."""
import cProfile
import hashlib
import io
import json
from pathlib import Path
import pstats
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import bounded_syndrome as B


def run(repeats=10):
    x=np.random.default_rng(5501).integers(0,256,(512,512,3),dtype=np.uint8)
    y=x.copy();y[100:164,120:184]=(y[100:164,120:184].astype(np.uint16)+17).clip(0,255).astype(np.uint8)
    key=Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
    packet=B.sign(x,key,17,289,backend='accelerated')
    B.verify(y,packet,key.public_key(),17,backend='accelerated')
    prof=cProfile.Profile();sign_times=[];verify_times=[]
    for _ in range(repeats):
        t=time.perf_counter();prof.enable();p=B.sign(x,key,17,289,backend='accelerated');prof.disable();sign_times.append(time.perf_counter()-t)
        t=time.perf_counter();prof.enable();r=B.verify(y,p,key.public_key(),17,backend='accelerated');prof.disable();verify_times.append(time.perf_counter()-t)
        if r.verdict!='FAILED_INTEGRITY' or r.failed_blocks is None:raise AssertionError('expected local map for synthetic clustered edit')
    stream=io.StringIO();pstats.Stats(prof,stream=stream).strip_dirs().sort_stats('cumulative').print_stats(30)
    output=stream.getvalue()
    return {'schema':'bounded289-cprofile-synthetic-v1','synthetic':True,'source_sha256':hashlib.sha256(x.tobytes()).hexdigest(),
        'packet_bytes':len(packet),'changed_tiles':int(r.failed_blocks.sum()),'calls_each':repeats,
        'sign_mean_seconds':float(np.mean(sign_times)),'verify_mean_seconds':float(np.mean(verify_times)),
        'cprofile_top30':output,'limitations':['Seeded synthetic RGB and clustered patch; not medical images.',
        'Single environment CPU timing only; no deployment throughput claim.',
        'cProfile attributes Python call costs and may not expose internal native-library cost separately.',
        'No test split access.']}

if __name__=='__main__':
    out=ROOT/'deliverables/verification-evidence/bounded289-cprofile-synthetic-v1.json'
    if out.exists():raise SystemExit(f'new output required: {out}')
    result=run();out.write_text(json.dumps(result,indent=2)+'\n');print(result['sign_mean_seconds'],result['verify_mean_seconds'],result['changed_tiles']);print(result['cprofile_top30'])
