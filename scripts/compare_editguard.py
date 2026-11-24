"""Execute official EditGuard clean weights against explicit classical controls.

External reviewed upstream code/weights are required and are not redistributed.
Synthetic mode is only an adapter/engineering smoke, never an ISIC result.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
import torch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import authentication as A,signed_manifest as S
from src.editguard_adapter import EditGuard
from src.localization_comparison import evaluate
from src.persistence import atomic_json,atomic_write,source_digest
from src.showcase import DEMO_KEY,IMAGE_ID


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--checkout',type=Path,required=True)
    ap.add_argument('--checkpoint',type=Path,required=True)
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--synthetic',action='store_true')
    mode.add_argument('--images',type=Path,nargs='+',help='authorised already-prepared 512px RGB PNG files; no implicit resize')
    ap.add_argument('--preparation',type=Path,help='optional preparation.json binding exact selected image files/provenance')
    ap.add_argument('--n',type=int,default=2,help='synthetic fixtures only')
    ap.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    ap.add_argument('--threads',type=int,default=2)
    ap.add_argument('--out',type=Path,required=True,help='new directory for receipts and numerical maps')
    args=ap.parse_args()
    if args.out.exists() or not 1<=args.n<=8 or not 1<=args.threads<=16:ap.error('new output directory, n1..8, threads1..16 required')
    preparation=None
    if args.preparation:
        if args.synthetic:ap.error('preparation applies only to actual --images inputs')
        preparation=json.loads(args.preparation.read_text())
        if not preparation.get('complete'):ap.error('complete preparation receipt required')
        selected=preparation['selected']
        expected={r['image_id']+'.png':r['prepared_file_sha256'] for r in selected}
        actual={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.images}
        if len(actual)!=len(args.images) or actual!=expected:ap.error('input images do not match exact preparation selection/hashes')
    torch.set_num_threads(args.threads)
    model=EditGuard(args.checkout,args.checkpoint,args.device)
    report={'schema':'editguard-matched-smoke-v1','synthetic':args.synthetic,
            'isic_study':False,'scope':'adapter/engineering pilot, not a reproduced paper benchmark or SOTA superiority result',
            'source_sha256':source_digest(ROOT),'editguard':model.provenance,
            'input_preparation':preparation,
            'preparation_file_sha256':hashlib.sha256(args.preparation.read_bytes()).hexdigest() if args.preparation else None,
            'threshold':{'value':.2,'origin':'official README clean checkpoint, not selected on pilot outcomes'},
            'environment':{'python':sys.version,'platform':platform.platform(),'torch':torch.__version__,'threads':args.threads},
            'pairing':'same decoded source/operators/coordinates; truth measured separately against each method protected reference',
            'limitations':['Prepared 512px decoded RGB only, not native-resolution clinical validation.',
                           'Exact-match authentication and robust learned localisation are distinct contracts.',
                           'Image positivity means any highlighted pixel for this diagnostic; not calibrated paper image detection.',
                           'JPEG is a separate benign-lossy contract test, excluded from edited-image summaries.',
                           'No official AGE-Set/AIGC benchmark scores reproduced.',
                           'EditGuard copyright decoding and key/context robustness are not evaluated here.',
                           'Single source/operator timing, no warmed-up throughput claim.'],
            'samples':[],'artifacts':{}}
    args.out.mkdir(parents=True)
    atomic_json(args.out/'report.json',report)
    signing=Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b'PUBLIC comparison signature seed').digest())
    inputs=range(args.n) if args.synthetic else args.images
    for i,path in enumerate(inputs):
        if args.synthetic:
            from src.fixtures import phantom
            rgb,_=phantom(seed=i)
            source='synthetic phantom '+str(i)
        else:
            with Image.open(path) as im:
                if im.format!='PNG' or im.mode!='RGB' or im.size!=(512,512):raise ValueError('explicit prepared 512px RGB PNG required')
                rgb=np.array(im)
            source=Path(path).name
        sample={'id':i,'source':source,'methods':[]}
        if preparation:
            entry=next(r for r in preparation['selected'] if r['image_id']+'.png'==source)
            sample['diagnosis']=entry['diagnosis']
            sample['grouping_verified']=False
        for name in ('EditGuard clean','Classical baseline','Signed grid 8'):
            began=time.perf_counter();sidecar_bytes=0
            if name=='EditGuard clean':
                reference=model.embed(rgb,seed=i)
                localize=model.localize
            elif name=='Classical baseline':
                reference=A.embed(rgb,DEMO_KEY,IMAGE_ID)
                def localize(x):
                    p=A.failures(x,DEMO_KEY,IMAGE_ID).repeat(8,0).repeat(8,1)
                    return p.astype(float),p
            else:
                block=8
                reference=rgb.copy();evidence=S.sign(reference,signing,IMAGE_ID)
                sidecar_bytes=len(evidence)
                def localize(x,block=block,evidence=evidence):
                    check=S.verify(x,evidence,signing.public_key(),IMAGE_ID)
                    if check.failed_blocks is None:raise RuntimeError('trusted signature fixture failed')
                    p=check.failed_blocks.repeat(block,0).repeat(block,1)
                    return p.astype(float),p
            setup=time.perf_counter()-began
            result,maps=evaluate(rgb,reference,localize,seed=100+i)
            result.update(method=name,setup_seconds=setup,sidecar_bytes=sidecar_bytes)
            if args.device=='cuda':result['timing_warning']='CUDA calls are not synchronized; do not interpret these as GPU latency'
            map_name=f'maps-{i}-{len(sample["methods"])}.npz'
            atomic_write(args.out/map_name,lambda f:np.savez_compressed(f,**maps))
            report['artifacts'][map_name]=hashlib.sha256((args.out/map_name).read_bytes()).hexdigest()
            sample['methods'].append(result)
            print(i,name,'edited IoUs',[round(c['pixel_iou'],4) if c['pixel_iou'] is not None else None for c in result['cases'] if c['family']=='edit'],flush=True)
            # Preserve completed methods if a subsequent model/fixture fails.
            if len(sample['methods'])==1:report['samples'].append(sample)
            atomic_json(args.out/'report.json',report)
    report['complete']=True
    atomic_json(args.out/'report.json',report)
    print(args.out)


if __name__=='__main__':main()
