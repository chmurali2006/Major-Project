"""Summary contracts; historical fixture values are not new measurements."""
import json
from pathlib import Path
import subprocess
import sys

import pytest
from src.diagnostic_report import summarize

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def report():
    return json.loads((ROOT/'deliverables/verification-evidence/development-audit-v1.json').read_text())['learning_trace']


def test_completion_is_never_study_approval(report):
    result = summarize(report)
    assert result['run_complete'] is True
    assert result['study_ready'] is False
    row = result['models'][0]
    assert row['selected_epoch'] == 6 and row['last_completed_epoch'] == 8
    assert row['shared_rule_training_iou'] == 0.
    assert row['pixel_only_intact_positive_pixel_counts'] == [112]
    assert row['shared_rule_minus_classical_iou'] < 0
    assert row['pixel_only_minus_classical_iou'] < 0
    assert len(row['observations']) == 4


@pytest.mark.parametrize('kind', ['missing', 'running', 'trace', 'selected', 'disagreement'])
def test_incomplete_or_inconsistent_is_not_complete(report, kind):
    result = next(iter(report['models'].values()))
    if kind == 'missing':
        report['models'] = {}
    elif kind == 'running':
        result['status'] = 'running'
    elif kind == 'trace':
        result['epoch_trace'] = result['epoch_trace'][:-1]
    elif kind == 'selected':
        result['selected_epoch'] = 99
    else:
        result['after']['metrics']['iou_tampered_mean'] = .9
    summary = summarize(report)
    assert not summary['run_complete'] and not summary['study_ready']
    assert summary['problems']


@pytest.mark.parametrize('kind', ['scope', 'source', 'duplicate', 'nan', 'bool'])
def test_malformed_claims_rejected(report, kind):
    if kind == 'scope':
        report['usable'] = True
    elif kind == 'source':
        report['source_sha256'] = 'unknown'
    elif kind == 'duplicate':
        report['training_ids'][0] = report['training_ids'][1]
    elif kind == 'nan':
        report['classical_reference']['metrics']['iou_tampered_mean'] = float('nan')
    else:
        report['classical_reference']['metrics']['iou_tampered_mean'] = True
    with pytest.raises(ValueError):
        summarize(report)


def test_missing_raw_receipt_can_still_export_failure_summary(tmp_path):
    out = tmp_path/'summary.json'
    subprocess.run([sys.executable, str(ROOT/'scripts/summarize_diagnostic.py'),
                    '--input', str(tmp_path/'missing.json'), '--out', str(out)], check=True)
    result = json.loads(out.read_text())
    assert result['run_complete'] is result['study_ready'] is False
    assert result['problems']


def test_summary_refuses_to_overwrite_raw_receipt(tmp_path, report):
    path = tmp_path/'raw.json'
    path.write_text(json.dumps(report))
    before = path.read_bytes()
    result = subprocess.run([sys.executable, str(ROOT/'scripts/summarize_diagnostic.py'),
                             '--input', str(path), '--out', str(path)], capture_output=True)
    assert result.returncode != 0
    assert path.read_bytes() == before



def test_manual_notebook_defaults_are_safe():
    from scripts.validate_notebook import validate_defaults
    nb = json.loads((ROOT/'notebooks/keyswm_isic2019.ipynb').read_text())
    validate_defaults([c for c in nb['cells'] if c['cell_type'] == 'code'])


@pytest.mark.parametrize('old,new', [
    ("STAGE = 'diagnostic'", "STAGE = 'main-model'"),
    ('DIAGNOSTIC_EPOCHS = 20', 'DIAGNOSTIC_EPOCHS = 100'),
    ('AUTHENTIC_EPOCHS = 2', 'AUTHENTIC_EPOCHS = 0'),
    ('RESTORE_FROM = None', "RESTORE_FROM = 'old-run'"),
    ('INSTALL_MISSING = False', 'INSTALL_MISSING = True'),
    ('ALLOW_LABELLED_SUBSET = False', 'ALLOW_LABELLED_SUBSET = True'),
    ('ACKNOWLEDGE_EXPERIMENTAL_PROTOCOL_V2 = False', 'ACKNOWLEDGE_EXPERIMENTAL_PROTOCOL_V2 = True'),
    ('SEED = 0', 'SEED = 2'),
])
def test_handoff_rejects_changed_execution_defaults(old, new):
    from scripts.validate_notebook import validate_defaults
    nb = json.loads((ROOT/'notebooks/keyswm_isic2019.ipynb').read_text())
    cells = [c for c in nb['cells'] if c['cell_type'] == 'code']
    source = ''.join(cells[1]['source'])
    assert old in source
    cells[1]['source'] = source.replace(old, new)
    with pytest.raises(ValueError, match='handoff default'):
        validate_defaults(cells)
