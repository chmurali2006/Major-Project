import sys,json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_adapted_isic_cohort import prepare
from build_adapted_preparation_notebook import build


def test_preparation_fixed_ids_and_no_substitution(tmp_path):
    images=tmp_path/'images';images.mkdir();manifest=tmp_path/'m.json'
    rows=[{'image_id':str(i),'lesion_id':'l'+str(i),'split':s,'diagnosis':'NV'} for i,s in enumerate(('train','validation','test'))]
    manifest.write_text(json.dumps({'exact_paper_reproduction':False,'selected':rows}))
    for i in range(3):Image.fromarray(np.full((12,15,3),30+i,np.uint8)).save(images/f'{i}.png')
    r=prepare(manifest,images,tmp_path/'out')
    assert r['ready_for_training'] and r['split_counts']=={'train':1,'validation':1,'test':1}
    (images/'2.png').unlink()
    with pytest.raises(ValueError):prepare(manifest,images,tmp_path/'missing')
    assert not (tmp_path/'missing').exists()


def test_cross_split_pixel_duplicate_blocks_training(tmp_path):
    images=tmp_path/'images';images.mkdir();manifest=tmp_path/'m.json'
    rows=[{'image_id':str(i),'lesion_id':'l'+str(i),'split':s} for i,s in enumerate(('train','test'))]
    manifest.write_text(json.dumps({'exact_paper_reproduction':False,'selected':rows}))
    for i in range(2):Image.new('RGB',(16,16)).save(images/f'{i}.png')
    with pytest.raises(ValueError):prepare(manifest,images,tmp_path/'out')
    assert json.loads((tmp_path/'out/preparation.json').read_text())['ready_for_training'] is False


def test_notebook_cells_compile():
    for c in build()['cells']:
        if c['cell_type']=='code':compile(''.join(c['source']),'cell','exec')


def test_actual_notebook_cells_end_to_end(tmp_path):
    import zipfile
    images=tmp_path/'images';images.mkdir();work=tmp_path/'work';work.mkdir()
    rows=[{'image_id':str(i),'lesion_id':'l'+str(i),'split':s,'diagnosis':'NV'}
          for i,s in enumerate(('train','validation','test'))]
    for i in range(3):Image.fromarray(np.full((18,21,3),40+i,np.uint8)).save(images/f'{i}.png')
    manifest=json.dumps({'exact_paper_reproduction':False,'selected':rows,
                         'split_counts':{'train':1,'validation':1,'test':1}}).encode()
    nb=build(manifest_bytes=manifest)
    context={'WORK':work,'INPUT':images,'OUT':work/'fixture-preparation'}
    for c in nb['cells']:
        if c['cell_type']=='code':exec(compile(''.join(c['source']),'notebook-cell','exec'),context)
    package=context['PACKAGE']
    with zipfile.ZipFile(package) as z:
        assert set(z.namelist())=={'preparation.json','cohort.json'}
        receipt=json.loads(z.read('preparation.json'))
        assert receipt['ready_for_training'] is True and len(receipt['selected'])==3
    assert len(list((context['OUT']/'prepared').glob('*.png')))==3
    # Reruns must not overwrite completed preparation.
    with pytest.raises(ValueError):
        for c in nb['cells']:
            if c['cell_type']=='code':exec(compile(''.join(c['source']),'rerun','exec'),context)
