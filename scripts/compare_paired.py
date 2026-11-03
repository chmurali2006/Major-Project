"""Paired image bootstrap, stratified by intact/tampered label.

Intervals reflect test-image sampling, not variability across training seeds.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def compare(a, b, seed=0, draws=2000):
    if draws < 1:
        raise ValueError('draws must be positive')
    with np.load(a, allow_pickle=False) as x, np.load(b, allow_pickle=False) as y:
        ai, bi = x['image_id'].astype(str), y['image_id'].astype(str)
        if len(set(ai)) != len(ai) or len(set(bi)) != len(bi) or set(ai) != set(bi):
            raise ValueError('paired files require identical unique image ids')
        lookup = {ident: i for i,ident in enumerate(bi)}
        order = [lookup[ident] for ident in ai]
        label = x['tampered'].astype(bool)
        if not np.array_equal(label,y['tampered'][order].astype(bool)):
            raise ValueError('paired labels differ')
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
    return {'n':len(label), 'direction':'B minus A', 'bootstrap_seed':seed,'draws':draws,
            'interval_scope':'image sampling only, not training-seed uncertainty',
            'delta':{name:{'estimate':point[k], 'ci95':np.quantile(vals[:,k],[.025,.975]).tolist()}
                     for k,name in enumerate(('iou_tampered','balanced_accuracy'))}}


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--a',type=Path,required=True)
    ap.add_argument('--b',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(compare(args.a,args.b),indent=2)+'\n')


if __name__=='__main__':
    main()
