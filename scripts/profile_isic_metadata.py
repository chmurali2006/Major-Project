"""Join uploaded ISIC CSVs and quantify grouping/exclusions; never invent a paper split."""
import argparse
import csv
import hashlib
import json
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CLASSES=('MEL','NV','BCC','AK','BKL','DF','VASC','SCC')


def read(path,required):
    with Path(path).open(newline='',encoding='utf-8-sig') as stream:
        reader=csv.DictReader(stream)
        if not set(required)<=set(reader.fieldnames or []):raise ValueError('required columns missing')
        rows=list(reader)
    ids=[r['image'] for r in rows]
    if not rows or any(not x for x in ids) or len(set(ids))!=len(ids):raise ValueError('unique nonempty image IDs required')
    return {r['image']:r for r in rows}


def profile(metadata,labels,used):
    meta=read(metadata,('image','lesion_id'));truth=read(labels,('image',*CLASSES))
    if set(meta)!=set(truth):raise ValueError('metadata/label IDs differ')
    diagnoses={}
    for ident,row in truth.items():
        values=[float(row[k]) for k in CLASSES]
        if any(v not in (0.,1.) for v in values) or sum(values)!=1:raise ValueError('exactly one supported class required')
        if float(row.get('UNK','0'))!=0:raise ValueError('unexpected unknown label')
        diagnoses[ident]=CLASSES[values.index(1.)]
    used=set(used)
    unknown=used-set(meta)
    if unknown:raise ValueError('previously used IDs absent from uploaded metadata: '+str(sorted(unknown)))
    used_lesions={meta[i]['lesion_id'].strip() for i in used if meta[i]['lesion_id'].strip()}
    reasons={};groups=defaultdict(set)
    for ident,row in meta.items():
        lesion=row['lesion_id'].strip()
        if lesion:groups[lesion].add(diagnoses[ident])
        if ident in used:reasons[ident]='previously_used_image'
        elif not lesion:reasons[ident]='missing_lesion_id'
        elif lesion in used_lesions:reasons[ident]='shares_used_lesion'
    conflicts={g for g,classes in groups.items() if len(classes)>1}
    for ident,row in meta.items():
        if ident not in reasons and row['lesion_id'].strip() in conflicts:reasons[ident]='conflicting_lesion_labels'
    eligible=[{'image_id':ident,'lesion_id':row['lesion_id'].strip(),'diagnosis':diagnoses[ident]}
              for ident,row in sorted(meta.items()) if ident not in reasons]
    return {'schema':'isic2019-metadata-profile-v1','inputs':{
        'metadata_sha256':hashlib.sha256(Path(metadata).read_bytes()).hexdigest(),
        'labels_sha256':hashlib.sha256(Path(labels).read_bytes()).hexdigest()},
        'images':len(meta),'class_counts':dict(Counter(diagnoses.values())),
        'with_lesion_id':sum(bool(r['lesion_id'].strip()) for r in meta.values()),
        'missing_lesion_id':sum(not r['lesion_id'].strip() for r in meta.values()),
        'unique_known_lesions':len(groups),'conflicting_label_lesions':len(conflicts),
        'previously_used_images':len(used),'used_images_missing_lesion_id':sum(not meta[i]['lesion_id'].strip() for i in used),
        'exclusion_counts':dict(Counter(reasons.values())),
        'candidate_images':len(eligible),'candidate_lesions':len({r['lesion_id'] for r in eligible}),
        'candidate_class_counts':dict(Counter(r['diagnosis'] for r in eligible)),
        'candidates':eligible,'previously_used_ids':sorted(used),
        'limits':['Metadata does not verify source pixel availability or official download provenance.',
            'Known lesion-disjoint eligibility only; missing patient IDs preclude patient-disjoint claim.',
            'Used images missing lesion IDs cannot be group-excluded completely.',
            'Candidates are not a frozen final split and not the PFF-WM authors selection.',
            'Exact paper release/2500image selection/split and code still require confirmation.']}


def prior_ids(root=ROOT):
    result=set()
    for path in (root/'deliverables/verification-evidence').glob('*/preparation.json'):
        packet=json.loads(path.read_text())
        for row in packet.get('selected',[]):
            ident=row.get('image_id','')
            if ident.startswith('ISIC_'):result.add(ident)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--labels',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('new output required')
    report=profile(a.metadata,a.labels,prior_ids());a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('candidates','previously_used_ids')},indent=2))
