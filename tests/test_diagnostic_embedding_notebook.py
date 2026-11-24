import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('embedding_notebook',ROOT/'scripts/build_diagnostic_embedding_notebook.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
from scripts.review_isic_classifier_return import notebook_sources


def test_handoff_bundle_and_cli_import_in_isolation(tmp_path):
    notebook=b.build('a'*64);path=tmp_path/'pilot.ipynb';path.write_text(json.dumps(notebook))
    for cell in notebook['cells']:
        if cell['cell_type']=='code':compile(''.join(cell['source']),'cell','exec')
    bundle=notebook_sources(path)
    for name,raw in bundle.items():
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        if name.endswith('.py'):compile(raw,name,'exec')
    result=subprocess.run([sys.executable,str(tmp_path/'scripts/experiment_diagnostic_embedding.py'),'--help'],cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert '--guide-training' in result.stdout
    text=''.join(''.join(c['source']) for c in notebook['cells'])
    assert "summary['rows']==72" in text
    assert 'independent_evaluator_tested' in text
    assert "'artifacts'" not in text # export recursively; no silent omission of packet evidence
    assert 'evaluate_adapted_classifier.py' not in bundle
    assert b'first N fixed train rows' in bundle['scripts/experiment_diagnostic_embedding.py']


def test_actual_review_hash_required():
    with pytest.raises(ValueError):b.build('placeholder')
