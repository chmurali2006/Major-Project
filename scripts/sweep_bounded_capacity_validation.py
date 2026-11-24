"""Predeclared 50-image validation-only empirical capacity curve for bounded289.

No test access, no guarantee/probability claim; map recovery is measured, not
assumed from a nominal tile budget. Original pixels are not exported.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from src.bounded_syndrome import sign,verify
from src.isic_classifier_training import PreparedSplit
from src.persistence import source_digest

SQUARES=(16,32,48,64,80)
PATCH_COUNTS=(1,2,3,4)

def tile_truth(source,received,block=4):
    truth=np.any(source!=received,axis=2)
    return truth.reshape(512//block,block,512//block,block).any(axis=(1,3))

def edit_square(x,seed,size):
    rng=np.random.default_rng(seed);y=int(rng.integers(0,512-size+1));x0=int(rng.integers(0,512-size+1))
    out=x.copy();patch=out[y:y+size,x0:x0+size].astype(np.int16)
    # Fixed +31 RGB channel change; clipping can produce unchanged channels but not whole patch.
    out[y:y+size,x0:x0+size]=np.clip(patch+31,0,255).astype(np.uint8)
    return out,{'pattern':'square-add31','size':size,'top_left':[y,x0]}

def edit_patches(x,seed,count):
    rng=np.random.default_rng(seed);out=x.copy();coords=[]
    for i in range(count):
        candidates=[(y,x0) for y in range(0,481,32) for x0 in range(0,481,32)
                    if all(abs(y-a)>=32 or abs(x0-b)>=32 for a,b in coords)]
        y,x0=candidates[int(rng.integers(len(candidates)))];coords.append((y,x0))
        patch=out[y:y+32,x0:x0+32].astype(np.int16)
        out[y:y+32,x0:x0+32]=np.clip(patch+31,0,255).astype(np.uint8)
    return out,{'pattern':'disjoint32-square-add31','patch_count':count,'top_lefts':[list(q) for q in coords]}

def scenarios(x,seed):
    yield 'intact',x.copy(),{'pattern':'intact'}
    for size in SQUARES:
        y,p=edit_square(x,seed+size,size);yield f'square{size}',y,p
    for count in PATCH_COUNTS:
        y,p=edit_patches(x,seed+100+count,count);yield f'patch32x{count}',y,p

def run(preparation,cohort,out,n=50):
    ds=PreparedSplit(preparation,cohort,'validation')
    if len(ds)<n:raise ValueError('50 validation images required')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'packets').mkdir()
    key=Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)));public=key.public_key()
    (out/'public-key.bin').write_bytes(public.public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
    rows=[];setup=[]
    for index in range(n):
        _,label,ident=ds[index];entry=ds.rows[index]
        with Image.open(Path(preparation)/'prepared'/(ident+'.png')) as im:x=np.array(im.convert('RGB'))
        if hashlib.sha256(x.tobytes()).hexdigest()!=entry['prepared_rgb_sha256']:raise ValueError('source hash differs')
        t=time.perf_counter();packet=sign(x,key,index,289,4,backend='accelerated');sign_seconds=time.perf_counter()-t
        (out/'packets'/f'{index:03d}.bin').write_bytes(packet)
        setup.append({'image_id':ident,'label':label,'source_sha256':hashlib.sha256(x.tobytes()).hexdigest(),'sidecar_bytes':len(packet),'sign_seconds':sign_seconds})
        for case_i,(case,y,parameters) in enumerate(scenarios(x,91001+index)):
            truth=tile_truth(x,y);t=time.perf_counter();result=verify(y,packet,public,index,4,backend='accelerated');seconds=time.perf_counter()-t
            available=result.failed_blocks is not None;match=bool(np.array_equal(result.failed_blocks,truth)) if available else None
            if result.verdict!=('VERIFIED' if not truth.any() else 'FAILED_INTEGRITY'):raise AssertionError('integrity verdict wrong')
            if available and not match:raise AssertionError('incorrect localization map')
            tp=int((truth&result.failed_blocks).sum()) if available else None
            fp=int((~truth&result.failed_blocks).sum()) if available else None
            fn=int((truth&~result.failed_blocks).sum()) if available else None
            rows.append({'image_id':ident,'case':case,'parameters':parameters,'changed_tiles':int(truth.sum()),
                'changed_pixels':int(np.any(x!=y,axis=2).sum()),'verdict':result.verdict,'reason':result.reason,
                'fine_map_available':available,'map_matches_truth':match,'tile_confusion':{'tp':tp,'fp':fp,'fn':fn} if available else None,
                'sidecar_bytes':len(packet),'verify_seconds':seconds})
        print('capacity sweep',index+1,'/',n,flush=True)
    groups={}
    for r in rows:groups.setdefault(r['case'],[]).append(r)
    summary=[]
    for case,rr in groups.items():
        available=sum(q['fine_map_available'] for q in rr)
        summary.append({'case':case,'images':len(rr),'mean_changed_tiles':float(np.mean([q['changed_tiles'] for q in rr])),
            'fine_map_recovery_count':available,'map_unavailable_count':len(rr)-available,
            'within_available_map_correct_count':sum(q['map_matches_truth'] is True for q in rr),
            'mean_verification_seconds':float(np.mean([q['verify_seconds'] for q in rr])),
            'median_verification_seconds':float(np.median([q['verify_seconds'] for q in rr]))})
    protocol={'schema':'bounded289-validation-capacity-sweep-v1','cohort_sha256':ds.cohort_sha256,'split':'validation','n':n,
        'image_selection':'first50 fixed validation manifest rows in order','block':4,'buckets':289,'backend':'accelerated',
        'square_sizes':SQUARES,'disjoint32_patch_counts':PATCH_COUNTS,'edit':'deterministic +31 RGB, clipped; pixel-level truth generated from actual resulting RGB',
        'seed_rule':'91001 + image index; case sub-seeds derived deterministically','test_evaluated':False,
        'limits':['Empirical selected50-image VAL curve, not a worst-case/adaptive attack bound or universal exact capacity.',
            'Map availability may depend on changed tile pattern as well as count; all abstentions retained.',
            'Clustered edits use deterministic pseudo-random offset; disjoint patches use deterministic coordinates.',
            'Exact RGB changes and bitmaps; not semantic lesion edits or diagnostic outcomes.',
            'Single local runtime measurements per case, not throughput statistics.']}
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2));(out/'setup.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in setup))
    (out/'rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows));(out/'summary.json').write_text(json.dumps({'completed':True,'images':n,'rows':len(rows),'test_evaluated':False,'cases':summary},indent=2))
    (out/'artifact-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2)+'\n')
    return {'images':n,'rows':len(rows),'cases':summary}

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--preparation',type=Path,required=True);p.add_argument('--cohort',type=Path,default=ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    print(json.dumps(run(a.preparation,a.cohort,a.out),indent=2))
