"""Offline checks of returned signatures/maps/receipts; no invented re-decoding."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from src import bounded_syndrome as B,index_syndrome as I,sparse_refinement as S,binary_signed_grid as G

METHODS={'bounded289':(B,289,18620),'index288':(I,288,18558),'set330':(S,330,18606),'full4':(G,4,524378)}
CASES=('intact','one-bit','brightness32','replace64','copy64','jpeg75')


def review(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        expected={'coding-results.json','preparation.json','artifacts/public-key.bin'}
        for i in range(32):
            expected.add(f'artifacts/{i:03d}-maps.npz')
            for method in METHODS:expected.add(f'artifacts/{i:03d}-{method}.bin')
        assert len(z.namelist())==len(expected) and set(z.namelist())==expected
        r=json.loads(z.read('coding-results.json'));p=json.loads(z.read('preparation.json'))
        previous=json.loads((ROOT/'deliverables/verification-evidence/followup32-v1/preparation.json').read_text())
        assert len(p['selected'])==32 and len(r['rows'])==768 and len(r['setup'])==128 and r['synthetic'] is False
        assert r['preparation_file_sha256']==hashlib.sha256(z.read('preparation.json')).hexdigest()
        for a,b in zip(p['selected'],previous['selected']):
            assert {k:v for k,v in a.items() if k!='prepared_file_sha256'}=={k:v for k,v in b.items() if k!='prepared_file_sha256'}
        # Compare packaged src/scripts digest, not the changing entire checkout.
        notebook=json.loads((ROOT/'deliverables/coding32_development.ipynb').read_text())
        import ast
        text=''.join(notebook['cells'][1]['source']);tree=ast.parse(text)
        encoded=None
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='b64decode':encoded=ast.literal_eval(node.args[0])
        assert encoded is not None
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded))) as code:
            digest=hashlib.sha256()
            for name in sorted(code.namelist()):digest.update(name.encode());digest.update(code.read(name))
            assert digest.hexdigest()==r['source_sha256']
        pub=Ed25519PublicKey.from_public_bytes(z.read('artifacts/public-key.bin'))
        indexed={(row['source_index'],row['case'],row['method']):row for row in r['rows']}
        assert len(indexed)==768
        signatures=0;checked_maps=0
        for i,entry in enumerate(p['selected']):
            commitments=[]
            for method,(module,parameter,size) in METHODS.items():
                packet=z.read(f'artifacts/{i:03d}-{method}.bin');assert len(packet)==size
                pub.verify(packet[-64:],module.DOMAIN+packet[:-64]);signatures+=1
                header=module.HEADER.unpack(packet[:module.HEADER.size])
                if module is G:assert header==(G.MAGIC,1,i,512,512,4)
                else:
                    assert header==(module.MAGIC,i,512,512,4,parameter)
                    commitments.append(packet[module.HEADER.size:module.HEADER.size+32])
            assert len(set(commitments))==1
            with np.load(io.BytesIO(z.read(f'artifacts/{i:03d}-maps.npz')),allow_pickle=False) as maps:
                expected_keys={case+'-truth' for case in CASES}
                for case in CASES:
                    truth=maps[case+'-truth'];assert truth.dtype==np.bool_ and truth.shape==(128,128)
                    for method,(_,_,size) in METHODS.items():
                        row=indexed[i,case,method]
                        assert row['source_id']==entry['image_id'] and row['source_rgb_sha256']==entry['prepared_rgb_sha256']
                        assert row['source_operator_seed']==100+i and row['sidecar_bytes']==size and row['embedding_mse']==0
                        assert row['changed_tiles']==int(truth.sum()) and row['verdict']==('FAILED_INTEGRITY' if truth.any() else 'VERIFIED')
                        assert 0<=row['verification_seconds']<1000
                        if row['fine_map_available']:
                            key=case+'-'+method;expected_keys.add(key)
                            assert np.array_equal(maps[key],truth) and row['map_matches_truth'] is True
                            assert row['missed_pixels']==0
                            assert row['extra_pixels']==16*int(truth.sum())-row['changed_pixels']
                            expected_iou=row['changed_pixels']/(16*int(truth.sum())) if truth.any() else None
                            assert row['pixel_iou']==expected_iou
                            checked_maps+=1
                        else:
                            assert all(row[k] is None for k in ('map_matches_truth','missed_pixels','extra_pixels','pixel_iou'))
                        if method=='bounded289' and truth.sum()<=289:assert row['fine_map_available']
                assert set(maps.files)==expected_keys
        summary=[]
        for method in METHODS:
            for case in CASES:
                rows=[indexed[i,case,method] for i in range(32)]
                summary.append({'method':method,'case':case,'trials':32,'fine_maps':sum(row['fine_map_available'] for row in rows),
                    'sidecar_bytes':METHODS[method][2],
                    'mean_verify_seconds':float(np.mean([row['verification_seconds'] for row in rows])),
                    'median_verify_seconds':float(np.median([row['verification_seconds'] for row in rows])),
                    'mean_available_iou':float(np.mean([row['pixel_iou'] for row in rows if row['pixel_iou'] is not None])) if any(row['pixel_iou'] is not None for row in rows) else None})
        return r,p,{'schema':'coding32-return-review-v1','zip_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            'zip_bytes':Path(path).stat().st_size,'signatures_checked':signatures,'available_maps_checked':checked_maps,
            'summary':summary,'limits':['Signatures checked against returned run key, not external issuer provenance.',
            'Saved maps compared with saved truth; source pixels absent, cannot independently reconstruct truth or rerun decoding.',
            'Exact32 development selection and packaged source digest checked; no heldout/patient-independence claim.',
            'Same-run timing one measurement per case; not guaranteed latency or SOTA ranking.']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('zip',type=Path);a=parser.parse_args()
    r,p,report=review(a.zip)
    out=ROOT/'deliverables/verification-evidence/coding32-development-v1';out.mkdir(exist_ok=False)
    for name,value in (('coding-results.json',r),('preparation.json',p),('review.json',report)):
        (out/name).write_text(json.dumps(value,indent=2)+'\n')
    for row in report['summary']:print(row)
    print('signature/map checks',report['signatures_checked'],report['available_maps_checked'])
