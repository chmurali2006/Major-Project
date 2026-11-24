import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('capacity',ROOT/'scripts/sweep_bounded_capacity_validation.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_capacity_sweep_preserves_abstentions_and_no_test_access(tmp_path):
    import importlib.util as iu
    s=iu.spec_from_file_location('prepfixture',ROOT/'tests/test_isic_classifier_training.py');fixture=iu.module_from_spec(s);s.loader.exec_module(fixture)
    prep,cohort=fixture.prepared(tmp_path)
    result=m.run(prep,cohort,tmp_path/'out',n=2)
    assert result['images']==2 and result['rows']==20
    protocol=json.loads((tmp_path/'out/protocol.json').read_text())
    assert protocol['split']=='validation' and protocol['test_evaluated'] is False
    rows=[json.loads(x) for x in (tmp_path/'out/rows.jsonl').read_text().splitlines()]
    assert all(r['fine_map_available'] or r['tile_confusion'] is None for r in rows)
    assert all(r['map_matches_truth'] is True for r in rows if r['fine_map_available'])
