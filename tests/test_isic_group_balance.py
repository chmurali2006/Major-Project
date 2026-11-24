import importlib.util
import json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('group_audit',ROOT/'scripts/audit_isic_group_balance.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_source_range_groups_are_explicit_proxies():
    assert 'HAM-family' in m.source_group('ISIC_0032853')
    assert 'BCN-family' in m.source_group('ISIC_0061070')
    assert 'MSK' in m.source_group('ISIC_0012653_downsampled')
    assert m.source_group('ISIC_0099999')=='other/unclassified'


def test_hash_audit_and_optional_phash(tmp_path):
    c={'selected':[]};p={'selected':[]}
    for i,split in enumerate(('train','validation','test')):
        ident=f'ISIC_003{i:04d}'; lesion=f'L{i}';c['selected'].append({'image_id':ident,'split':split,'lesion_id':lesion})
        rgb=np.full((40,40,3),i*80,dtype=np.uint8);im=Image.fromarray(rgb);f=tmp_path/(ident+'.png');im.save(f)
        import hashlib
        h=hashlib.sha256(rgb.tobytes()).hexdigest();p['selected'].append({'image_id':ident,'split':split,'lesion_id':lesion,'source_decoded_rgb_sha256':h,'prepared_rgb_sha256':h})
    cp=tmp_path/'c.json';pp=tmp_path/'p.json';cp.write_text(json.dumps(c));pp.write_text(json.dumps(p))
    r=m.audit(cp,pp,tmp_path,expected_count=3)
    assert r['exact_rgb']['source_decoded_cross_split_duplicate_groups']==0
    assert r['pHash']['status']=='completed' and r['pHash']['cross_split_pairs_within_hamming4']==2
