"""Audit matched EditGuard return receipts/maps without running returned code.

The review recomputes metrics from returned predictions and map confusion from
returned packed masks. Without original pixels/model execution, these are not
independent image/attack replay or clinical evidence.
"""
import argparse
import ast
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from src import binary_signed_grid as G
from src.diagnostic_impact import analyse


def require(value,message):
    if not value:raise ValueError(message)


def close(actual,expected,path='summary'):
    """Compare nested JSON metrics with tight tolerance for floating values."""
    if isinstance(expected,dict):
        require(isinstance(actual,dict) and actual.keys()==expected.keys(),'keys differ: '+path)
        for key in expected:close(actual[key],expected[key],path+'/'+key)
    elif isinstance(expected,list):
        require(isinstance(actual,list) and len(actual)==len(expected),'list differs: '+path)
        for i,value in enumerate(expected):close(actual[i],value,path+'/'+str(i))
    elif isinstance(expected,float):
        require(isinstance(actual,(int,float)) and not isinstance(actual,bool) and np.isfinite(actual) and np.isclose(actual,expected,rtol=1e-9,atol=1e-10),'metric differs: '+path)
    else:
        require(type(actual)==type(expected) and actual==expected,'value differs: '+path)

CASES=('intact','copy32','local_blur32_surrogate','jpeg70','jpeg85','jpeg95','resize90_restore','contrast90','contrast110','gaussian05')
METHODS=('EditGuard clean','Signed4 on EditGuard container')

def embedded_bundle(notebook):
    nb=json.loads(Path(notebook).read_text());found=[]
    for cell in nb['cells']:
        if cell['cell_type']!='code':continue
        tree=ast.parse(''.join(cell['source']))
        for node in ast.walk(tree):
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BUNDLE_B64' for t in node.targets):found.append(ast.literal_eval(node.value))
    require(len(found)==1,'sent notebook bundle literal missing/duplicate')
    return __import__('base64').b64decode(found[0])

def probability(p):
    a=np.asarray(p,dtype=float)
    require(a.shape==(2,) and np.isfinite(a).all() and (a>=0).all() and (a<=1).all() and np.isclose(a.sum(),1,rtol=0,atol=1e-6),'invalid probabilities')
    return a

def packed_map(data):
    bits=np.unpackbits(np.frombuffer(data,dtype=np.uint8))
    require(len(bits)==512*512,'invalid packed map length')
    return bits.astype(bool).reshape(512,512)

def confusion(truth,pred):
    tp=int((truth&pred).sum());fp=int((~truth&pred).sum());fn=int((truth&~pred).sum());tn=int((~truth&~pred).sum())
    return {'tp':tp,'fp':fp,'fn':fn,'tn':tn}

def review(archive,notebook,out,*,public_key_path=None,allow_missing_public_key=False):
    archive=Path(archive);notebook=Path(notebook);out=Path(out)
    external_key=Path(public_key_path).read_bytes() if public_key_path is not None else None
    if external_key is not None:require(len(external_key)==32,'external Ed25519 public key must be 32 raw bytes')
    bundle=embedded_bundle(notebook);bundle_sha=hashlib.sha256(bundle).hexdigest()
    expected_code={}
    with zipfile.ZipFile(io.BytesIO(bundle)) as b:
        for name in b.namelist():expected_code[name]=b.read(name)
    notebook_hash=hashlib.sha256(notebook.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();require(len(names)==len(set(names)) and z.testzip() is None,'duplicate/corrupt ZIP')
        cohort_bytes=(ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json').read_bytes()
        require(z.read('cohort.json')==cohort_bytes==expected_code['cohort.json'],'cohort mismatch')
        for name,raw in expected_code.items():
            if name.endswith('.py'):require(z.read('code/'+name)==raw,'returned source mismatch '+name)
        required={'protocol.json','rows.jsonl','setup.jsonl','diagnostic-predictions.jsonl','diagnostic-summary.json','summary.json','cohort.json','preparation.json','editguard-checkout.json'}
        has_archive_key='public-key.bin' in names
        if has_archive_key:required.add('public-key.bin')
        archive_key=z.read('public-key.bin') if has_archive_key else None
        if archive_key is not None and external_key is not None:
            require(archive_key==external_key,'archive and external public keys differ')
        key_bytes=archive_key if archive_key is not None else external_key
        key_source='archive' if archive_key is not None else ('external_file' if external_key is not None else None)
        require(key_bytes is not None or allow_missing_public_key,'public-key.bin missing; supply --public-key to verify signatures')
        expected_names=required|{'code/'+n for n in expected_code if n.endswith('.py')}|{f'artifacts/{i:03d}-signed4.bin' for i in range(500)}|{f'artifacts/{i:03d}-maps.npz' for i in range(500)}
        require(set(names)==expected_names,'archive members missing/unexpected')
        protocol=json.loads(z.read('protocol.json'));summary=json.loads(z.read('summary.json'))
        prep=json.loads(z.read('preparation.json'));manifest=json.loads(cohort_bytes);editguard=json.loads(z.read('editguard-checkout.json'))
        require(protocol['schema']=='adapted-matched-editguard-validation-v2' and protocol['split']=='validation' and protocol['n']==500,'wrong protocol or split')
        require(protocol['cohort_sha256']==hashlib.sha256(cohort_bytes).hexdigest(),'cohort hash differs')
        require(protocol['diagnostic_pairing'].startswith('four conditions'),'diagnostic pairing not specified')
        require(prep['cohort_sha256']==protocol['cohort_sha256'] and prep['ready_for_training'] is True,'preparation differs/incomplete')
        selected=[r for r in prep['selected'] if r['split']=='validation'];require(len(selected)==500,'validation preparation count differs')
        require([r['image_id'] for r in selected]==[r['image_id'] for r in manifest['selected'] if r['split']=='validation'],'validation membership/order differs')
        guide=json.loads((ROOT/'deliverables/verification-evidence/adapted-classifier-return-v1/review.json').read_text())
        require(protocol['classifier']['checkpoint_sha256']==guide['checkpoint_sha256'],'frozen classifier differs')
        require(protocol['classifier']['protocol']['cohort_sha256']==protocol['cohort_sha256'],'classifier cohort differs')
        require(editguard['repository']=='https://github.com/xuanyuzhang21/EditGuard' and editguard['commit']=='174778fb371640bb31b32fcb9f7bfd440c88766b','EditGuard provenance differs')
        require(editguard['checkpoint_md5']=='fd8c6987d67071d3e629133499b44765','EditGuard checkpoint differs')
        rows=[json.loads(line) for line in z.read('rows.jsonl').splitlines()];require(len(rows)==10000,'localisation row count differs')
        setup=[json.loads(line) for line in z.read('setup.jsonl').splitlines()];require(len(setup)==500,'setup count differs')
        byid={r['image_id']:r for r in selected};setupidx={r['image_id']:r for r in setup};require(set(setupidx)==set(byid),'setup image ids differ')
        for i,r in enumerate(selected):
            s=setupidx[r['image_id']];require(s['signed4_bytes']==524378 and s['embedding_seed']==7301+i,'setup cost/seed differs')
            require(np.isfinite(s['embedding_mse']) and s['embedding_mse']>=0 and bool(re.fullmatch('[0-9a-f]{64}',s['protected_rgb_sha256'])),'invalid embedding setup')
            require((s['embedding_mse']==0 and s['embedding_psnr_db'] is None) or (s['embedding_mse']>0 and np.isfinite(s['embedding_psnr_db'])),'MSE/PSNR mismatch')
        idx={}
        for r in rows:
            key=(r['image_id'],r['case'],r['method']);require(r['image_id'] in byid and r['case'] in CASES and r['method'] in METHODS and key not in idx,'unknown/duplicate localisation row')
            require(r['lesion_id']==byid[r['image_id']]['lesion_id'] and r['seed']==2301+next(i for i,q in enumerate(selected) if q['image_id']==r['image_id']),'image identity/seed differs')
            require(r['additional_sidecar_bytes']==(524378 if r['method']==METHODS[1] else 0),'byte cost differs')
            require(re.fullmatch('[0-9a-f]{64}',r['received_rgb_sha256']) and np.isfinite(r['seconds']) and r['seconds']>=0,'invalid receipt hash/timing')
            c=r['confusion'];require(sum(c.values())==512*512 and all(type(v) is int and v>=0 for v in c.values()),'invalid pixel confusion')
            require(c['fn']==r['missed_pixels'] and c['fp']==r['extra_highlights'] and (c['fn']+c['tp'])==r['changed_pixels'],'confusion/count mismatch')
            idx[key]=r
        require(len(idx)==10000 and set(idx)=={(i['image_id'],c,m) for i in selected for c in CASES for m in METHODS},'incomplete matrix')
        public=Ed25519PublicKey.from_public_bytes(key_bytes) if key_bytes is not None else None
        map_count=0;packet_hashes={};signature_count=0
        for image_index,r in enumerate(selected):
            ident=r['image_id'];s=setupidx[ident];packet=z.read(f'artifacts/{image_index:03d}-signed4.bin')
            require(len(packet)==524378 and G.HEADER.unpack(packet[:G.HEADER.size])==(G.MAGIC,1,image_index,512,512,4),'signed4 packet header/length differs')
            if public is not None:
                public.verify(packet[-64:],G.DOMAIN+packet[:-64]);signature_count+=1
            packet_hashes[f'{image_index:03d}-signed4.bin']=hashlib.sha256(packet).hexdigest()
            with np.load(io.BytesIO(z.read(f'artifacts/{image_index:03d}-maps.npz')),allow_pickle=False) as maps:
                require(set(maps.files)=={case+'-'+suffix for case in CASES for suffix in ('truth','editguard','signed4')},'map member matrix differs')
                for case in CASES:
                    truth=packed_map(maps[case+'-truth'].tobytes())
                    for method,suffix in zip(METHODS,('editguard','signed4')):
                        pred=packed_map(maps[case+'-'+suffix].tobytes());row=idx[ident,case,method]
                        c=confusion(truth,pred);require(c==row['confusion'],'row/map confusion differs')
                        union=c['tp']+c['fp']+c['fn'];iou=c['tp']/union if union else None
                        close(row['pixel_iou'],iou,'pixel_iou');map_count+=1
        diagnostic=[json.loads(line) for line in z.read('diagnostic-predictions.jsonl').splitlines()];require(len(diagnostic)==5000,'diagnostic record count differs')
        didx={}
        for r in diagnostic:
            key=(r['image_id'],r['case']);require(r['image_id'] in byid and r['case'] in CASES and key not in didx,'unknown/duplicate diagnostic row')
            require(r['label']==byid[r['image_id']]['melanoma_label'] and r['seed']==2301+next(i for i,q in enumerate(selected) if q['image_id']==r['image_id']),'diagnostic labels/seed differ')
            require(r['source_rgb_sha256']==byid[r['image_id']]['prepared_rgb_sha256'],'diagnostic source hash differs')
            for k in ('original_probabilities','marked_probabilities','original_received_probabilities','marked_received_probabilities'):probability(r[k])
            require(r['parameters'] is not None and r['original_received_rgb_sha256'] and r['marked_received_rgb_sha256'],'operator receipts missing')
            if r['case']=='intact':
                require(r['original_received_rgb_sha256']==r['source_rgb_sha256'],'intact original hash differs')
                require(r['marked_received_rgb_sha256']==r['marked_rgb_sha256'],'intact marked hash differs')
                close(r['original_probabilities'],r['original_received_probabilities'],'intact original')
                close(r['marked_probabilities'],r['marked_received_probabilities'],'intact marked')
            didx[key]=r
        require(len(didx)==5000 and set(didx)=={(r['image_id'],c) for r in selected for c in CASES},'incomplete diagnostic matrix')
        diagnostic_summary=json.loads(z.read('diagnostic-summary.json'));recomputed={}
        for case in CASES:
            rr=[didx[r['image_id'],case] for r in selected];labels=np.array([q['label'] for q in rr]);recomputed[case]={}
            for name,left,right in [('operator_without_embedding','original_probabilities','original_received_probabilities'),
                ('embedding_given_operator','original_received_probabilities','marked_received_probabilities'),
                ('total_embedding_plus_operator','original_probabilities','marked_received_probabilities')]:
                recomputed[case][name]=analyse(labels,np.array([q[left] for q in rr]),np.array([q[right] for q in rr]),['nonMEL','MEL'],repetitions=2000)
        close(diagnostic_summary,recomputed,'diagnostic summary')
        require(summary=={'completed':True,'images':500,'rows':10000,'test_evaluated':False,'diagnostic_rows':5000},'completion summary differs')
        report={'schema':'matched-editguard-validation-review-v1','archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'notebook_sha256':notebook_hash,'notebook_bundle_sha256':bundle_sha,'images':500,'localisation_rows':10000,
            'diagnostic_rows':5000,'recovery_maps_checked':map_count,'signed_packet_signatures_checked':signature_count,
            'status':'audited_with_missing_public_key' if key_bytes is None else ('audited' if key_source=='archive' else 'audited_with_external_public_key'),
            'public_key_present':key_bytes is not None,'public_key_source':key_source,
            'limits':['Returned pixels absent: no independent EditGuard re-execution, operation replay, source/marked MSE verification, or classifier re-inference.',
                'Map confusion and metrics recomputed from returned packed masks/probabilities; receipts may still be self-generated.',
                'No signed-packet signatures verified because the return archive omits public-key.bin and no external key was supplied; packet hashes/header structure alone are not signature authentication.' if key_bytes is None else 'Packet signatures verify under the supplied public key; key-to-issuer identity is not independently authenticated.',
                'Validation was used for classifier selection: development evidence only.',
                'Signed4 adds full 524378-byte sidecar per image to EditGuard and is not equal-cost end-to-end comparison.',
                'One frozen adapted DenseNet is not a clinical model; no patient-level inference.']}
        if out.exists():raise ValueError('new output directory required')
        out.mkdir(parents=True)
        (out/'review.json').write_text(json.dumps(report,indent=2)+'\n')
        (out/'recomputed-diagnostic-summary.json').write_text(json.dumps(recomputed,indent=2)+'\n')
        (out/'packet-hashes.json').write_text(json.dumps(packet_hashes,indent=2)+'\n')
        return report

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('archive',type=Path);p.add_argument('--notebook',type=Path,default=ROOT/'deliverables/matched_editguard_validation_v1.ipynb');p.add_argument('--out',type=Path,required=True)
    p.add_argument('--public-key',type=Path,help='external raw 32-byte Ed25519 public key when not packaged in the ZIP')
    p.add_argument('--allow-missing-public-key',action='store_true',help='write a clearly partial audit without verifying signed-packet signatures')
    a=p.parse_args()
    print(json.dumps(review(a.archive,a.notebook,a.out,public_key_path=a.public_key,allow_missing_public_key=a.allow_missing_public_key),indent=2))
