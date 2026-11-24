import csv
import json
import numpy as np
from PIL import Image
import pytest
from src.dataset_audit import CLASSES
from src.local_isic_pilot import prepare,groups_from_metadata


@pytest.fixture
def dataset(tmp_path):
    data=tmp_path/'images';data.mkdir()
    labels=tmp_path/'labels.csv';meta=tmp_path/'metadata.csv'
    rng=np.random.default_rng(4)
    with labels.open('w',newline='') as f,meta.open('w',newline='') as m:
        w=csv.writer(f);w.writerow(['image',*CLASSES]);g=csv.writer(m);g.writerow(['image','patient_id','lesion_id'])
        for k in range(8):
            for j in range(2):
                ident=f'class{k}_{j}'
                Image.fromarray(rng.integers(0,256,(33+k,40+j,3),dtype=np.uint8)).save(data/(ident+'.png'))
                w.writerow([ident,*[int(i==k) for i in range(8)]])
                g.writerow([ident,f'patient{k}_{j}',f'lesion{k}_{j}'])
    return data,labels,meta


def test_native_properties_and_group_manifest_preserved(dataset,tmp_path):
    data,labels,meta=dataset
    r=prepare(data,labels,tmp_path/'pilot',metadata=meta,group_field='patient_id')
    assert r['complete'] and len(r['selected'])==8
    assert not r['official_identity_verified']
    assert len({e['group'] for e in r['selected']})==8
    for e in r['selected']:
        assert e['source_dimensions'][1]!=512
        with Image.open(tmp_path/'pilot/prepared'/(e['image_id']+'.png')) as im:assert im.size==(512,512)
    assert 'patient_id supplied' in r['grouping']
    manifest=list(csv.DictReader((tmp_path/'pilot/manifest.csv').open()))
    assert [x['image_id'] for x in manifest]==[x['image_id'] for x in r['selected']]


def test_no_invented_patient_groups(dataset,tmp_path):
    data,labels,_=dataset
    with pytest.raises(ValueError,match='explicitly allow'):prepare(data,labels,tmp_path/'denied')
    assert not (tmp_path/'denied').exists()
    r=prepare(data,labels,tmp_path/'explicit',allow_image_level=True)
    assert 'dependence unknown' in r['grouping']


def test_exclusion_propagates_to_declared_group(dataset,tmp_path):
    data,labels,meta=dataset
    lines=list(csv.DictReader(meta.open()))
    lines[2]['patient_id']=lines[0]['patient_id']
    with meta.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['image','patient_id','lesion_id']);w.writeheader();w.writerows(lines)
    r=prepare(data,labels,tmp_path/'pilot',metadata=meta,group_field='patient_id',exclude_ids=['class0_0'])
    ids={x['image_id'] for x in r['selected']}
    assert 'class0_0' not in ids and 'class1_0' not in ids
    assert r['excluded_group_count']==1


def test_missing_groups_fail_closed(dataset,tmp_path):
    _,labels,meta=dataset
    meta.write_text('image,patient_id\nclass0_0,one\n')
    with pytest.raises(ValueError,match='complete supplied'):groups_from_metadata(meta,['class0_0','class1_0'],'patient_id')


def test_output_cannot_nest_in_source(dataset):
    data,labels,_=dataset
    with pytest.raises(ValueError,match='inside input'):prepare(data,labels,data/'output',allow_image_level=True)


def test_prepare_only_cli_end_to_end_manifest_order(dataset,tmp_path):
    import subprocess,sys
    from pathlib import Path
    data,labels,meta=dataset;root=Path(__file__).resolve().parents[1]
    out=tmp_path/'cli-pilot'
    proc=subprocess.run([sys.executable,str(root/'scripts/run_local_isic_pilot.py'),
       '--data',str(data),'--labels',str(labels),'--metadata',str(meta),
       '--group-field','patient_id','--out',str(out),'--prepare-only'],capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    report=json.loads((out/'preparation.json').read_text())
    assert report['complete'] and len(report['selected'])==8
    assert not (out/'results').exists()


def test_notebook_source_archive_is_bound_and_python_cells_compile():
    import ast,base64,hashlib,io,zipfile
    from scripts.build_editguard_pilot_notebook import build,FILES,ROOT
    nb=build()
    for cell in nb['cells']:
        if cell['cell_type']=='code':ast.parse(''.join(cell['source']))
    bootstrap=''.join(nb['cells'][1]['source'])
    # Inspect the inert source archive without running installs, downloads or inference.
    tree=ast.parse(bootstrap)
    literal=next(n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_B64' for t in n.targets))
    raw=base64.b64decode(literal)
    assert hashlib.sha256(raw).hexdigest()==nb['metadata']['source_archive_sha256']
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert set(z.namelist())==set(FILES)
        for name in FILES:
            assert z.read(name)==(ROOT/name).read_bytes()
            assert not name.endswith(('.pth','.jpg','.png'))
    assert 'ALLOW_IMAGE_LEVEL_PILOT=False' in ''.join(nb['cells'][2]['source'])
