import csv
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_isic_metadata import profile,CLASSES


def write(path,fields,rows):
    with path.open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=fields);w.writeheader();w.writerows(rows)


def test_group_exclusion_and_missing_ids(tmp_path):
    meta=tmp_path/'m.csv';labels=tmp_path/'l.csv'
    write(meta,['image','lesion_id'],[{'image':str(i),'lesion_id':g} for i,g in enumerate(('a','a','','b','c'))])
    write(labels,['image',*CLASSES],[{'image':str(i),**{k:int(k=='MEL') for k in CLASSES}} for i in range(5)])
    r=profile(meta,labels,{'0'})
    assert r['exclusion_counts']=={'previously_used_image':1,'shares_used_lesion':1,'missing_lesion_id':1}
    assert r['candidate_images']==2 and r['candidate_lesions']==2
    with pytest.raises(ValueError):profile(meta,labels,{'absent'})


def test_duplicate_or_invalid_labels_rejected(tmp_path):
    meta=tmp_path/'m.csv';labels=tmp_path/'l.csv'
    write(meta,['image','lesion_id'],[{'image':'0','lesion_id':'a'}])
    write(labels,['image',*CLASSES],[{'image':'0',**{k:0 for k in CLASSES}}])
    with pytest.raises(ValueError):profile(meta,labels,set())
    write(meta,['image','lesion_id'],[{'image':'0','lesion_id':'a'}]*2)
    with pytest.raises(ValueError):profile(meta,labels,set())
