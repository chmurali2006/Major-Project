from pathlib import Path
import sys
import numpy as np
import pytest
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_matrix as R
from src.persistence import atomic_json, atomic_write, load_checkpoint
from src.protocol import MATRIX


def test_atomic_failure_keeps_previous_file(tmp_path):
    p=tmp_path/'receipt.json'
    atomic_json(p,{'valid':True})
    def fail(f):
        f.write(b'partial')
        raise RuntimeError('interruption')
    with pytest.raises(RuntimeError): atomic_write(p,fail)
    assert p.read_text().find('true') >= 0
    assert not list(tmp_path.glob('*.tmp'))


def test_epoch_resume_matches_uninterrupted_training(tmp_path,monkeypatch):
    torch.set_num_threads(2)
    monkeypatch.setattr(R,'tune_learned_tau',lambda m,v:(.5,{'iou_tampered_mean':.1,'iou_mean':.1,'block_acc':.5}))
    cfg=next(c for c in MATRIX if c.cid=='C8')
    def build():
        torch.manual_seed(12)
        return R.build_model(cfg,13,4)
    s=R.Sample(np.ones((13,8,8),np.float16),np.zeros(4,np.float32),
               np.ones((3,64,64),np.uint8),np.zeros((8,8),bool),
               np.zeros((64,64),bool),0,'none','NV')
    kw=dict(train_s=[s],val_s=[s],batch=1,lr=.001,smoke=True,run_id='test',log=lambda x:None)
    R.train(build(),epochs=2,checkpoint_path=tmp_path/'full.pt',**kw)
    R.train(build(),epochs=1,checkpoint_path=tmp_path/'partial.pt',**kw)
    R.train(build(),epochs=2,checkpoint_path=tmp_path/'partial.pt',resume=True,**kw)
    a,b=load_checkpoint(tmp_path/'full.pt'),load_checkpoint(tmp_path/'partial.pt')
    assert b['epoch']==2
    for module in a['model']:
        for name in a['model'][module]:
            torch.testing.assert_close(a['model'][module][name],b['model'][module][name],rtol=0,atol=0)
    with pytest.raises(ValueError,match='mismatch'):
        R.train(build(),epochs=2,checkpoint_path=tmp_path/'partial.pt',resume=True,
                **{**kw,'run_id':'changed'})
