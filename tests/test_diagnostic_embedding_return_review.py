import copy
import gzip
import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('embedding_review',ROOT/'scripts/review_diagnostic_embedding_return.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def receipts():
    path=ROOT/'deliverables/verification-evidence/diagnostic-embedding-train12-return-v1/rows.jsonl.gz'
    rows=[json.loads(line) for line in gzip.decompress(path.read_bytes()).splitlines()]
    prep=json.loads((ROOT/'deliverables/verification-evidence/adapted-isic2500-preparation-v2/preparation.json').read_text())
    return rows,[q for q in prep['selected'] if q['split']=='train'][:12]


def test_reviewed_real_receipt_matrix_and_controls():
    rows,selected=receipts();index=r.validate_rows(rows,selected)
    assert len(index)==72
    assert len(selected)==12 and sum(v['melanoma_label'] for v in selected)==2
    assert sum(r.kl(index[i['image_id'],'diagnostic_correction'])<r.kl(index[i['image_id'],'fixed_qim'])-1e-7 for i in selected)==1


@pytest.mark.parametrize('defect',['missing','duplicate','label','recovery','query','gate','energy','probability'])
def test_corrupted_receipt_fails(defect):
    rows,selected=receipts();rows=copy.deepcopy(rows)
    if defect=='missing':rows.pop()
    elif defect=='duplicate':rows[1]=copy.deepcopy(rows[0])
    elif defect=='label':rows[0]['label']=1-rows[0]['label']
    elif defect=='recovery':rows[0]['recovery'][0]['payload_bit_errors']=1
    elif defect=='query':rows[0]['optimization_forward_queries']=1
    elif defect=='gate':next(v for v in rows if v['variant']=='distortion_gated_correction')['embedding_mse']=999.
    elif defect=='energy':next(v for v in rows if v['variant']=='energy_matched_random')['embedding_mse']=999.
    elif defect=='probability':rows[0]['probabilities']['guide']=[.9,.9]
    with pytest.raises(ValueError):r.validate_rows(rows,selected)
