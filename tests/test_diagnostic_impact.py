import numpy as np
import pytest
from src.diagnostic_impact import analyse


def test_known_confusion_and_paired_repeatability():
    y=np.array([0,0,1,1]);a=np.array([[.9,.1],[.8,.2],[.2,.8],[.1,.9]])
    b=np.array([[.9,.1],[.4,.6],[.2,.8],[.7,.3]])
    r=analyse(y,a,b,['nonMEL','MEL'],repetitions=100)
    assert r==analyse(y,a,b,['nonMEL','MEL'],repetitions=100)
    assert r['clean']['balanced_accuracy']==1
    assert r['received']['confusion_matrix']==[[1,1],[1,1]]
    assert r['received']['balanced_accuracy']==.5
    assert r['received']['macro_f1']==.5
    assert r['received']['per_class_sensitivity']==[.5,.5]
    assert r['correct_to_wrong']==2 and r['wrong_to_correct']==0 and r['prediction_flips']==2
    assert r['paired_differences']['balanced_accuracy']['received_minus_clean']==-.5


def test_missing_class_never_silently_dropped():
    p=np.array([[.9,.1],[.8,.2]])
    r=analyse(np.array([0,0]),p,p,['a','b'],repetitions=100)
    assert r['clean']['balanced_accuracy'] is None
    assert r['clean']['macro_f1'] is None
    assert r['clean']['per_class_sensitivity']==[1.,None]
    assert r['paired_differences']['balanced_accuracy']['paired_percentile95'] is None
    assert r['flip_rate']==0


@pytest.mark.parametrize('bad',[
    [[float('nan'),.1],[.2,.8]],[[.8,.8],[.2,.8]],[[1.1,-.1],[.2,.8]]])
def test_invalid_probabilities_rejected(bad):
    with pytest.raises(ValueError,match='probabilities'):analyse(np.array([0,1]),bad,bad,['a','b'],repetitions=100)


def test_probability_shift_and_complete_failure_retained():
    a=np.eye(2);b=1-a
    r=analyse(np.array([0,1]),a,b,['a','b'],repetitions=100)
    assert r['mean_probability_l1_shift']==2
    assert r['mean_true_class_probability_shift']==-1
    assert r['received']['macro_f1']==0 and r['received']['accuracy']==0
    assert r['paired_differences']['accuracy']['paired_percentile95']==[-1.,-1.]


def test_auc_ties_orientation_and_missing_class():
    from src.diagnostic_impact import binary_auc
    assert binary_auc(np.array([0,1]),[.1,.9])==1
    assert binary_auc(np.array([0,1]),[.9,.1])==0
    assert binary_auc(np.array([0,1]),[.5,.5])==.5
    assert binary_auc(np.array([0,0,1,1]),[.1,.5,.5,.9])==.875
    assert binary_auc(np.array([0,0]),[.1,.5]) is None
    with pytest.raises(ValueError):binary_auc(np.array([0,2]),[.1,.9])
    a=np.eye(2);b=1-a
    r=analyse(np.array([0,1]),a,b,['nonMEL','MEL'],repetitions=100)
    assert r['clean']['binary_roc_auc']==1 and r['received']['binary_roc_auc']==0
    assert r['paired_differences']['binary_roc_auc']['paired_percentile95']==[-1.,-1.]
