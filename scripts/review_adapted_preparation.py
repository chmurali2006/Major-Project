"""Validate returned fixed-cohort receipts; source pixels absent, not re-decoded."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile
ROOT=Path(__file__).resolve().parents[1]


def review(archive,cohort_path):
    archive=Path(archive);cohort_path=Path(cohort_path)
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=2 or set(z.namelist())!={'preparation.json','cohort.json'} or z.testzip() is not None:raise ValueError('unexpected/corrupt receipt package')
        if z.read('cohort.json')!=cohort_path.read_bytes():raise ValueError('fixed cohort differs')
        cohort=json.loads(z.read('cohort.json'));p=json.loads(z.read('preparation.json'))
    if p['cohort_sha256']!=hashlib.sha256(cohort_path.read_bytes()).hexdigest():raise ValueError('cohort hash differs')
    if p['exact_paper_reproduction'] is not False or p['ready_for_training'] is not True:raise ValueError('unexpected preparation state')
    if len(p['selected'])!=len(cohort['selected']):raise ValueError('row count differs')
    groups={key:defaultdict(set) for key in ('lesion_id','source_decoded_rgb_sha256','prepared_rgb_sha256')}
    for expected,row in zip(cohort['selected'],p['selected']):
        if any(row.get(k)!=v for k,v in expected.items()):raise ValueError('source identity/order/split changed')
        for key in ('source_file_sha256','source_decoded_rgb_sha256','prepared_file_sha256','prepared_rgb_sha256'):
            if not re.fullmatch('[0-9a-f]{64}',row.get(key,'')):raise ValueError('invalid hash')
        dims=row['source_dimensions']
        if len(dims)!=2 or any(type(d) is not int or d<=0 for d in dims):raise ValueError('invalid dimensions')
        for key in groups:groups[key][row[key]].add(row['split'])
    splits=dict(Counter(r['split'] for r in p['selected']))
    if splits!=cohort['split_counts'] or p['split_counts']!=splits:raise ValueError('incorrect split counts')
    cross={key:sum(len(v)>1 for v in mapping.values()) for key,mapping in groups.items()}
    if any(cross.values()) or p['cross_split_identical_decoded_rgb_groups']!=0:raise ValueError('cross-split overlap')
    return p,{'schema':'adapted-preparation-return-review-v1','zip_bytes':archive.stat().st_size,
        'zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'images':len(p['selected']),
        'split_counts':splits,'cross_split_groups':cross,
        'source_modes':dict(Counter(r['source_mode'] for r in p['selected'])),
        'unique_prepared_rgb':len(groups['prepared_rgb_sha256']),
        'status':'fixed_cohort_receipts_consistent; no_model_training_or_evaluation',
        'limits':['Hashes are returned records, not independently recomputed from source images here.',
        'Exact decoded/prepared duplicate checks do not detect near duplicates or establish patient independence.',
        'No official source checksum comparison or exact authors reproduction.',
        'Preparation flag is data readiness only, not research/clinical approval.']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('archive',type=Path);a=parser.parse_args()
    p,r=review(a.archive,ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json')
    out=ROOT/'deliverables/verification-evidence/adapted-isic2500-preparation-v2';out.mkdir(exist_ok=False)
    for name,value in (('preparation.json',p),('review.json',r)):(out/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(r,indent=2))
