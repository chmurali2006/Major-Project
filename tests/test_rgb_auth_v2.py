"""New RGB authentication invariants, independent MAC oracle and ablation wiring."""
import hashlib
import hmac
import struct
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from src import authentication as A, evidence as E, metrics as M, degradation
from src.ablations import ABLATIONS, mask_evidence
from src.classical import fit_count_rule
from run_isic_study import build_paired_model, learned_rule
import run_matrix as R


def test_independent_hmac_definition_and_lossless_intact():
    x=np.random.default_rng(20).integers(0,256,(16,24,3),dtype=np.uint8)
    y=A.embed(x,b'secret',29)
    assert A.verify(y,b'secret',29)
    assert np.max(abs(y.astype(int)-x.astype(int)))<=1
    for r in range(2):
        for c in range(3):
            tile=y[r*8:r*8+8,c*8:c*8+8]
            msg=(b'MajorProject/RGB-block-authentication/v1\0'+struct.pack('>QII',29,16,24)
                 +struct.pack('>II',r,c)+(tile&254).tobytes())
            expected=hmac.new(b'secret',msg,hashlib.sha256).digest()[:24]
            assert np.packbits((tile&1).ravel()).tobytes()==expected


def test_every_single_bit_in_block_is_checked():
    y=A.embed(np.full((8,8,3),127,np.uint8),b'key',1)
    for index in range(192):
        for bit in range(8):
            z=y.copy();z.ravel()[index]^=np.uint8(1<<bit)
            assert not A.verify(z,b'key',1),(index,bit)


@pytest.mark.parametrize('profile',['authenticated','authenticated-single'])
def test_brightness_colour_sparse_and_copy_edits_are_exactly_localised(profile):
    x=np.random.default_rng(4).integers(65,110,(128,128,3),dtype=np.uint8)
    y=E.protect(x,b'key',41,profile=profile)
    assert not E.read_full(y,b'key',41,profile=profile)['E'].any()
    yy,xx=np.mgrid[:128,:128];disk=(yy-65)**2+(xx-61)**2<17**2
    edits=[]
    z=y.copy();z[32:64,48:80]=(z[32:64,48:80].astype(int)+64).astype(np.uint8);edits.append(z)
    z=y.copy();z[disk]=(z[disk].astype(int)+[15,-9,7]).astype(np.uint8);edits.append(z)
    z=y.copy();z[12,20,2]^=1;edits.append(z)
    z=y.copy();z[16:24,16:24]=y[:8,:8];edits.append(z)
    for z in edits:
        truth=M.measured_mask(y,z)
        np.testing.assert_array_equal(A.failures(z,b'key',41),truth)
        np.testing.assert_array_equal(E.read_full(z,b'key',41,profile=profile)['E'],truth)
        assert not A.verify(z,b'key',41)


def test_key_identifier_geometry_address_and_replay_boundary():
    x=np.zeros((16,16,3),np.uint8);y=A.embed(x,b'key',2**48)
    assert A.verify(y,b'key',2**48)
    assert A.failures(y,b'wrong',2**48).all()
    assert A.failures(y,b'key',2**48+1).all()
    assert not A.verify(y[:8],b'key',2**48)
    z=y.copy();z[8:16,8:16]=y[:8,:8]
    assert A.failures(z,b'key',2**48)[1,1]
    # No false claim of replay prevention: the identical old valid image passes.
    assert A.verify(y.copy(),b'key',2**48)
    assert E.full_tensor(E.protect(x,b'key',2**48),b'key',2**48).shape==(13,2,2)


@pytest.mark.parametrize('bad',[np.zeros((7,8,3),np.uint8),np.zeros((8,8),np.uint8),np.zeros((8,8,3),float)])
def test_invalid_representation_fails_closed(bad):
    with pytest.raises(ValueError): A.verify(bad,b'key',1)


def test_sharpness_is_content_dependent_with_analytic_scale():
    flat=np.full((64,64,3),100,np.uint8)
    stripes=np.repeat(np.tile(((np.arange(64)//2)%2)*255,(64,1))[...,None],3,axis=2).astype(np.uint8)
    assert degradation.estimate(flat)[2]==0
    assert 0<degradation.estimate(stripes)[2]<=1
    assert degradation.estimate(stripes)[2]==pytest.approx(degradation.sharpness(stripes)/(1020*np.sqrt(2)))


def test_one_changed_pixel_gets_block_training_label():
    clean=np.full((512,512,3),100,np.uint8);marked=E.protect(clean,b'key',9)
    changed=marked.copy();changed[12,20,0]^=1
    with patch.object(R.T,'make_pair',return_value=(changed,None)):
        sample=R.build_sample(R.Item(9,'NV',marked,clean,b'key'),'T1',np.random.default_rng(1))
    assert sample.cls==1 and sample.gt_pixel.sum()==1 and sample.gt_block.sum()==1
    assert sample.gt_block[1,2]


@pytest.mark.parametrize('variant',ABLATIONS)
def test_each_ablation_has_real_removed_path_and_shared_initialisation(variant):
    torch.set_num_threads(2)
    base=build_paired_model('C8',4,7);model=build_paired_model(variant,4,7)
    for name in ('refine','ae','saliency'):
        for key,value in base[name].state_dict().items():
            assert torch.equal(value,model[name].state_dict()[key])
    t={'ev':torch.randn(1,13,8,8),'deg':torch.rand(1,4),'image':torch.rand(1,3,64,64)}
    out=R.forward_all(model,t)
    assert out['pixel_logits'].shape==(1,1,64,64)
    assert torch.isfinite(out['pixel_logits']).all()
    out['pixel_logits'].square().mean().backward()
    if variant in ('without-ae','rgb-only'):
        assert not model['use_ae'] and all(p.grad is None for p in model['ae'].parameters())
    if variant=='without-saliency':
        assert not model['use_saliency'] and all(p.grad is None for p in model['saliency'].parameters())
    if variant=='without-degradation': assert not model['use_degrade']
    if variant=='without-pixel':
        assert not model['use_pixel'] and all(p.grad is None for p in model['refine'].pixel_head.parameters())
    masked=mask_evidence(model,t['ev'])
    if variant=='without-fragile': assert not masked[:,:10].any()
    if variant=='without-semi': assert not masked[:,10:].any()
    if variant=='rgb-only': assert not masked.any()


def test_classical_and_learned_selection_use_identical_objective():
    samples=[];maps=[]
    for changed in (False,True,True):
        ev=np.zeros((13,2,2),np.float32);ev[10]=1
        if changed:ev[0,0,0]=1
        block=ev[0]>.5;pixels=np.repeat(np.repeat(block,8,0),8,1)
        samples.append(SimpleNamespace(ev=ev,gt_block=block,gt_pixel=pixels,cls=int(changed)))
        maps.append((ev[0],pixels.astype(float)))
    rule=fit_count_rule(samples)
    assert learned_rule(samples,maps)==(rule.tau,rule.k)
    assert rule.k==0


def test_lossless_png_survives_but_jpeg_is_not_authenticated():
    import cv2
    x=np.random.default_rng(15).integers(30,220,(64,64,3),dtype=np.uint8)
    marked=E.protect(x,b'key',15)
    ok,png=cv2.imencode('.png',cv2.cvtColor(marked,cv2.COLOR_RGB2BGR));assert ok
    restored=cv2.cvtColor(cv2.imdecode(png,cv2.IMREAD_COLOR),cv2.COLOR_BGR2RGB)
    assert np.array_equal(restored,marked) and A.verify(restored,b'key',15)
    ok,jpeg=cv2.imencode('.jpg',cv2.cvtColor(marked,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,75]);assert ok
    changed=cv2.cvtColor(cv2.imdecode(jpeg,cv2.IMREAD_COLOR),cv2.COLOR_BGR2RGB)
    assert not A.verify(changed,b'key',15)


def test_consistency_uses_presence_not_occupancy_for_sparse_truth():
    from src.models import consistency_loss
    pixels=torch.full((1,1,16,16),-20.)
    pixels[0,0,3,5]=20.
    blocks=torch.full((1,1,2,2),-20.);blocks[0,0,0,0]=20.
    assert consistency_loss(pixels,blocks).item()<1e-12
