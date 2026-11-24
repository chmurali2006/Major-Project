import numpy as np
import pytest
from src.paper_aligned_operators import operators,gaussian


def test_deterministic_truth_and_regions():
    x=np.random.default_rng(5).integers(0,256,(512,512,3),dtype=np.uint8);original=x.copy()
    a=list(operators(x,44));b=list(operators(x,44))
    assert len(a)==10 and np.array_equal(x,original)
    for left,right in zip(a,b):
        assert np.array_equal(left['received'],right['received'])
        assert np.array_equal(left['pixel_truth'],np.any(left['received']!=x,axis=2))
        assert left['received'].dtype==np.uint8 and left['received'].shape==x.shape
        if left['requested_region'] is not None:
            assert left['requested_region'].sum()==1024
            assert not (left['pixel_truth']&~left['requested_region']).any()
    assert sum(r['family']=='paper_benign' for r in a)==7


def test_constant_blur_and_no_false_semantic_mask():
    x=np.full((512,512,3),100,np.uint8)
    assert np.array_equal(gaussian(x,.5),x)
    packets=list(operators(x,1))
    assert not packets[1]['pixel_truth'].any() and packets[1]['requested_region'].any()
    with pytest.raises(ValueError):list(operators(x.astype(float),1))
