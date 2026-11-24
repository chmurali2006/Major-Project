import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('review',ROOT/'scripts/review_adapted_validation.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def test_empty_return_rejected_before_output(tmp_path):
    with pytest.raises(ValueError,match='missing member'):
        r.review([],ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json',tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_duplicate_parts_rejected_before_output(tmp_path):
    import zipfile
    p=tmp_path/'part.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('protocol.json','{}')
    with pytest.raises(ValueError,match='duplicate archive member'):
        r.review([p,p],ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json',tmp_path/'out')
    assert not (tmp_path/'out').exists()
