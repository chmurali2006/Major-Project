import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from compare_paired import compare
from run_isic_study import DiskSamples
from run_matrix import Sample
from dataclasses import asdict


def test_disk_sample_roundtrip(tmp_path):
    s = Sample(np.zeros((13,8,8),np.float16),np.zeros(4,np.float32),
               np.zeros((3,64,64),np.uint8),np.zeros((8,8),bool),
               np.zeros((64,64),bool),0,'none','NV')
    path = tmp_path/'s.npz'
    np.savez(path,**asdict(s))
    got = DiskSamples([path])[0]
    assert got.family == 'none' and got.strata == 'NV' and got.cls == 0
    assert got.ev.dtype == np.float16


def test_bootstrap_pairs_by_id(tmp_path):
    a,b = tmp_path/'a.npz',tmp_path/'b.npz'
    np.savez(a,image_id=['a','b'],tampered=[1,0],prediction=[0,1],iou=[0.,0.])
    np.savez(b,image_id=['b','a'],tampered=[0,1],prediction=[0,1],iou=[1.,1.])
    r=compare(a,b,draws=10)
    assert r['delta']['iou_tampered']['estimate'] == 1
    assert r['delta']['balanced_accuracy']['estimate'] == 1
    np.savez(b,image_id=['c','a'],tampered=[0,1],prediction=[0,1],iou=[1.,1.])
    with pytest.raises(ValueError):
        compare(a,b,draws=10)
