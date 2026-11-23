"""Current-method demonstration contracts; fixtures are not medical evidence."""
import base64
import io
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from PIL import Image
import pytest
from src import authentication as A
from src.showcase import build_report, render_html, DEMO_KEY, IMAGE_ID, block_truth

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def demo():
    rgb = np.random.default_rng(42).integers(0, 256, (64, 64, 3), dtype=np.uint8)
    return rgb, build_report(rgb, '</script><img src=x onerror=alert(1)>', True)


def test_intact_and_storage_roundtrip(demo):
    rgb, (report, protected, _, _, _) = demo
    with Image.open(io.BytesIO(protected)) as im:
        stored = np.array(im)
    assert A.verify(stored, DEMO_KEY, IMAGE_ID)
    assert report['embedding']['maximum_absolute_channel_change'] <= 1
    assert np.max(abs(stored.astype(int)-rgb.astype(int))) <= 1
    row = report['cases'][0]
    assert row['verdict'] == 'VERIFIED'
    assert row['failed_blocks'] == row['changed_pixels'] == 0
    assert row['localisation']['block_iou'] is None
    assert row['localisation']['expanded_block_pixel_iou'] is None


def test_one_pixel_exposes_resolution_limit(demo):
    _, (report, *_) = demo
    row = next(c for c in report['cases'] if c['id'] == 'one-pixel')
    assert row['changed_pixels'] == row['failed_blocks'] == 1
    assert row['localisation']['block_iou'] == 1.
    assert row['localisation']['expanded_block_pixel_iou'] == 1/64
    assert row['localisation']['block_confusion'] == {'tp': 1, 'fp': 0, 'fn': 0, 'tn': 63}


def test_context_failure_is_not_reported_as_pixel_tampering(demo):
    _, (report, *_) = demo
    for row in report['cases']:
        if row['scenario_type'] == 'context':
            assert row['verdict'] == 'FAILED_INTEGRITY'
            assert row['changed_pixels'] == 0
            assert row['failed_blocks'] == row['total_blocks']
            assert row['localisation'] is None


def test_truth_and_overlay_are_independent_of_verifier(demo):
    _, (report, _, views, _, _) = demo
    for row, view in zip(report['cases'], views):
        def decode(name):
            return np.array(Image.open(io.BytesIO(base64.b64decode(view[name].split(',')[1]))))
        received, truth = decode('received'), decode('truth')
        assert int((truth[..., 0] != 0).sum()) == row['changed_pixels']
        key = b'wrong-public-key' if row['id'] == 'wrong-key' else DEMO_KEY
        ident = IMAGE_ID+1 if row['id'] == 'wrong-id' else IMAGE_ID
        failed = A.failures(received, key, ident)
        assert int(failed.sum()) == row['failed_blocks']
        if row['localisation'] is not None:
            gt = block_truth(truth[..., 0] != 0)
            assert row['localisation']['block_confusion']['fn'] == int((~failed & gt).sum())


def test_html_no_external_assets_and_escapes_untrusted_label(demo):
    _, (report, _, views, original, protected) = demo
    page = render_html(report, views, original, protected)
    assert '</script><img src=x' not in page
    assert '&lt;/script&gt;' in page
    assert not re.search(r'<(?:script|img)[^>]+src=["\']https?://', page)
    raw = re.search(r'<script id="evidence" type="application/json">(.*?)</script>', page, re.S).group(1)
    assert json.loads(raw)['report']['source_label'] == report['source_label']
    assert 'No neural checkpoint required' in page
    assert 'SYNTHETIC FIXTURE' in page


def test_cli_real_input_export_and_preprocessing(tmp_path):
    image = tmp_path/'input.png'
    Image.fromarray(np.full((33, 49, 3), 100, np.uint8)).save(image)
    out = tmp_path/'showcase'
    command = [sys.executable, str(ROOT/'scripts/showcase.py'), '--image', str(image),
               '--out', str(out)]
    bad = subprocess.run(command, capture_output=True, text=True)
    assert bad.returncode != 0 and not out.exists()
    subprocess.run(command+['--resize', '64'], check=True)
    report = json.loads((out/'report.json').read_text())
    assert report['synthetic'] is False
    assert report['input_shape_before_preprocessing'] == [33, 49, 3]
    assert report['shape'] == [64, 64, 3]
    assert 'explicit bicubic' in report['preprocessing']
    assert 'no dataset membership' in report['source_label']
    assert (out/'index.html').exists() and (out/'protected.png').exists()
    again = subprocess.run(command+['--resize', '64'], capture_output=True)
    assert again.returncode != 0


def test_cli_blocks_pixel_outputs_in_repository():
    result = subprocess.run([sys.executable, str(ROOT/'scripts/showcase.py'), '--synthetic',
                             '--out', str(ROOT/'should-not-exist-showcase')], capture_output=True, text=True)
    assert result.returncode != 0
    assert 'outside the repository' in result.stderr
    assert not (ROOT/'should-not-exist-showcase').exists()


@pytest.mark.parametrize('shape', [(24, 32, 3), (33, 40, 3)])
def test_invalid_geometry_not_silently_resized(shape):
    with pytest.raises(ValueError):
        build_report(np.zeros(shape, np.uint8), 'fixture', True)


def test_non_aligned_edit_exposes_boundary_expansion(demo):
    _, (report, *_) = demo
    row = next(c for c in report['cases'] if c['id'] == 'boundary-patch')
    assert row['changed_pixels'] == 15
    assert row['failed_blocks'] == 4
    assert row['localisation']['block_iou'] == 1.
    assert row['localisation']['expanded_block_pixel_iou'] == 15/256
