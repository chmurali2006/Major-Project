"""Review multipart validation evidence without executing returned code/pixels."""
import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src import binary_signed_grid as G,bounded_syndrome as B
from src.paper_aligned_operators import SETTINGS
from src.paired_coding_analysis import paired_interval,wilson

CASES=('intact','copy32','local_blur32_surrogate','jpeg70','jpeg85','jpeg95','resize90_restore','contrast90','contrast110','gaussian05')
METHODS={'full4':(G,4,524378),'full8':(G,8,131162),'bounded289':(B,4,18620)}


def require(condition,message):
    if not condition:raise ValueError(message)


def review(paths,cohort_path,out,repetitions=10000):
    paths=list(map(Path,paths));out=Path(out)
    with ExitStack() as stack:
        members={};archives=[]
        for path in paths:
            z=stack.enter_context(zipfile.ZipFile(path))
            require(z.testzip() is None,'corrupt archive')
            archives.append({'name':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            for name in z.namelist():
                require(name not in members,'duplicate archive member')
                members[name]=z
        def read(name):
            require(name in members,'missing member: '+name)
            return members[name].read(name)
        def obj(name):return json.loads(read(name))
        cohort_bytes=Path(cohort_path).read_bytes();cohort=json.loads(cohort_bytes)
        require(read('cohort.json')==cohort_bytes,'fixed cohort differs')
        p=obj('preparation.json');protocol=obj('protocol.json');summary=obj('summary.json')
        require(protocol['cohort_sha256']==p['cohort_sha256']==hashlib.sha256(cohort_bytes).hexdigest(),'cohort hash')
        require(protocol['preparation_sha256']==hashlib.sha256(read('preparation.json')).hexdigest(),'preparation hash')
        require(p['ready_for_training'] is True and protocol['split']=='validation' and protocol['operators']==SETTINGS,'protocol mismatch')
        require(len(p['selected'])==len(cohort['selected']) and all(all(r.get(k)==v for k,v in e.items()) for r,e in zip(p['selected'],cohort['selected'])),'preparation identity')
        selected=[r for r in p['selected'] if r['split']=='validation'];ids=[r['image_id'] for r in selected]
        require(len(ids)==500 and len(set(ids))==500,'validation count')
        code_members=[n for n in members if n.startswith('code/')]
        require(bool(code_members),'missing code')
        for name in code_members:
            local=ROOT/name[5:]
            require(local.is_file() and local.read_bytes()==read(name),'returned code differs: '+name)
        rows=[json.loads(line) for line in read('rows.jsonl').splitlines()]
        setup=[json.loads(line) for line in read('setup.jsonl').splitlines()]
        index={(r['image_id'],r['case'],r['method']):r for r in rows}
        require(len(index)==len(rows)==len(ids)*len(CASES)*len(METHODS),'row cardinality')
        require(set(index)=={(i,c,m) for i in ids for c in CASES for m in METHODS},'paired matrix')
        setups={(r['image_id'],r['method']):r for r in setup}
        require(len(setups)==len(setup)==len(ids)*3 and set(setups)=={(i,m) for i in ids for m in METHODS},'setup matrix')
        counts=dict(Counter(r['method']+'/'+r['case'] for r in rows))
        require(summary=={'completed':True,'images':500,'rows':15000,'counts':counts,'invariant_violations':0},'summary mismatch')
        key=Ed25519PublicKey.from_public_bytes(read('public-key.bin'));signature_count=0;map_count=0
        expected_artifacts=set()
        for i,source in enumerate(selected):
            ident=source['image_id']
            for method,(module,block,size) in METHODS.items():
                name=f'artifacts/{i:03d}-{method}.bin';expected_artifacts.add(name);packet=read(name)
                require(len(packet)==size,'packet size');key.verify(packet[-64:],module.DOMAIN+packet[:-64]);signature_count+=1
                context=module.HEADER.unpack(packet[:module.HEADER.size])
                expected=(module.MAGIC,i,512,512,block,289) if module is B else (module.MAGIC,1,i,512,512,block)
                require(context==expected,'packet context')
                s=setups[ident,method]
                require(s['bytes']==size and np.isfinite(s['seconds']) and s['seconds']>=0,'invalid setup')
            name=f'artifacts/{i:03d}-maps.npz';expected_artifacts.add(name)
            with np.load(io.BytesIO(read(name)),allow_pickle=False) as arrays:
                expected_keys={case+'-truth' for case in CASES}
                for case in CASES:
                    packed=arrays[case+'-truth'];require(packed.dtype==np.uint8 and packed.shape==(32768,),'truth encoding')
                    truth=np.unpackbits(packed).reshape(512,512).astype(bool)
                    received_hashes=set();parameters=[]
                    for method,(module,block,size) in METHODS.items():
                        r=index[ident,case,method];received_hashes.add(r['rgb_sha256']);parameters.append(r['parameters'])
                        tiles=truth.reshape(512//block,block,512//block,block).any(axis=(1,3))
                        require(r['seed']==2301+i and r['lesion_id']==source['lesion_id'],'identity/seed')
                        require(r['changed_pixels']==int(truth.sum()) and r['changed_tiles']==int(tiles.sum()),'changed counts')
                        require(r['evidence_bytes']==size and np.isfinite(r['seconds']) and r['seconds']>=0,'size/time')
                        require(r['verdict']==('FAILED_INTEGRITY' if truth.any() else 'VERIFIED') and r['invariant_violation'] is False,'verdict/invariant')
                        available=r['fine_map_available'];require(type(available) is bool,'availability type')
                        if available:
                            k=case+'-'+method;expected_keys.add(k);mask=arrays[k]
                            require(mask.dtype==bool and np.array_equal(mask,tiles),'exposed map mismatch');map_count+=1
                            pixel=mask.repeat(block,0).repeat(block,1);union=int((pixel|truth).sum())
                            iou=int((pixel&truth).sum())/union if union else None
                            require(r['map_matches_tile_truth'] is True and r['missed_pixels']==int((truth&~pixel).sum()) and r['extra_pixels']==int((pixel&~truth).sum()) and r['pixel_iou']==iou,'map metrics')
                        else:
                            require(module is B and tiles.sum()>289,'unexpected abstention')
                            require(all(r[k] is None for k in ('map_matches_tile_truth','missed_pixels','extra_pixels','pixel_iou')),'unavailable metrics not null')
                    require(len(received_hashes)==1 and parameters[0]==parameters[1]==parameters[2],'unpaired operator')
                    if case=='intact':require(not truth.any() and next(iter(received_hashes))==source['prepared_rgb_sha256'],'intact source mismatch')
                require(set(arrays.files)==expected_keys,'missing/extra map keys')
        require({n for n in members if n.startswith('artifacts/')}==expected_artifacts,'artifact matrix differs')
        rng=np.random.default_rng(5101);draws=rng.integers(0,len(ids),size=(repetitions,len(ids)))
        groups=[];paired=[]
        for case in CASES:
            for method in METHODS:
                rs=[index[i,case,method] for i in ids];available=[r for r in rs if r['fine_map_available']]
                groups.append({'case':case,'method':method,'n':len(rs),'fine_maps':len(available),'coverage_wilson95_descriptive':wilson(len(available),len(rs)),
                    'evidence_bytes':rs[0]['evidence_bytes'],'mean_verify_seconds_all':float(np.mean([r['seconds'] for r in rs])),
                    'median_verify_seconds_all':float(np.median([r['seconds'] for r in rs])),
                    'mean_pixel_iou_available_only':float(np.mean([r['pixel_iou'] for r in available if r['pixel_iou'] is not None])) if any(r['pixel_iou'] is not None for r in available) else None,
                    'missed_pixels_available_only':sum(r['missed_pixels'] for r in available) if available else None,'extra_pixels_available_only':sum(r['extra_pixels'] for r in available) if available else None})
            for comparator in ('full4','full8'):
                a=[index[i,case,'bounded289'] for i in ids];b=[index[i,case,comparator] for i in ids]
                paired.append({'case':case,'minus':comparator,'seconds_difference':paired_interval([r['seconds'] for r in a],[r['seconds'] for r in b],draws),
                    'coverage_difference':paired_interval([r['fine_map_available'] for r in a],[r['fine_map_available'] for r in b],draws)})
        result={'schema':'adapted-validation-return-analysis-v1','archives':archives,'images':len(ids),'rows':len(rows),'signatures_checked':signature_count,'maps_checked':map_count,
            'bootstrap':{'repetitions':repetitions,'seed':5101,'unit':'paired source image NOT patient'},'groups':groups,'paired_comparisons':paired,
            'setup':[{'method':m,'bytes':METHODS[m][2],'mean_sign_seconds':float(np.mean([s['seconds'] for s in setup if s['method']==m]))} for m in METHODS],
            'limits':['Returned masks and packet signatures checked; no original/received pixels here to independently replay operators or verify image bindings.',
            'Returned public key is evidence consistency, not independent issuer trust.',
            'Validation development results, image-not-patient intervals; no final/SOTA/clinical claim.',
            'Available-only IoU excludes abstentions: always read alongside map coverage.',
            'Exact-pixel authentication does not tolerate operations labelled benign in the paper.']}
        out.mkdir(parents=True,exist_ok=False)
        for name in ('rows.jsonl','setup.jsonl','protocol.json','summary.json','preparation.json'):(out/name).write_bytes(read(name))
        (out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
        import csv
        with (out/'metrics.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(groups[0]));writer.writeheader();writer.writerows(groups)
        return result

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('parts',nargs='+',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=review(a.parts,ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json',a.out)
    print(json.dumps({k:r[k] for k in ('images','rows','signatures_checked','maps_checked','groups','setup')},indent=2))
