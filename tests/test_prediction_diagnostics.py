from types import SimpleNamespace
import numpy as np
import pytest
from src.prediction_diagnostics import map_diagnostics, collapse_summary


def test_exact_counts_and_strict_threshold():
    sample = SimpleNamespace(gt_block=np.array([[1, 0]], bool),
                             gt_pixel=np.array([[1, 0], [0, 1]], bool))
    packet = map_diagnostics([sample], [np.array([[.5, .6]])],
                             [np.ones((2, 2))], .5)
    assert packet['block_confusion'].tolist() == [[0, 1, 1, 0]]
    assert packet['pixel_confusion'].tolist() == [[2, 2, 0, 0]]
    assert collapse_summary(packet)['pixel']['all_foreground_images'] == 1
    assert packet['block_truth_count'].tolist() == [1]
    assert packet['pixel_quantiles'].shape == (1, 7)


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1., 1.1])
def test_bad_probabilities_rejected(bad):
    sample = SimpleNamespace(gt_block=np.zeros((1, 1)), gt_pixel=np.zeros((1, 1)))
    with pytest.raises(ValueError):
        map_diagnostics([sample], [np.array([[bad]])], [np.zeros((1, 1))], .5)


def test_misaligned_maps_rejected():
    with pytest.raises(ValueError):
        map_diagnostics([], [], [], .5)


def test_diagnostic_indices_never_leave_train():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from diagnose_learning import training_indices
    order = np.random.default_rng(20261103).permutation(100)
    selected = training_indices(100, 7)
    assert set(selected) <= set(order[:70])
    assert not set(selected) & set(order[70:])
    with pytest.raises(ValueError):
        training_indices(10, 8)


def test_diagnostic_cli_decodes_only_selected_train_images(tmp_path):
    """All unselected/VAL/TEST files are intentionally undecodable fixtures."""
    import json
    import subprocess
    import sys
    from pathlib import Path
    import cv2
    from scripts.diagnose_learning import training_indices
    root = Path(__file__).resolve().parents[1]
    data = tmp_path / 'images'
    data.mkdir()
    selected = set(training_indices(20, 7))
    rows = ['image,MEL,NV,BCC,AK,BKL,DF,VASC,SCC']
    for i in range(20):
        name = f'ISIC_FIXTURE_{i:04d}'
        path = data / (name + '.jpg')
        if i in selected:
            image = np.random.default_rng(i).integers(0, 256, (512, 512, 3), dtype=np.uint8)
            assert cv2.imwrite(str(path), image)
        else:
            path.write_bytes(b'intentionally not a decodable image')
        rows.append(name + ',0,1,0,0,0,0,0,0')
    metadata = tmp_path / 'labels.csv'
    metadata.write_text('\n'.join(rows) + '\n')
    # Execute the notebook's actual launch/export cell using a portable bundle.
    import ast
    import shutil
    import zipfile
    from scripts.package_project import build
    bundle = build(tmp_path / 'source.zip')
    project = tmp_path / 'project'
    with zipfile.ZipFile(bundle) as z:
        z.extractall(project)
    runs = tmp_path / 'runs'
    runs.mkdir()
    tree = ast.parse((root / 'scripts/build_notebook.py').read_text())
    cell = next(node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)
                and isinstance(node.value, str) and node.value.startswith('cmd = [sys.executable'))
    cell = cell.replace("'--device', 'cuda'", "'--device', 'cpu'")
    cell = cell.replace('/kaggle/working', str(tmp_path))
    ns = dict(subprocess=subprocess, sys=sys, Path=Path, PROJECT=project, DATA=data,
              CANONICAL_CSV=metadata, RUNS=runs, CACHE=tmp_path/'unused-cache', SEED=0,
              TRAIN_N=7, VAL_N=7, TEST_N=7, EPOCHS=1, AUTHENTIC_EPOCHS=2, WIDTH=4,
              RESUME=False, SANITY=True, STAGE='diagnostic', RUN_NAME='fixture-diagnostic',
              DIAGNOSTIC=True, DIAGNOSTIC_EPOCHS=1, json=json, shutil=shutil)
    exec(compile(cell, '<notebook diagnostic launch/export>', 'exec'), ns)
    with zipfile.ZipFile(ns['archive']) as z:
        assert 'training-only/diagnostic.json' in z.namelist()
        assert 'execution.log' in z.namelist()
        assert not any('/cache/' in n or n.endswith('.jpg') for n in z.namelist())
    out = runs / 'training-only'
    report = json.loads((out / 'diagnostic.json').read_text())
    assert report['usable'] is False
    assert report['training_ids'] == [f'ISIC_FIXTURE_{i:04d}' for i in training_indices(20, 7)]
    assert len(report['models']) == 2
    for result in report['models'].values():
        assert result['selected_epoch'] == result['last_completed_epoch'] == 1
        assert len(result['epoch_trace']) == 1
        assert 'operating_points' in result['epoch_trace'][0]
        assert result['status'] == 'complete'
    assert not (out / 'cache').exists()
    for cid in ('C8', 'C12'):
        with np.load(out / f'{cid}_after.npz', allow_pickle=False) as packet:
            assert packet['pixel_confusion'].shape == (7, 4)
            assert (packet['pixel_confusion'].sum(1) == 512**2).all()


def test_operating_point_audit_exposes_head_threshold_disagreement():
    from scripts.diagnose_learning import operating_point_audit
    from scripts.run_matrix import Sample
    truth = np.zeros((8,8), bool)
    truth[0,0] = True
    samples = [Sample(np.zeros((13,1,1), np.float16), np.zeros(4, np.float32),
                      np.zeros((3,8,8), np.uint8), np.array([[cls]], bool),
                      truth.copy() if cls else np.zeros_like(truth), cls,
                      'T1' if cls else 'none', 'NV') for cls in (1,0)]
    pixels = [np.where(truth, .4, .1), np.full((8,8), .1)]
    audit = operating_point_audit(samples, [np.array([[.9]]), np.array([[.6]])], pixels)
    assert audit['shared_rule']['balanced_accuracy'] == 1.
    assert audit['shared_rule']['tampered_pixel_iou'] == 0.
    assert audit['pixel_only_training_diagnostic']['tampered_pixel_iou'] == 1.
    assert audit['pixel_only_training_diagnostic']['intact_positive_pixel_counts'] == [0]
    assert 'TRAIN-only' in audit['warning']
