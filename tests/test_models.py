"""Shape and gradient tests for the v2 pixel-resolution architecture."""
import numpy as np
import pytest
import torch

from src.models import (N_RICH, PixelRefineNet, SaliencyNet, consistency_loss,
                        pixel_mask_loss)


def test_saliency_output_shape_and_range():
    m = SaliencyNet()
    out = m(torch.rand(2, 3, 512, 512))
    assert out.shape == (2, 1, 512, 512)
    assert float(out.min()) >= 0.0 and float(out.max()) <= 1.0


def test_saliency_is_not_constant():
    """v1 passed torch.zeros for this channel, which silently made row 1 of the
    synthesis table decorative."""
    m = SaliencyNet()
    out = m(torch.rand(2, 3, 512, 512))
    assert float(out.std()) > 1e-4


@pytest.mark.parametrize("width,resolution", [(12, 256), (16, 512)])
def test_pixel_refine_shapes(width, resolution):
    m = PixelRefineNet(width=width)
    g = resolution // 8
    out = m(torch.randn(2, N_RICH, g, g), torch.rand(2, 4),
            torch.rand(2, 1, resolution, resolution), torch.rand(2, 3, resolution, resolution))
    assert out["pixel_logits"].shape == (2, 1, resolution, resolution)
    assert out["block_logits"].shape == (2, 1, g, g)
    assert out["cls"].shape == (2, 3)


def test_gradients_reach_every_parameter():
    """The pixel-only loss left the block head and the classifier with no
    gradient at all -- trained-looking but random. total_loss must reach
    everything."""
    from src.models import total_loss
    m = PixelRefineNet(width=12)
    out = m(torch.randn(1, N_RICH, 64, 64), torch.rand(1, 4),
            torch.rand(1, 1, 512, 512), torch.rand(1, 3, 512, 512))
    loss, parts = total_loss(out, torch.zeros(1, 1, 64, 64),
                             torch.zeros(1, 1, 512, 512), torch.tensor([0]))
    assert all(v > 0 for v in parts.values()), parts
    loss.backward()
    missing = [n for n, p in m.named_parameters() if p.grad is None]
    assert not missing, f"no gradient: {missing}"


def test_consistency_loss_is_zero_when_heads_agree():
    """Both arguments are LOGITS. Agreeing heads means the block logit equals
    the pooled pixel logit, so pick both far negative (a confident zero)."""
    p = torch.full((2, 1, 64, 64), -20.0)
    b = torch.full((2, 1, 8, 8), -20.0)
    assert float(consistency_loss(p, b)) < 1e-6


def test_consistency_loss_is_positive_when_heads_disagree():
    p = torch.full((2, 1, 64, 64), 20.0)
    b = torch.full((2, 1, 8, 8), -20.0)
    assert float(consistency_loss(p, b)) > 0.5


def test_pixel_mask_loss_perfect_prediction_is_low():
    tgt = torch.zeros(1, 1, 64, 64)
    good = pixel_mask_loss(torch.full((1, 1, 64, 64), -12.0), tgt)
    bad = pixel_mask_loss(torch.full((1, 1, 64, 64), 12.0), tgt)
    assert float(good) < float(bad)


def test_stage_attention_shapes_gradients_and_legacy_checkpoint():
    from src.models import StageAttention
    torch.manual_seed(7)
    gate = StageAttention(8)
    x = torch.rand(2, 8, 16, 16, requires_grad=True)
    out = gate(x)
    assert out.shape == x.shape and torch.isfinite(out).all()
    out.sum().backward()
    assert all(p.grad is not None for p in gate.parameters())
    base = PixelRefineNet(width=4)
    clone = PixelRefineNet(width=4, stage_attention=False)
    clone.load_state_dict(base.state_dict(), strict=True)
    assert not any('stage_gates' in k for k in base.state_dict())
    net = PixelRefineNet(width=4, stage_attention=True)
    result = net(torch.rand(2, N_RICH, 8, 8), torch.rand(2, 4),
                 torch.rand(2, 1, 64, 64), torch.rand(2, 3, 64, 64))
    sum(v.square().mean() for v in result.values()).backward()
    assert result['pixel_logits'].shape == (2, 1, 64, 64)
    assert all(p.grad is not None for p in net.parameters())
