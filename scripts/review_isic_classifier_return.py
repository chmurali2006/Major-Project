"""Check completed classifier receipts against the exact notebook sent for training.

Never imports/executes returned code. Stored probabilities are not recomputed
without images; this review cannot establish clinical utility or source trust.
"""
import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from src.diagnostic_impact import analyse,binary_auc,scores
from src.isic_classifier_training import load_frozen_densenet,MEAN,STD


def required(value,message):
    if not value:raise ValueError(message)


def notebook_sources(path):
    """Decode a literal embedded bundle without eval/exec of notebook cells."""
    notebook=json.loads(Path(path).read_text())
    for cell in notebook['cells']:
        if cell['cell_type']!='code':continue
        tree=ast.parse(''.join(cell['source']))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='base64' and node.func.attr=='b64decode':
                raw=base64.b64decode(ast.literal_eval(node.args[0]),validate=True)
                with zipfile.ZipFile(io.BytesIO(raw)) as z:return {name:z.read(name) for name in z.namelist()}
    raise ValueError('No embedded source bundle in supplied training notebook')


def review(archive,cohort_path,training_notebook,out,*,expected_epochs=20,repetitions=2000):
    archive=Path(archive);out=Path(out);cohort_bytes=Path(cohort_path).read_bytes()
    cohort=json.loads(cohort_bytes);source=notebook_sources(training_notebook)
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();required(len(names)==len(set(names)) and z.testzip() is None,'duplicate/corrupt archive')
        required(z.read('cohort.json')==cohort_bytes==source['cohort.json'],'fixed cohort differs')
        expected={'protocol.json','history.jsonl','best.pt','selected-validation.json','summary.json','preparation.json','cohort.json','initialization.json'}|{'code/'+n for n in source if n.endswith('.py')}
        required(set(names)==expected,'incomplete or unexpected training return')
        for name,content in source.items():
            if name.endswith('.py'):required(z.read('code/'+name)==content,'code differs from sent notebook: '+name)
        obj=lambda name:json.loads(z.read(name))
        p=obj('protocol.json');summary=obj('summary.json');pred=obj('selected-validation.json');prep=obj('preparation.json');init=obj('initialization.json')
        history=[json.loads(line) for line in z.read('history.jsonl').splitlines()]
        digest=hashlib.sha256(z.read('best.pt')).hexdigest();ch=hashlib.sha256(cohort_bytes).hexdigest()
        required(summary.get('completed') is True and summary['test_evaluated'] is False and summary['checkpoint_sha256']==digest,'completion/checkpoint hash')
        required(p['cohort_sha256']==prep['cohort_sha256']==ch and prep['ready_for_training'] is True,'preparation state')
        required(len(prep['selected'])==len(cohort['selected']) and all(all(r.get(k)==v for k,v in e.items()) for r,e in zip(prep['selected'],cohort['selected'])),'preparation membership')
        by_split={s:[r for r in cohort['selected'] if r['split']==s] for s in ('train','validation','test')}
        for split in ('train','validation'):required(p[split+'_ids']==sorted(r['image_id'] for r in by_split[split]),'training/validation membership')
        required(not set(p['train_ids'])&set(p['validation_ids']),'image overlap')
        required(not {r['lesion_id'] for r in by_split['train']}&{r['lesion_id'] for r in by_split['validation']},'lesion overlap')
        required(p['class_names']==['nonMEL','MEL'] and tuple(p['mean'])==MEAN and tuple(p['std'])==STD and p['input_size']==512,'class order/preprocessing')
        required(p['epochs']==summary['epochs']==expected_epochs and p['batch_size']==8 and p['optimizer']=='Adam' and p['lr']==1e-5,'training protocol')
        required(p['exact_paper_reproduction'] is False and p['augmentation']=='none' and p['cuda_amp'] is True,'adapted GPU protocol')
        train_counts=np.bincount([r['melanoma_label'] for r in by_split['train']],minlength=2)
        required(np.allclose(p['train_only_class_weights'],len(by_split['train'])/(2*train_counts),rtol=1e-6),'class weights')
        required(init==json.loads(p['initialization']['initial_weights_source']),'initialization receipt')
        required(init['compatible_state_dict_sha256']==p['initialization']['initial_weights_sha256'],'initialization hash')
        from torchvision.models import DenseNet121_Weights
        url=DenseNet121_Weights.IMAGENET1K_V1.url
        required(init['source_url']==url and init['original_file_sha256'].startswith(Path(url).stem.rsplit('-',1)[-1]),'official initialization receipt')
        required([h['epoch'] for h in history]==list(range(1,expected_epochs+1)),'incomplete history')
        for h in history:
            required(np.isfinite(h['mean_batch_weighted_training_loss']) and h['mean_batch_weighted_training_loss']>=0,'invalid loss')
            value=h['validation']['balanced_accuracy'];required(value is not None and np.isfinite(value) and 0<=value<=1,'invalid selection score')
        best=max(h['validation']['balanced_accuracy'] for h in history)
        epoch=next(h['epoch'] for h in history if h['validation']['balanced_accuracy']==best)
        required(pred['epoch']==epoch and summary['selected_validation_balanced_accuracy']==best,'checkpoint selection differs')
        expected_ids=[r['image_id'] for r in by_split['validation']]
        labels=np.array([r['melanoma_label'] for r in by_split['validation']],dtype=int)
        required(pred['image_ids']==expected_ids and pred['labels']==labels.tolist(),'prediction identity/order')
        probs=np.array(pred['probabilities'],dtype=float)
        validation=analyse(labels,probs,probs,['nonMEL','MEL'],repetitions=repetitions)
        metric=scores(labels,probs.argmax(1),2)
        required(metric==history[epoch-1]['validation'],'selected metrics disagree with predictions')
        # Check checkpoint tensor shapes, epoch, protocol and freeze without executing returned source.
        with tempfile.TemporaryDirectory(prefix='classifier-review-') as directory:
            checkpoint=Path(directory)/'best.pt';checkpoint.write_bytes(z.read('best.pt'))
            model,identity=load_frozen_densenet(checkpoint,digest,ch)
            # torch preserves tuples whereas protocol.json encodes them as lists.
            # Compare canonical JSON, retaining every key and scalar value.
            required(json.dumps(identity['protocol'],sort_keys=True)==json.dumps(p,sort_keys=True) and identity['selected_epoch']==epoch,'checkpoint protocol/epoch')
            del model
        # Absolute descriptive intervals, conditional on observed true-class counts.
        rng=np.random.default_rng(6101);strata=[np.flatnonzero(labels==k) for k in (0,1)]
        samples={k:[] for k in ('balanced_accuracy','macro_f1','melanoma_sensitivity','binary_roc_auc')}
        for _ in range(repetitions):
            draw=np.concatenate([rng.choice(s,len(s),replace=True) for s in strata])
            m=scores(labels[draw],probs[draw].argmax(1),2)
            for k,value in [('balanced_accuracy',m['balanced_accuracy']),('macro_f1',m['macro_f1']),('melanoma_sensitivity',m['per_class_sensitivity'][1]),('binary_roc_auc',binary_auc(labels[draw],probs[draw,1]))]:samples[k].append(value)
        majority=scores(labels,np.zeros(len(labels),dtype=int),2)
        result={'schema':'adapted-classifier-return-review-v1','zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'checkpoint_sha256':digest,'cohort_sha256':ch,'selected_epoch':epoch,'validation':validation['clean'],
            'validation_class_stratified_image_bootstrap95':{k:np.quantile(v,[.025,.975]).tolist() for k,v in samples.items()},
            'bootstrap_repetitions':repetitions,'bootstrap_seed':6101,'always_nonMEL_reference':majority,
            'model_vs_always_nonMEL_balanced_accuracy':metric['balanced_accuracy']-majority['balanced_accuracy'],
            'review_findings':['Melanoma sensitivity is zero at frozen argmax threshold.'] if metric['per_class_sensitivity'][1]==0 else [],
            'limits':['Stored predictions checked arithmetically, not rerun on validation images here.',
            'Validation selected checkpoint; bootstrap intervals are descriptive and selection-biased, not final.',
            'Initialization hashes are returned receipts; original source bytes not independently rehashed here.',
            'No calibrated clinical confidence or diagnostic safety established. Checkpoint consistency is not clinical readiness.']}
        out.mkdir(parents=True,exist_ok=False)
        for name in ('protocol.json','history.jsonl','selected-validation.json','summary.json','initialization.json'):(out/name).write_bytes(z.read(name))
        (out/'review.json').write_text(json.dumps(result,indent=2)+'\n')
        return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('archive',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(review(args.archive,ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json',ROOT/'deliverables/adapted_isic2500_classifier.ipynb',args.out),indent=2))
