import numpy as np
import pytest
import torch
from src.diagnostic_constrained_embedding import Settings,embed_fixed,decode,carrier_mask,embed_guided,energy_matched_random


class Guide(torch.nn.Module):
    def __init__(self,opposite=False):
        super().__init__();self.register_buffer('scale',torch.tensor(20.));self.opposite=opposite
    def forward(self,x):
        value=(x[:,0,0,0]-x[:,2,0,1]) if self.opposite else (x[:,0,0,0]+x[:,2,0,1]-256/255.)
        value=value*self.scale
        return torch.stack((value,-value),1)


@pytest.mark.parametrize('step',[1,4,8,16,64])
def test_blind_payload_recovery_including_boundaries(step):
    x=np.random.default_rng(1).integers(0,256,(32,32,3),dtype=np.uint8)
    x[:8]=0;x[8:16]=255;before=x.copy();payload=np.random.default_rng(2).integers(0,2,(4,4),dtype=np.uint8)
    y=embed_fixed(x,payload,8,step)
    assert np.array_equal(decode(y,8,step),payload)
    assert np.array_equal(x,before)
    assert np.array_equal(x[~carrier_mask(x)],y[~carrier_mask(x)])


def test_guidance_cannot_change_carrier_or_payload_and_transfer_not_guaranteed():
    x=np.full((8,8,3),128,np.uint8);payload=np.ones((1,1),np.uint8);guide=Guide().eval()
    before={k:v.clone() for k,v in guide.state_dict().items()}
    r=embed_guided(guide,x,payload,(0,0,0),(1,1,1),Settings(steps=8))
    mask=carrier_mask(x);assert np.array_equal(r['received'][mask],r['base'][mask])
    assert np.array_equal(decode(r['received']),payload)
    assert min(v['guide_kl'] for v in r['trace'])<r['trace'][0]['guide_kl']
    for k,v in guide.state_dict().items():assert torch.equal(v,before[k])
    def shift(model,y):
        tensor=lambda a:torch.tensor(a.transpose(2,0,1).copy()).float()[None]/255.
        with torch.no_grad():return float((model(tensor(y)).softmax(1)-model(tensor(x)).softmax(1)).abs().sum())
    # Explicit counterexample: better guiding-model preservation may worsen another model.
    unseen=Guide(opposite=True).eval()
    assert shift(unseen,r['received'])>shift(unseen,r['base'])


def test_energy_matched_control_exact_distortion_and_margin():
    x=np.random.default_rng(3).integers(0,256,(16,16,3),dtype=np.uint8);payload=np.ones((2,2),np.uint8)
    base=embed_fixed(x,payload);guided=base.copy();mask=carrier_mask(x)
    guided[~mask]=np.clip(x[~mask].astype(int)+3,0,255).astype(np.uint8)
    control=energy_matched_random(x,guided,base,seed=7)
    assert np.array_equal(decode(control),payload)
    assert np.array_equal(control[mask],base[mask])
    assert np.array_equal(np.abs(control.astype(int)-x),np.abs(guided.astype(int)-x))


def test_clean_watermark_is_not_content_authentication():
    x=np.full((8,8,3),128,np.uint8);payload=np.ones((1,1),np.uint8)
    y=embed_fixed(x,payload);y[5,5,1]^=1
    assert np.array_equal(decode(y),payload) # Non-carrier edits are invisible to this payload reader.


def test_invalid_settings_and_trainable_guide_rejected():
    x=np.full((8,8,3),128,np.uint8);payload=np.ones((1,1),np.uint8)
    with pytest.raises(ValueError,match='frozen'):embed_guided(Guide(),x,payload,(0,0,0),(1,1,1))
    with pytest.raises(ValueError):embed_fixed(x,np.array([[2]],np.uint8))
