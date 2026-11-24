"""Review the frozen validation-impact return without executing returned code.

Receipt/probability audit only: no independent image or attack replay implied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts.review_isic_classifier_return import notebook_sources
from src.diagnostic_impact import analyse

CASES=('intact','copy32','local_blur32_surrogate','jpeg70','jpeg85','jpeg95','resize90_restore','contrast90','contrast110','gaussian05','fgsm4_adapted','pgd4_adapted')


def require(value,message):
    if not value:raise ValueError(message)


def close(actual,expected,path='summary'):
    if isinstance(expected,dict):
        require(isinstance(actual,dict) and actual.keys()==expected.keys(),'keys differ: '+path)
        for k in expected:close(actual[k],expected[k],path+'/'+k)
    elif isinstance(expected,list):
        require(isinstance(actual,list) and len(actual)==len(expected),'list differs: '+path)
        for i,v in enumerate(expected):close(actual[i],v,path+'/'+str(i))
    elif isinstance(expected,float):
        require(isinstance(actual,(int,float)) and not isinstance(actual,bool) and np.isfinite(actual) and np.isclose(actual,expected,rtol=1e-9,atol=1e-10),'metric differs: '+path)
    else:require(type(actual)==type(expected) and actual==expected,'value differs: '+path)


def validate_rows(rows,selected):
    expected={r['image_id']:r for r in selected};indexed={}
    require(len(expected)==len(selected),'duplicate cohort ids')
    for r in rows:
        ident=r['image_id'];case=r['case'];key=(ident,case)
        require(ident in expected and case in CASES and key not in indexed,'unknown/duplicate image-case')
        if 'family' in r:
            family={'intact':'intact','copy32':'classic_tamper','local_blur32_surrogate':'classic_surrogate'}.get(case,'adapted_adversarial' if case.endswith('4_adapted') else 'paper_benign')
            require(r['family']==family,'operator family differs')
        require(type(r['label']) is int and r['label']==expected[ident]['melanoma_label'],'label differs')
        require(r['source_rgb_sha256']==expected[ident]['prepared_rgb_sha256'],'source hash differs')
        require(bool(re.fullmatch('[0-9a-f]{64}',r['received_rgb_sha256'])),'invalid received hash')
        for k in ('clean_probabilities','received_probabilities'):
            p=np.asarray(r[k],dtype=float)
            require(p.shape==(2,) and np.isfinite(p).all() and (p>=0).all() and (p<=1).all() and np.isclose(p.sum(),1,atol=1e-6,rtol=0),'invalid probabilities')
        require(type(r['changed_pixels']) is int and 0<=r['changed_pixels']<=512*512,'invalid changed count')
        require(type(r['linf_rgb']) is int and 0<=r['linf_rgb']<=255,'invalid Linf')
        require((r['changed_pixels']==0)==(r['linf_rgb']==0)==(r['source_rgb_sha256']==r['received_rgb_sha256']),'change/hash inconsistency')
        if case=='intact':
            require(r['changed_pixels']==0 and r['clean_probabilities']==r['received_probabilities'],'intact mismatch')
        if case.endswith('4_adapted'):require(r['linf_rgb']<=4,'attack exceeds bound')
        indexed[key]=r
    require(set(indexed)=={(i,c) for i in expected for c in CASES},'incomplete image-case matrix')
    for ident in expected:
        first=indexed[ident,'intact']['clean_probabilities']
        require(all(indexed[ident,c]['clean_probabilities']==first for c in CASES),'clean predictions differ across cases')
    return indexed


def review(archive,out,notebook=None,baseline_dir=None,repetitions=2000):
    notebook=notebook or ROOT/'deliverables/adapted_classifier_impact.ipynb'
    baseline_dir=Path(baseline_dir or ROOT/'deliverables/verification-evidence/adapted-classifier-return-v1')
    original=notebook_sources(notebook);training=json.loads((baseline_dir/'review.json').read_text())
    cohort_bytes=(ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json').read_bytes()
    archive=Path(archive);out=Path(out)
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();require(len(names)==len(set(names)) and z.testzip() is None,'duplicate/corrupt ZIP')
        expected={'protocol.json','predictions.jsonl','summary.json','cohort.json','preparation.json'}|{'code/'+n for n in original if n.endswith('.py')}
        require(set(names)==expected,'unexpected or incomplete archive')
        require(z.read('cohort.json')==cohort_bytes==original['cohort.json'],'cohort differs')
        for name,value in original.items():
            if name.endswith('.py'):require(z.read('code/'+name)==value,'sent source differs: '+name)
        obj=lambda n:json.loads(z.read(n))
        p=obj('protocol.json');summary=obj('summary.json');prep=obj('preparation.json')
        require(p['schema']=='adapted-frozen-classifier-impact-v1' and p['split']=='validation','wrong protocol/split')
        require(p['cohort_sha256']==training['cohort_sha256']==prep['cohort_sha256'],'cohort hash differs')
        require(p['checkpoint']['checkpoint_sha256']==training['checkpoint_sha256'],'checkpoint differs')
        close(p['checkpoint']['protocol'],json.loads((baseline_dir/'protocol.json').read_text()),'checkpoint/protocol')
        require(p['checkpoint']['selected_epoch']==training['selected_epoch'],'epoch differs')
        source=json.loads(cohort_bytes)['selected'];selected=[r for r in prep['selected'] if r['split']=='validation']
        require(prep['ready_for_training'] is True and len(prep['selected'])==len(source),'preparation incomplete')
        for r,e in zip(prep['selected'],source):require(all(r.get(k)==v for k,v in e.items()),'preparation membership differs')
        require(p['n']==len(selected)==500,'expected 500 validation images')
        from src.paper_aligned_operators import SETTINGS
        from src.isic_classifier_training import MEAN,STD
        close(p['classic_operators'],SETTINGS,'operator settings')
        close(p['mean'],list(MEAN),'mean');close(p['std'],list(STD),'std')
        require(p['class_names']==['nonMEL','MEL'] and p['exact_paper_reproduction'] is False,'class order/adapted status')
        require(p['attack_objective']=='untargeted ground-truth CE ascent; clean start','attack objective differs')
        require((p['fgsm_epsilon_rgb'],p['pgd_epsilon_rgb'],p['pgd_steps'],p['pgd_step_rgb'])==(4,4,3,1),'attack settings differ')
        rows=[json.loads(line) for line in z.read('predictions.jsonl').splitlines()]
        indexed=validate_rows(rows,selected);ids=[r['image_id'] for r in selected]
        for index,ident in enumerate(ids):
            require(all(indexed[ident,c]['operator_seed']==2301+index for c in CASES),'operator seed differs')
        labels=np.array([r['melanoma_label'] for r in selected]);a=np.array([indexed[i,'intact']['clean_probabilities'] for i in ids])
        cases={}
        for case in CASES:
            b=np.array([indexed[i,case]['received_probabilities'] for i in ids])
            m=analyse(labels,a,b,['nonMEL','MEL'],repetitions=repetitions)
            if case.endswith('4_adapted'):
                eligible=a.argmax(1)==labels;success=b.argmax(1)!=labels
                m['untargeted_success']={'all_images_numerator':int(success.sum()),'all_images_denominator':len(labels),
                    'clean_correct_numerator':int((eligible&success).sum()),'clean_correct_denominator':int(eligible.sum()),
                    'clean_correct_rate':float(success[eligible].mean()) if eligible.any() else None}
            cases[case]=m
        recomputed={'completed':True,'images':500,'rows':6000,'test_evaluated':False,'cases':cases}
        close(summary,recomputed)
        baseline=json.loads((baseline_dir/'selected-validation.json').read_text())
        old=dict(zip(baseline['image_ids'],baseline['probabilities']))
        shift=max(float(np.abs(a[j]-old[i]).max()) for j,i in enumerate(ids))
        report={'schema':'classifier-impact-return-review-v1','zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'sent_notebook_sha256':hashlib.sha256(Path(notebook).read_bytes()).hexdigest(),'checkpoint_sha256':training['checkpoint_sha256'],
            'images':500,'rows':6000,'cases':list(CASES),'max_clean_probability_difference_from_training_receipt':shift,
            'findings':[] if shift<=1e-5 else ['Clean probabilities differ from training return; investigate environment or source replay before interpretation.'],
            'limits':['No returned code executed; source identity and receipt arithmetic checked.',
                      'Images, operator outputs and attacks are not independently replayed here.',
                      'Validation selected checkpoint: all results are development evidence.',
                      'Original-image operator effects do not measure embedding-caused effects.',
                      'Source consistency is not independent trust, clinical safety or novelty.']}
        out.mkdir(parents=True,exist_ok=False)
        for name in ('protocol.json','summary.json'):(out/name).write_bytes(z.read(name))
        (out/'review.json').write_text(json.dumps(report,indent=2)+'\n')
        (out/'recomputed-summary.json').write_text(json.dumps(recomputed,indent=2)+'\n')
        return report

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('archive',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    print(json.dumps(review(a.archive,a.out),indent=2))
