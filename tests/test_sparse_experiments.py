import ast
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sweep_sparse_capacity import locations,summarise
from experiment_sparse_real import run
from build_sparse_notebook import build_sparse


def test_patterns_exact_distinct_counts():
    for pattern in ('distributed','clustered'):
        for count in (16,32,64,128,256,512):
            indices=locations(123,count,pattern)
            assert len(indices)==len(set(indices))==count
            assert min(indices)>=0 and max(indices)<128**2
            assert np.array_equal(indices,locations(123,count,pattern))


def test_unavailable_results_stay_in_denominators():
    rows=[dict(buckets=128,changed_tiles=64,pattern='distributed',sidecar_bytes=7294,
               fine_map_available=v,verdict='FAILED_INTEGRITY',map_matches_truth=True if v else None) for v in (True,False,False)]
    r=summarise(rows)[0]
    assert r['trials']==3 and r['fine_maps']==1 and r['unavailable']==2


def test_real_runner_fixture_and_notebook_contract():
    result=run(n=1)
    assert result['synthetic'] is True and len(result['rows'])==18
    assert all(r['map_matches_truth'] is not False for r in result['rows'])
    for r in result['rows']:
        if not r['fine_map_available']:
            assert r['missed_pixels'] is None and r['pixel_iou'] is None
    nb=build_sparse()
    for c in nb['cells']:
        if c['cell_type']=='code':ast.parse(''.join(c['source']))
    last=''.join(nb['cells'][-1]['source'])
    assert "len(result['rows'])==576" in last and 'sparse32-development-results.zip' in last
