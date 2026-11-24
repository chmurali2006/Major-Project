"""Adapted validation500 published-checkpoint reader comparison, not author scores.

EditGuard and a signed4 reader receive IDENTICAL marked images and manipulations.
The signed4 sidecar is an additional full digest grid, not equal-storage evidence.
This isolates localisation readers; it is not an end-to-end fair-storage ranking.
No generative attacks, copyright decoding, classifier utility or clinical claims.
"""
import argparse
from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from src.binary_signed_grid import sign,verify
from src.isic_classifier_training import PreparedSplit
from src.paper_aligned_operators import operators,SETTINGS


def run(adapter,preparation,cohort,out,*,synchronize=lambda:None,classifier=None,classifier_identity=None,repetitions=2000):
    if (classifier is None)!=(classifier_identity is None):raise ValueError('classifier and reviewed identity required together')
    if classifier is not None:
        import torch
        from src.isic_classifier_training import MEAN,STD
        from src.diagnostic_impact import analyse
        if any(m.training for m in classifier.modules()) or any(p.requires_grad for p in classifier.parameters()):raise ValueError('frozen eval classifier required')
        if not classifier_identity.get('checkpoint_sha256'):raise ValueError('checkpoint identity required')
        device=next(iter({t.device for t in list(classifier.parameters())+list(classifier.buffers())}))
        mn=torch.tensor(MEAN,device=device)[None,:,None,None];sd=torch.tensor(STD,device=device)[None,:,None,None]
        def predict(image):
            t=torch.tensor(image.transpose(2,0,1).copy(),device=device,dtype=torch.float32)[None]/255.
            with torch.no_grad():v=classifier((t-mn)/sd).softmax(1).cpu().numpy()[0]
            if v.shape!=(2,) or not np.isfinite(v).all():raise ValueError('finite binary predictions required')
            return v.tolist()
    diagnostic_rows=[]
    dataset=PreparedSplit(preparation,cohort,'validation')
    # Complete preflight before any model execution/output creation.
    for i in range(len(dataset)):dataset[i]
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'artifacts').mkdir()
    key=Ed25519PrivateKey.generate();public=key.public_key()
    (out/'public-key.bin').write_bytes(public.public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
    protocol={'schema':'adapted-matched-editguard-validation-v1','cohort_sha256':dataset.cohort_sha256,'split':'validation','n':len(dataset),
        'editguard':adapter.provenance,'threshold':.2,'operator_seed':'2301 + fixed validation index','operators':SETTINGS,
        'pairing':'identical EditGuard-marked reference and received RGB for both readers; same exact-pixel truth',
        'signed_control':'full signed4 digest grid added to EditGuard container; not a separate nonembedding end-to-end treatment',
        'limits':['Different evidence costs: signed4 additional524378bytes/image; EditGuard fixed model weights reported separately.',
        'Global operations labelled paper-benign change exact RGB; not automatically malicious semantic edits.',
        'Local blur is a surrogate, not semantic lesion removal. No FGSM/PGD/generative edits here.',
        'Official reviewed EditGuard clean checkpoint under adapted ISIC/operators, NOT reproduced author benchmark scores.',
        'Timing calls synchronized when CUDA; one measurement per image/case, no throughput claim.',
        'Validation development only; test not evaluated. Classifier utility is a separate evaluation.']}
    if classifier is not None:
        protocol['schema']='adapted-matched-editguard-validation-v2'
        protocol['classifier']=classifier_identity
        protocol['diagnostic_pairing']='four conditions: original, operated original, marked, operated marked; same operator seed/parameters; classifier calls excluded from localisation timing'
        protocol['diagnostic_limits']=['Frozen imperfect classifier; model effects not clinical safety.',
            'Embedding given operator compares operated marked vs operated original, not only original vs marked+operation.',
            'No SSIM implemented in this version; MSE/PSNR only. No threshold or checkpoint tuning.']
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2))
    count=0
    with (out/'rows.jsonl').open('w',buffering=1) as f,(out/'setup.jsonl').open('w',buffering=1) as setup, ((out/'diagnostic-predictions.jsonl').open('w',buffering=1) if classifier is not None else nullcontext()) as diagnostic:
        for index,r in enumerate(dataset.rows):
            with Image.open(Path(preparation)/'prepared'/(r['image_id']+'.png')) as im:x=np.array(im.convert('RGB'))
            if hashlib.sha256(x.tobytes()).hexdigest()!=r['prepared_rgb_sha256']:raise ValueError('source changed after preflight')
            synchronize();began=time.perf_counter();reference=adapter.embed(x.copy(),seed=7301+index);synchronize();embed_seconds=time.perf_counter()-began
            if reference.dtype!=np.uint8 or reference.shape!=(512,512,3):raise ValueError('invalid protected RGB')
            embedding_mse=float(np.mean((reference.astype(float)-x.astype(float))**2))
            began=time.perf_counter();packet=sign(reference,key,index,4);sign_seconds=time.perf_counter()-began
            (out/'artifacts'/f'{index:03d}-signed4.bin').write_bytes(packet)
            setup.write(json.dumps({'image_id':r['image_id'],'embedding_seed':7301+index,'embedding_mse':embedding_mse,
                'embedding_psnr_db':float(10*np.log10(255**2/embedding_mse)) if embedding_mse else None,
                'embedding_seconds':embed_seconds,'signed4_setup_seconds':sign_seconds,'signed4_bytes':len(packet),
                'protected_rgb_sha256':hashlib.sha256(reference.tobytes()).hexdigest()})+'\n')
            maps={}
            if classifier is not None:
                original_prob=predict(x);marked_prob=predict(reference)
                original_ops={a['case']:a for a in operators(x,2301+index)}
            for op in operators(reference,2301+index):
                truth=op['pixel_truth'];y=op['received'];received_hash=hashlib.sha256(y.tobytes()).hexdigest()
                if classifier is not None:
                    original_op=original_ops[op['case']]
                    if original_op['parameters']!=op['parameters']:raise AssertionError('unpaired operation parameters')
                    original_received_prob=original_prob if op['case']=='intact' else predict(original_op['received'])
                    marked_received_prob=marked_prob if op['case']=='intact' else predict(y)
                    dr={'image_id':r['image_id'],'label':r['melanoma_label'],'case':op['case'],'seed':2301+index,
                        'parameters':op['parameters'],'source_rgb_sha256':r['prepared_rgb_sha256'],
                        'marked_rgb_sha256':hashlib.sha256(reference.tobytes()).hexdigest(),
                        'original_received_rgb_sha256':hashlib.sha256(original_op['received'].tobytes()).hexdigest(),
                        'marked_received_rgb_sha256':received_hash,'original_probabilities':original_prob,
                        'marked_probabilities':marked_prob,'original_received_probabilities':original_received_prob,
                        'marked_received_probabilities':marked_received_prob}
                    diagnostic.write(json.dumps(dr)+'\n');diagnostic_rows.append(dr)
                maps[op['case']+'-truth']=np.packbits(truth)
                for method in ('EditGuard clean','Signed4 on EditGuard container'):
                    synchronize();began=time.perf_counter()
                    if method=='EditGuard clean':
                        score,mask=adapter.localize(y,threshold=.2)
                        if score.shape!=(512,512) or not np.isfinite(score).all():raise ValueError('invalid model score')
                    else:
                        result=verify(y,packet,public,index,4)
                        if result.failed_blocks is None:raise ValueError('signed grid unexpectedly unavailable')
                        mask=result.failed_blocks.repeat(4,0).repeat(4,1)
                    synchronize();elapsed=time.perf_counter()-began
                    if mask.dtype!=bool or mask.shape!=(512,512):raise ValueError('invalid predicted mask')
                    if hashlib.sha256(y.tobytes()).hexdigest()!=received_hash:raise ValueError('reader mutated received RGB')
                    tp=int((truth&mask).sum());fp=int((~truth&mask).sum());fn=int((truth&~mask).sum());tn=int((~truth&~mask).sum())
                    maps[op['case']+'-'+('editguard' if method=='EditGuard clean' else 'signed4')]=np.packbits(mask)
                    row={'image_id':r['image_id'],'lesion_id':r['lesion_id'],'case':op['case'],'family':op['family'],'method':method,
                        'seed':2301+index,'parameters':op['parameters'],'received_rgb_sha256':received_hash,'changed_pixels':int(truth.sum()),
                        'confusion':{'tp':tp,'fp':fp,'fn':fn,'tn':tn},'pixel_iou':tp/(tp+fp+fn) if tp+fp+fn else None,
                        'extra_highlights':fp,'missed_pixels':fn,'complete_target_miss':bool(truth.any() and tp==0),
                        'predicted_image_positive':bool(mask.any()),'seconds':elapsed,'additional_sidecar_bytes':len(packet) if method!='EditGuard clean' else 0}
                    f.write(json.dumps(row)+'\n');count+=1
            np.savez_compressed(out/'artifacts'/f'{index:03d}-maps.npz',**maps)
            print('Matched EditGuard validation',index+1,'/',len(dataset),flush=True)
    summary={'completed':True,'images':len(dataset),'rows':count,'test_evaluated':False}
    if classifier is not None:
        summary['diagnostic_rows']=len(diagnostic_rows)
        impacts={}
        for case in dict.fromkeys(r['case'] for r in diagnostic_rows):
            rr=[r for r in diagnostic_rows if r['case']==case];labels=np.array([r['label'] for r in rr])
            impacts[case]={}
            for name,left,right in [('operator_without_embedding','original_probabilities','original_received_probabilities'),
                ('embedding_given_operator','original_received_probabilities','marked_received_probabilities'),
                ('total_embedding_plus_operator','original_probabilities','marked_received_probabilities')]:
                impacts[case][name]=analyse(labels,np.array([r[left] for r in rr]),np.array([r[right] for r in rr]),['nonMEL','MEL'],repetitions=repetitions)
        (out/'diagnostic-summary.json').write_text(json.dumps(impacts,indent=2))
    (out/'summary.json').write_text(json.dumps(summary,indent=2));return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for name in ('preparation','cohort','checkout','checkpoint','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--classifier-checkpoint',type=Path);p.add_argument('--classifier-sha256')
    p.add_argument('--device',choices=('cpu','cuda'),default='cuda');a=p.parse_args()
    import torch
    from src.editguard_adapter import EditGuard
    torch.set_num_threads(2)
    if a.device=='cuda' and not torch.cuda.is_available():raise ValueError('CUDA requested but unavailable')
    adapter=EditGuard(a.checkout,a.checkpoint,a.device)
    adapter.provenance['checkpoint_bytes']=a.checkpoint.stat().st_size
    model=identity=None
    if a.classifier_checkpoint is not None:
        if not a.classifier_sha256:raise ValueError('reviewed classifier hash required')
        from src.isic_classifier_training import load_frozen_densenet
        cohort_hash=hashlib.sha256(a.cohort.read_bytes()).hexdigest()
        model,identity=load_frozen_densenet(a.classifier_checkpoint,a.classifier_sha256,cohort_hash,a.device)
        cohort=json.loads(a.cohort.read_text())
        for split in ('train','validation'):
            if set(identity['protocol'][split+'_ids'])!={r['image_id'] for r in cohort['selected'] if r['split']==split}:raise ValueError('classifier membership differs')
    elif a.classifier_sha256:raise ValueError('classifier path required')
    run(adapter,a.preparation,a.cohort,a.out,synchronize=torch.cuda.synchronize if a.device=='cuda' else lambda:None,
        classifier=model,classifier_identity=identity)
