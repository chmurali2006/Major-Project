import numpy as np
import pytest
import torch
from src.adversarial_operators import AttackSettings,attack


class Toy(torch.nn.Module):
    def __init__(self):
        super().__init__();self.register_buffer('scale',torch.tensor(1.))
    def forward(self,x):
        value=x.mean((1,2,3))*self.scale
        return torch.stack((value,-value),1)


def settings(algorithm='fgsm',targeted=False):
    return AttackSettings(algorithm,(0.,0.,0.),(1.,1.,1.),targeted)


@pytest.mark.parametrize('algorithm,expected',[('fgsm',4),('pgd',3)])
def test_gradient_direction_projection_and_quantization(algorithm,expected):
    model=Toy().eval();x=np.full((2,4,4,3),128,np.uint8);original=x.copy()
    with torch.no_grad():r=attack(model,x,np.array([0,0]),settings(algorithm))
    assert np.array_equal(x,original) and (r['received']==128-expected).all()
    assert r['linf_rgb_per_image']==[expected,expected]
    assert r['pixel_truth'].all() and not model.training
    targeted=attack(model,x,np.array([1,1]),settings(algorithm,True))
    assert np.array_equal(targeted['received'],r['received'])
    opposite=attack(model,x,np.array([0,0]),settings(algorithm,True))
    assert (opposite['received']==128+expected).all()


def test_clipping_and_no_parameter_mutation():
    model=torch.nn.Sequential(torch.nn.Flatten(),torch.nn.Linear(12,2)).eval()
    for p in model.parameters():p.requires_grad_(False)
    before={k:v.clone() for k,v in model.state_dict().items()}
    x=np.array([0,255]*6,dtype=np.uint8).reshape(1,2,2,3)
    r=attack(model,x,np.array([0]),settings('pgd'))
    assert max(r['linf_rgb_per_image'])<=4
    assert np.array_equal(r['pixel_truth'],np.any(r['received']!=x,axis=-1))
    assert all(torch.equal(before[k],v) for k,v in model.state_dict().items())
    assert all(p.grad is None for p in model.parameters())


def test_requires_frozen_eval_valid_logits_and_labels():
    x=np.full((1,2,2,3),100,np.uint8)
    with pytest.raises(ValueError,match='eval'):attack(Toy(),x,np.array([0]),settings())
    model=torch.nn.Sequential(torch.nn.Flatten(),torch.nn.Linear(12,2)).eval()
    with pytest.raises(ValueError,match='freeze'):attack(model,x,np.array([0]),settings())
    with pytest.raises(ValueError,match='outside'):attack(Toy().eval(),x,np.array([2]),settings())
    with pytest.raises(ValueError,match='integer label'):attack(Toy().eval(),x,np.array([0.]),settings())
    with pytest.raises(ValueError,match='std'):attack(Toy().eval(),x,np.array([0]),AttackSettings('fgsm',(0,0,0),(1,0,1),False))

def test_connected_evaluation_uses_quantized_predictions():
    from src.adversarial_evaluation import evaluate
    model=Toy().eval();x=np.full((2,4,4,3),128,np.uint8)
    r=evaluate(model,x,np.array([0,1]),['a','b'],['zero','one'],settings('pgd'),repetitions=100)
    assert r['impact']['n']==2
    assert r['attack_success']['clean_correct_denominator']==1
    assert r['attack_success']['clean_correct_rate']==0
    assert len(r['rows'])==2 and all(row['linf_rgb']==3 for row in r['rows'])
    assert all(len(row['received_rgb_sha256'])==64 for row in r['rows'])
    with pytest.raises(ValueError,match='target labels required'):
        evaluate(model,x,np.array([0,1]),['a','b'],['zero','one'],settings(targeted=True),repetitions=100)
