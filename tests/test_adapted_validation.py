import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('validation',ROOT/'scripts/experiment_adapted_validation.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def fixture(tmp_path):
    p=tmp_path/'prep';(p/'prepared').mkdir(parents=True)
    x=np.random.default_rng(44).integers(0,256,(512,512,3),dtype=np.uint8)
    Image.fromarray(x).save(p/'prepared'/'fixture.png')
    e={'image_id':'fixture','lesion_id':'lesion','split':'validation'}
    c=tmp_path/'cohort.json';c.write_text(json.dumps({'selected':[e]}))
    receipt={'cohort_sha256':hashlib.sha256(c.read_bytes()).hexdigest(),'ready_for_training':True,
        'selected':[{**e,'prepared_rgb_sha256':hashlib.sha256(x.tobytes()).hexdigest()}]}
    (p/'preparation.json').write_text(json.dumps(receipt));return p,c

def test_actual_runner(tmp_path):
    p,c=fixture(tmp_path);out=tmp_path/'out';s=v.run(p,c,out)
    assert s['rows']==30 and s['invariant_violations']==0
    rows=[json.loads(r) for r in (out/'rows.jsonl').read_text().splitlines()]
    assert all(r['map_matches_tile_truth'] for r in rows if r['fine_map_available'])
    assert all(r['verdict']=='VERIFIED' for r in rows if r['case']=='intact')
    assert all(r['fine_map_available'] for r in rows if r['method'].startswith('full'))
    assert not any(r['fine_map_available'] for r in rows if r['method']=='bounded289' and r['case']=='jpeg70')
    with pytest.raises(FileExistsError):v.run(p,c,out)

def test_hash_mismatch_stops_before_output(tmp_path):
    p,c=fixture(tmp_path);Image.new('RGB',(512,512)).save(p/'prepared'/'fixture.png')
    with pytest.raises(ValueError,match='RGB mismatch'):v.run(p,c,tmp_path/'out')
    assert not (tmp_path/'out').exists()

def test_export_parts_size_and_no_pixels(tmp_path):
    spec=importlib.util.spec_from_file_location('package',ROOT/'scripts/package_validation_results.py')
    pkg=importlib.util.module_from_spec(spec);spec.loader.exec_module(pkg)
    import zipfile
    out=tmp_path/'out';(out/'artifacts').mkdir(parents=True)
    code=tmp_path/'code';code.mkdir();prep=tmp_path/'prep';prep.mkdir()
    (code/'cohort.json').write_text('{}');(prep/'preparation.json').write_text('{}')
    (code/'runner.py').write_text('pass')
    (out/'rows.jsonl').write_text('{}\n')
    for i in range(3):(out/'artifacts'/f'{i}.bin').write_bytes(bytes(600))
    (out/'secret.png').write_bytes(b'not for export')
    parts=pkg.package(out,code,prep,limit=1300)
    assert len(parts)>1 and all(p['bytes']<1300 for p in parts)
    names=[]
    for part in parts:
        with zipfile.ZipFile(tmp_path/part['name']) as z:
            assert z.testzip() is None;names.extend(z.namelist())
    assert len(names)==len(set(names)) and 'secret.png' not in names
    assert {'cohort.json','preparation.json','code/runner.py','rows.jsonl'}<=set(names)
    with pytest.raises(ValueError,match='Previous export'):pkg.package(out,code,prep,limit=1300)

def test_notebook_actual_cells_recover_run_export(tmp_path, monkeypatch):
    import shutil
    spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build_adapted_validation_notebook.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    bundle=tmp_path/'bundle'
    for name in builder.FILES:
        target=bundle/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    inp=tmp_path/'input';inp.mkdir()
    entries=[]
    for i,split in enumerate(('train','validation','test')):
        ident=f'fixture{i}'
        Image.fromarray(np.random.default_rng(i).integers(0,256,(64,64,3),dtype=np.uint8)).save(inp/(ident+'.png'))
        entries.append({'image_id':ident,'lesion_id':f'lesion{i}','split':split})
    manifest=bundle/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json'
    manifest.parent.mkdir(parents=True);manifest.write_text(json.dumps({'exact_paper_reproduction':False,'selected':entries}))
    monkeypatch.setattr(builder,'ROOT',bundle)
    notebook=builder.build();scope={}
    for c in notebook['cells']:
        if c['cell_type']=='code':
            text=''.join(c['source']).replace('/kaggle/working',str(tmp_path)).replace('/kaggle/input',str(inp))
            exec(compile(text,'<actual-notebook-cell>','exec'),scope)
    summary=json.loads((scope['OUT']/'summary.json').read_text())
    assert summary['rows']==30 and summary['invariant_violations']==0
    assert list(tmp_path.glob('*-results-part001.zip'))
    # Configuration cell refuses an accidental rerun instead of overwriting results.
    with pytest.raises(AssertionError,match='fresh OUT'):
        exec(''.join(notebook['cells'][1]['source']).replace('/kaggle/working',str(tmp_path)).replace('/kaggle/input',str(inp)),scope)
