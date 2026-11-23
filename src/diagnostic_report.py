"""Read-only TRAIN diagnostic interpretation, never a benchmark approval gate."""
import math
import re
from .names import model_name


def _score(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f'{name}: finite score in [0,1] required')
    return float(value)


def summarize(report):
    if (not isinstance(report, dict) or report.get('usable') is not False
            or not isinstance(report.get('purpose'), str) or 'TRAIN-only' not in report['purpose']):
        raise ValueError('only explicitly non-claimable TRAIN diagnostics are accepted')
    source = report.get('source_sha256', '')
    if not isinstance(source, str) or not re.fullmatch('[0-9a-f]{64}', source):
        raise ValueError('valid source fingerprint required')
    settings = report['settings']
    mode = settings.get('model', 'both')
    configs = {'main': ('C8',), 'attention': ('C12',), 'both': ('C8', 'C12')}
    if mode not in configs:
        raise ValueError('unsupported diagnostic model selection')
    epochs, n = settings['epochs'], settings['n']
    if type(epochs) is not int or epochs < 1 or type(n) is not int or n < 7:
        raise ValueError('invalid diagnostic settings')
    ids = report['training_ids']
    if len(ids) != n or any(not isinstance(i, str) for i in ids) or len(set(ids)) != n:
        raise ValueError('training identifiers must be unique and match n')
    baseline = _score(report['classical_reference']['metrics']['iou_tampered_mean'], 'classical IoU')
    expected = [model_name(c) for c in configs[mode]]
    problems, rows = [], []
    for name in expected:
        result = report.get('models', {}).get(name)
        if not result or result.get('status') != 'complete':
            problems.append(f'{name}: missing or incomplete')
            continue
        trace = result.get('epoch_trace', [])
        selected = result.get('selected_epoch')
        if (len(trace) != epochs or [r.get('epoch') for r in trace] != list(range(1, epochs+1))
                or result.get('last_completed_epoch') != epochs or type(selected) is not int
                or not 1 <= selected <= epochs):
            problems.append(f'{name}: inconsistent epoch history')
            continue
        after, chosen = result['after'], trace[selected-1]['operating_points']
        shared = _score(after['metrics']['iou_tampered_mean'], name+' shared IoU')
        pixel = _score(after['pixel_only_training_iou'], name+' pixel-only IoU')
        chosen_shared = _score(chosen['shared_rule']['tampered_pixel_iou'], 'selected shared IoU')
        detail = chosen['pixel_only_training_diagnostic']
        chosen_pixel = _score(detail['tampered_pixel_iou'], 'selected pixel-only IoU')
        if abs(shared-chosen_shared) > 1e-6 or abs(pixel-chosen_pixel) > 1e-6:
            problems.append(f'{name}: returned model and selected-epoch metrics disagree')
        counts = detail['intact_positive_pixel_counts']
        if any(type(v) is not int or v < 0 for v in counts):
            raise ValueError('intact positive counts must be nonnegative integers')
        families = {family: _score(value, family+' pixel IoU')
                    for family,value in detail['tampered_pixel_iou_by_family'].items()}
        rows.append({'model': name, 'selected_epoch': selected, 'last_completed_epoch': epochs,
                     'shared_rule_training_iou': shared, 'pixel_only_training_iou': pixel,
                     'shared_rule_minus_classical_iou': shared-baseline,
                     'pixel_only_minus_classical_iou': pixel-baseline,
                     'pixel_only_intact_positive_pixel_counts': counts,
                     'pixel_only_training_iou_by_family': families,
                     'shared_rule_pixel_collapse': after['collapse']['pixel'],
                     'observations': [
                         *(['Shared-rule localisation is below block expansion.'] if shared < baseline else []),
                         *(['Pixel-only training threshold improves IoU; this is NOT a validated replacement rule.'] if pixel > shared else []),
                         *(['Pixel-only threshold flags pixels on intact TRAIN images.'] if any(counts) else []),
                         *(['The returned checkpoint is earlier than the final epoch.'] if selected != epochs else [])]})
    return {'schema': 'train-diagnostic-summary-v1', 'source_sha256': source,
            'scope': 'TRAIN-only in-sample debugging; no validation/test evaluation',
            'synthetic': report.get('synthetic'), 'run_complete': not problems,
            'study_ready': False, 'expected_models': expected, 'problems': problems,
            'classical_training_iou': baseline, 'models': rows,
            'limitations': ['Completion is not scientific success or permission to start the full study.',
                            'Training thresholds, IoUs and intact errors are not generalisation estimates.',
                            'No novelty, clinical safety or learned superiority is established.']}
