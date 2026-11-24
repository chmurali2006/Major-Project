import hashlib
import io
import json
from pathlib import Path
import shutil
import zipfile
import numpy as np
import pytest
from src.comparison_results_audit import audit,_json,_arrays

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'deliverables/verification-evidence/editguard-synthetic-smoke-v1'


@pytest.fixture
def copied(tmp_path):
    target=tmp_path/'receipt';shutil.copytree(EVIDENCE,target)
    return target


def mutate_report(path,change):
    report=json.loads((path/'report.json').read_text());change(report)
    (path/'report.json').write_text(json.dumps(report))


def test_actual_evidence_directory_recomputes_every_case():
    r=audit(EVIDENCE)
    assert r['verified_cases']==36 and r['sample_count']==2
    assert not r['safety_or_superiority_established']
    intact=next(x for x in r['summary'] if x['method']=='Classical baseline' and x['case']=='intact')
    assert intact['mean_iou_defined_cases'] is None and intact['defined_iou_cases']==0
    brightness=next(x for x in r['paired_iou_differences'] if x['case']=='brightness32')
    assert brightness['classical_higher_pairs']==2


def test_notebook_zip_layout_matches_directory_audit(tmp_path):
    archive=tmp_path/'results.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in EVIDENCE.iterdir():
            if p.suffix=='.npz' or p.name=='report.json':z.write(p,'results/'+p.name)
    assert audit(archive)==audit(EVIDENCE)
    assert list(tmp_path.iterdir())==[archive]  # no extraction files


@pytest.mark.parametrize('kind',['metric','family','seed','method','case','threshold','source','artifact'])
def test_tampered_receipts_are_rejected(copied,kind):
    def change(r):
        row=r['samples'][0]['methods'][0]['cases'][0]
        if kind=='metric':row['confusion']['tp']+=1
        elif kind=='family':row['family']='edit'
        elif kind=='seed':row['source_operator_seed']+=1
        elif kind=='method':r['samples'][0]['methods'].pop()
        elif kind=='case':r['samples'][0]['methods'][0]['cases'].pop()
        elif kind=='threshold':r['threshold']['value']=.4
        elif kind=='source':r['samples'][0]['methods'][0]['source_rgb_sha256']='0'*64
        elif kind=='artifact':r['artifacts']['maps-0-0.npz']='0'*64
    mutate_report(copied,change)
    with pytest.raises(ValueError):audit(copied)


def test_score_map_cannot_disagree_with_prediction_even_after_checksum_update(copied):
    path=copied/'maps-0-0.npz'
    with np.load(path,allow_pickle=False) as z:packet={k:z[k] for k in z.files}
    packet['intact_score']=np.ones((512,512),float)
    np.savez_compressed(path,**packet)
    mutate_report(copied,lambda r:r['artifacts'].update({'maps-0-0.npz':hashlib.sha256(path.read_bytes()).hexdigest()}))
    with pytest.raises(ValueError,match='score threshold'):audit(copied)


@pytest.mark.parametrize('name',['../escape','/absolute','results/payload.py','results/image.png'])
def test_zip_rejects_paths_and_unexpected_content(tmp_path,name):
    p=tmp_path/'bad.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr(name,'bad')
    with pytest.raises(ValueError):audit(p)


def test_json_duplicate_keys_and_nonfinite_values_rejected():
    for raw in ('{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}'):
        with pytest.raises(ValueError):_json(raw)


def test_object_arrays_rejected_without_unpickling():
    buf=io.BytesIO();np.savez_compressed(buf,case_truth=np.array([[object()]],object))
    with pytest.raises(ValueError):_arrays(buf.getvalue(),{'case_truth'})


def test_oversized_declared_array_shape_rejected_before_read():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        header=io.BytesIO()
        np.lib.format.write_array_header_1_0(header,{'descr':'<f8','fortran_order':False,'shape':(999999999,999999999)})
        z.writestr('case_score.npy',header.getvalue())
    with pytest.raises(ValueError,match='512px'):_arrays(buf.getvalue(),{'case_score'})


def test_preparation_cannot_silently_omit_selected_inputs(copied):
    def change(r):
        r['input_preparation']={'complete':True,'selected':[{'image_id':'not_evaluated','prepared_rgb_sha256':'0'*64}]}
    mutate_report(copied,change)
    with pytest.raises(ValueError,match='preparation selection'):audit(copied)


def test_duplicate_source_names_rejected(copied):
    mutate_report(copied,lambda r:r['samples'][1].update(source=r['samples'][0]['source']))
    with pytest.raises(ValueError,match='duplicate evaluated source'):audit(copied)


def test_cli_audit_zip_to_json_and_html(tmp_path):
    import subprocess,sys
    archive=tmp_path/'returned.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in EVIDENCE.iterdir():
            if p.name=='report.json' or p.suffix=='.npz':z.write(p,'results/'+p.name)
    out=tmp_path/'audit.json'
    cmd=[sys.executable,str(ROOT/'scripts/audit_comparison_results.py'),'--input',str(archive),'--out',str(out)]
    proc=subprocess.run(cmd,capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    assert json.loads(out.read_text())['verified_cases']==36
    assert 'undefined' in out.with_suffix('.html').read_text()
    assert subprocess.run(cmd,capture_output=True).returncode!=0


def test_returned_kaggle_zip_recomputes_complete_image_level_pilot():
    path=ROOT/'google_drive/editguard-local-pilot-results.zip'
    result=audit(path)
    assert result['verified_cases']==144 and result['sample_count']==8
    assert not result['synthetic']
    intact=next(r for r in result['summary'] if r['method']=='EditGuard clean' and r['case']=='intact')
    assert intact['extra_pixels']==38 and intact['any_highlight_images']==6
    copied=next(r for r in result['summary'] if r['method']=='EditGuard clean' and r['case']=='copy64')
    assert copied['missed_pixels']==4145
    assert copied['mean_iou_defined_cases']==pytest.approx(.77074849724212)
