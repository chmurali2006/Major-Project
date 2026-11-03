"""Adversarial/regression checks for findings from the pre-run audit."""
from dataclasses import asdict
from pathlib import Path
import itertools
import sys
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_matrix as R
from run_isic_study import DiskSamples, build_paired_model
from compare_paired import compare
from src.authentic_training import pretrain_authentic
from src.persistence import atomic_json, seal_artifacts, artifacts_valid
from src.metrics import optimal_block_iou, block_ceiling, iou
from src import evidence


def sample(tampered=False):
    mask=np.zeros((64,64),bool)
    if tampered: mask[:8,:8]=True
    return R.Sample(np.ones((13,8,8),np.float16),np.zeros(4,np.float32),
        np.ones((3,64,64),np.uint8),mask.reshape(8,8,8,8).any(axis=(1,3)),
        mask,int(tampered),'T1' if tampered else 'none','NV')


def test_exact_block_oracle_matches_exhaustive_search():
    rng=np.random.default_rng(2)
    for _ in range(15):
        mask=rng.random((4,4))>.7
        brute=max(iou(np.repeat(np.repeat(np.array(bits).reshape(2,2),2,0),2,1),mask)
                  for bits in itertools.product((0,1),repeat=4))
        assert optimal_block_iou(mask,2)==pytest.approx(brute)
    # Any-overlap is demonstrably NOT an upper bound.
    mask=np.zeros((4,4),bool); mask[:2,:2]=True; mask[2,2]=True
    assert optimal_block_iou(mask,2)>block_ceiling(mask,2)


def test_shared_initialisation_is_exact():
    a,b=build_paired_model('C8',4,7),build_paired_model('C12',4,7)
    for module in ('ae','saliency','refine'):
        aa,bb=a[module].state_dict(),b[module].state_dict()
        for name in aa:
            torch.testing.assert_close(aa[name],bb[name],rtol=0,atol=0)
    assert a['refine'].cls_head[-1].out_features==2


def test_authentic_pretraining_frozen_including_batchnorm(tmp_path):
    torch.set_num_threads(2)
    model=build_paired_model('C8',4,3)
    info=pretrain_authentic(model,[sample(),sample(True)],1,tmp_path/'ae.pt',False,'auth',device='cpu',log=lambda x:None)
    assert info['n_authentic_train']==1
    assert not any(p.requires_grad for p in model['ae'].parameters())
    before={k:v.clone() for k,v in model['ae'].state_dict().items()}
    R.to_train(model)
    assert not model['ae'].training
    s=sample(True)
    t={'ev':torch.from_numpy(s.ev)[None].float(),'deg':torch.from_numpy(s.degrade)[None],
       'image':torch.from_numpy(s.image)[None].float()/255}
    out=R.forward_all(model,t)
    out['pixel_logits'].square().mean().backward()
    assert all(p.grad is None for p in model['ae'].parameters())
    for name,value in before.items():
        torch.testing.assert_close(value,model['ae'].state_dict()[name],rtol=0,atol=0)


def test_score_lengths_shapes_scalar_verdicts_and_diagnosis_iou():
    intact,tampered=sample(),sample(True)
    masks=[np.zeros((64,64)),np.zeros((64,64))]
    blocks=[np.zeros((8,8)),np.zeros((8,8))]
    r=R.score([intact,tampered],blocks,masks,[0,0])
    assert r['iou_tampered_mean']==0
    assert r['by_diagnosis'][0]['iou']==0
    assert r['by_diagnosis'][0]['n']==1
    assert r['balanced_accuracy']==.5
    with pytest.raises(ValueError,match='aligned'):
        R.score([intact,tampered],blocks[:1],masks,[0,0])
    with pytest.raises(ValueError,match='scalar'):
        R.score([intact],blocks[:1],masks[:1],[[1]])
    with pytest.raises(ValueError,match='shapes'):
        R.score([intact],[np.zeros((1,1))],masks[:1],[0])


def test_cache_nonfinite_and_corruption_seal(tmp_path):
    s=sample(); s.ev[0,0,0]=np.nan
    path=tmp_path/'sample.npz'
    np.savez(path,**asdict(s))
    with pytest.raises(ValueError,match='nonfinite'): DiskSamples([path])[0]
    atomic_json(tmp_path/'model.json',{'metric':.5})
    (tmp_path/'model_state.pt').write_bytes(b'weights')
    seal_artifacts(tmp_path,'model',['.json','_state.pt'])
    assert artifacts_valid(tmp_path,'model',['.json','_state.pt'])
    (tmp_path/'model_state.pt').write_bytes(b'truncated')
    assert not artifacts_valid(tmp_path,'model',['.json','_state.pt'])


def test_bootstrap_rejects_different_attack_truth(tmp_path):
    kw=dict(image_id=['a','b'],tampered=[1,0],prediction=[1,0],iou=[.5,1.],family=['T1','none'])
    a,b=tmp_path/'a.npz',tmp_path/'b.npz'
    np.savez(a,**kw,gt_sha256=['mask1','empty'])
    np.savez(b,**kw,gt_sha256=['different-mask','empty'])
    with pytest.raises(ValueError,match='masks differ'): compare(a,b,strict=True)


def test_single_carrier_profile_really_omits_second_carrier():
    image=np.random.default_rng(3).integers(20,230,(64,64,3),dtype=np.uint8)
    np.testing.assert_array_equal(evidence.protect(image,b'key',3,profile='single'),
                                  evidence.embed(image,b'key',3))


def test_authentic_checkpoint_resume_matches_uninterrupted(tmp_path):
    from src.persistence import load_checkpoint
    model=build_paired_model('C8',4,7)
    pretrain_authentic(model,[sample()],2,tmp_path/'full.pt',False,'auth',device='cpu',log=lambda x:None)
    partial=build_paired_model('C8',4,7)
    pretrain_authentic(partial,[sample()],1,tmp_path/'partial.pt',False,'auth',device='cpu',log=lambda x:None)
    partial=build_paired_model('C8',4,7)
    pretrain_authentic(partial,[sample()],2,tmp_path/'partial.pt',True,'auth',device='cpu',log=lambda x:None)
    a,b=load_checkpoint(tmp_path/'full.pt'),load_checkpoint(tmp_path/'partial.pt')
    for name in a['model']:
        torch.testing.assert_close(a['model'][name],b['model'][name],rtol=0,atol=0)


def test_nonfinite_logits_fail_before_boolean_thresholding(monkeypatch):
    model=build_paired_model('C8',4,0)
    def broken(*args):
        return {'pixel_logits':torch.full((1,1,64,64),float('nan')),
                'block_logits':torch.zeros(1,1,8,8),'cls':torch.zeros(1,2)}
    monkeypatch.setattr(R,'forward_all',broken)
    with pytest.raises(FloatingPointError,match='logits'):
        R.predict_maps(model,[sample()])
