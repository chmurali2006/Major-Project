"""Connected attack/inference/impact evaluation for an externally frozen classifier.

Not connected to the running validation notebook. No model download/training or
checkpoint selection. Caller is responsible for independent training provenance.
"""
import hashlib
import numpy as np
import torch
from .adversarial_operators import attack
from .diagnostic_impact import analyse


def evaluate(model,rgb,labels,image_ids,class_names,settings,*,target_labels=None,repetitions=2000):
    x=np.asarray(rgb);y=np.asarray(labels)
    if len(image_ids)!=len(x) or len(set(image_ids))!=len(x) or not all(isinstance(i,str) and i for i in image_ids):
        raise ValueError('unique image IDs aligned to batch required')
    if settings.targeted and target_labels is None:raise ValueError('explicit target labels required')
    if not settings.targeted and target_labels is not None:raise ValueError('target labels forbidden for untargeted attack')
    if settings.targeted:
        targets=np.asarray(target_labels)
        if targets.shape!=y.shape or (targets==y).any():raise ValueError('target must differ from ground truth for every image')
    else:targets=y
    result=attack(model,x,targets,settings)
    device=next(iter({t.device for t in list(model.parameters())+list(model.buffers())}))
    mean=torch.tensor(settings.mean,device=device,dtype=torch.float32)[None,:,None,None]
    std=torch.tensor(settings.std,device=device,dtype=torch.float32)[None,:,None,None]
    def predict(batch):
        value=torch.tensor(batch.transpose(0,3,1,2).copy(),device=device,dtype=torch.float32)/255.
        with torch.no_grad():return model((value-mean)/std).softmax(1).cpu().numpy()
    clean=predict(x);received=predict(result['received'])
    impact=analyse(y,clean,received,class_names,repetitions=repetitions)
    before=clean.argmax(1);after=received.argmax(1);eligible=before==y
    success=(after==targets) if settings.targeted else (after!=y)
    rows=[]
    for i,ident in enumerate(image_ids):
        rows.append({'image_id':ident,'label':int(y[i]),'target_label':int(targets[i]) if settings.targeted else None,
            'clean_probabilities':clean[i].tolist(),'received_probabilities':received[i].tolist(),
            'clean_rgb_sha256':hashlib.sha256(x[i].tobytes()).hexdigest(),
            'received_rgb_sha256':hashlib.sha256(result['received'][i].tobytes()).hexdigest(),
            'changed_pixels':int(result['pixel_truth'][i].sum()),'linf_rgb':result['linf_rgb_per_image'][i],
            'clean_correct':bool(eligible[i]),'attack_success_on_quantized_output':bool(success[i])})
    return {'schema':'adapted-adversarial-evaluation-v1','settings':result['settings'],'rows':rows,'impact':impact,
        'attack_success':{'all_images_numerator':int(success.sum()),'all_images_denominator':len(x),
            'clean_correct_numerator':int((success&eligible).sum()),'clean_correct_denominator':int(eligible.sum()),
            'clean_correct_rate':float(success[eligible].mean()) if eligible.any() else None},
        'limits':['No checkpoint identity/provenance established by this function; must accompany result externally.',
        'Attack success is re-evaluated after uint8 quantization; not guaranteed by epsilon or gradient loss.',
        'No author checkpoint/objective equivalence or PFF-WM reproduction claim.']}
