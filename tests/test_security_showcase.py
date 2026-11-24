import numpy as np
import pytest
from src.security_showcase import build_security_report, render_security_html


@pytest.mark.parametrize('constant', [False, True])
def test_security_checks_and_replay_limit(constant):
    rgb = np.full((32,40,3),255,np.uint8) if constant else np.random.default_rng(9).integers(0,256,(32,40,3),dtype=np.uint8)
    before = rgb.copy()
    report, views = build_security_report(rgb)
    assert report['all_checks_passed']
    assert np.array_equal(rgb,before)
    rows = {r['case']:r for r in report['cases']}
    assert rows['old-pair-old-expected-version']['verdict']=='VERIFIED'
    assert rows['old-pair-new-expected-version']['verdict']=='CANNOT_AUTHENTICATE'
    assert rows['swapped-content-same-id']['verdict']=='FAILED_INTEGRITY'
    for r,v in zip(report['cases'],views):
        if r['verdict']=='CANNOT_AUTHENTICATE':
            assert r['failed_blocks'] is None and v['overlay'] is None
    page=render_security_html(report,views)
    assert 'No localisation map' in page
    assert 'not the classical HMAC' in page
