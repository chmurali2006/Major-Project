"""TRAIN-only pilot of constrained embedding and explicit controls.

No claim of novelty, robustness, clinical safety or final medical-image benefit.
Select fixed first N training rows before loading outcomes; never validation/test.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
import torch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from src import binary_signed_grid as G
from src.diagnostic_constrained_embedding import Settings,embed_fixed,embed_guided,decode,carrier_mask,energy_matched_random
from src.diagnostic_correction_controls import query_matched_random,distortion_noninferiority
from src.diagnostic_impact import analyse
from src.isic_classifier_training import PreparedSplit,MEAN,STD,load_frozen_densenet
from src.paper_aligned_operators import operators


def run(guide,preparation,cohort,out,guide_identity,*,evaluator=None,evaluator_identity=None,n=12,settings=Settings(),repetitions=1000):
    if type(n) is not int or not 1<=n<=32:raise ValueError('bounded pilot n1..32 required')
    if not guide_identity.get('checkpoint_sha256'):raise ValueError('reviewed guide identity required')
    if (evaluator is None)!=(evaluator_identity is None):raise ValueError('evaluator and its identity must be supplied together')
    if evaluator is not None and (not evaluator_identity.get('checkpoint_sha256') or evaluator_identity['checkpoint_sha256']==guide_identity['checkpoint_sha256']):raise ValueError('distinct evaluator checkpoint required')
    data=PreparedSplit(preparation,cohort,'train');selected=data.rows[:n]
    if len(selected)!=n:raise ValueError('insufficient fixed training inputs')
    for i in range(n):data[i]
    def predict(model,image):
        if any(m.training for m in model.modules()) or any(p.requires_grad for p in model.parameters()):raise ValueError('frozen eval model required')
        device=next(iter({t.device for t in list(model.parameters())+list(model.buffers())}))
        x=torch.tensor(image.transpose(2,0,1).copy(),device=device,dtype=torch.float32)[None]/255.
        mean=torch.tensor(MEAN,device=device)[None,:,None,None];std=torch.tensor(STD,device=device)[None,:,None,None]
        with torch.no_grad():return model((x-mean)/std).softmax(1)[0].cpu().numpy().tolist()
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'artifacts').mkdir()
    protocol={'schema':'diagnostic-constrained-embedding-train-pilot-v2','split':'train','image_ids':[r['image_id'] for r in selected],
        'cohort_sha256':data.cohort_sha256,'guide':guide_identity,'evaluator':evaluator_identity,'settings':asdict(settings),
        'selection':'first N fixed train rows, no outcome selection','variants':['fixed_qim','uniform_weaker_qim','energy_matched_random','diagnostic_correction','query_matched_random','distortion_gated_correction'],
        'hypothesis':'payload-preserving non-carrier correction can reduce guide shift; transfer and additional distortion remain open',
        'scope':['QIM is an established, public, fragile payload carrier, not content authentication.',
        'A full signed4 sidecar authenticates final RGB independently; its entire524378bytes/image is counted.',
        'Guide-only KL non-increase is by candidate selection, NOT evidence of general diagnostic preservation.',
        'Original guide predictions can be wrong; retaining them is not a clinical objective by itself.',
        'Random control matches exact per-sample distortion magnitude, not compute budget or guide-query selection.',
        'Weaker QIM changes margin and is NOT recovery-strength matched.',
        'Pilot images belong to classifier TRAIN, not independent evaluation; cannot establish generalization or SOTA.',
        'Same number of bits across controls; non-carrier corrections preserve carrier values but not attack robustness.']}
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2));key=Ed25519PrivateKey.generate()
    (out/'public-key.bin').write_bytes(key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
    clean={name:[] for name in ('guide','evaluator')};predictions={};labels=[];row_count=0
    with (out/'rows.jsonl').open('w',buffering=1) as f:
        for index,r in enumerate(selected):
            with Image.open(Path(preparation)/'prepared'/(r['image_id']+'.png')) as im:x=np.array(im.convert('RGB'))
            if hashlib.sha256(x.tobytes()).hexdigest()!=r['prepared_rgb_sha256']:raise ValueError('prepared source changed')
            labels.append(r['melanoma_label']);bits=np.random.default_rng(8001+index).integers(0,2,(512//settings.block,512//settings.block),dtype=np.uint8)
            result=embed_guided(guide,x,bits,MEAN,STD,settings)
            random_search=query_matched_random(guide,x,bits,MEAN,STD,settings,seed=8201+index)
            gate=distortion_noninferiority(x,result['base'],result['received'],settings.block)
            variants={'query_matched_random':(random_search['received'],settings.qim_step),
                'distortion_gated_correction':(gate['received'],settings.qim_step),'fixed_qim':(result['base'],settings.qim_step),
                'uniform_weaker_qim':(embed_fixed(x,bits,settings.block,max(1,settings.qim_step//2)),max(1,settings.qim_step//2)),
                'energy_matched_random':(energy_matched_random(x,result['received'],result['base'],settings.block,8101+index),settings.qim_step),
                'diagnostic_correction':(result['received'],settings.qim_step)}
            for model_name,model in (('guide',guide),('evaluator',evaluator)):
                if model is not None:clean[model_name].append(predict(model,x))
            for name,(y,step) in variants.items():
                diff=y.astype(np.int16)-x.astype(np.int16);packet=G.sign(y,key,index)
                (out/'artifacts'/f'{index:03d}-{name}.bin').write_bytes(packet)
                model_predictions={}
                for model_name,model in (('guide',guide),('evaluator',evaluator)):
                    if model is not None:
                        prob=predict(model,y);model_predictions[model_name]=prob;predictions.setdefault((model_name,name),[]).append(prob)
                recoveries=[]
                for op in operators(y,2301+index):
                    recovered=decode(op['received'],settings.block,step)
                    check=G.verify(op['received'],packet,key.public_key(),index)
                    if check.verdict!=('FAILED_INTEGRITY' if op['pixel_truth'].any() else 'VERIFIED'):raise AssertionError('signed integrity invariant failed')
                    recoveries.append({'case':op['case'],'payload_bit_errors':int((recovered!=bits).sum()),'payload_bits':int(bits.size),
                        'changed_pixels':int(op['pixel_truth'].sum()),'signed_rgb_verdict':check.verdict})
                carrier=carrier_mask(x,settings.block)
                carrier_equal=bool(np.array_equal(y[carrier],result['base'][carrier])) if name!='uniform_weaker_qim' else None
                row={'image_id':r['image_id'],'label':r['melanoma_label'],'variant':name,'source_rgb_sha256':r['prepared_rgb_sha256'],
                    'received_rgb_sha256':hashlib.sha256(y.tobytes()).hexdigest(),'payload_sha256':hashlib.sha256(bits.tobytes()).hexdigest(),
                    'payload_bits':int(bits.size),'qim_step':step,'embedding_mse':float(np.mean(diff.astype(float)**2)),
                    'linf_rgb':int(np.abs(diff).max()),'changed_samples':int((diff!=0).sum()),'signed_evidence_bytes':len(packet),
                    'same_carrier_values_as_fixed':carrier_equal,'original_probabilities':{k:v[-1] for k,v in clean.items() if v},'probabilities':model_predictions,'recovery':recoveries,
                    'guide_trace':result['trace'] if name=='diagnostic_correction' else None,
                    'random_search':{k:v for k,v in random_search.items() if k not in ('received','base')} if name=='query_matched_random' else None,
                    'distortion_gate':{k:v for k,v in gate.items() if k!='received'} if name=='distortion_gated_correction' else None,
                    'optimization_forward_queries':2*settings.steps+3 if name in ('diagnostic_correction','query_matched_random') else None,
                    'optimization_backward_queries':settings.steps if name=='diagnostic_correction' else 0 if name=='query_matched_random' else None}
                f.write(json.dumps(row)+'\n');row_count+=1
            print('Diagnostic embedding TRAIN pilot',index+1,'/',n,flush=True)
    summary={'completed':True,'images':n,'rows':row_count,'test_evaluated':False,'independent_evaluator_tested':evaluator is not None,
        'diagnostic_impact':{model_name+'/'+variant:analyse(np.array(labels),np.array(clean[model_name]),np.array(prob),['nonMEL','MEL'],repetitions=repetitions) for (model_name,variant),prob in predictions.items()}}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for name in ('preparation','cohort','guide_training','out'):p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    p.add_argument('--guide-sha256',required=True);p.add_argument('--device',default='cuda');a=p.parse_args()
    complete=json.loads((a.guide_training/'summary.json').read_text())
    if complete.get('completed') is not True or complete['checkpoint_sha256']!=a.guide_sha256:raise ValueError('reviewed completed guide training required')
    cohort_hash=hashlib.sha256(a.cohort.read_bytes()).hexdigest()
    model,identity=load_frozen_densenet(a.guide_training/'best.pt',a.guide_sha256,cohort_hash,a.device)
    run(model,a.preparation,a.cohort,a.out,identity)
