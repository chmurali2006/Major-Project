import copy
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('impact_return',ROOT/'scripts/review_classifier_impact_return.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def fixture():
    selected=[{'image_id':'val0','melanoma_label':1,'prepared_rgb_sha256':'a'*64}]
    rows=[{'image_id':'val0','label':1,'case':c,'source_rgb_sha256':'a'*64,'received_rgb_sha256':'a'*64,
           'clean_probabilities':[.2,.8],'received_probabilities':[.2,.8],'changed_pixels':0,'linf_rgb':0} for c in r.CASES]
    return rows,selected


def test_complete_matrix():
    rows,selected=fixture();assert len(r.validate_rows(rows,selected))==12


@pytest.mark.parametrize('defect',['missing','duplicate','label','probability','intact','hash','bound','cross_case'])
def test_defective_receipts_rejected(defect):
    rows,selected=fixture()
    if defect=='missing':rows.pop()
    elif defect=='duplicate':rows.append(copy.deepcopy(rows[0]))
    elif defect=='label':rows[0]['label']=0
    elif defect=='probability':rows[0]['received_probabilities']=[float('nan'),.8]
    elif defect=='intact':rows[0]['received_probabilities']=[.3,.7]
    elif defect=='hash':rows[1]['received_rgb_sha256']='b'*64
    elif defect=='bound':rows[-1].update(linf_rgb=5,changed_pixels=1,received_rgb_sha256='b'*64)
    elif defect=='cross_case':rows[1]['clean_probabilities']=[.3,.7]
    with pytest.raises(ValueError):r.validate_rows(rows,selected)


def test_comparison_rejects_forged_metric_and_extra_keys():
    r.close({'metric':[.1,2,True,None]},{'metric':[.1,2,True,None]})
    with pytest.raises(ValueError):r.close({'metric':.8},{'metric':.7})
    with pytest.raises(ValueError):r.close({'metric':.7,'extra':1},{'metric':.7})
    with pytest.raises(ValueError):r.close({'metric':True},{'metric':1})


def test_synthetic_full_archive_review_and_source_tampering(tmp_path):
    import hashlib
    import json
    import zipfile
    import numpy as np
    from src.paper_aligned_operators import SETTINGS
    from src.isic_classifier_training import MEAN,STD
    from src.diagnostic_impact import analyse
    baseline=ROOT/'deliverables/verification-evidence/adapted-classifier-return-v1'
    training=json.loads((baseline/'review.json').read_text())
    cohort=(ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json').read_bytes()
    selected=json.loads(cohort)['selected']
    prep=[{**v,'prepared_rgb_sha256':hashlib.sha256(v['image_id'].encode()).hexdigest()} for v in selected]
    val=[v for v in prep if v['split']=='validation']
    rows=[]
    for index,v in enumerate(val):
        for case in r.CASES:
            rows.append({'image_id':v['image_id'],'label':v['melanoma_label'],'case':case,
                'source_rgb_sha256':v['prepared_rgb_sha256'],'received_rgb_sha256':v['prepared_rgb_sha256'],
                'clean_probabilities':[.6,.4],'received_probabilities':[.6,.4],
                'changed_pixels':0,'linf_rgb':0,'operator_seed':2301+index,'family':{'intact':'intact','copy32':'classic_tamper','local_blur32_surrogate':'classic_surrogate'}.get(case,'adapted_adversarial' if case.endswith('4_adapted') else 'paper_benign'),'parameters':{}})
    labels=np.array([v['melanoma_label'] for v in val]);probs=np.tile([.6,.4],(500,1))
    cases={}
    for case in r.CASES:
        m=analyse(labels,probs,probs,['nonMEL','MEL'],repetitions=100)
        if case.endswith('4_adapted'):
            m['untargeted_success']={'all_images_numerator':int(labels.sum()),'all_images_denominator':500,
                'clean_correct_numerator':0,'clean_correct_denominator':int((labels==0).sum()),'clean_correct_rate':0.}
        cases[case]=m
    protocol={'schema':'adapted-frozen-classifier-impact-v1','checkpoint':{
        'checkpoint_sha256':training['checkpoint_sha256'],'protocol':json.loads((baseline/'protocol.json').read_text()),
        'selected_epoch':training['selected_epoch']},'cohort_sha256':training['cohort_sha256'],'split':'validation','n':500,
        'classic_operators':SETTINGS,'mean':list(MEAN),'std':list(STD),'class_names':['nonMEL','MEL'],
        'exact_paper_reproduction':False,'attack_objective':'untargeted ground-truth CE ascent; clean start',
        'fgsm_epsilon_rgb':4,'pgd_epsilon_rgb':4,'pgd_steps':3,'pgd_step_rgb':1}
    bundle=r.notebook_sources(ROOT/'deliverables/adapted_classifier_impact.ipynb')
    archive=tmp_path/'synthetic.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('cohort.json',cohort)
        z.writestr('predictions.jsonl','\n'.join(json.dumps(v) for v in rows))
        for name,value in [('protocol.json',protocol),('preparation.json',{'selected':prep,'ready_for_training':True,'cohort_sha256':training['cohort_sha256']}),
            ('summary.json',{'completed':True,'images':500,'rows':6000,'test_evaluated':False,'cases':cases})]:z.writestr(name,json.dumps(value))
        for name,value in bundle.items():
            if name.endswith('.py'):z.writestr('code/'+name,value)
    result=r.review(archive,tmp_path/'out',repetitions=100)
    assert result['rows']==6000
    assert result['findings'] # synthetic probabilities differ from the actual training receipt
    bad=tmp_path/'bad.zip'
    with zipfile.ZipFile(archive) as src,zipfile.ZipFile(bad,'w') as dst:
        for name in src.namelist():dst.writestr(name,src.read(name)+b'\n# altered' if name.endswith('.py') else src.read(name))
    with pytest.raises(ValueError,match='source differs'):r.review(bad,tmp_path/'bad-out',repetitions=100)
    assert not (tmp_path/'bad-out').exists()
