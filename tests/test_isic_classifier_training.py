import hashlib
import json
import numpy as np
from PIL import Image
import pytest
import torch
from src.isic_classifier_training import PreparedSplit,fit,initialise_densenet


def prepared(tmp_path):
    root=tmp_path/'prep';(root/'prepared').mkdir(parents=True)
    selected=[];records=[]
    for i,split in enumerate(('train','train','validation','validation','test')):
        r={'image_id':f'image{i}','lesion_id':f'lesion{i}','split':split,'melanoma_label':i%2}
        selected.append(r)
        x=np.full((512,512,3),i*40,np.uint8)
        # Deliberately omit test pixels: training must never need them.
        if split!='test':Image.fromarray(x).save(root/'prepared'/(r['image_id']+'.png'))
        records.append({**r,'prepared_rgb_sha256':hashlib.sha256(x.tobytes()).hexdigest()})
    cohort=tmp_path/'cohort.json';cohort.write_text(json.dumps({'selected':selected}))
    (root/'preparation.json').write_text(json.dumps({'ready_for_training':True,'cohort_sha256':hashlib.sha256(cohort.read_bytes()).hexdigest(),'selected':records}))
    return root,cohort


def test_actual_training_selection_and_no_test_access(tmp_path):
    p,c=prepared(tmp_path);train=PreparedSplit(p,c,'train');val=PreparedSplit(p,c,'validation')
    torch.manual_seed(4)
    model=torch.nn.Sequential(torch.nn.AdaptiveAvgPool2d(1),torch.nn.Flatten(),torch.nn.Linear(3,2))
    r=fit(model,train,val,tmp_path/'out',{'initial_weights_sha256':'fixture','initial_weights_source':'synthetic fixture, not ImageNet'},epochs=2,batch_size=2)
    assert r['completed'] and not r['test_evaluated']
    checkpoint=torch.load(tmp_path/'out/best.pt',weights_only=True)
    assert checkpoint['epoch'] in (1,2)
    assert len(checkpoint['protocol']['train_ids'])==2
    assert len(checkpoint['protocol']['validation_ids'])==2
    assert len((tmp_path/'out/history.jsonl').read_text().splitlines())==2
    with pytest.raises(ValueError,match='test access'):PreparedSplit(p,c,'test')


def test_rgb_mismatch_and_provenance_failure(tmp_path):
    p,c=prepared(tmp_path);train=PreparedSplit(p,c,'train');val=PreparedSplit(p,c,'validation')
    Image.new('RGB',(512,512),(1,1,1)).save(p/'prepared/image0.png')
    with pytest.raises(ValueError,match='RGB mismatch'):train[0]
    with pytest.raises(ValueError,match='provenance'):fit(torch.nn.Linear(3,2),train,val,tmp_path/'out',{})
    assert not (tmp_path/'out').exists()


def test_bad_initialization_hash_rejected(tmp_path):
    p=tmp_path/'bad.pt';p.write_bytes(b'not weights')
    with pytest.raises(ValueError,match='SHA256'):initialise_densenet(p,'0'*64)


def test_densenet_architecture_initialization_roundtrip(tmp_path):
    from torchvision.models import densenet121
    torch.manual_seed(11)
    original=densenet121(weights=None)
    path=tmp_path/'imagenet-shaped-fixture.pt'
    torch.save(original.state_dict(),path)
    loaded=initialise_densenet(path,hashlib.sha256(path.read_bytes()).hexdigest()).eval()
    assert loaded.classifier.out_features==2
    assert torch.equal(loaded.features.conv0.weight,original.features.conv0.weight)
    with torch.no_grad():assert loaded(torch.zeros(1,3,64,64)).shape==(1,2)


def test_time_budget_never_marks_partial_run_complete(tmp_path):
    p,c=prepared(tmp_path);train=PreparedSplit(p,c,'train');val=PreparedSplit(p,c,'validation')
    model=torch.nn.Sequential(torch.nn.AdaptiveAvgPool2d(1),torch.nn.Flatten(),torch.nn.Linear(3,2))
    with pytest.raises(TimeoutError):
        fit(model,train,val,tmp_path/'out',{'initial_weights_sha256':'fixture','initial_weights_source':'fixture'},epochs=2,batch_size=2,max_seconds=1e-12)
    assert not (tmp_path/'out/summary.json').exists()


def test_frozen_loader_hash_class_order_and_freeze(tmp_path):
    from torchvision.models import densenet121
    from src.isic_classifier_training import load_frozen_densenet,MEAN,STD
    model=densenet121(weights=None);model.classifier=torch.nn.Linear(model.classifier.in_features,2)
    path=tmp_path/'trained.pt'
    protocol={'cohort_sha256':'fixed','class_names':['nonMEL','MEL'],'mean':MEAN,'std':STD,'input_size':512,'train_ids':['a'],'validation_ids':['b']}
    torch.save({'state_dict':model.state_dict(),'protocol':protocol,'epoch':2},path)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    frozen,metadata=load_frozen_densenet(path,digest,'fixed')
    assert metadata['selected_epoch']==2 and not frozen.training
    assert all(not p.requires_grad for p in frozen.parameters())
    with pytest.raises(ValueError,match='SHA256'):load_frozen_densenet(path,'wrong','fixed')
    with pytest.raises(ValueError,match='cohort'):load_frozen_densenet(path,digest,'wrong')
