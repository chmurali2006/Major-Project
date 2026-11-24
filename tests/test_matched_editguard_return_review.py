import importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('matched_return_review',ROOT/'scripts/review_matched_editguard_validation.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_sent_notebook_bundle_can_be_read_without_execution():
    bundle=m.embedded_bundle(ROOT/'deliverables/matched_editguard_validation_v1.ipynb')
    import io,zipfile
    with zipfile.ZipFile(io.BytesIO(bundle)) as z:
        names=set(z.namelist())
        assert 'scripts/experiment_matched_editguard_validation.py' in names
        assert 'src/isic_classifier_training.py' in names
        assert 'cohort.json' in names


def test_packaging_cell_includes_public_verification_key():
    notebook=__import__('json').loads((ROOT/'deliverables/matched_editguard_validation_v1.ipynb').read_text())
    package_cell=''.join(notebook['cells'][6]['source'])
    assert "z.write(OUT/'public-key.bin','public-key.bin')" in package_cell


def test_probability_and_packed_mask_validation():
    truth=np.zeros((512,512),dtype=bool);truth[12,7]=1
    packed=np.packbits(truth).tobytes()
    assert np.array_equal(m.packed_map(packed),truth)
    assert m.confusion(truth,truth)=={'tp':1,'fp':0,'fn':0,'tn':512*512-1}
    import pytest
    with pytest.raises(ValueError):m.packed_map(b'bad')
    with pytest.raises(ValueError):m.probability([.4,.4])
