"""Summarize a reviewed matched EditGuard return into compact CSV tables.

This consumes receipt rows and the audit products, never source pixels. It is a
summary of returned validation evidence, not an independent image/model replay.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np

CASES=('intact','copy32','local_blur32_surrogate','jpeg70','jpeg85','jpeg95',
       'resize90_restore','contrast90','contrast110','gaussian05')
METHODS=('EditGuard clean','Signed4 on EditGuard container')
CONTRASTS=('operator_without_embedding','embedding_given_operator','total_embedding_plus_operator')


def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def read_jsonl(data):
    return [json.loads(line) for line in data.splitlines() if line.strip()]


def divide(a,b):
    return float(a/b) if b else None


def confusion_metrics(rows):
    tp=sum(r['confusion']['tp'] for r in rows)
    fp=sum(r['confusion']['fp'] for r in rows)
    fn=sum(r['confusion']['fn'] for r in rows)
    tn=sum(r['confusion']['tn'] for r in rows)
    precision=divide(tp,tp+fp);recall=divide(tp,tp+fn)
    f1=divide(2*tp,2*tp+fp+fn)
    union=tp+fp+fn
    image_ious=[r['pixel_iou'] for r in rows if r['pixel_iou'] is not None]
    return {
        'tp':tp,'fp':fp,'fn':fn,'tn':tn,
        'pooled_pixel_precision':precision,'pooled_pixel_recall':recall,
        'pooled_pixel_f1':f1,'pooled_pixel_iou':divide(tp,union),
        'mean_per_image_iou_defined':float(np.mean(image_ious)) if image_ious else None,
        'n_images_with_defined_iou':len(image_ious),
    }


def summarize(archive,review_dir,out_dir):
    archive=Path(archive);review_dir=Path(review_dir);out_dir=Path(out_dir)
    review=json.loads((review_dir/'review.json').read_text())
    archive_hash=sha256(archive)
    if review.get('archive_sha256')!=archive_hash:raise ValueError('review does not match supplied archive hash')
    if review.get('localisation_rows')!=10000 or review.get('diagnostic_rows')!=5000:raise ValueError('review is not a complete matched return')
    if review.get('status') not in ('audited','audited_with_external_public_key','audited_with_missing_public_key'):raise ValueError('review is not an accepted audit state')
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('corrupt archive')
        rows=read_jsonl(z.read('rows.jsonl'))
        setup=read_jsonl(z.read('setup.jsonl'))
    if len(rows)!=10000 or len(setup)!=500:raise ValueError('receipt matrix size differs')
    table=[]
    for case in CASES:
        for method in METHODS:
            subset=[r for r in rows if r['case']==case and r['method']==method]
            if len(subset)!=500:raise ValueError(f'incomplete condition {case}/{method}: {len(subset)}')
            metrics=confusion_metrics(subset)
            is_intact=case=='intact'
            truth_positive=sum(r['changed_pixels']>0 for r in subset)
            positive_predictions=sum(bool(r['predicted_image_positive']) for r in subset)
            false_positive_images=sum(bool(r['predicted_image_positive']) for r in subset if r['changed_pixels']==0)
            table.append({
                'case':case,'method':method,'images':len(subset),'map_coverage':len(subset)/500,
                **metrics,
                'intact_image_false_positive_rate':divide(false_positive_images,500) if is_intact else None,
                'tampered_image_detection_rate':divide(sum(bool(r['predicted_image_positive']) for r in subset if r['changed_pixels']>0),truth_positive) if truth_positive else None,
                'complete_target_misses':sum(bool(r['complete_target_miss']) for r in subset),
                'images_with_any_predicted_mask':positive_predictions,
                'mean_extra_highlight_pixels':float(np.mean([r['extra_highlights'] for r in subset])),
                'mean_reader_seconds':float(np.mean([r['seconds'] for r in subset])),
                'median_reader_seconds':float(np.median([r['seconds'] for r in subset])),
                'p95_reader_seconds':float(np.quantile([r['seconds'] for r in subset],.95)),
                'additional_sidecar_bytes_per_image':subset[0]['additional_sidecar_bytes'],
            })
    diagnostic=json.loads((review_dir/'recomputed-diagnostic-summary.json').read_text())
    dtable=[]
    for case in CASES:
        for contrast in CONTRASTS:
            item=diagnostic[case][contrast]
            clean=item['clean'];received=item['received'];diff=item['paired_differences']
            dtable.append({
                'case':case,'contrast':contrast,'images':item['n'],
                'accuracy_clean':clean['accuracy'],'accuracy_received':received['accuracy'],
                'accuracy_delta':diff['accuracy']['received_minus_clean'],
                'accuracy_delta_ci95_low':diff['accuracy']['paired_percentile95'][0],
                'accuracy_delta_ci95_high':diff['accuracy']['paired_percentile95'][1],
                'balanced_accuracy_clean':clean['balanced_accuracy'],'balanced_accuracy_received':received['balanced_accuracy'],
                'balanced_accuracy_delta':diff['balanced_accuracy']['received_minus_clean'],
                'balanced_accuracy_delta_ci95_low':diff['balanced_accuracy']['paired_percentile95'][0],
                'balanced_accuracy_delta_ci95_high':diff['balanced_accuracy']['paired_percentile95'][1],
                'melanoma_sensitivity_clean':clean['per_class_sensitivity'][1],
                'melanoma_sensitivity_received':received['per_class_sensitivity'][1],
                'melanoma_sensitivity_delta':received['per_class_sensitivity'][1]-clean['per_class_sensitivity'][1],
                'macro_f1_delta':diff['macro_f1']['received_minus_clean'],
                'macro_f1_delta_ci95_low':diff['macro_f1']['paired_percentile95'][0],
                'macro_f1_delta_ci95_high':diff['macro_f1']['paired_percentile95'][1],
                'roc_auc_clean':clean['binary_roc_auc'],'roc_auc_received':received['binary_roc_auc'],
                'roc_auc_delta':diff['binary_roc_auc']['received_minus_clean'],
                'roc_auc_delta_ci95_low':diff['binary_roc_auc']['paired_percentile95'][0],
                'roc_auc_delta_ci95_high':diff['binary_roc_auc']['paired_percentile95'][1],
                'prediction_flips':item['prediction_flips'],'flip_rate':item['flip_rate'],
                'mean_probability_l1_shift':item['mean_probability_l1_shift'],
                'mean_true_class_probability_shift':item['mean_true_class_probability_shift'],
            })
    out_dir.mkdir(parents=True,exist_ok=False)
    for name,content in [('table_editguard_metrics.csv',table),('table_editguard_diagnostic_impact.csv',dtable)]:
        with (out_dir/name).open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(content[0]))
            writer.writeheader();writer.writerows(content)
    mse=np.array([float(r['embedding_mse']) for r in setup])
    psnr=[float(r['embedding_psnr_db']) for r in setup if r['embedding_psnr_db'] is not None]
    summary={
        'schema':'matched-editguard-validation-summary-v1','archive_sha256':archive_hash,
        'review_status':review['status'],'public_key_present':review['public_key_present'],'public_key_source':review.get('public_key_source'),
        'images':500,'localisation_rows':len(rows),'diagnostic_rows':review['diagnostic_rows'],
        'cases':list(CASES),'methods':list(METHODS),
        'distortion_receipts':{
            'mse_mean_per_image':float(mse.mean()),'mse_median_per_image':float(np.median(mse)),
            'psnr_mean_per_image':float(np.mean(psnr)) if psnr else None,
            'psnr_median_per_image':float(np.median(psnr)) if psnr else None,
            'psnr_defined_images':len(psnr),'zero_mse_images':int(np.count_nonzero(mse==0)),
        },
        'limits':[
            'Receipt/map audit only: no source pixels, operation replay, EditGuard model re-execution, or classifier re-inference.',
            'Metrics are validation/development evidence; the classifier was selected using validation.',
            'Image-level bootstrap is not patient-level inference; no patient independence is established.',
            'EditGuard and Signed4 have unequal evidence costs; Signed4 adds 524378 bytes/image to the EditGuard-marked representation.',
            'Signed packet signatures are unaudited because this return ZIP omitted public-key.bin.' if not review['public_key_present'] else 'Signatures verify under the supplied public key; issuer identity is not independently authenticated.',
            'Embedding MSE/PSNR summaries are computed from returned per-image receipts, not independently recomputed from pixels.',
        ],
    }
    (out_dir/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('--review-dir',type=Path,required=True)
    parser.add_argument('--out-dir',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(summarize(args.archive,args.review_dir,args.out_dir),indent=2))
