import copy
import numpy as np
import pytest
from src.paired_coding_analysis import analyse,wilson,paired_interval,METHODS,CASES


def fixture():
    preparation={'selected':[{'image_id':str(i),'diagnosis':'A' if i<2 else 'B'} for i in range(4)]}
    rows=[{'source_id':str(i),'case':case,'method':method,'fine_map_available':method=='bounded289',
           'map_matches_truth':True if method=='bounded289' else None,'verification_seconds':2. if method=='bounded289' else 1.}
          for i in range(4) for case in CASES for method in METHODS]
    return {'rows':rows},preparation


def test_wilson_not_degenerate_at_extremes():
    lo,hi=wilson(32,32)
    assert .89<lo<.90 and hi==1.
    lo,hi=wilson(0,32)
    assert lo==0. and .10<hi<.11


def test_pairing_and_failure_denominators():
    r,p=fixture();out=analyse(r,p,100)
    group=next(g for g in out['groups'] if g['method']=='set330')
    assert group['n']==4 and group['fine_maps']==0 and group['coverage']==0
    pair=out['paired_comparisons'][0]
    assert pair['coverage_difference']['mean_difference']==1.
    assert pair['coverage_difference']['paired_percentile95']==[1.,1.]
    assert len(out['classwise'])==48
    rng=np.random.default_rng(3);draws=rng.integers(0,4,(100,4))
    a=np.arange(4);b=a-7
    assert paired_interval(a,b,draws)['paired_percentile95']==[7.,7.]


def test_invalid_or_unpaired_matrix_rejected():
    r,p=fixture()
    for invalid in ({'rows':r['rows'][:-1]},{'rows':r['rows']+[r['rows'][0]]}):
        with pytest.raises(ValueError):analyse(invalid,p,100)
    bad=copy.deepcopy(r);bad['rows'][0]['map_matches_truth']=False
    with pytest.raises(ValueError):analyse(bad,p,100)
