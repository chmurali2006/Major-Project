import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def test_embedded_sources_and_actual_export_cell(tmp_path):
    spec=importlib.util.spec_from_file_location('builder',ROOT/'scripts/build_isic_classifier_notebook.py')
    b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);nb=b.build()
    for c in nb['cells']:
        if c['cell_type']=='code':compile(''.join(c['source']),'<notebook>','exec')
    # Execute real decode cell with existing receipt to avoid invoking preparation.
    work=tmp_path;prep=tmp_path/'prep';prep.mkdir();(prep/'preparation.json').write_text('{}')
    scope={'WORK':work,'PREPARATION':prep,'INPUT':tmp_path,'base64':base64,'hashlib':hashlib,'io':io,'zipfile':zipfile}
    exec(''.join(nb['cells'][2]['source']),scope)
    for name in b.FILES:assert (scope['CODE']/name).read_bytes()==(ROOT/name).read_bytes()
    out=work/'training';out.mkdir();(out/'best.pt').write_bytes(b'fixture checkpoint')
    (out/'protocol.json').write_text('{}');(out/'summary.json').write_text('{"completed":true}')
    (work/'classifier-initialization.json').write_text('{}')
    (out/'secret-image.png').write_bytes(b'must not export')
    scope.update({'OUT':out,'json':json})
    exec(''.join(nb['cells'][-1]['source']),scope)
    with zipfile.ZipFile(scope['PACKAGE']) as z:
        assert 'best.pt' in z.namelist() and 'secret-image.png' not in z.namelist()
        assert {'cohort.json','preparation.json','initialization.json'}<=set(z.namelist())
        assert z.testzip() is None
