import importlib.util
import json
from pathlib import Path
import torch

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class FixtureClassifier(torch.nn.Module):
    def __init__(self):
        super().__init__();self.register_buffer('scale',torch.tensor(1.))
    def forward(self,x):
        value=x.mean((1,2,3))*self.scale
        return torch.stack((value,-value),1)


def test_all_operators_and_quantized_adversarial_predictions(tmp_path):
    fixture=load('training_fixture',ROOT/'tests/test_isic_classifier_training.py')
    runner=load('evaluation',ROOT/'scripts/evaluate_adapted_classifier.py')
    p,c=fixture.prepared(tmp_path)
    result=runner.run(FixtureClassifier().eval(),p,c,tmp_path/'out',{'checkpoint_sha256':'synthetic fixture, not trained'},repetitions=100)
    assert result['completed'] and result['images']==2 and result['rows']==24
    assert not result['test_evaluated']
    assert result['cases']['intact']['prediction_flips']==0
    for case in ('fgsm4_adapted','pgd4_adapted'):
        assert 'untargeted_success' in result['cases'][case]
    rows=[json.loads(line) for line in (tmp_path/'out/predictions.jsonl').read_text().splitlines()]
    assert all(r['linf_rgb']<=4 for r in rows if r['family']=='adapted_adversarial')
    assert all(r['changed_pixels']==0 for r in rows if r['case']=='intact')
    assert {r['image_id'] for r in rows}=={'image2','image3'}
