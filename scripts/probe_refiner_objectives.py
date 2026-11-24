"""Bounded synthetic TRAIN-only objective probe, not a model-comparison result.

Same seven diagnostic samples/seeds as diagnose_learning.py. No validation/test
images, no new variants/thresholds/losses. Restores identical initial refiner state
before each forward; authentic-only AE pretraining is the existing two epochs.
"""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import numpy as np
import torch
import torch.nn.functional as F
import run_matrix as R
import run_isic_study as S
from src import models
from src.authentic_training import pretrain_authentic
from src.names import model_name
from src.persistence import atomic_json,source_digest
from src.objective_diagnostics import gradient_comparison


def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2);torch.manual_seed(0);torch.use_deterministic_algorithms(True)
    families=['T1','T2','T3','T4','T5','none','B1:jpeg75']
    items=R.load_items(None,7,0,True)
    samples=[R.build_sample(it,families[j],np.random.default_rng(10000+j),donor=items[(j+1)%7] if families[j]=='T5' else None) for j,it in enumerate(items)]
    report={'schema':'refiner-objective-gradient-probe-v1','synthetic':True,'usable_as_study_result':False,
        'source_sha256':source_digest(ROOT),'width':4,'seed':0,'parameter_subset':'refine.stem (image/saliency/degradation shared stem)',
        'scope':'initial refiner, train mode; identical state restored before each sample; no localization training','models':{}}
    for cid in ('C8','C12'):
        model=S.build_paired_model(cid,4,0)
        pretrain_authentic(model,samples,2,out/(cid+'-fixture-ae.pt'),False,'objective-probe:'+cid,device='cpu',log=lambda _:None)
        original={module:{k:v.detach().clone() for k,v in state.items()} for module,state in R.state_of(model).items()}
        rows=[]
        for sample in samples:
            R.load_state(model,original);R.to_train(model)
            t={'ev':torch.from_numpy(sample.ev).float()[None],'deg':torch.from_numpy(sample.degrade)[None],
                'image':torch.from_numpy(sample.image).float()[None]/255.,'gt_block':torch.from_numpy(sample.gt_block).float()[None,None],
                'gt_pixel':torch.from_numpy(sample.gt_pixel).float()[None,None]}
            prediction=R.forward_all(model,t)
            losses={'block':models.mask_loss(prediction['block_logits'],t['gt_block'],pos_weight=12.),
                'pixel':models.pixel_mask_loss(prediction['pixel_logits'],t['gt_pixel'],pos_weight=4.),
                'weighted_consistency':.5*models.consistency_loss(prediction['pixel_logits'],prediction['block_logits']),
                'weighted_classification':.5*F.cross_entropy(prediction['cls'],torch.tensor([sample.cls]))}
            row=gradient_comparison(losses,model['refine'].stem.parameters())
            row.update({'family':sample.family,'changed_pixels':int(sample.gt_pixel.sum()),'changed_blocks':int(sample.gt_block.sum())})
            rows.append(row)
        report['models'][model_name(cid)]=rows
    atomic_json(out/'probe.json',report)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    run(args.out);print('Saved synthetic objective probe:',args.out/'probe.json')
