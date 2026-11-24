import pytest
from src.followup_protocol import check_protocol
from src.comparison_results_audit import CASES
from src.dataset_audit import CLASSES


def fixture():
    selected=[dict(image_id=f'{c}{i}',diagnosis=c,group=f'image:{c}{i}') for c in CLASSES for i in range(4)]
    c=dict(schema='followup32-config-v1',per_class=4,seed=73,threshold=.2,checkpoint='official clean',cases=list(CASES),labels_sha256='a'*64,metadata_sha256=None,prior_ids=['old'],group_field=None,allow_image_level=True)
    g=dict(schema='supplied-grouping-audit-v1',labels_sha256='a'*64,metadata_sha256=None,ready_fields=[])
    p=dict(complete=True,seed=73,per_class=4,labels_sha256='a'*64,metadata_sha256=None,excluded_ids=['old'],selected=selected,grouping='image only; patient/lesion dependence unknown')
    r=dict(complete=True,synthetic=False,input_preparation=p,samples=[{}]*32,threshold={'value':.2})
    return c,g,r


def test_valid_image_level_protocol():
    assert check_protocol(*fixture(),['old'])['declarations_consistent']


@pytest.mark.parametrize('attack',['labels','seed','count','prior','balance','group','threshold','missing_ack','metadata','cases'])
def test_protocol_drift_refused(attack):
    c,g,r=fixture();p=r['input_preparation']
    if attack=='labels':g['labels_sha256']='b'*64
    if attack=='seed':p['seed']=74
    if attack=='count':r['samples'].pop()
    if attack=='prior':c['prior_ids']=[]
    if attack=='balance':p['selected'][0]['diagnosis']='NV'
    if attack=='group':p['selected'][1]['group']=p['selected'][0]['group']
    if attack=='threshold':r['threshold']['value']=.4
    if attack=='missing_ack':c['allow_image_level']=False
    if attack=='metadata':c['group_field']='patient_id'
    if attack=='cases':c['cases']=[]
    with pytest.raises(ValueError):check_protocol(c,g,r,['old'])


def test_grouped_scope_requires_complete_audit():
    c,g,r=fixture();p=r['input_preparation']
    c['group_field']='lesion_id';g['ready_fields']=['lesion_id']
    for x in (c,g,p):x['metadata_sha256']='b'*64
    p['grouping']='lesion_id supplied by caller, not independently verified'
    for s in p['selected']:s['group']='lesion_id:'+s['image_id']
    result=check_protocol(c,g,r,['old'])
    assert 'lesion_id supplied' in result['scope']
