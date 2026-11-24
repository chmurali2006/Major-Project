"""Validation-only diagnostic impact for reviewed frozen classifier checkpoint.

Run AFTER training completion/provenance review, not during checkpoint selection.
All results here remain validation development evidence. No test access.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
import torch
from src.adversarial_operators import AttackSettings,attack
from src.diagnostic_impact import analyse
from src.isic_classifier_training import PreparedSplit,MEAN,STD,load_frozen_densenet
from src.paper_aligned_operators import operators,SETTINGS


def run(model,preparation,cohort,out,identity,repetitions=2000):
    dataset=PreparedSplit(preparation,cohort,'validation')
    if not identity.get('checkpoint_sha256'):raise ValueError('reviewed checkpoint identity required')
    if model.training or any(p.requires_grad for p in model.parameters()):raise ValueError('frozen eval classifier required')
    device=next(iter({t.device for t in list(model.parameters())+list(model.buffers())}))
    mean=torch.tensor(MEAN,device=device,dtype=torch.float32)[None,:,None,None]
    std=torch.tensor(STD,device=device,dtype=torch.float32)[None,:,None,None]
    def predict(x):
        value=torch.tensor(x.transpose(2,0,1).copy(),device=device,dtype=torch.float32)[None]/255.
        with torch.no_grad():p=model((value-mean)/std).softmax(1).cpu().numpy()[0]
        if p.shape!=(2,) or not np.isfinite(p).all():raise ValueError('finite binary classifier output required')
        return p.tolist()
    # Preflight validation inputs and membership before writing output.
    for i in range(len(dataset)):dataset[i]
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    protocol={'schema':'adapted-frozen-classifier-impact-v1','checkpoint':identity,'cohort_sha256':dataset.cohort_sha256,
        'split':'validation','n':len(dataset),'class_names':['nonMEL','MEL'],'mean':MEAN,'std':STD,
        'classic_operators':SETTINGS,'attack_objective':'untargeted ground-truth CE ascent; clean start',
        'fgsm_epsilon_rgb':4,'pgd_epsilon_rgb':4,'pgd_steps':3,'pgd_step_rgb':1,
        'exact_paper_reproduction':False,'limits':['Validation reused for checkpoint selection: development evidence only.',
        'This classifier differs from author CheXpert initialization; no exact author attack reproduction.',
        'Clean accuracy and class sensitivity must accompany agreement/attack-success results.',
        'No clinical-safety claim from these metrics or image bootstrap.']}
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2))
    grouped={};clean=[];labels=[]
    with (out/'predictions.jsonl').open('w',buffering=1) as f:
        for index,r in enumerate(dataset.rows):
            with Image.open(Path(preparation)/'prepared'/(r['image_id']+'.png')) as im:x=np.array(im.convert('RGB'))
            if hashlib.sha256(x.tobytes()).hexdigest()!=r['prepared_rgb_sha256']:raise ValueError('source changed after preflight')
            p=predict(x);label=int(r['melanoma_label']);clean.append(p);labels.append(label)
            def write(case,family,y,truth,parameters):
                received=predict(y);grouped.setdefault(case,[]).append(received)
                row={'image_id':r['image_id'],'label':label,'case':case,'family':family,'operator_seed':2301+index,
                    'source_rgb_sha256':r['prepared_rgb_sha256'],'received_rgb_sha256':hashlib.sha256(y.tobytes()).hexdigest(),
                    'clean_probabilities':p,'received_probabilities':received,'changed_pixels':int(truth.sum()),
                    'linf_rgb':int(np.abs(y.astype(np.int16)-x.astype(np.int16)).max()),'parameters':parameters}
                f.write(json.dumps(row)+'\n')
            for op in operators(x,2301+index):write(op['case'],op['family'],op['received'],op['pixel_truth'],op['parameters'])
            for algorithm in ('fgsm','pgd'):
                settings=AttackSettings(algorithm,MEAN,STD,False)
                result=attack(model,x[None],np.array([label]),settings)
                write(algorithm+'4_adapted','adapted_adversarial',result['received'][0],result['pixel_truth'][0],result['settings'])
            print('Classifier impact',index+1,'/',len(dataset),flush=True)
    y=np.array(labels);a=np.array(clean);eligible=a.argmax(1)==y;impact={}
    for case,prob in grouped.items():
        b=np.array(prob);metrics=analyse(y,a,b,['nonMEL','MEL'],repetitions=repetitions)
        if case in ('fgsm4_adapted','pgd4_adapted'):
            success=b.argmax(1)!=y
            metrics['untargeted_success']={'all_images_numerator':int(success.sum()),'all_images_denominator':len(y),
                'clean_correct_numerator':int((eligible&success).sum()),'clean_correct_denominator':int(eligible.sum()),
                'clean_correct_rate':float(success[eligible].mean()) if eligible.any() else None}
        impact[case]=metrics
    summary={'completed':True,'images':len(dataset),'rows':len(dataset)*len(grouped),'test_evaluated':False,'cases':impact}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for name in ('preparation','cohort','training','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--device',default='cuda');a=p.parse_args()
    completed=json.loads((a.training/'summary.json').read_text())
    if completed.get('completed') is not True or completed['checkpoint_sha256']!=a.checkpoint_sha256:raise ValueError('reviewed complete training required')
    cohort_hash=hashlib.sha256(a.cohort.read_bytes()).hexdigest()
    model,identity=load_frozen_densenet(a.training/'best.pt',a.checkpoint_sha256,cohort_hash,a.device)
    manifest=json.loads(a.cohort.read_text())
    for split in ('train','validation'):
        if set(identity['protocol'][split+'_ids'])!={r['image_id'] for r in manifest['selected'] if r['split']==split}:raise ValueError('classifier training membership differs')
    run(model,a.preparation,a.cohort,a.out,identity)
