import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('matched_summary',ROOT/'scripts/summarize_matched_editguard_validation.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_confusion_summary_uses_pooled_pixel_denominators():
    rows=[{'confusion':{'tp':3,'fp':1,'fn':2,'tn':10},'pixel_iou':.5},
          {'confusion':{'tp':0,'fp':2,'fn':4,'tn':10},'pixel_iou':0.0}]
    out=m.confusion_metrics(rows)
    assert out['tp']==3 and out['fp']==3 and out['fn']==6 and out['tn']==20
    assert out['pooled_pixel_precision']==.5
    assert out['pooled_pixel_recall']==1/3
    assert out['pooled_pixel_f1']==.4
    assert out['pooled_pixel_iou']==1/4
    assert out['n_images_with_defined_iou']==2
