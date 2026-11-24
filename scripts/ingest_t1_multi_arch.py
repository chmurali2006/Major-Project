"""Validate a T1 Kaggle result ZIP and build compact model comparison tables.

This ingests TRAIN/validation-only outputs. It does not access TEST data.
"""
import argparse,csv,gzip,json,zipfile
from pathlib import Path

EXPECTED_COHORT='c524a43fce2951dbd68514a94d60610a8daa4f88fd40b8b93c53ee1f03f5aa42'
EXPECTED_MODELS=('densenet121_base','densenet121_aug','resnet50_aug')
EXPECTED_CASES=('intact','copy32','local_blur32_surrogate','jpeg70','jpeg85','jpeg95','resize90_restore','contrast90','contrast110','gaussian05')
BASE_ROWS=Path(__file__).resolve().parents[1]/'deliverables/verification-evidence/classifier-impact-return-v1/predictions.jsonl.gz'

def _member(z,suffix):
    m=[n for n in z.namelist() if n.endswith(suffix)]
    if len(m)!=1:raise ValueError(f'expected one ZIP member ending {suffix!r}; found {len(m)}')
    return m[0]

def _jsonl(z,name):
    return [json.loads(line) for line in z.read(name).decode().splitlines() if line.strip()]

def _metric_row(model,case,m):
    rec=m['received'];delta=m['paired_differences']
    sens=rec['per_class_sensitivity']
    def d(name):return delta[name]['received_minus_clean']
    def ci(name):
        v=delta[name]['paired_percentile95'];return v if v is not None else [None,None]
    return {'model':model,'case':case,'n':m['n'],'accuracy':rec['accuracy'],
        'balanced_accuracy':rec['balanced_accuracy'],'macro_f1':rec['macro_f1'],'roc_auc':rec['binary_roc_auc'],
        'nonMEL_specificity':sens[0],'MEL_sensitivity':sens[1],
        'delta_accuracy_pp':None if d('accuracy') is None else 100*d('accuracy'),
        'delta_balanced_accuracy_pp':None if d('balanced_accuracy') is None else 100*d('balanced_accuracy'),
        'delta_MEL_sensitivity_pp':None if sens[1] is None or m['clean']['per_class_sensitivity'][1] is None else 100*(sens[1]-m['clean']['per_class_sensitivity'][1]),
        'delta_BA_ci95_low_pp':None if ci('balanced_accuracy')[0] is None else 100*ci('balanced_accuracy')[0],
        'delta_BA_ci95_high_pp':None if ci('balanced_accuracy')[1] is None else 100*ci('balanced_accuracy')[1]}

def ingest(results_zip,out_dir):
    out=Path(out_dir)
    out.mkdir(parents=True,exist_ok=True)
    targets=[out/'table_multi_arch_diagnostic_drift.csv',out/'table_editguard_ssim_and_multi_arch.csv',out/'t1-ingestion-summary.json']
    if any(p.exists() for p in targets):raise ValueError('refusing to overwrite existing T1 tables')
    with zipfile.ZipFile(results_zip) as z:
        if z.testzip() is not None:raise ValueError('corrupt ZIP')
        table=[];edit=[];reference={}
        with gzip.open(BASE_ROWS,'rt') as f:
            for line in f:
                r=json.loads(line)
                if r['case'] in EXPECTED_CASES:reference[(r['image_id'],r['case'])]=r
        if len(reference)!=500*len(EXPECTED_CASES):raise ValueError('historical baseline reference row count mismatch')
        for model in EXPECTED_MODELS:
            prefix=model+'/'
            sm=json.loads(z.read(_member(z,prefix+'operator-evaluation/summary.json')))
            if sm.get('completed') is not True or sm.get('test_accessed') is not False or sm.get('images')!=500 or sm.get('cohort_sha256')!=EXPECTED_COHORT:raise ValueError('incomplete/out-of-scope operator result')
            if set(sm['cases'])!=set(EXPECTED_CASES):raise ValueError('unexpected operator cases')
            rows=_jsonl(z,_member(z,prefix+'operator-evaluation/predictions.jsonl'))
            if len(rows)!=5000:raise ValueError('operator prediction row count mismatch')
            seen=set()
            for r in rows:
                key=(r['image_id'],r['case'])
                if key in seen or key not in reference:raise ValueError('duplicate/unmatched image-case row')
                seen.add(key);old=reference[key]
                if (r['label']!=old['label'] or r['seed']!=old['operator_seed'] or
                    r['source_rgb_sha256']!=old['source_rgb_sha256'] or
                    r['received_rgb_sha256']!=old['received_rgb_sha256']):
                    raise ValueError('source/operator pairing differs from retained Model-0 validation record')
            if len(seen)!=5000:raise ValueError('missing operator rows')
            for case in EXPECTED_CASES:table.append(_metric_row(model,case,sm['cases'][case]))
            eg=json.loads(z.read(_member(z,prefix+'editguard-paired/summary.json')))
            if eg.get('schema')!='t1-editguard-paired-v1' or eg.get('test_accessed') is not False or eg.get('images')!=500 or eg.get('cohort_sha256')!=EXPECTED_COHORT:raise ValueError('invalid EditGuard paired output')
            if set(eg['cases'])!={'intact','copy32','jpeg70','jpeg85','gaussian05'}:raise ValueError('EditGuard case mismatch')
            rows=_jsonl(z,_member(z,prefix+'editguard-paired/paired-predictions.jsonl'))
            if len(rows)!=500 or len({r['image_id'] for r in rows})!=500:raise ValueError('EditGuard paired prediction rows mismatch')
            expected_ids={ident for ident,case in reference if case=='intact'}
            if {r['image_id'] for r in rows}!=expected_ids:raise ValueError('EditGuard cohort membership mismatch')
            for r in rows:
                old=reference[(r['image_id'],'intact')]
                if r['label']!=old['label'] or r['source_rgb_sha256']!=old['source_rgb_sha256']:
                    raise ValueError('EditGuard source/label pairing differs from retained validation cohort')
            fid=eg['marking_fidelity']
            metrics=[('marked_intact','',eg['marked_intact_vs_original_intact'])]
            for case,contrasts in eg['cases'].items():
                metrics.extend((('operator_without_embedding',case,contrasts['operator_without_embedding']),
                                ('embedding_given_operator',case,contrasts['embedding_given_operator']),
                                ('total_embedding_plus_operator',case,contrasts['total_embedding_plus_operator'])))
            for contrast,case,m in metrics:
                r=_metric_row(model,contrast+('_'+case if case else ''),m)
                r.update({'editguard_mean_mse':fid['mean_mse'],'editguard_mean_per_image_psnr_db':fid['mean_per_image_psnr_db'],
                          'editguard_mean_ssim':fid['mean_ssim'],'editguard_checkpoint_sha256':eg['editguard_checkpoint_sha256']})
                edit.append(r)
        out.mkdir(parents=True,exist_ok=True)
        with (out/'table_multi_arch_diagnostic_drift.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
        with (out/'table_editguard_ssim_and_multi_arch.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(edit[0]));w.writeheader();w.writerows(edit)
        summary={'completed_ingestion':True,'cohort_sha256':EXPECTED_COHORT,'models':list(EXPECTED_MODELS),
                 'standard_operator_rows':len(table),'editguard_contrast_rows':len(edit),'test_accessed':False,
                 'reference_match':'All three model runs matched the prior validation source/operator hashes and seeds.'}
        (out/'t1-ingestion-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--results-zip',type=Path,required=True);p.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'deliverables/tables');a=p.parse_args()
    print(json.dumps(ingest(a.results_zip,a.out),indent=2))
