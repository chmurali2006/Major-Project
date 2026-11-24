import numpy as np
import pytest
import torch
from src.diagnostic_constrained_embedding import Settings,embed_guided,carrier_mask,decode
from src.diagnostic_correction_controls import query_matched_random,distortion_noninferiority


class CountingGuide(torch.nn.Module):
    def __init__(self):
        super().__init__();self.register_buffer('scale',torch.tensor(20.));self.calls=0
    def forward(self,x):
        self.calls+=1
        z=(x[:,0,0,0]+x[:,2,0,1]-256/255.)*self.scale
        return torch.stack((z,-z),1)


@pytest.mark.parametrize('steps',[0,1,8])
def test_equal_observed_forward_budget_and_payload(steps):
    x=np.full((8,8,3),128,np.uint8);bits=np.ones((1,1),np.uint8);s=Settings(steps=steps)
    guide=CountingGuide().eval();guided=embed_guided(guide,x,bits,(0,0,0),(1,1,1),s);observed=guide.calls
    guide.calls=0;r=query_matched_random(guide,x,bits,(0,0,0),(1,1,1),s,seed=11)
    assert guide.calls==observed==r['forward_queries']==2*steps+3
    mask=carrier_mask(x)
    assert np.array_equal(r['received'][mask],guided['base'][mask])
    assert np.array_equal(decode(r['received']),bits)
    assert np.abs(r['received'].astype(int)-x)[~mask].max()<=s.correction_linf_rgb
    assert r['guide_kl']<=r['trace'][0]['guide_kl']
    repeat=query_matched_random(guide,x,bits,(0,0,0),(1,1,1),s,seed=11)
    assert np.array_equal(r['received'],repeat['received'])


def test_equal_distortion_gate_exposes_no_headroom():
    x=np.full((8,8,3),128,np.uint8);bits=np.ones((1,1),np.uint8)
    r=embed_guided(CountingGuide().eval(),x,bits,(0,0,0),(1,1,1),Settings(steps=8))
    gate=distortion_noninferiority(x,r['base'],r['received'])
    assert not gate['accepted']
    assert gate['candidate_squared_error']>gate['base_squared_error']
    assert np.array_equal(gate['received'],r['base'])
    assert distortion_noninferiority(x,r['base'],r['base'])['accepted']
    corrupt=r['received'].copy();corrupt[0,0,0]^=1
    with pytest.raises(ValueError,match='carriers'):distortion_noninferiority(x,r['base'],corrupt)


def test_frozen_requirement():
    x=np.full((8,8,3),128,np.uint8)
    with pytest.raises(ValueError,match='frozen'):query_matched_random(CountingGuide(),x,np.ones((1,1),np.uint8),(0,0,0),(1,1,1))
