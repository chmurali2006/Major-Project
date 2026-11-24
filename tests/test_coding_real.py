import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import numpy as np
from experiment_coding_real import run
from build_coding_notebook import build_coding


def test_fixture_comparison_and_exports(tmp_path):
    root=tmp_path/'evidence';r=run(n=1,artifacts=root)
    assert r['synthetic'] is True and len(r['rows'])==24
    assert {s['method']:s['sidecar_bytes'] for s in r['setup']}=={'bounded289':18620,'index288':18558,'set330':18606,'full4':524378}
    assert len(list(root.glob('*.bin')))==5
    with np.load(root/'000-maps.npz',allow_pickle=False) as maps:
        for row in r['rows']:
            assert row['map_matches_truth'] is not False
            if row['fine_map_available']:
                assert row['missed_pixels']==0
                assert np.array_equal(maps[row['case']+'-truth'],maps[row['case']+'-'+row['method']])
            else:assert row['missed_pixels'] is None and row['pixel_iou'] is None
    assert not list(root.glob('*.png'))


def test_notebook_compiles_and_contains_complete_runner():
    nb=build_coding();source='\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
    for c in nb['cells']:
        if c['cell_type']=='code':compile(''.join(c['source']),'cell','exec')
    assert "len(result['rows'])==768" in source
    assert "'--artifacts'" in source and "'artifacts/'+path.name" in source
    assert 'coding32-development-results.zip' in source
