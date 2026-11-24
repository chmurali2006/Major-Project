"""Select actual ISIC IDs for an explicitly adapted PFF-WM-size cohort.

One image/known lesion, deterministic SHA256 ranking, proportional8class allocation.
Not authors' IDs/split, patient-disjointness, image-file verification or final result.
"""
import argparse
import hashlib
import json
from collections import Counter,defaultdict
from pathlib import Path
from profile_isic_metadata import profile,prior_ids,CLASSES,ROOT


def allocate(counts,total):
    if type(total) is not int or total<0 or total>sum(counts.values()):raise ValueError('invalid requested size')
    n=sum(counts.values())
    if not n:return {k:0 for k in counts}
    quotas={k:total*v//n for k,v in counts.items()}
    for k in sorted(counts,key=lambda k:(-(total*counts[k]%n),k))[:total-sum(quotas.values())]:quotas[k]+=1
    return quotas


def select(report,seed=1301,size=2500):
    if type(size) is not int or size<5 or size%5:raise ValueError('size must be a positive multiple of5')
    if type(seed) is not int:raise ValueError('integer seed required')
    def rank(scope,value):return hashlib.sha256(f'isic-adapted-v1/{seed}/{scope}/{value}'.encode()).digest()
    groups=defaultdict(list)
    for r in report['candidates']:groups[r['lesion_id']].append(r)
    representatives=[]
    for lesion,rows in groups.items():
        if not lesion or len({r['diagnosis'] for r in rows})!=1:raise ValueError('valid consistently labelled lesions required')
        representatives.append(min(rows,key=lambda r:rank('representative',r['image_id'])))
    counts=Counter(r['diagnosis'] for r in representatives)
    total=allocate(counts,size);chosen={}
    for diagnosis in sorted(counts):
        chosen[diagnosis]=sorted((r for r in representatives if r['diagnosis']==diagnosis),key=lambda r:rank('selection',r['lesion_id']))[:total[diagnosis]]
    train=allocate(total,size*3//5)
    remaining={k:total[k]-train[k] for k in total};validation=allocate(remaining,size//5)
    selected=[]
    for diagnosis,rows in sorted(chosen.items()):
        rows=sorted(rows,key=lambda r:rank('split',r['lesion_id']))
        for i,row in enumerate(rows):
            split='train' if i<train[diagnosis] else 'validation' if i<train[diagnosis]+validation[diagnosis] else 'test'
            selected.append({**row,'split':split,'melanoma_label':int(diagnosis=='MEL')})
    selected.sort(key=lambda r:(r['split'],rank('output',r['image_id'])))
    assert len(selected)==size and len({r['lesion_id'] for r in selected})==size
    assert not ({r['image_id'] for r in selected}&set(report['previously_used_ids']))
    return {'schema':'adapted-isic2019-cohort-v1','seed':seed,'selection_rule':'one image per known lesion; proportional diagnosis allocation; SHA256 ranking',
        'paper':'doi:10.1016/j.iswa.2026.200684','exact_paper_reproduction':False,
        'metadata_input_hashes':report['inputs'],'excluded_previous_images':report['previously_used_images'],
        'split_counts':dict(Counter(r['split'] for r in selected)),
        'diagnosis_by_split':{split:dict(Counter(r['diagnosis'] for r in selected if r['split']==split)) for split in ('train','validation','test')},
        'selected':selected,'status':'selection_fixed_before_new_model_training_or_evaluation; source_pixels_not_verified',
        'limits':['Adapted2500image60/20/20 protocol, not the authors image selection or split.',
            'Known lesion disjoint only; patient independence cannot be established from these CSVs.',
            'Missing lesion IDs excluded; cannot exclude unknown relatives of prior-used missing-ID images.',
            'Class allocation follows eligible lesion counts, not a claimed paper-specified class balance.',
            'Melanoma-vs-rest label supplied, original8class diagnosis retained.',
            'No pixel/preprocessing match verified yet; no replacement if image absent.',
            'No classifier checkpoint, attack models, novelty, diagnostic safety or result implied.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--labels',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('new output required, never silently regenerate selection')
    result=select(profile(a.metadata,a.labels,prior_ids()))
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(result['split_counts']);print(json.dumps(result['diagnosis_by_split'],indent=2))
