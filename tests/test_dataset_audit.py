import csv
from pathlib import Path
import cv2
import numpy as np
import pytest
from src.dataset_audit import CLASSES, audit, discover, label_rows


def fixture(tmp_path):
    data=tmp_path/'input'/'images'
    data.mkdir(parents=True)
    for i in range(2):
        cv2.imwrite(str(data/f'ISIC_{i}.jpg'),np.full((16,16,3),100,np.uint8))
    labels=tmp_path/'input'/'groundtruth.csv'
    with labels.open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['image',*CLASSES])
        for i in range(2): w.writerow([f'ISIC_{i}',1,0,0,0,0,0,0,0])
    return data,labels


def test_audit_rejects_subset_unless_explicit(tmp_path):
    data,labels=fixture(tmp_path)
    with pytest.raises(ValueError,match='not the complete'):
        audit(data,labels,tmp_path/'verified.csv')
    r=audit(data,labels,tmp_path/'verified.csv',allow_subset=True)
    assert r['unique_labels']==2 and not r['full_official_count_profile']
    assert len(discover(tmp_path)['ground_truth_csvs'])==2


def test_missing_and_duplicate_images(tmp_path):
    data,labels=fixture(tmp_path)
    (data/'ISIC_0.jpg').unlink()
    with pytest.raises(ValueError,match='missing'):
        audit(data,labels,tmp_path/'verified.csv',True)
    nested=data/'nested'
    nested.mkdir()
    (nested/'ISIC_1.jpg').write_bytes((data/'ISIC_1.jpg').read_bytes())
    with pytest.raises(ValueError,match='duplicate image'):
        audit(data,labels,tmp_path/'verified.csv',True)


def test_invalid_and_conflicting_labels(tmp_path):
    _,labels=fixture(tmp_path)
    with labels.open('a') as f: f.write('ISIC_0,0,1,0,0,0,0,0,0\n')
    with pytest.raises(ValueError,match='conflicting'):
        label_rows(labels)
    labels.write_text('image,'+','.join(CLASSES)+'\nISIC_0,1,1,0,0,0,0,0,0\n')
    with pytest.raises(ValueError,match='exactly one'):
        label_rows(labels)
