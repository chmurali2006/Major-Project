"""Forward-query-matched random search for the constrained correction prototype.

Not energy or wall-clock matched: gradients make guided search more expensive.
Both methods include the fixed baseline and select using the guiding model only.
"""
import numpy as np
import torch
import torch.nn.functional as F
from src.diagnostic_constrained_embedding import Settings,_input,carrier_mask,embed_fixed,decode


def query_matched_random(model,rgb,payload,mean,std,settings=Settings(),seed=0):
    s=settings;x=_input(rgb,s.block)
    if type(s.steps) is not int or not 0<=s.steps<=100 or type(s.correction_linf_rgb) is not int or not 0<=s.correction_linf_rgb<=16:
        raise ValueError('bounded correction/steps required')
    if len(mean)!=3 or len(std)!=3 or not np.isfinite(mean).all() or not np.isfinite(std).all() or min(std)<=0:
        raise ValueError('explicit RGB preprocessing required')
    if any(m.training for m in model.modules()) or any(p.requires_grad for p in model.parameters()):
        raise ValueError('frozen eval guide required')
    devices={t.device for t in list(model.parameters())+list(model.buffers())}
    if len(devices)!=1:raise ValueError('guide must reside on one device')
    device=next(iter(devices));mask=carrier_mask(x,s.block);base=embed_fixed(x,payload,s.block,s.qim_step)
    mn=torch.tensor(mean,device=device,dtype=torch.float32)[None,:,None,None]
    sd=torch.tensor(std,device=device,dtype=torch.float32)[None,:,None,None]
    queries=0
    def probabilities(a):
        nonlocal queries
        t=torch.tensor(a.transpose(2,0,1).copy(),device=device,dtype=torch.float32)[None]/255.
        with torch.no_grad():v=model((t-mn)/sd)
        queries+=1
        if v.ndim!=2 or v.shape[0]!=1 or v.shape[1]<2 or not torch.isfinite(v).all():raise ValueError('finite class logits required')
        return v.softmax(1)
    target=probabilities(x)
    def evaluate(a):
        p=probabilities(a)
        return max(0.,float(F.kl_div(p.clamp_min(1e-12).log(),target,reduction='batchmean')))
    best=base.copy();best_loss=evaluate(base);trace=[{'candidate':0,'guide_kl':best_loss}]
    rng=np.random.default_rng(seed)
    # Guided uses target + base + (gradient forward + integer evaluation)*steps
    # + final probability receipt = 2*steps+3 forwards. Spend all remaining
    # forwards on independent random candidates instead; no gradient queries.
    for index in range(1,2*s.steps+2):
        delta=rng.integers(-s.correction_linf_rgb,s.correction_linf_rgb+1,size=x.shape,dtype=np.int16)
        candidate=np.clip(x.astype(np.int16)+delta,0,255).astype(np.uint8);candidate[mask]=base[mask]
        loss=evaluate(candidate);trace.append({'candidate':index,'guide_kl':loss})
        if loss<best_loss:best=candidate;best_loss=loss
    if not np.array_equal(best[mask],base[mask]) or not np.array_equal(decode(best,s.block,s.qim_step),payload):
        raise AssertionError('carrier/payload constraint violated')
    return {'received':best,'base':base,'trace':trace,'guide_kl':best_loss,'forward_queries':queries,
            'backward_queries':0,'seed':seed,'selection':'strictly lower guide KL; baseline wins ties',
            'limits':['Same forward-query count and non-carrier Linf allowance as guided; not compute or energy matched.',
                      'Random magnitudes sampled uniformly over the full integer correction allowance.',
                      'Includes original prediction query and baseline evaluation; no unseen-model selection.',
                      'Better guide KL alone is not clinical or transfer efficacy.']}


def distortion_noninferiority(source,base,candidate,block=8):
    """Exact integer squared-error gate; does not establish clinical fidelity.

    A predeclared conservative deployment option: abstain from correction if its
    total pixel distortion exceeds fixed embedding. Often rejects useful guide
    corrections; report this, do not silently omit rejected images.
    """
    x=_input(source,block);mask=carrier_mask(x,block)
    for a in (base,candidate):
        if a.shape!=x.shape or a.dtype!=np.uint8:raise ValueError('aligned uint8 candidates required')
    if not np.array_equal(base[mask],candidate[mask]):raise ValueError('candidate changed carriers')
    energy=lambda a:int(np.square(a.astype(np.int64)-x.astype(np.int64)).sum())
    original_energy=energy(base);candidate_energy=energy(candidate);accept=candidate_energy<=original_energy
    return {'received':candidate.copy() if accept else base.copy(),'accepted':accept,
            'base_squared_error':original_energy,'candidate_squared_error':candidate_energy,
            'reason':'within_fixed_distortion' if accept else 'abstain_added_distortion',
            'limit':'Pixel squared error only; not clinical preservation or authentication.'}
