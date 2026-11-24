"""Research prototype: payload-preserving diagnostic correction, NOT novel/SOTA proof.

Standard pair-difference QIM carries one bit per spatial block in two red samples.
A bounded correction changes ONLY non-carrier samples to reduce a frozen guide's
prediction shift. Carrier samples stay bit-identical, so payload and clean decoding
margin cannot be weakened by the correction. This is an experimental mechanism,
not robust medical watermarking, content authentication, or clinical safety.
The fixed public carrier can be attacked; signed image authentication is separate.
"""
from dataclasses import dataclass
import numpy as np
import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class Settings:
    block: int = 8
    qim_step: int = 8
    correction_linf_rgb: int = 4
    steps: int = 12
    step_rgb: float = 1.


def _input(rgb,block):
    x=np.asarray(rgb)
    if type(block) is not int or block<2 or x.dtype!=np.uint8 or x.ndim!=3 or x.shape[-1]!=3 or min(x.shape[:2])<block or any(d%block for d in x.shape[:2]):
        raise ValueError('aligned HxWx3 uint8 RGB and block>=2 required')
    return x


def carrier_mask(rgb,block=8):
    x=_input(rgb,block);mask=np.zeros_like(x,dtype=bool)
    mask[::block,::block,0]=True;mask[::block,1::block,0]=True
    return mask


def embed_fixed(rgb,payload,block=8,qim_step=8):
    x=_input(rgb,block);bits=np.asarray(payload)
    if type(qim_step) is not int or not 1<=qim_step<=64:raise ValueError('integer QIM step1..64 required')
    if bits.shape!=(x.shape[0]//block,x.shape[1]//block) or bits.dtype.kind not in 'biu' or not np.isin(bits,[0,1]).all():raise ValueError('one binary payload bit per block required')
    out=x.copy()
    for row in range(bits.shape[0]):
        for col in range(bits.shape[1]):
            y,z=row*block,col*block;a,b=map(int,(x[y,z,0],x[y,z+1,0]));d=a-b
            # Nearest legal coset point; deterministic smaller-difference tie.
            lattice=[v for v in range(-255,256) if v%qim_step==0 and (v//qim_step)%2==int(bits[row,col])]
            target=min(lattice,key=lambda v:(abs(v-d),v))
            new_b=int(np.clip(np.rint((a+b-target)/2),max(0,-target),min(255,255-target)))
            out[y,z,0]=new_b+target;out[y,z+1,0]=new_b
    return out


def decode(rgb,block=8,qim_step=8):
    x=_input(rgb,block)
    if type(qim_step) is not int or not 1<=qim_step<=64:raise ValueError('integer QIM step1..64 required')
    difference=x[::block,::block,0].astype(np.int16)-x[::block,1::block,0].astype(np.int16)
    symbol=np.rint(difference/qim_step).astype(np.int16)
    return (symbol%2).astype(np.uint8)


def energy_matched_random(source,guided,base,block=8,seed=0):
    """Random signs with EXACT per-sample correction magnitudes and total MSE.

    Invalid sign choices at0/255 retain original sign, not clipped. Carrier values
    remain unchanged. This is an energy-matched directional control, not an
    independent watermark scheme or a compute-matched optimization baseline.
    """
    x=_input(source,block);mask=carrier_mask(x,block)
    if guided.shape!=x.shape or base.shape!=x.shape or guided.dtype!=np.uint8 or base.dtype!=np.uint8:raise ValueError('aligned uint8 candidates required')
    if not np.array_equal(guided[mask],base[mask]):raise ValueError('guided candidate changed carriers')
    delta=guided.astype(np.int16)-x.astype(np.int16)
    rng=np.random.default_rng(seed);sign=rng.choice([-1,1],size=x.shape)
    proposed=x.astype(np.int16)+np.abs(delta)*sign
    valid=(proposed>=0)&(proposed<=255)&~mask
    out=guided.copy();out[valid]=proposed[valid].astype(np.uint8);out[mask]=base[mask]
    return out


def embed_guided(model,rgb,payload,mean,std,settings=Settings()):
    s=settings;x=_input(rgb,s.block)
    if type(s.correction_linf_rgb) is not int or not 0<=s.correction_linf_rgb<=16 or type(s.steps) is not int or not 0<=s.steps<=100 or not np.isfinite(s.step_rgb) or s.step_rgb<=0:
        raise ValueError('bounded correction/step settings required')
    if len(mean)!=3 or len(std)!=3 or not np.isfinite(mean).all() or not np.isfinite(std).all() or min(std)<=0:raise ValueError('explicit RGB preprocessing required')
    if any(m.training for m in model.modules()) or any(p.requires_grad for p in model.parameters()):raise ValueError('frozen eval guide required')
    devices={t.device for t in list(model.parameters())+list(model.buffers())}
    if len(devices)!=1:raise ValueError('guide must reside on one device')
    device=next(iter(devices));base=embed_fixed(x,payload,s.block,s.qim_step);mask=carrier_mask(x,s.block)
    tensor=lambda a:torch.tensor(a.transpose(2,0,1).copy(),device=device,dtype=torch.float32)[None]/255.
    original=tensor(x);fixed=tensor(base);locked=torch.tensor(mask.transpose(2,0,1).copy(),device=device)[None]
    mn=torch.tensor(mean,device=device,dtype=torch.float32)[None,:,None,None];sd=torch.tensor(std,device=device,dtype=torch.float32)[None,:,None,None]
    def logits(value):
        v=model((value-mn)/sd)
        if v.ndim!=2 or v.shape[0]!=1 or v.shape[1]<2 or not torch.isfinite(v).all():raise ValueError('finite single-image class logits required')
        return v
    with torch.no_grad():target=logits(original).softmax(1).detach()
    # Avoid negative floating point KL roundoff by clamp at0 for receipts only.
    def evaluate(a):
        with torch.no_grad():
            p=logits(tensor(a)).softmax(1)
            loss=F.kl_div(p.clamp_min(1e-12).log(),target,reduction='batchmean')
        return max(0.,float(loss)),p[0].cpu().numpy().tolist()
    best=base.copy();best_loss,base_prob=evaluate(base);trace=[{'step':0,'guide_kl':best_loss}]
    lo=(original-s.correction_linf_rgb/255.).clamp(0,1);hi=(original+s.correction_linf_rgb/255.).clamp(0,1)
    current=fixed.clone()
    with torch.enable_grad():
        for step in range(1,s.steps+1):
            current=current.detach().requires_grad_(True)
            loss=F.kl_div(logits(current).log_softmax(1),target,reduction='batchmean')
            if not loss.requires_grad:raise ValueError('guide has no input gradient')
            gradient=torch.autograd.grad(loss,current)[0]
            if not torch.isfinite(gradient).all():raise ValueError('nonfinite guide gradient')
            proposed=current-s.step_rgb/255.*gradient.sign()
            current=torch.where(locked,fixed,torch.maximum(lo,torch.minimum(hi,proposed)))
            candidate=np.rint(current.detach().cpu().numpy()[0].transpose(1,2,0)*255).clip(0,255).astype(np.uint8)
            candidate[mask]=base[mask]
            value,_=evaluate(candidate);trace.append({'step':step,'guide_kl':value})
            if value<best_loss:best=candidate;best_loss=value
    if not np.array_equal(best[mask],base[mask]) or not np.array_equal(decode(best,s.block,s.qim_step),payload):raise AssertionError('watermark constraint violated')
    difference=np.abs(best.astype(np.int16)-x.astype(np.int16))
    if int(difference[~mask].max())>s.correction_linf_rgb:raise AssertionError('correction bound violated')
    _,best_prob=evaluate(best)
    return {'received':best,'base':base,'trace':trace,'original_probabilities':target[0].cpu().numpy().tolist(),
        'base_probabilities':base_prob,'guided_probabilities':best_prob,'settings':s.__dict__,
        'carrier_samples':int(mask.sum()),'payload_bits':int(np.size(payload)),
        'limits':['Standard QIM carrier; no claim of new coding or authentication construction.',
        'Post-embedding non-carrier correction differs from saliency strength allocation; feasibility candidate only.',
        'Guide output preservation may overfit or preserve wrong predictions; independent evaluator is required.',
        'Clean payload/margin constraint does not guarantee watermark robustness after JPEG, attacks or resizing.',
        'Candidate selection minimizes guide KL, not diagnostic error or human clinical distortion.',
        'Additional correction can increase distortion. Compare energy-matched controls and report no-improvement cases.']}
