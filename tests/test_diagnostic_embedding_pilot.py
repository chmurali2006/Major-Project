import importlib.util
import json
from pathlib import Path
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class Toy(torch.nn.Module):
    def __init__(self,sign=1):
        super().__init__();self.register_buffer('sign',torch.tensor(float(sign)))
    def forward(self,x):
        v=(x[:,0,0,0]+self.sign*x[:,2,0,1])
        return torch.stack((v,-v),1)


def test_train_only_pilot_controls_recovery_and_signed_evidence(tmp_path):
    fixture=load('training_fixture',ROOT/'tests/test_isic_classifier_training.py')
    runner=load('candidate',ROOT/'scripts/experiment_diagnostic_embedding.py')
    from src.diagnostic_constrained_embedding import Settings
    p,c=fixture.prepared(tmp_path)
    # Make validation inaccessible: no evaluation image may be opened by this pilot.
    for path in (p/'prepared').glob('image[23].png'):path.unlink()
    result=runner.run(Toy().eval(),p,c,tmp_path/'out',{'checkpoint_sha256':'guide fixture'},
        evaluator=Toy(-1).eval(),evaluator_identity={'checkpoint_sha256':'distinct evaluator fixture'},n=2,settings=Settings(steps=2),repetitions=100)
    assert result['completed'] and result['rows']==12 and result['independent_evaluator_tested']
    rows=[json.loads(line) for line in (tmp_path/'out/rows.jsonl').read_text().splitlines()]
    assert {r['image_id'] for r in rows}=={'image0','image1'}
    for ident in ('image0','image1'):
        indexed={r['variant']:r for r in rows if r['image_id']==ident}
        assert indexed['energy_matched_random']['embedding_mse']==indexed['diagnostic_correction']['embedding_mse']
        assert indexed['fixed_qim']['qim_step']==indexed['diagnostic_correction']['qim_step']
        assert indexed['uniform_weaker_qim']['qim_step']<indexed['fixed_qim']['qim_step']
        assert indexed['query_matched_random']['optimization_forward_queries']==indexed['diagnostic_correction']['optimization_forward_queries']==7
        assert indexed['distortion_gated_correction']['embedding_mse']==indexed['fixed_qim']['embedding_mse']
        assert len({r['payload_sha256'] for r in indexed.values()})==1
    assert len(list((tmp_path/'out/artifacts').glob('*.bin')))==12
    for r in rows:
        assert r['signed_evidence_bytes']==524378
        assert next(v for v in r['recovery'] if v['case']=='intact')['payload_bit_errors']==0
        assert next(v for v in r['recovery'] if v['case']=='intact')['signed_rgb_verdict']=='VERIFIED'
