import pytest
import torch
from src.objective_diagnostics import gradient_comparison


def test_conflicting_gradients_and_untouched_parameters():
    p=torch.nn.Parameter(torch.tensor([2.,1.]));q=torch.nn.Parameter(torch.tensor([1.]))
    p.grad=torch.tensor([8.,9.]);original=p.detach().clone();oldgrad=p.grad.clone()
    result=gradient_comparison({'up':p.square().sum(),'down':-p.square().sum(),'unused':q.square().sum()},[p])
    pairs={(r['left'],r['right']):r for r in result['pairs']}
    assert pairs['up','down']['cosine']==pytest.approx(-1)
    assert pairs['up','unused']['cosine'] is None
    assert result['gradient_l2_norms']['unused']==0
    assert torch.equal(p,original) and torch.equal(p.grad,oldgrad) and q.grad is None


def test_invalid_loss_rejected():
    p=torch.nn.Parameter(torch.tensor([1.]))
    with pytest.raises(ValueError,match='scalar'):gradient_comparison({'bad':p.square()},[p])
