"""Shared validation objective: balanced image accuracy, then pixel IoU.

Both classical and learned verifiers use this same operating-point selection.
The network's epoch selection remains validation pixel IoU, never test selection.
"""
import numpy as np
from .metrics import iou

THRESHOLDS = tuple(np.arange(.05,2.01,.05))
COUNTS = (0,1,2,4,8,16,32,64,128,256)


def fit_boundary(samples, block_scores, pixel_scores):
    samples=list(samples)
    if not samples or len(block_scores)!=len(samples) or len(pixel_scores)!=len(samples):
        raise ValueError('aligned nonempty validation samples/maps required')
    labels=np.array([s.cls for s in samples])
    if not np.isin(labels,[0,1]).all() or not labels.any() or labels.all():
        raise ValueError('validation must include both binary classes')
    for s,b,p in zip(samples,block_scores,pixel_scores):
        truth=getattr(s,'gt_pixel',s.gt_block)
        if np.shape(b)!=np.shape(s.gt_block) or np.shape(p)!=np.shape(truth):
            raise ValueError('validation map/truth shapes differ')
        if not np.isfinite(b).all() or not np.isfinite(p).all():
            raise ValueError('nonfinite validation scores')
    best=None
    for tau in THRESHOLDS:
        counts=np.array([(b>tau).sum() for b in block_scores])
        loc=float(np.mean([iou(p>tau,getattr(s,'gt_pixel',s.gt_block))
                           for s,p in zip(samples,pixel_scores) if s.cls]))
        for k in COUNTS:
            pred=counts>k
            bal=float(.5*(pred[labels==1].mean()+(~pred[labels==0]).mean()))
            key=(bal,loc,-float(tau),-k)
            if best is None or key>best[0]: best=(key,float(tau),k)
    return best
