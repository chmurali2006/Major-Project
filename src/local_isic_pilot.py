"""Local-image pilot preparation, with explicit supplied-metadata grouping limits."""
import csv
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from .dataset_audit import label_rows,CLASSES
from .persistence import atomic_json


def groups_from_metadata(path,ids,field):
    """No synthetic patient IDs; blank supplied groups cannot pass as complete."""
    if field not in ('patient_id','lesion_id'):raise ValueError('explicit patient_id or lesion_id field required')
    groups={}
    with Path(path).open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if not {'image',field}.issubset(reader.fieldnames or []):raise ValueError('metadata requires image and selected group column')
        for row in reader:
            ident=Path(row['image']).stem;value=(row.get(field) or '').strip()
            if ident in groups and groups[ident]!=value:raise ValueError('conflicting grouping metadata')
            groups[ident]=value
    if any(not groups.get(i) for i in ids):raise ValueError('complete supplied groups required; missing groups cannot be invented')
    return {i:field+':'+groups[i] for i in ids}


def prepare(data,labels,destination,*,metadata=None,group_field=None,allow_image_level=False,
            per_class=1,seed=73,exclude_ids=()):
    data=Path(data).resolve();destination=Path(destination).resolve()
    if destination.exists():raise ValueError('new preparation destination required')
    if not 1<=per_class<=4 or type(per_class) is not int:raise ValueError('per_class1..4 required')
    if destination==data or data in destination.parents:raise ValueError('destination must not be inside input image directory')
    rows,total=label_rows(labels)
    paths={}
    for p in sorted(data.rglob('*')):
        if p.suffix.lower() not in ('.jpg','.jpeg','.png'):continue
        if p.stem in paths:raise ValueError('ambiguous duplicate image stems in input dataset')
        paths[p.stem]=p
    if any(i not in paths for i in rows):raise ValueError('labelled image missing; use matching complete image/label roots')
    if metadata and group_field:
        groups=groups_from_metadata(metadata,rows,group_field)
        grouping=group_field+' supplied by caller, not independently verified'
    elif allow_image_level and not metadata and not group_field:
        groups={i:'image:'+i for i in rows};grouping='image only; patient/lesion dependence unknown'
    else:raise ValueError('supply metadata+group_field, or explicitly allow image-level pilot')
    excluded=set(exclude_ids)
    # Exclude entire supplied groups whenever any prior evaluated ID is known.
    excluded_groups={groups[i] for i in excluded if i in groups}
    selected=[];used=set()
    for k,name in enumerate(CLASSES):
        candidates=[i for i,v in rows.items() if v[k]==1 and i not in excluded and groups[i] not in excluded_groups]
        candidates.sort(key=lambda i:(hashlib.sha256(f'{seed}/{i}'.encode()).hexdigest(),i))
        for ident in candidates:
            if groups[ident] in used:continue
            selected.append({'image_id':ident,'diagnosis':name,'label':k,'group':groups[ident]})
            used.add(groups[ident])
            if sum(x['diagnosis']==name for x in selected)==per_class:break
        if sum(x['diagnosis']==name for x in selected)!=per_class:
            raise ValueError('insufficient distinct unexcluded groups for '+name)
    destination.mkdir(parents=True);(destination/'prepared').mkdir()
    report={'schema':'local-isic-pilot-preparation-v1','complete':False,
            'scope':'caller-supplied local ISIC-labelled feasibility pilot, not an independently verified held-out study',
            'seed':seed,'per_class':per_class,'label_rows':total,'unique_label_ids':len(rows),
            'labels_sha256':hashlib.sha256(Path(labels).read_bytes()).hexdigest(),
            'metadata_sha256':hashlib.sha256(Path(metadata).read_bytes()).hexdigest() if metadata else None,
            'grouping':grouping,'excluded_ids':sorted(excluded),'excluded_group_count':len(excluded_groups),
            'selection':'deterministic SHA256(seed/image_id), at most one per supplied group, no model/pixel selection',
            'official_identity_verified':False,'selected':[],
            'limitations':['A local path or label profile does not authenticate native-original ISIC identity.',
                           'Caller-supplied grouping is not independently verified; lesion grouping is not patient grouping.',
                           'Native dimensions, file hashes and prepared hashes are recorded; no native-original claim inferred.',
                           'Preparation explicitly resizes to512 nearest to match baseline; fidelity is measured against prepared RGB.',
                           'Tiny balanced pilot cannot support population, clinical or per-diagnosis superiority claims.']}
    atomic_json(destination/'preparation.json',report)
    hashes=set()
    for entry in selected:
        p=paths[entry['image_id']]
        raw=p.read_bytes()
        with Image.open(p) as im:
            if getattr(im,'n_frames',1)!=1 or im.mode!='RGB':raise ValueError('single-frame RGB required; prepare conversion separately')
            native_size=list(im.size)
            original=np.array(im)
            prepared=im.resize((512,512),Image.Resampling.NEAREST)
        native_hash=hashlib.sha256(original.tobytes()).hexdigest()
        if native_hash in hashes:raise ValueError('duplicate decoded images selected; do not silently substitute')
        hashes.add(native_hash)
        target=destination/'prepared'/(entry['image_id']+'.png');prepared.save(target)
        report['selected'].append({**entry,'source_file_sha256':hashlib.sha256(raw).hexdigest(),
              'source_decoded_rgb_sha256':native_hash,'source_dimensions':native_size,
              'prepared_file_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
              'prepared_rgb_sha256':hashlib.sha256(prepared.tobytes()).hexdigest(),
              'preparation':'explicit nearest-neighbour square512 resize from decoded RGB; no implicit source conversion'})
        atomic_json(destination/'preparation.json',report)
    with (destination/'manifest.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['image_id','path','label','group'])
        for entry in selected:writer.writerow([entry['image_id'],'prepared/'+entry['image_id']+'.png',entry['label'],entry['group']])
    report['complete']=True;atomic_json(destination/'preparation.json',report)
    return report
