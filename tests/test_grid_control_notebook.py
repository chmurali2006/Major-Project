import ast
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_grid_control_notebook import build
from experiment_grid_tradeoff import run


def test_notebook_fixed_selection_and_ast():
    nb=build()
    for c in nb['cells']:
        if c['cell_type']=='code':ast.parse(''.join(c['source']))
    bootstrap=''.join(nb['cells'][1]['source'])
    node=next(n for n in ast.parse(bootstrap).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='PREPARATION')
    p=json.loads(ast.literal_eval(node.value.args[0]))
    assert len(p['selected'])==32 and p['per_class']==4
    assert p==json.loads((ROOT/'deliverables/verification-evidence/followup32-v1/preparation.json').read_text())


def test_actual_preparation_cell_and_real_loader(tmp_path):
    data=tmp_path/'input';data.mkdir()
    rgb=np.random.default_rng(5).integers(0,256,(64,64,3),dtype=np.uint8)
    path=data/'sample.png';Image.fromarray(rgb).save(path)
    prepared=Image.fromarray(rgb).resize((512,512),Image.Resampling.NEAREST)
    entry=dict(image_id='sample',source_file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
               source_dimensions=[64,64],source_decoded_rgb_sha256=hashlib.sha256(rgb.tobytes()).hexdigest(),
               prepared_rgb_sha256=hashlib.sha256(prepared.tobytes()).hexdigest())
    prep={'complete':True,'selected':[entry]};out=tmp_path/'out'
    text=''.join(build()['cells'][2]['source'])
    ns=dict(OUT=out,INPUT=data,PREPARATION=prep,hashlib=hashlib,np=np,Image=Image,json=json)
    exec(text,ns)
    result=run(preparation=out/'preparation.json')
    assert result['synthetic'] is False and len(result['rows'])==2
    assert all(r['source_id']=='sample' for r in result['rows'])
    assert all(c['confusion']['fn']==0 for r in result['rows'] for c in r['cases'] if c['family']=='edit')
    (out/'prepared/sample.png').write_bytes(b'changed')
    with pytest.raises(ValueError,match='hash mismatch'):run(preparation=out/'preparation.json')
    with pytest.raises(ValueError,match='new OUT'):exec(text,ns)
