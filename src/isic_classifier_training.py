"""Adapted binary ISIC classifier; not the paper's CheXpert-initialized model.

No test split access. Validation selects checkpoint by balanced accuracy; fixed
argmax threshold. Checkpoint selection makes validation metrics developmental.
ImageNet initialization must be supplied locally with explicit SHA256/provenance.
"""
import hashlib
import json
from pathlib import Path
import random
import time
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset,DataLoader
from .diagnostic_impact import scores
from .persistence import atomic_write

MEAN=(.485,.456,.406)
STD=(.229,.224,.225)


class PreparedSplit(Dataset):
    def __init__(self,preparation,cohort,split):
        if split not in ('train','validation'):raise ValueError('test access forbidden in training')
        self.root=Path(preparation);cohort=Path(cohort)
        p=json.loads((self.root/'preparation.json').read_text());c=json.loads(cohort.read_text())
        if p.get('ready_for_training') is not True or p['cohort_sha256']!=hashlib.sha256(cohort.read_bytes()).hexdigest():
            raise ValueError('fixed prepared cohort required')
        if len(p['selected'])!=len(c['selected']) or any(any(r.get(k)!=v for k,v in e.items()) for r,e in zip(p['selected'],c['selected'])):
            raise ValueError('cohort identity mismatch')
        self.rows=[r for r in p['selected'] if r['split']==split]
        if not self.rows or set(r['melanoma_label'] for r in self.rows)!={0,1}:raise ValueError('both binary classes required in split')
        self.cohort_sha256=p['cohort_sha256']
    def __len__(self):return len(self.rows)
    def __getitem__(self,index):
        r=self.rows[index]
        with Image.open(self.root/'prepared'/(r['image_id']+'.png')) as im:x=np.array(im.convert('RGB'))
        if x.shape!=(512,512,3) or hashlib.sha256(x.tobytes()).hexdigest()!=r['prepared_rgb_sha256']:
            raise ValueError('prepared RGB mismatch: '+r['image_id'])
        value=torch.from_numpy(x.transpose(2,0,1).copy()).float()/255.
        value=(value-torch.tensor(MEAN)[:,None,None])/torch.tensor(STD)[:,None,None]
        return value,int(r['melanoma_label']),r['image_id']


def initialise_densenet(weights,expected_sha256):
    """Accept torchvision DenseNet121 1000-class state dict only, no pickle objects."""
    from torchvision.models import densenet121
    path=Path(weights)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=expected_sha256:raise ValueError('initial weights SHA256 mismatch')
    model=densenet121(weights=None)
    state=torch.load(path,map_location='cpu',weights_only=True)
    model.load_state_dict(state,strict=True)
    model.classifier=torch.nn.Linear(model.classifier.in_features,2)
    return model


def fit(model,train,validation,out,provenance,*,epochs=20,batch_size=8,device='cpu',seed=4101,max_seconds=21600):
    if type(epochs) is not int or epochs<1 or type(batch_size) is not int or batch_size<1:raise ValueError('positive epochs/batch size required')
    if not provenance.get('initial_weights_sha256') or not provenance.get('initial_weights_source'):
        raise ValueError('explicit initialization provenance required')
    train_ids={r['image_id'] for r in train.rows};val_ids={r['image_id'] for r in validation.rows}
    if train_ids&val_ids:raise ValueError('train validation image overlap')
    if {r['lesion_id'] for r in train.rows}&{r['lesion_id'] for r in validation.rows}:raise ValueError('train validation lesion overlap')
    if train.cohort_sha256!=validation.cohort_sha256:raise ValueError('different cohorts')
    if not np.isfinite(max_seconds) or max_seconds<=0:raise ValueError('positive finite time budget required')
    began=time.monotonic()
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.deterministic=True
    generator=torch.Generator().manual_seed(seed)
    tl=DataLoader(train,batch_size=batch_size,shuffle=True,generator=generator,num_workers=0)
    vl=DataLoader(validation,batch_size=batch_size,shuffle=False,num_workers=0)
    model=model.to(device)
    for p in model.parameters():p.requires_grad_(True)
    optimizer=torch.optim.Adam(model.parameters(),lr=1e-5)
    amp=str(device).startswith('cuda')
    scaler=torch.cuda.amp.GradScaler(enabled=amp)
    counts=np.bincount([r['melanoma_label'] for r in train.rows],minlength=2)
    if (counts==0).any():raise ValueError('both training classes required')
    # Explicit adaptation to binary imbalance, not a recovered author setting.
    weight=torch.tensor(len(train)/(2*counts),dtype=torch.float32,device=device)
    loss_fn=torch.nn.CrossEntropyLoss(weight=weight)
    protocol={'schema':'adapted-isic-classifier-training-v1','initialization':provenance,'cohort_sha256':train.cohort_sha256,
        'class_names':['nonMEL','MEL'],'mean':MEAN,'std':STD,'input_size':512,'epochs':epochs,'batch_size':batch_size,
        'optimizer':'Adam','lr':1e-5,'cuda_amp':amp,'max_seconds':max_seconds,'train_only_class_weights':weight.cpu().tolist(),'seed':seed,
        'selection':'highest validation balanced accuracy; earliest epoch breaks ties','threshold':'argmax, no tuning',
        'augmentation':'none','train_ids':sorted(train_ids),'validation_ids':sorted(val_ids),
        'torch':str(torch.__version__),'device':str(device),'exact_paper_reproduction':False,
        'limits':['ImageNet rather than verified CheXpert initialization; binary classifier is an adapted baseline.',
        'Validation selects weights; not an independent clinical evaluation. No test images accessed.',
        'Known lesion disjointness does not establish patient independence.',
        'Backend deterministic flags do not guarantee cross-device/version bitwise reproducibility.']}
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2))
    best=-1.;history=[]
    with (out/'history.jsonl').open('w',buffering=1) as log:
        for epoch in range(1,epochs+1):
            model.train();total=0.;seen=0
            for x,y,_ in tl:
                if time.monotonic()-began>max_seconds:raise TimeoutError('Training budget exceeded; retain partial output, do not treat as completed')
                x=x.to(device);y=y.to(device);optimizer.zero_grad(set_to_none=True)
                with torch.cuda.amp.autocast(enabled=amp):loss=loss_fn(model(x),y)
                if not torch.isfinite(loss):raise ValueError('nonfinite training loss')
                scaler.scale(loss).backward();scaler.step(optimizer);scaler.update();total+=float(loss.detach())*len(y);seen+=len(y)
            model.eval();labels=[];prob=[];ids=[]
            with torch.no_grad():
                for x,y,ident in vl:
                    if time.monotonic()-began>max_seconds:raise TimeoutError('Validation budget exceeded; retain partial output')
                    p=model(x.to(device)).softmax(1).cpu().numpy()
                    if not np.isfinite(p).all():raise ValueError('nonfinite validation probability')
                    labels.extend(y.tolist());prob.extend(p.tolist());ids.extend(ident)
            metric=scores(np.array(labels),np.array(prob).argmax(1),2)
            if metric['balanced_accuracy'] is None:raise ValueError('both validation classes required')
            row={'epoch':epoch,'mean_batch_weighted_training_loss':total/seen,'validation':metric,'elapsed_seconds':time.monotonic()-began}
            history.append(row);log.write(json.dumps(row)+'\n')
            if metric['balanced_accuracy']>best:
                best=metric['balanced_accuracy']
                atomic_write(out/'best.pt',lambda f:torch.save({'state_dict':model.state_dict(),'epoch':epoch,'protocol':protocol},f))
                (out/'selected-validation.json').write_text(json.dumps({'epoch':epoch,'image_ids':ids,'labels':labels,'probabilities':prob}))
            print('Classifier epoch',epoch,'validation balanced accuracy',metric['balanced_accuracy'],flush=True)
    checkpoint=out/'best.pt'
    summary={'completed':True,'selected_validation_balanced_accuracy':best,'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        'epochs':epochs,'test_evaluated':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));return summary


def load_frozen_densenet(checkpoint,expected_sha256,expected_cohort_sha256,device='cpu'):
    """Reconstruct binary architecture using safe tensor loading and explicit hashes.

    Caller must first review run completion/provenance and select this checksum.
    Matching a self-supplied checksum does not establish trusted clinical provenance.
    """
    from torchvision.models import densenet121
    path=Path(checkpoint)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha256:raise ValueError('trained checkpoint SHA256 mismatch')
    ck=torch.load(path,map_location='cpu',weights_only=True);protocol=ck['protocol']
    if protocol['cohort_sha256']!=expected_cohort_sha256:raise ValueError('trained cohort differs')
    if protocol['class_names']!=['nonMEL','MEL'] or tuple(protocol['mean'])!=MEAN or tuple(protocol['std'])!=STD or protocol['input_size']!=512:
        raise ValueError('classifier class order/preprocessing differs')
    if set(protocol['train_ids'])&set(protocol['validation_ids']):raise ValueError('checkpoint split overlap')
    model=densenet121(weights=None);model.classifier=torch.nn.Linear(model.classifier.in_features,2)
    model.load_state_dict(ck['state_dict'],strict=True);model.to(device).eval()
    for parameter in model.parameters():parameter.requires_grad_(False)
    return model,{'checkpoint_sha256':expected_sha256,'selected_epoch':ck['epoch'],'protocol':protocol}
