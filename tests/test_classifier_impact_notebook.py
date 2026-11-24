import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile
import pytest
import torch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build_classifier_impact_notebook.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


def test_requires_actual_hash_and_pins_checkpoint():
    with pytest.raises(ValueError,match='actual reviewed'):b.build('')
    with pytest.raises(ValueError,match='actual reviewed'):b.build('replace-me')


def test_actual_setup_discovers_saved_output_and_exports_no_weights(tmp_path,monkeypatch):
    checkpoint=b'synthetic test checkpoint, not a trained classifier';digest=hashlib.sha256(checkpoint).hexdigest()
    nb=b.build(digest)
    for c in nb['cells']:
        if c['cell_type']=='code':compile(''.join(c['source']),'<cell>','exec')
    inp=tmp_path/'input';training=inp/'saved-output';training.mkdir(parents=True)
    (training/'best.pt').write_bytes(checkpoint)
    (training/'summary.json').write_text(json.dumps({'completed':True,'checkpoint_sha256':digest}))
    monkeypatch.setattr(torch.cuda,'is_available',lambda:True)
    monkeypatch.setattr(torch.cuda,'get_device_name',lambda i:'fixture GPU name, no CUDA computation')
    scope={}
    text=''.join(nb['cells'][1]['source']).replace('/kaggle/working',str(tmp_path)).replace('/kaggle/input',str(inp))
    exec(text,scope);assert scope['TRAINING']==training
    prep=scope['PREPARATION'];prep.mkdir();(prep/'preparation.json').write_text('{}')
    exec(''.join(nb['cells'][2]['source']),scope)
    for name in b.FILES:assert (scope['CODE']/name).read_bytes()==(ROOT/name).read_bytes()
    scope['OUT'].mkdir();(scope['OUT']/'protocol.json').write_text('{}')
    exec(''.join(nb['cells'][-1]['source']),scope)
    with zipfile.ZipFile(scope['PACKAGE']) as z:
        assert z.testzip() is None and 'best.pt' not in z.namelist()
        assert 'preparation.json' in z.namelist() and 'protocol.json' in z.namelist()
