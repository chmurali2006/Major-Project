"""Summarise completed receipts; incomplete or failed runs stay explicit."""
import argparse
import json
from pathlib import Path
import numpy as np


def summarize(root):
    rows = []
    missing = []
    for seed in (0,1,2):
        folder = root / f'seed-{seed}'
        for config in ('C0_count','C0_B','C8','C12'):
            path = folder / f'{config}.json'
            if not path.exists():
                missing.append(str(path))
                continue
            r = json.loads(path.read_text())
            row = {'seed':seed,'config':config,'usable':r['usable'],
                   'iou_tampered':r['iou_tampered_mean'],
                   'balanced_accuracy':r['balanced_accuracy'],
                   'tpr':r['tpr'],'fpr':r['fpr']}
            if 'selective' in r:
                row['selective'] = r['selective']
            if 'rekey' in r:
                delta = r['iou_tampered_mean'] - r['rekey']['iou_tampered_mean']
                row['rekey_drop_iou'] = delta
                row['rekey_gate_pass'] = delta <= .05
            rows.append(row)
    aggregates = {}
    for config in ('C8','C12'):
        rr = [r for r in rows if r['config'] == config and r['usable']]
        if len(rr) == 3:
            aggregates[config] = {metric:{'mean':float(np.mean([r[metric] for r in rr])),
                                          'seed_sd':float(np.std([r[metric] for r in rr], ddof=1))}
                                  for metric in ('iou_tampered','balanced_accuracy','tpr','fpr')}
    heldout_path = root/'heldout-T5'/'C8.json'
    heldout = json.loads(heldout_path.read_text()).get('heldout') if heldout_path.exists() else None
    if heldout is None:
        missing.append(str(heldout_path))
    return {'complete':not missing,'missing':missing,'runs':rows,
            'three_seed_aggregates':aggregates,'heldout_T5':heldout,
            'limitations':['Image-level split, not lesion/patient grouped.',
                           'Bootstrap intervals reflect image sampling, not training-seed uncertainty.',
                           'Validation risk constraints are empirical, not a population guarantee.',
                           'No cross-paper parity claim from this protocol.']}


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    result=summarize(args.root)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f"complete={result['complete']}; completed receipts={len(result['runs'])}; missing={len(result['missing'])}")


if __name__=='__main__':
    main()
