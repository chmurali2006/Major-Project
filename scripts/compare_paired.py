"""Paired image bootstrap, stratified by intact/tampered label.

Intervals reflect test-image sampling, not variability across training seeds.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def compare(a, b, seed=0, draws=2000, strict=False):
    if draws < 1:
        raise ValueError('draws must be positive')
    with np.load(a, allow_pickle=False) as x, np.load(b, allow_pickle=False) as y:
        ai, bi = x['image_id'].astype(str), y['image_id'].astype(str)
        if len(set(ai)) != len(ai) or len(set(bi)) != len(bi) or set(ai) != set(bi):
            raise ValueError('paired files require identical unique image ids')
        for packet in (x,y):
            for field in ('tampered','iou','prediction'):
                if packet[field].ndim != 1 or len(packet[field]) != len(ai):
                    raise ValueError('unaligned per-image vectors')
            if not np.isin(packet['tampered'],[0,1]).all():
                raise ValueError('invalid ground-truth labels')
        lookup = {ident: i for i,ident in enumerate(bi)}
        order = [lookup[ident] for ident in ai]
        label = x['tampered'].astype(bool)
        if not np.array_equal(label,y['tampered'][order].astype(bool)):
            raise ValueError('paired labels differ')
        verified = all(field in x and field in y for field in ('family','gt_sha256'))
        if strict and not verified:
            raise ValueError('strict pairing requires attack family and measured mask hashes')
        if verified and any(not np.array_equal(x[field],y[field][order]) for field in ('family','gt_sha256')):
            raise ValueError('paired attack families or ground-truth masks differ')
        for values in (x['iou'], y['iou']):
            if not np.isfinite(values).all() or ((values<0)|(values>1)).any():
                raise ValueError('invalid per-image IoU')
        if not np.isin(x['prediction'],[0,1]).all() or not np.isin(y['prediction'],[0,1]).all():
            raise ValueError('invalid predicted verdict')
        loc = y['iou'][order] - x['iou']
        pa, pb = x['prediction'], y['prediction'][order]
    pos, neg = np.flatnonzero(label), np.flatnonzero(~label)
    if not len(pos) or not len(neg):
        raise ValueError('both classes required')
    def delta(i,j):
        return [float(loc[i].mean()), float(.5*((pb[i] == 1).mean() -
                (pa[i] == 1).mean() + (pb[j] == 0).mean() - (pa[j] == 0).mean()))]
    rng = np.random.default_rng(seed)
    vals = np.array([delta(rng.choice(pos,len(pos)),rng.choice(neg,len(neg))) for _ in range(draws)])
    point = delta(pos,neg)
    return {'measured_masks_verified':verified,'n':len(label), 'direction':'B minus A', 'bootstrap_seed':seed,'draws':draws,
            'interval_scope':'image sampling only, not training-seed uncertainty',
            'delta':{name:{'estimate':point[k], 'ci95':np.quantile(vals[:,k],[.025,.975]).tolist()}
                     for k,name in enumerate(('iou_tampered','balanced_accuracy'))}}


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--a',type=Path,required=True)
    ap.add_argument('--b',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--strict',action='store_true')
    args=ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(compare(args.a,args.b,strict=args.strict),indent=2)+'\n')


if __name__=='__main__':
    main()
