import numpy as np
import pytest
from src.editguard_adapter import residual_mask
from src.localization_comparison import operators,evaluate


def test_official_residual_threshold_is_strict_and_channelwise():
    blue=np.zeros((4,4,3),np.uint8);blue[:,:,2]=255
    score,pred=residual_mask(blue)
    assert not pred.any() and not score.any()
    blue[0,0,0]=51;blue[1,1,0]=52
    score,pred=residual_mask(blue,.2)
    assert not pred[0,0] and pred[1,1]
    blue[2,2]=[255,255,0]
    assert residual_mask(blue)[1][2,2]


@pytest.mark.parametrize('threshold',[-1,float('nan'),2])
def test_bad_threshold_rejected(threshold):
    with pytest.raises(ValueError):residual_mask(np.zeros((2,2,3),np.uint8),threshold)


def test_operators_pair_coordinates_and_do_not_mutate_reference():
    a=np.zeros((512,512,3),np.uint8);b=np.full_like(a,100)
    before=a.copy()
    aa=list(operators(a,10));bb=list(operators(b,10))
    assert np.array_equal(a,before)
    for name in ('one-bit','brightness32','replace64'):
        x=next(r for r in aa if r[0]==name)[2]
        y=next(r for r in bb if r[0]==name)[2]
        assert np.array_equal(np.any(x!=a,2),np.any(y!=b,2))
    assert next(r for r in aa if r[0]=='jpeg75')[1]=='benign-lossy'


def test_metrics_use_protected_reference_not_original():
    original=np.zeros((512,512,3),np.uint8)
    protected=np.full_like(original,100)
    def localize(x):
        mask=np.any(x!=protected,2)
        return mask.astype(float),mask
    report,maps=evaluate(original,protected,localize,10)
    assert report['embedding_mse']==10000
    intact=report['cases'][0]
    assert intact['changed_pixels']==0 and intact['pixel_iou'] is None
    assert not intact['predicted_image_positive']
    for row in report['cases'][1:]:
        assert row['confusion']['fn']==0 and row['confusion']['fp']==0
        if row['changed_pixels']:assert row['pixel_iou']==1
    assert len(maps)==18


def test_bad_prediction_shape_fails():
    a=np.zeros((512,512,3),np.uint8)
    with pytest.raises(ValueError):evaluate(a,a,lambda x:(np.zeros((2,2)),np.zeros((2,2),bool)),0)


def test_editguard_input_contract_rejects_wrong_geometry_before_inference():
    from src.editguard_adapter import EditGuard
    adapter=object.__new__(EditGuard)
    with pytest.raises(ValueError,match='512'):
        adapter.tensor(np.zeros((128,128,3),np.uint8))


def test_missing_checkout_fails_without_loading_weights(tmp_path):
    from src.editguard_adapter import EditGuard
    import subprocess
    with pytest.raises(subprocess.CalledProcessError):
        EditGuard(tmp_path,tmp_path/'absent.pth')


def test_report_preserves_misses_and_escapes_input_labels():
    from scripts.report_editguard_comparison import render
    a=np.zeros((512,512,3),np.uint8)
    result,_=evaluate(a,a,lambda x:(np.zeros((512,512)),np.zeros((512,512),bool)),3)
    result.update(method='Example method',sidecar_bytes=0,setup_seconds=0.)
    report={'complete':True,'synthetic':True,'samples':[{'source':'<script>unsafe</script>','methods':[result]}]}
    text=render([('Smoke',report)])
    assert '&lt;script&gt;' in text and '<script>unsafe' not in text
    assert 'one-bit' in text and 'benign-lossy' in text
    assert 'not a reproduced paper benchmark' in text.lower()
    report['complete']=False
    with pytest.raises(ValueError):render([('Smoke',report)])
