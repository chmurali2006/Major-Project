"""Fixed validation-only classical controls; no learned-method/SOTA claim."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image, __version__ as pillow_version
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from src import binary_signed_grid as G, bounded_syndrome as B
from src.paper_aligned_operators import operators, SETTINGS

CONFIGS=(('full4',G,4,4),('full8',G,8,8),('bounded289',B,289,4))

def run(preparation, cohort, out):
    preparation=Path(preparation);cohort=Path(cohort);out=Path(out)
    p=json.loads((preparation/'preparation.json').read_text());c=json.loads(cohort.read_text())
    if p['cohort_sha256']!=hashlib.sha256(cohort.read_bytes()).hexdigest() or not p['ready_for_training']:
        raise ValueError('fixed preparation required')
    if [{k:r[k] for k in e} for r,e in zip(p['selected'],c['selected'])]!=c['selected'] or len(p['selected'])!=len(c['selected']):
        raise ValueError('cohort records differ')
    selected=[r for r in p['selected'] if r['split']=='validation']
    if not selected:raise ValueError('empty validation')
    # Validate every selected input before creating output; never open test pixels.
    for r in selected:
        with Image.open(preparation/'prepared'/(r['image_id']+'.png')) as im:x=np.array(im.convert('RGB'))
        if x.shape!=(512,512,3) or hashlib.sha256(x.tobytes()).hexdigest()!=r['prepared_rgb_sha256']:
            raise ValueError('prepared RGB mismatch: '+r['image_id'])
    out.mkdir(parents=True,exist_ok=False);(out/'artifacts').mkdir()
    key=Ed25519PrivateKey.generate();pub=key.public_key()
    (out/'public-key.bin').write_bytes(pub.public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
    (out/'protocol.json').write_text(json.dumps({'schema':'adapted-validation-v1','cohort_sha256':p['cohort_sha256'],
        'split':'validation','n':len(selected),'seed_rule':'2301 + fixed validation index','operators':SETTINGS,
        'pillow':pillow_version,'numpy':np.__version__,'embedding_mse':0,
        'preparation_sha256':hashlib.sha256((preparation/'preparation.json').read_bytes()).hexdigest(),
        'truth_encoding':'np.packbits row-major 512x512 boolean, bitorder big',
        'configs':[{'name':n,'parameter':p,'block':b} for n,m,p,b in CONFIGS],
        'limits':['Classical controls only; no PFF-WM reproduction or SOTA claim.',
        'All exact RGB changes are integrity failures, including paper benign operations.',
        'No patient independence, semantic localisation or clinical utility claim.',
        'Returned public key is experiment evidence, not independent issuer trust.',
        'Validation outcomes are development evidence. Evaluation does not access test pixels; optional preparation does.']},indent=2))
    counts={};errors=0
    with (out/'rows.jsonl').open('w',buffering=1) as rows, (out/'setup.jsonl').open('w',buffering=1) as setup:
        for index,r in enumerate(selected):
            with Image.open(preparation/'prepared'/(r['image_id']+'.png')) as im:x=np.array(im.convert('RGB'))
            packets={};maps={}
            for name,module,param,block in CONFIGS:
                kw={'backend':'accelerated'} if module is B else {}
                start=time.perf_counter();packet=module.sign(x,key,index,param,**kw)
                elapsed=time.perf_counter()-start
                packets[name]=packet;(out/'artifacts'/f'{index:03d}-{name}.bin').write_bytes(packet)
                setup.write(json.dumps({'image_id':r['image_id'],'method':name,'seconds':elapsed,'bytes':len(packet)})+'\n')
            for trial,op in enumerate(operators(x,2301+index)):
                truth=op['pixel_truth'];y=op['received'];maps[op['case']+'-truth']=np.packbits(truth)
                for name,module,param,block in CONFIGS[trial%3:]+CONFIGS[:trial%3]:
                    kw={'backend':'accelerated'} if module is B else {'block':block}
                    start=time.perf_counter();v=module.verify(y,packets[name],pub,index,**kw);seconds=time.perf_counter()-start
                    tiles=truth.reshape(512//block,block,512//block,block).any(axis=(1,3))
                    available=v.failed_blocks is not None
                    mask=v.failed_blocks.repeat(block,0).repeat(block,1) if available else None
                    match=bool(np.array_equal(v.failed_blocks,tiles)) if available else None
                    expected='FAILED_INTEGRITY' if truth.any() else 'VERIFIED'
                    violation=v.verdict!=expected or match is False or (not available and (module is G or int(tiles.sum())<=289))
                    errors+=int(violation)
                    if available:maps[op['case']+'-'+name]=v.failed_blocks
                    row={'image_id':r['image_id'],'lesion_id':r['lesion_id'],'case':op['case'],'family':op['family'],
                        'method':name,'seed':2301+index,'parameters':op['parameters'],'rgb_sha256':hashlib.sha256(y.tobytes()).hexdigest(),
                        'changed_pixels':int(truth.sum()),'changed_tiles':int(tiles.sum()),'verdict':v.verdict,'reason':v.reason,
                        'fine_map_available':available,'map_matches_tile_truth':match,'invariant_violation':bool(violation),
                        'seconds':seconds,'evidence_bytes':len(packets[name]),
                        'missed_pixels':int((truth&~mask).sum()) if available else None,
                        'extra_pixels':int((mask&~truth).sum()) if available else None,
                        'pixel_iou':float((truth&mask).sum()/(truth|mask).sum()) if available and (truth|mask).any() else None}
                    rows.write(json.dumps(row)+'\n');k=name+'/'+op['case'];counts[k]=counts.get(k,0)+1
            np.savez_compressed(out/'artifacts'/f'{index:03d}-maps.npz',**maps)
            print('Validation',index+1,'/',len(selected),flush=True)
    summary={'completed':True,'images':len(selected),'rows':sum(counts.values()),'counts':counts,'invariant_violations':errors}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));return summary

if __name__=='__main__':
    a=argparse.ArgumentParser(__doc__)
    for k in ('preparation','cohort','out'):a.add_argument('--'+k,required=True,type=Path)
    args=a.parse_args();result=run(args.preparation,args.cohort,args.out)
    print(json.dumps(result,indent=2))
    if result['invariant_violations']:sys.exit(2)
