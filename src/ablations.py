"""Matched input/component removals on the SAME protected samples and truth.

Carrier ablations remove verification features, not embedding: modifying the
protected image would change attack truth and invalidate strict paired masks.
"""
import numpy as np

ABLATIONS = ('without-ae','without-saliency','without-degradation','without-pixel',
             'without-fragile','without-semi','rgb-only')


def configure(model, name, channels=13):
    model['variant'] = name
    mask = np.ones(channels,np.float32)
    if name=='without-fragile': mask[:10]=0
    if name=='without-semi': mask[10:]=0
    if name=='rgb-only': mask[:]=0
    model['evidence_mask'] = mask.tolist()
    model['use_ae'] = name not in ('without-ae','rgb-only')
    if not model['use_ae']:
        for p in model['ae'].parameters(): p.requires_grad_(False)
        model['ae'].eval()
    if name=='without-saliency':
        model['use_saliency']=False
        for p in model['saliency'].parameters(): p.requires_grad_(False)
    if name=='without-degradation': model['use_degrade']=False
    if name=='without-pixel':
        model['use_pixel']=False
        model['refine'].pixel_enabled=False
        for module in ('u4','u3','u2','pixel_head'):
            for p in getattr(model['refine'],module).parameters(): p.requires_grad_(False)
    return model


def mask_evidence(model, evidence):
    mask=model.get('evidence_mask')
    if mask is None: return evidence
    return evidence * evidence.new_tensor(mask).view(1,-1,1,1)
