import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import zipfile
import numpy as np
import pytest
import torch
from torchvision.models import densenet121,DenseNet121_Weights
from src.diagnostic_impact import scores
from src.isic_classifier_training import MEAN,STD

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('return_review',ROOT/'scripts/review_isic_classifier_return.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def fixture_return(tmp_path,corrupt=False):
    selected=[{'image_id':f'{split}{i}','lesion_id':f'{split}lesion{i}','split':split,'melanoma_label':i} for split in ('train','validation','test') for i in (0,1)]
    cohort=json.dumps({'selected':selected}).encode();ch=hashlib.sha256(cohort).hexdigest()
    cohort_path=tmp_path/'cohort.json';cohort_path.write_bytes(cohort)
    bundle=io.BytesIO()
    with zipfile.ZipFile(bundle,'w') as z:z.writestr('cohort.json',cohort);z.writestr('scripts/fixture.py','pass')
    notebook=tmp_path/'sent.ipynb';notebook.write_text(json.dumps({'cells':[{'cell_type':'code','source':[f'import base64\nraw=base64.b64decode({base64.b64encode(bundle.getvalue()).decode()!r})']}]}))
    url=DenseNet121_Weights.IMAGENET1K_V1.url;prefix=Path(url).stem.rsplit('-',1)[-1]
    init={'compatible_state_dict_sha256':'a'*64,'source_url':url,'original_file_sha256':prefix+'0'*(64-len(prefix))}
    protocol={'cohort_sha256':ch,'train_ids':['train0','train1'],'validation_ids':['validation0','validation1'],
        'class_names':['nonMEL','MEL'],'mean':list(MEAN),'std':list(STD),'input_size':512,'epochs':20,'batch_size':8,'optimizer':'Adam','lr':1e-5,
        'exact_paper_reproduction':False,'augmentation':'none','cuda_amp':True,'train_only_class_weights':[1.,1.],
        'initialization':{'initial_weights_source':json.dumps(init),'initial_weights_sha256':'a'*64}}
    model=densenet121(weights=None);model.classifier=torch.nn.Linear(model.classifier.in_features,2)
    checkpoint_protocol={**protocol,'mean':tuple(MEAN),'std':tuple(STD)}
    buffer=io.BytesIO();torch.save({'state_dict':model.state_dict(),'protocol':checkpoint_protocol,'epoch':1},buffer);ck=buffer.getvalue()
    probs=[[.9,.1],[.2,.8]];labels=np.array([0,1]);metric=scores(labels,np.array(probs).argmax(1),2)
    history=[{'epoch':i,'mean_batch_weighted_training_loss':.5,'validation':metric} for i in range(1,21)]
    pred={'epoch':1,'image_ids':['validation0','validation1'],'labels':[0,1],'probabilities':[[.9,.9],[.2,.8]] if corrupt else probs}
    summary={'completed':True,'test_evaluated':False,'checkpoint_sha256':hashlib.sha256(ck).hexdigest(),'epochs':20,'selected_validation_balanced_accuracy':1.}
    archive=tmp_path/'return.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('best.pt',ck);z.writestr('cohort.json',cohort);z.writestr('code/scripts/fixture.py','pass')
        for name,obj in [('protocol.json',protocol),('selected-validation.json',pred),('summary.json',summary),('preparation.json',{'cohort_sha256':ch,'ready_for_training':True,'selected':selected}),('initialization.json',init)]:z.writestr(name,json.dumps(obj))
        z.writestr('history.jsonl','\n'.join(json.dumps(h) for h in history))
    return archive,cohort_path,notebook


def test_actual_receipt_review_safe_load_and_tie_selection(tmp_path):
    archive,cohort,notebook=fixture_return(tmp_path)
    result=r.review(archive,cohort,notebook,tmp_path/'out',repetitions=100)
    assert result['selected_epoch']==1
    assert result['validation']['balanced_accuracy']==1
    assert result['validation']['binary_roc_auc']==1
    assert result['always_nonMEL_reference']['balanced_accuracy']==.5
    assert result['always_nonMEL_reference']['per_class_sensitivity']==[1.,0.]
    assert result['validation_class_stratified_image_bootstrap95']['melanoma_sensitivity']==[1.,1.]


def test_corrupt_probabilities_block_acceptance(tmp_path):
    archive,cohort,notebook=fixture_return(tmp_path,True)
    with pytest.raises(ValueError,match='probabilities'):r.review(archive,cohort,notebook,tmp_path/'out',repetitions=100)
    assert not (tmp_path/'out').exists()


def test_decode_original_notebook_not_current_working_sources():
    sources=r.notebook_sources(ROOT/'deliverables/adapted_isic2500_classifier.ipynb')
    assert 'src/isic_classifier_training.py' in sources
    assert b'def initialise_densenet' in sources['src/isic_classifier_training.py']
