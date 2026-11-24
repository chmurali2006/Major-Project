import pytest
from src.grouping_audit import audit_grouping


def test_missing_metadata_is_not_patient_independence(tmp_path):
    labels=tmp_path/'labels.csv';labels.write_text('image,MEL\na,1\nb,1\nc,1\n')
    assert audit_grouping(labels)['status']=='metadata_missing'
    meta=tmp_path/'meta.csv';meta.write_text('image,patient_id,lesion_id\na,p1,l1\nb,p1,l1\nc,,l2\n')
    report=audit_grouping(labels,meta,prior_ids=['a'])
    assert report['ready_fields']==['lesion_id']
    assert report['fields']['patient_id']['missing_labelled_ids']==1
    assert report['fields']['lesion_id']['remaining_candidate_ids']==1
    assert report['fields']['lesion_id']['multi_image_groups']==1


def test_duplicate_metadata_refused(tmp_path):
    labels=tmp_path/'labels.csv';labels.write_text('image\na\n')
    meta=tmp_path/'meta.csv';meta.write_text('image,patient_id\na,p\na,p\n')
    with pytest.raises(ValueError,match='duplicate'):audit_grouping(labels,meta)


def test_followup_notebook_gated_bound_and_excludes_both_pilots():
    import ast,sys,json,base64,zipfile,io,hashlib
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'scripts'))
    from build_editguard_pilot_notebook import FILES
    from build_grouped_comparison_notebook import build_followup
    before=list(FILES)
    nb=build_followup()
    assert FILES==before
    cells=[''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code']
    for text in cells:ast.parse(text)
    config=next(c for c in cells if 'RUN_EVALUATION=False' in c)
    assert 'PER_CLASS=4' in config
    assignment=next(n for n in ast.parse(config).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='PRIOR_EVALUATION_IDS')
    assert len(ast.literal_eval(assignment.value))==16
    preflight=next(c for c in cells if 'metadata_audit=audit_grouping' in c)
    assert preflight.index('if not RUN_EVALUATION:')<preflight.index('if METADATA is not None or')
    bootstrap=ast.parse(cells[0]);values={n.targets[0].id:ast.literal_eval(n.value) for n in bootstrap.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('SOURCE_B64','EXPECTED_SOURCE_ARCHIVE_SHA256')}
    raw=base64.b64decode(values['SOURCE_B64'])
    assert hashlib.sha256(raw).hexdigest()==values['EXPECTED_SOURCE_ARCHIVE_SHA256']
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert z.read('src/grouping_audit.py')==(root/'src/grouping_audit.py').read_bytes()


def test_actual_notebook_preflight_stops_before_inference(tmp_path,monkeypatch):
    import sys,json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'scripts'))
    from build_grouped_comparison_notebook import build_followup
    from src import pilot_inputs
    labels=tmp_path/'labels.csv';labels.write_text('image\na\n')
    monkeypatch.setattr(pilot_inputs,'resolve_inputs',lambda *a,**kw:dict(data=tmp_path,labels=labels,checkpoint=tmp_path/'clean.pth',labelled_image_ids=1,identity_limitation='fixture'))
    text=next(''.join(c['source']) for c in build_followup()['cells'] if 'metadata_audit=audit_grouping' in ''.join(c['source']))
    ns=dict(CODE=root,INPUT_ROOT=tmp_path,DATA=None,LABELS=None,CHECKPOINT=None,METADATA=None,
            PRIOR_EVALUATION_IDS=[],WORK=tmp_path,RUN_EVALUATION=False,Path=Path,json=json)
    with pytest.raises(RuntimeError,match='STOP before inference'):exec(text,ns)
    assert json.loads((tmp_path/'grouping-audit.json').read_text())['status']=='metadata_missing'
