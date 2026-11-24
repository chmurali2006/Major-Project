"""Diagnostic gradient conflicts, never an automatic loss-weight adjustment."""
import itertools
import torch


def gradient_comparison(losses,parameters):
    """Compare scalar losses on an existing graph; leaves .grad untouched.

    Requires a shared parameter subset and losses retaining their computation
    graphs. Zero/unused gradients yield null cosine, not fabricated alignment.
    Does not run a forward pass or alter modes, buffers, parameters or weights.
    """
    parameters=list(parameters)
    if not parameters or not losses:raise ValueError('shared parameters and scalar losses required')
    gradients={};norms={};values={}
    for name,loss in losses.items():
        if loss.ndim!=0 or not torch.isfinite(loss) or not loss.requires_grad:raise ValueError('finite differentiable scalar loss required')
        parts=torch.autograd.grad(loss,parameters,retain_graph=True,allow_unused=True)
        vector=torch.cat([(g if g is not None else torch.zeros_like(p)).detach().reshape(-1).double() for p,g in zip(parameters,parts)])
        if not torch.isfinite(vector).all():raise ValueError('nonfinite objective gradient')
        gradients[name]=vector;norms[name]=float(vector.norm());values[name]=float(loss.detach())
    pairs=[]
    for left,right in itertools.combinations(losses,2):
        den=norms[left]*norms[right]
        dot=float(torch.dot(gradients[left],gradients[right]))
        pairs.append({'left':left,'right':right,'dot':dot,'cosine':max(-1.,min(1.,dot/den)) if den else None})
    return {'loss_values':values,'gradient_l2_norms':norms,'pairs':pairs,
        'limits':['Local gradient conflict is not proof of a training failure cause or a generalization result.',
        'Cosines depend on the specified shared parameter subset and model state.',
        'No objective/weight modification is made by this diagnostic.']}
