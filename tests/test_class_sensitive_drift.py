import importlib.util
from pathlib import Path
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('drift',ROOT/'scripts/analyse_class_sensitive_drift.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_threshold_handles_ties_without_rethresholding():
    y=np.array([0]*10+[1]);p=np.array([.2]*9+[.8,.7]);t=m.threshold_for_specificity(y,p)
    assert t>.2 and t<=.8
    assert np.mean(p[y==0]<t)==.9
    assert np.mean((p[y==0]+.2)<t)<.9 # received specificity need not stay90%


def test_paired_shift_and_fixed_threshold_analysis():
    rows=[]
    for i,(label,a,b) in enumerate([(0,[.9,.1],[.95,.05]),(0,[.8,.2],[.85,.15]),(1,[.3,.7],[.4,.6])]):
        for case,prob in [('intact',a),('jpeg70',b)]:rows.append({'image_id':str(i),'label':label,'case':case,'clean_probabilities':a,'received_probabilities':prob})
    r=m.analyse(rows,repetitions=100)
    assert r['cases']['jpeg70']['class_specific_shift']['1']['mean_MEL_probability_shift']==pytest.approx(-.1)
    assert r['cases']['intact']['class_specific_shift']['0']['paired_image_mean95']==[0.,0.]
    with pytest.raises(ValueError):m.analyse(rows+rows[:1],repetitions=100)
