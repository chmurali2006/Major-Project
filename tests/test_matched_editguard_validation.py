import importlib.util
import json
from pathlib import Path
import hashlib
import numpy as np
from PIL import Image
import pytest

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class StubReader:
    provenance={'kind':'synthetic intentionally failing test reader, NOT EditGuard'}
    def embed(self,x,seed):return np.clip(x.astype(np.int16)+1,0,255).astype(np.uint8)
    def localize(self,x,threshold):return np.zeros((512,512)),np.zeros((512,512),bool)


def test_identical_marked_inputs_exact_truth_and_failures_retained(tmp_path):
    fixture=load('train_fixture',ROOT/'tests/test_isic_classifier_training.py')
    runner=load('matched',ROOT/'scripts/experiment_matched_editguard_validation.py')
    p,c=fixture.prepared(tmp_path);receipt=json.loads((p/'preparation.json').read_text())
    for i,r in enumerate(receipt['selected']):
        if r['split']=='validation':
            x=np.random.default_rng(i).integers(0,256,(512,512,3),dtype=np.uint8)
            Image.fromarray(x).save(p/'prepared'/(r['image_id']+'.png'))
            r['prepared_rgb_sha256']=hashlib.sha256(x.tobytes()).hexdigest()
    (p/'preparation.json').write_text(json.dumps(receipt))
    sync_calls=[]
    result=runner.run(StubReader(),p,c,tmp_path/'out',synchronize=lambda:sync_calls.append(1))
    assert result['rows']==40 and result['images']==2 and not result['test_evaluated']
    rows=[json.loads(line) for line in (tmp_path/'out/rows.jsonl').read_text().splitlines()]
    for i in range(0,len(rows),2):
        a,b=rows[i:i+2]
        assert a['received_rgb_sha256']==b['received_rgb_sha256']
        assert a['changed_pixels']==b['changed_pixels']
        assert b['missed_pixels']==0
    assert all(row['changed_pixels']==0 for row in rows if row['case']=='intact')
    assert any(row['complete_target_miss'] for row in rows if row['method']=='EditGuard clean')
    setup=[json.loads(line) for line in (tmp_path/'out/setup.jsonl').read_text().splitlines()]
    assert all(row['embedding_mse']>0 and row['signed4_bytes']==524378 for row in setup)
    assert sync_calls


def test_four_condition_classifier_pairing_and_separate_timing_outputs(tmp_path):
    import torch
    class Guide(torch.nn.Module):
        def __init__(self):
            super().__init__();self.register_buffer('scale',torch.tensor(1.))
        def forward(self,x):
            v=x.mean((1,2,3))*self.scale
            return torch.stack((v,-v),1)
    fixture=load('train_fixture_diagnostic',ROOT/'tests/test_isic_classifier_training.py')
    runner=load('matched_diagnostic',ROOT/'scripts/experiment_matched_editguard_validation.py')
    p,c=fixture.prepared(tmp_path)
    # Final-test pixels are absent: validation execution must never open them.
    prep=json.loads((p/'preparation.json').read_text())
    for r in prep['selected']:
        if r['split']=='test':(p/'prepared'/(r['image_id']+'.png')).unlink(missing_ok=True)
    out=tmp_path/'out'
    result=runner.run(StubReader(),p,c,out,classifier=Guide().eval(),classifier_identity={'checkpoint_sha256':'synthetic-fixture'},repetitions=100)
    assert result['diagnostic_rows']==20 and result['rows']==40
    protocol=json.loads((out/'protocol.json').read_text());assert protocol['schema'].endswith('v2')
    rows=[json.loads(line) for line in (out/'diagnostic-predictions.jsonl').read_text().splitlines()]
    for row in rows:
        if row['case']=='intact':
            assert row['original_probabilities']==row['original_received_probabilities']
            assert row['marked_probabilities']==row['marked_received_probabilities']
            assert row['marked_received_rgb_sha256']==row['marked_rgb_sha256']
    summary=json.loads((out/'diagnostic-summary.json').read_text())
    assert set(summary['intact'])=={'operator_without_embedding','embedding_given_operator','total_embedding_plus_operator'}
    assert summary['intact']['operator_without_embedding']['prediction_flips']==0


def test_matched_gpu_notebook_bundles_analytic_contrast_and_never_uses_test():
    builder=load('matched_nb',ROOT/'scripts/build_matched_editguard_validation_notebook.py')
    nb=builder.build();assert len(nb['cells'])==7
    text='\n'.join(''.join(c['source']) for c in nb['cells'])
    assert 'embedding_given_operator' in text and 'checkpoint' in text
    assert 'checkpoint_dirs=[]' in text and "p.name.lower().startswith('clean')" in text
    assert 'TRAINING_ZIP is a directory' not in text  # Notebook detects and validates the directory directly.
    assert 'if Path(TRAINING_ZIP).is_dir()' in text
    assert 'validation only' in text.lower() and 'model training or threshold tuning' in text
    for i,c in enumerate(nb['cells']):
        if c['cell_type']=='code':compile(''.join(c['source']),f'cell{i}','exec')
