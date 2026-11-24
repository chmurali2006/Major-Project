"""T1 adapted ISIC multi-architecture training, TRAIN/validation pixels only.

This is development evidence, not clinical validation. TEST images are excluded
from source-image discovery, preparation, training, and evaluation.
"""
from __future__ import annotations
import hashlib, json, random, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance
import torch
from torch.utils.data import Dataset, DataLoader

COHORT_SHA256='c524a43fce2951dbd68514a94d60610a8daa4f88fd40b8b93c53ee1f03f5aa42'
MEAN=(.485,.456,.406); STD=(.229,.224,.225)


def prepare_trainval(cohort_path,image_root,out,source_manifest_path):
    """Read only fixed TRAIN/validation IDs and verify source pixels against retained hashes."""
    cohort_path,image_root,out,source_manifest_path=Path(cohort_path),Path(image_root),Path(out),Path(source_manifest_path)
    manifest=json.loads(cohort_path.read_text())
    if manifest.get('source_cohort_sha256')!=COHORT_SHA256: raise ValueError('fixed source cohort identity mismatch')
    source_manifest=json.loads(source_manifest_path.read_text())
    if source_manifest.get('cohort_sha256')!=COHORT_SHA256 or source_manifest.get('schema')!='t1-trainval-source-hashes-v1':
        raise ValueError('TRAIN/validation source hash manifest mismatch')
    rows=manifest.get('selected',[]);source_rows=source_manifest.get('selected',[])
    if any(r.get('split') not in ('train','validation') for r in rows+source_rows): raise ValueError('T1 manifest contains a forbidden split')
    if [(r['image_id'],r['lesion_id'],r['diagnosis'],r['split'],r['melanoma_label']) for r in rows] != [(r['image_id'],r['lesion_id'],r['diagnosis'],r['split'],r['melanoma_label']) for r in source_rows]:
        raise ValueError('source hash manifest membership differs')
    source_by_id={r['image_id']:r for r in source_rows}
    if len(source_by_id)!=len(source_rows): raise ValueError('duplicate source hash row')
    counts={s:sum(r['split']==s for r in rows) for s in ('train','validation')}
    if len(rows)!=2000 or counts!={'train':1500,'validation':500}: raise ValueError('fixed TRAIN/validation membership mismatch')
    class_counts={s:[sum(r['split']==s and r['melanoma_label']==k for r in rows) for k in (0,1)] for s in ('train','validation')}
    if class_counts!={'train':[1330,170],'validation':[444,56]}: raise ValueError('fixed binary class counts mismatch')
    if {r['lesion_id'] for r in rows if r['split']=='train'} & {r['lesion_id'] for r in rows if r['split']=='validation'}:
        raise ValueError('lesion overlap in fixed train/validation')
    ids=[r['image_id'] for r in rows]
    if len(set(ids))!=len(ids): raise ValueError('duplicate TRAIN/validation ID')
    if out.exists(): raise ValueError('fresh output directory required')
    matches={ident:[] for ident in ids}
    for path in image_root.rglob('*'):
        if path.is_file() and path.suffix.lower() in ('.jpg','.jpeg','.png') and path.stem in matches: matches[path.stem].append(path)
    bad={k:len(v) for k,v in matches.items() if len(v)!=1}
    if bad: raise ValueError('missing/ambiguous TRAIN/validation source; no substitutions: '+str(bad))
    out.mkdir(parents=True);(out/'prepared').mkdir();prepared=[]
    for i,row in enumerate(rows):
        source=matches[row['image_id']][0];expected=source_by_id[row['image_id']]
        source_bytes=source.read_bytes()
        if hashlib.sha256(source_bytes).hexdigest()!=expected['source_file_sha256']:
            raise ValueError('source file hash mismatch: '+row['image_id'])
        with Image.open(source) as im:
            im.load();decoded=hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()
            if decoded!=expected['source_decoded_rgb_sha256']: raise ValueError('decoded source RGB mismatch: '+row['image_id'])
            rgb=im.convert('RGB').resize((512,512),Image.Resampling.BICUBIC)
        path=out/'prepared'/(row['image_id']+'.png');rgb.save(path);arr=np.asarray(rgb)
        pixel_hash=hashlib.sha256(arr.tobytes()).hexdigest()
        if pixel_hash!=expected['prepared_rgb_sha256']: raise ValueError('prepared RGB hash mismatch: '+row['image_id'])
        prepared.append({**row,'prepared_rgb_sha256':pixel_hash,
                         'source_file_sha256':expected['source_file_sha256'],
                         'source_decoded_rgb_sha256':decoded,
                         'prepared_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        if (i+1)%250==0: print('Prepared TRAIN/validation',i+1,'/ 2000',flush=True)
    receipt={'schema':'t1-trainval-preparation-v1','cohort_sha256':COHORT_SHA256,'split_counts':counts,
             'selected':prepared,'preprocessing':'RGB conversion; direct bicubic resize to 512x512',
             'test_pixels_opened':False}
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


class T1Dataset(Dataset):
    def __init__(self,preparation,split,augment=False):
        if split not in ('train','validation'): raise ValueError('T1 forbids TEST access')
        self.root=Path(preparation);prep=json.loads((self.root/'preparation.json').read_text())
        if prep.get('cohort_sha256')!=COHORT_SHA256 or prep.get('test_pixels_opened') is not False: raise ValueError('T1 preparation provenance mismatch')
        self.rows=[r for r in prep['selected'] if r['split']==split]
        if len(self.rows)!=(1500 if split=='train' else 500): raise ValueError('T1 split size mismatch')
        self.augment=bool(augment)
    def __len__(self): return len(self.rows)
    def __getitem__(self,index):
        r=self.rows[index]
        with Image.open(self.root/'prepared'/(r['image_id']+'.png')) as im: im.load();im=im.convert('RGB')
        arr=np.asarray(im)
        if arr.shape!=(512,512,3) or hashlib.sha256(arr.tobytes()).hexdigest()!=r['prepared_rgb_sha256']: raise ValueError('prepared pixel hash mismatch: '+r['image_id'])
        if self.augment:
            if random.random()<.5: im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if random.random()<.5: im=im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            im=im.rotate(90*random.randrange(4))
            im=ImageEnhance.Brightness(im).enhance(random.uniform(.9,1.1))
            im=ImageEnhance.Contrast(im).enhance(random.uniform(.9,1.1))
            im=ImageEnhance.Color(im).enhance(random.uniform(.9,1.1))
        x=np.asarray(im).astype(np.float32).transpose(2,0,1)/255.
        x=(x-np.asarray(MEAN,dtype=np.float32)[:,None,None])/np.asarray(STD,dtype=np.float32)[:,None,None]
        return torch.from_numpy(x.copy()),int(r['melanoma_label']),r['image_id']


def make_model(architecture,weights):
    from torchvision.models import densenet121,DenseNet121_Weights,resnet50,ResNet50_Weights
    if architecture=='densenet121_aug':
        if weights!='IMAGENET1K_V1': raise ValueError('DenseNet initialization must be V1')
        model=densenet121(weights=DenseNet121_Weights.IMAGENET1K_V1);model.classifier=torch.nn.Linear(model.classifier.in_features,2);head=model.classifier
    elif architecture=='resnet50_aug':
        if weights!='IMAGENET1K_V2': raise ValueError('ResNet initialization must be V2')
        model=resnet50(weights=ResNet50_Weights.IMAGENET1K_V2);model.fc=torch.nn.Linear(model.fc.in_features,2);head=model.fc
    else: raise ValueError('unsupported T1 architecture')
    head_ids={id(p) for p in head.parameters()};backbone=[p for p in model.parameters() if id(p) not in head_ids]
    return model,backbone,list(head.parameters())


def _weight_provenance(architecture):
    from torchvision.models import DenseNet121_Weights,ResNet50_Weights
    selected=DenseNet121_Weights.IMAGENET1K_V1 if architecture=='densenet121_aug' else ResNet50_Weights.IMAGENET1K_V2
    name=selected.url.rsplit('/',1)[-1]
    path=Path(torch.hub.get_dir())/'checkpoints'/name
    if not path.is_file(): raise ValueError('official torchvision initialization file missing from cache')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    expected=name.rsplit('-',1)[-1].split('.')[0]
    if not digest.startswith(expected): raise ValueError('torchvision initialization checksum prefix mismatch')
    return {'weights_enum':str(selected),'url':selected.url,'filename':name,'sha256':digest,
            'verification':'torchvision published filename SHA256 prefix'}


def _evaluate(model,loader,device):
    model.eval();ys=[];ps=[];ids=[]
    with torch.inference_mode():
        for x,y,ident in loader:
            p=model(x.to(device,non_blocking=True)).float().softmax(1).cpu().numpy()
            if p.shape!=(len(y),2) or not np.isfinite(p).all(): raise ValueError('invalid model predictions')
            ys.extend(y.numpy().tolist());ps.extend(p.tolist());ids.extend(ident)
    return np.asarray(ys,dtype=np.int64),np.asarray(ps,dtype=np.float64),ids


def fit_one(architecture,weights,preparation,out,*,device='cuda',seed=4101,epochs=20,batch_size=8,accumulation=2):
    if device!='cuda' or not torch.cuda.is_available(): raise RuntimeError('T1 training requires CUDA; no fallback')
    if (epochs,batch_size,accumulation)!=(20,8,2): raise ValueError('frozen T1 training schedule changed')
    from sklearn.metrics import balanced_accuracy_score,f1_score,roc_auc_score,confusion_matrix
    from torch.optim.lr_scheduler import CosineAnnealingLR
    out=Path(out)
    if out.exists(): raise ValueError('fresh output directory required')
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    train=T1Dataset(preparation,'train',True);val=T1Dataset(preparation,'validation')
    if {r['image_id'] for r in train.rows}&{r['image_id'] for r in val.rows}: raise ValueError('split overlap')
    if {r['lesion_id'] for r in train.rows}&{r['lesion_id'] for r in val.rows}: raise ValueError('lesion overlap')
    counts=np.bincount([r['melanoma_label'] for r in train.rows],minlength=2)
    if counts.tolist()!=[1330,170]: raise ValueError('unexpected TRAIN class counts')
    class_weights=torch.tensor([len(train)/(2*counts[0]),len(train)/(2*counts[1])],device=device,dtype=torch.float32)
    if not np.allclose(class_weights.cpu().numpy(),[.56391,4.41176],atol=.002): raise ValueError('TRAIN-only class weights mismatch')
    gen=torch.Generator().manual_seed(seed)
    tl=DataLoader(train,batch_size=batch_size,shuffle=True,generator=gen,num_workers=2,pin_memory=True)
    vl=DataLoader(val,batch_size=16,shuffle=False,num_workers=2,pin_memory=True)
    model,backbone,head=make_model(architecture,weights);model.to(device)
    initialization=_weight_provenance(architecture)
    opt=torch.optim.AdamW([{'params':backbone,'lr':1e-4},{'params':head,'lr':3e-4}],weight_decay=1e-4)
    sched=CosineAnnealingLR(opt,T_max=epochs);loss_fn=torch.nn.CrossEntropyLoss(weight=class_weights)
    scaler=torch.cuda.amp.GradScaler(enabled=True);out.mkdir(parents=True)
    protocol={'schema':'t1-multi-architecture-v1','architecture':architecture,'initial_weights':weights,'initialization_provenance':initialization,
        'cohort_sha256':COHORT_SHA256,'train_n':1500,'validation_n':500,'test_accessed':False,
        'input_size':512,'mean':MEAN,'std':STD,
        'augmentation':'horizontal/vertical flips p=.5, random quarter-turn, brightness/contrast/saturation .9-1.1; no JPEG, blur, or rescale',
        'loss':'weighted cross entropy; TRAIN-only inverse-frequency weights','class_weights':class_weights.cpu().tolist(),
        'optimizer':'AdamW','backbone_lr':1e-4,'head_lr':3e-4,'weight_decay':1e-4,
        'scheduler':'CosineAnnealingLR','epochs':epochs,'batch_size':batch_size,'gradient_accumulation':accumulation,
        'seed':seed,'selection':'highest validation balanced accuracy, earliest tie','class_names':['nonMEL','MEL']}
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    best=-1.;history=[];began=time.monotonic()
    for epoch in range(1,epochs+1):
        model.train();opt.zero_grad(set_to_none=True);loss_sum=0.;seen=0
        for step,(x,y,_) in enumerate(tl):
            x=x.to(device,non_blocking=True);y=y.to(device,non_blocking=True)
            with torch.autocast('cuda',dtype=torch.float16): loss=loss_fn(model(x),y)/accumulation
            if not torch.isfinite(loss): raise ValueError('nonfinite training loss')
            scaler.scale(loss).backward()
            if (step+1)%accumulation==0 or step+1==len(tl): scaler.step(opt);scaler.update();opt.zero_grad(set_to_none=True)
            loss_sum+=float(loss.detach())*accumulation*len(y);seen+=len(y)
        y,p,ids=_evaluate(model,vl,device);ba=float(balanced_accuracy_score(y,p.argmax(1)))
        row={'epoch':epoch,'mean_loss':loss_sum/seen,'validation_balanced_accuracy':ba,'elapsed_seconds':time.monotonic()-began}
        history.append(row);print(architecture,'epoch',epoch,'val_BA',ba,flush=True);sched.step()
        if ba>best:
            best=ba;torch.save({'state_dict':model.state_dict(),'epoch':epoch,'protocol':protocol},out/'best.pt')
            with (out/'selected-validation.jsonl').open('w') as f:
                for j,(label,prob) in enumerate(zip(y,p)): f.write(json.dumps({'image_id':ids[j],'label':int(label),'probabilities':prob.tolist()})+'\n')
    (out/'history.json').write_text(json.dumps(history,indent=2)+'\n')
    ck=torch.load(out/'best.pt',map_location='cpu',weights_only=True);model.load_state_dict(ck['state_dict']);model.to(device)
    y,p,ids=_evaluate(model,vl,device);pred=p.argmax(1)
    neg=np.sort(p[y==0,1]);threshold=float(neg[min(len(neg)-1,int(np.ceil(.90*len(neg))))])
    specificity90=float(np.mean(p[y==0,1]<threshold));sensitivity90=float(np.mean(p[y==1,1]>=threshold))
    summary={'completed':True,'architecture':architecture,'selected_epoch':ck['epoch'],
        'selected_validation_balanced_accuracy':float(balanced_accuracy_score(y,pred)),
        'accuracy':float((pred==y).mean()),'mel_sensitivity':float((pred[y==1]==1).mean()),
        'specificity':float((pred[y==0]==0).mean()),'macro_f1':float(f1_score(y,pred,average='macro')),
        'roc_auc':float(roc_auc_score(y,p[:,1])),'fixed_target_specificity_90':{'threshold':threshold,
        'achieved_specificity':specificity90,'mel_sensitivity':sensitivity90,'threshold_selection_split':'validation'},
        'confusion_matrix':confusion_matrix(y,pred).tolist(),
        'test_accessed':False,'checkpoint_sha256':hashlib.sha256((out/'best.pt').read_bytes()).hexdigest()}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary


def _predict(model,x,device,mean,std):
    t=torch.from_numpy(x.transpose(2,0,1).copy()).to(device=device,dtype=torch.float32)[None]/255.
    with torch.inference_mode():p=model((t-mean)/std).softmax(1).cpu().numpy()[0]
    if p.shape!=(2,) or not np.isfinite(p).all(): raise ValueError('invalid probabilities')
    return p.tolist()


def evaluate_standard(model,preparation,out,architecture,*,device='cuda',repetitions=2000):
    from src.paper_aligned_operators import operators,SETTINGS
    from src.diagnostic_impact import analyse
    model.eval();root=Path(preparation);prep=json.loads((root/'preparation.json').read_text())
    rows=[r for r in prep['selected'] if r['split']=='validation']
    if len(rows)!=500: raise ValueError('exact 500 validation rows required')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);grouped={};labels=[]
    mean=torch.tensor(MEAN,device=device)[None,:,None,None];std=torch.tensor(STD,device=device)[None,:,None,None]
    with (out/'predictions.jsonl').open('w',buffering=1) as f:
        for i,r in enumerate(rows):
            with Image.open(root/'prepared'/(r['image_id']+'.png')) as im:x=np.asarray(im.convert('RGB'))
            if hashlib.sha256(x.tobytes()).hexdigest()!=r['prepared_rgb_sha256']: raise ValueError('source changed after preflight')
            labels.append(int(r['melanoma_label']))
            for op in operators(x,2301+i):
                prob=_predict(model,op['received'],device,mean,std);grouped.setdefault(op['case'],[]).append(prob)
                f.write(json.dumps({'image_id':r['image_id'],'label':int(r['melanoma_label']),'architecture':architecture,
                    'case':op['case'],'family':op['family'],'seed':2301+i,'parameters':op['parameters'],
                    'probabilities':prob,'source_rgb_sha256':r['prepared_rgb_sha256'],
                    'received_rgb_sha256':hashlib.sha256(op['received'].tobytes()).hexdigest()})+'\n')
            if (i+1)%50==0: print(architecture,'original operators',i+1,'/ 500',flush=True)
    y=np.asarray(labels,dtype=np.int64);intact=np.asarray(grouped['intact'],dtype=np.float64)
    metrics={case:analyse(y,intact,np.asarray(prob),['nonMEL','MEL'],repetitions=repetitions,seed=4101) for case,prob in grouped.items()}
    summary={'completed':True,'architecture':architecture,'images':len(y),'cases':metrics,'operators':SETTINGS,'split':'validation','cohort_sha256':COHORT_SHA256,'test_accessed':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary


def build_editguard_marked_cache(adapter,preparation,cache_dir):
    """Create each marked validation image once for reuse across both classifiers."""
    root=Path(preparation);prep=json.loads((root/'preparation.json').read_text())
    rows=[r for r in prep['selected'] if r['split']=='validation']
    if len(rows)!=500: raise ValueError('exact 500 validation rows required')
    cache=Path(cache_dir)
    if cache.exists(): raise ValueError('fresh EditGuard cache path required')
    (cache/'marked').mkdir(parents=True);manifest=[]
    from skimage.metrics import structural_similarity
    for i,r in enumerate(rows):
        with Image.open(root/'prepared'/(r['image_id']+'.png')) as im:x=np.asarray(im.convert('RGB'))
        if hashlib.sha256(x.tobytes()).hexdigest()!=r['prepared_rgb_sha256']: raise ValueError('validation pixels changed')
        marked=adapter.embed(x.copy(),seed=7301+i)
        if marked.dtype!=np.uint8 or marked.shape!=x.shape: raise ValueError('invalid EditGuard marked image')
        path=cache/'marked'/(r['image_id']+'.png');Image.fromarray(marked).save(path)
        mse=float(np.mean((marked.astype(np.float64)-x.astype(np.float64))**2))
        manifest.append({'image_id':r['image_id'],'source_rgb_sha256':r['prepared_rgb_sha256'],
            'marked_rgb_sha256':hashlib.sha256(marked.tobytes()).hexdigest(),'mse':mse,
            'psnr_db':float(10*np.log10(255**2/mse)) if mse>0 else None,
            'ssim':float(structural_similarity(x,marked,channel_axis=2,data_range=255))})
        if (i+1)%25==0: print('EditGuard embed',i+1,'/ 500',flush=True)
    (cache/'cache.json').write_text(json.dumps({'schema':'t1-editguard-marked-cache-v1','images':manifest,
        'checkpoint_sha256':adapter.provenance['checkpoint_sha256'],'cohort_sha256':COHORT_SHA256},indent=2)+'\n')
    return cache


def evaluate_editguard_pairs(model,preparation,marked_cache,out,architecture,*,device='cuda',repetitions=2000):
    from src.paper_aligned_operators import operators,SETTINGS
    from src.diagnostic_impact import analyse
    model.eval();root=Path(preparation);prep=json.loads((root/'preparation.json').read_text())
    rows=[r for r in prep['selected'] if r['split']=='validation'];cache=Path(marked_cache)
    cm=json.loads((cache/'cache.json').read_text())
    if len(rows)!=500 or len(cm['images'])!=500 or cm['cohort_sha256']!=COHORT_SHA256: raise ValueError('EditGuard cache mismatch')
    cache_rows={r['image_id']:r for r in cm['images']};cases=('intact','copy32','jpeg70','jpeg85','gaussian05')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);mean=torch.tensor(MEAN,device=device)[None,:,None,None];std=torch.tensor(STD,device=device)[None,:,None,None]
    records=[]
    with (out/'paired-predictions.jsonl').open('w',buffering=1) as f:
        for i,r in enumerate(rows):
            with Image.open(root/'prepared'/(r['image_id']+'.png')) as im:x=np.asarray(im.convert('RGB'))
            with Image.open(cache/'marked'/(r['image_id']+'.png')) as im:marked=np.asarray(im.convert('RGB'))
            cr=cache_rows[r['image_id']]
            if hashlib.sha256(x.tobytes()).hexdigest()!=r['prepared_rgb_sha256'] or hashlib.sha256(marked.tobytes()).hexdigest()!=cr['marked_rgb_sha256']: raise ValueError('cache source/mark hash mismatch')
            seed=2301+i;oo={q['case']:q for q in operators(x,seed)};mo={q['case']:q for q in operators(marked,seed)}
            row={'image_id':r['image_id'],'label':int(r['melanoma_label']),'architecture':architecture,
                 'source_rgb_sha256':r['prepared_rgb_sha256'],'marked_rgb_sha256':cr['marked_rgb_sha256'],
                 'original_probabilities':_predict(model,x,device,mean,std),
                 'marked_probabilities':_predict(model,marked,device,mean,std),'cases':{}}
            for case in cases:
                if oo[case]['parameters']!=mo[case]['parameters']: raise AssertionError('paired operator settings mismatch')
                row['cases'][case]={'original_received_probabilities':_predict(model,oo[case]['received'],device,mean,std),
                    'marked_received_probabilities':_predict(model,mo[case]['received'],device,mean,std),
                    'parameters':oo[case]['parameters']}
            f.write(json.dumps(row)+'\n');records.append(row)
            if (i+1)%50==0: print(architecture,'EditGuard pairs',i+1,'/ 500',flush=True)
    labels=np.asarray([r['label'] for r in records],dtype=np.int64)
    original=np.asarray([r['original_probabilities'] for r in records]);marked=np.asarray([r['marked_probabilities'] for r in records])
    summary={'schema':'t1-editguard-paired-v1','architecture':architecture,'images':len(rows),
        'marking_fidelity':{'n':len(cm['images']),'mean_mse':float(np.mean([r['mse'] for r in cm['images']])),
          'mean_per_image_psnr_db':float(np.mean([r['psnr_db'] for r in cm['images'] if r['psnr_db'] is not None])),
          'mean_ssim':float(np.mean([r['ssim'] for r in cm['images']]))},
        'cases':{},'split':'validation','cohort_sha256':COHORT_SHA256,'test_accessed':False,'editguard_checkpoint_sha256':cm['checkpoint_sha256'],
        'operator_settings':SETTINGS}
    summary['marked_intact_vs_original_intact']=analyse(labels,original,marked,['nonMEL','MEL'],repetitions=repetitions,seed=4101)
    for case in cases:
        a=np.asarray([r['cases'][case]['original_received_probabilities'] for r in records]);b=np.asarray([r['cases'][case]['marked_received_probabilities'] for r in records])
        summary['cases'][case]={'operator_without_embedding':analyse(labels,original,a,['nonMEL','MEL'],repetitions=repetitions,seed=4101),
            'embedding_given_operator':analyse(labels,a,b,['nonMEL','MEL'],repetitions=repetitions,seed=4101),
            'total_embedding_plus_operator':analyse(labels,original,b,['nonMEL','MEL'],repetitions=repetitions,seed=4101)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary


def load_baseline_densenet(checkpoint,trainval_manifest,device='cuda'):
    """Load retained Model-0 checkpoint only when its recorded identity matches."""
    from torchvision.models import densenet121
    path=Path(checkpoint)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    expected='38d52ca825472cb525c4c2745f9f7e2e047ddcbc34a6fe6cdcbfbdc0786ba57e'
    if digest!=expected: raise ValueError('historical Model-0 checkpoint hash mismatch')
    ck=torch.load(path,map_location='cpu',weights_only=True)
    protocol=ck.get('protocol',{})
    if (protocol.get('cohort_sha256')!=COHORT_SHA256 or protocol.get('class_names')!=['nonMEL','MEL']
        or protocol.get('input_size')!=512 or tuple(protocol.get('mean',()))!=MEAN or tuple(protocol.get('std',()))!=STD):
        raise ValueError('Model-0 training protocol/cohort/preprocessing mismatch')
    manifest=json.loads(Path(trainval_manifest).read_text())
    train_ids={r['image_id'] for r in manifest['selected'] if r['split']=='train'}
    val_ids={r['image_id'] for r in manifest['selected'] if r['split']=='validation'}
    if set(protocol.get('train_ids',[]))!=train_ids or set(protocol.get('validation_ids',[]))!=val_ids:
        raise ValueError('Model-0 membership differs from fixed manifest')
    model=densenet121(weights=None)
    model.classifier=torch.nn.Linear(model.classifier.in_features,2)
    model.load_state_dict(ck['state_dict'],strict=True);model.to(device).eval()
    for parameter in model.parameters():parameter.requires_grad_(False)
    return model,{'checkpoint_sha256':digest,'selected_epoch':ck['epoch'],'protocol':protocol}
