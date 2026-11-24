"""Explicitly adapted pixel-space attacks, NOT verified PFF-WM reproduction.

Paper reports epsilon4 and PGD3/step1, but author checkpoint, label objective,
normalisation and random-start details are not established. Here epsilon/step
are explicitly 8-bit RGB units; objective and preprocessing must be supplied.
No classifier is selected or trained here. Output is rounded RGB uint8: evaluate
attack success on that output, not merely the intermediate float image.
"""
from dataclasses import dataclass
import numpy as np
import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class AttackSettings:
    algorithm: str
    mean: tuple
    std: tuple
    targeted: bool
    epsilon_rgb: int = 4
    step_rgb: int = 1
    steps: int = 3


def attack(model, rgb, labels, settings):
    """labels are ground truth for untargeted CE, desired class for targeted CE.

    Model must already be eval/frozen, return finite NxC logits (C>=2), and
    reside on one device. RGB batch has shape NxHxWx3. No resizing/augmentation.
    PGD starts from the clean image (no random start). Does not alter weights,
    parameter gradients, model mode or the caller's source/labels.
    """
    s=settings;x=np.asarray(rgb)
    if x.dtype!=np.uint8 or x.ndim!=4 or x.shape[-1]!=3 or min(x.shape[:3])<1:
        raise ValueError('nonempty NxHxWx3 uint8 RGB required')
    if s.algorithm not in ('fgsm','pgd') or type(s.targeted) is not bool:
        raise ValueError('explicit algorithm and targeted boolean required')
    if any(type(v) is not int or v<1 for v in (s.epsilon_rgb,s.step_rgb,s.steps)) or s.epsilon_rgb>255:
        raise ValueError('positive integer RGB bounds/steps required')
    if len(s.mean)!=3 or len(s.std)!=3 or not np.isfinite(s.mean).all() or not np.isfinite(s.std).all() or min(s.std)<=0:
        raise ValueError('explicit finite RGB mean and positive std required')
    if any(module.training for module in model.modules()):raise ValueError('classifier must be in eval mode')
    if any(p.requires_grad for p in model.parameters()):raise ValueError('freeze classifier parameters before attacking')
    devices={t.device for t in list(model.parameters())+list(model.buffers())}
    if len(devices)!=1:raise ValueError('classifier must have parameters/buffers on one device')
    device=next(iter(devices))
    source=torch.tensor(x.transpose(0,3,1,2).copy(),dtype=torch.float32,device=device)/255.
    raw_labels=np.asarray(labels)
    if raw_labels.shape!=(len(x),) or raw_labels.dtype.kind not in 'iu':raise ValueError('integer label per image required')
    y=torch.tensor(raw_labels.copy(),dtype=torch.long,device=device)
    mean=torch.tensor(s.mean,dtype=torch.float32,device=device)[None,:,None,None]
    std=torch.tensor(s.std,dtype=torch.float32,device=device)[None,:,None,None]
    lo=(source-s.epsilon_rgb/255.).clamp(0,1);hi=(source+s.epsilon_rgb/255.).clamp(0,1)
    current=source.clone();losses=[]
    # Deliberately re-enable gradients if caller used no_grad for predictions.
    with torch.enable_grad():
        for _ in range(1 if s.algorithm=='fgsm' else s.steps):
            current=current.detach().requires_grad_(True)
            logits=model((current-mean)/std)
            if logits.ndim!=2 or logits.shape[0]!=len(x) or logits.shape[1]<2 or not torch.isfinite(logits).all():
                raise ValueError('finite NxC logits with C>=2 required')
            if (y<0).any() or (y>=logits.shape[1]).any():raise ValueError('class label outside logits')
            loss=F.cross_entropy(logits,y)
            if not loss.requires_grad:raise ValueError('classifier does not expose input gradients')
            grad=torch.autograd.grad(loss,current,only_inputs=True)[0]
            if not torch.isfinite(grad).all():raise ValueError('nonfinite input gradient')
            step=s.epsilon_rgb if s.algorithm=='fgsm' else s.step_rgb
            direction=-1 if s.targeted else 1
            current=torch.maximum(lo,torch.minimum(hi,current+direction*step/255.*grad.sign()))
            losses.append(float(loss.detach()))
    received=np.rint(current.detach().cpu().numpy().transpose(0,2,3,1)*255).clip(0,255).astype(np.uint8)
    delta=np.abs(received.astype(np.int16)-x.astype(np.int16))
    if int(delta.max())>s.epsilon_rgb:raise AssertionError('quantized perturbation exceeded epsilon')
    return {'received':received,'pixel_truth':np.any(received!=x,axis=-1),
        'linf_rgb_per_image':delta.reshape(len(x),-1).max(axis=1).tolist(),
        'loss_before_each_step':losses,'settings':{**s.__dict__,'random_start':False,
        'objective':'targeted CE descent' if s.targeted else 'untargeted CE ascent',
        'quantization':'nearest uint8 after projection; re-evaluate output',
        'exact_paper_reproduction':False}}
