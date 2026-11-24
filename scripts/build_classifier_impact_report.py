"""Build a compact report from the reviewed impact return, not raw headline scores."""
import csv
import gzip
import hashlib
import html
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]

def build():
    evidence=ROOT/'deliverables/verification-evidence/classifier-impact-return-v1'
    review=json.loads((evidence/'review.json').read_text())
    summary=json.loads((evidence/'recomputed-summary.json').read_text())
    archive=ROOT/'google_drive/adapted-isic2500-classifier-impact-v1-results.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=review['zip_sha256']:raise ValueError('reviewed archive changed')
    with zipfile.ZipFile(archive) as z:raw=z.read('predictions.jsonl')
    (evidence/'predictions.jsonl.gz').write_bytes(gzip.compress(raw,mtime=0))
    fields=['case','balanced_accuracy_percent','melanoma_sensitivity_percent','roc_auc','flips','correct_to_wrong','wrong_to_correct','delta_ba_percentage_points','paired95_low_pp','paired95_high_pp']
    # Guard the explanatory prose against stale or substituted evidence.
    jpeg=summary['cases']['jpeg70'];pgd=summary['cases']['pgd4_adapted']
    assert jpeg['clean']['confusion_matrix']==[[399,45],[23,33]]
    assert jpeg['received']['confusion_matrix'][1][1]==22
    assert abs(jpeg['received']['accuracy']-.892)<1e-12
    assert (jpeg['correct_to_wrong'],jpeg['wrong_to_correct'])==(14,28)
    assert pgd['untargeted_success']['clean_correct_numerator']==430
    assert pgd['untargeted_success']['clean_correct_denominator']==432
    rows=[]
    for case,m in summary['cases'].items():
        delta=m['paired_differences']['balanced_accuracy'];ci=delta['paired_percentile95']
        rows.append(dict(zip(fields,[case,100*m['received']['balanced_accuracy'],100*m['received']['per_class_sensitivity'][1],m['received']['binary_roc_auc'],m['prediction_flips'],m['correct_to_wrong'],m['wrong_to_correct'],100*delta['received_minus_clean'],100*ci[0],100*ci[1]])))
    with (evidence/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    table=''
    for r in rows:
        values=[r['case'],f"{r[fields[1]]:.2f}",f"{r[fields[2]]:.2f}",f"{r['roc_auc']:.4f}",str(r['flips']),f"{r['correct_to_wrong']} / {r['wrong_to_correct']}",f"{r[fields[7]]:+.2f} [{r[fields[8]]:+.2f}, {r[fields[9]]:+.2f}]"]
        table+='<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in values)+'</tr>'
    text='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Reviewed classifier impact — validation500</title>
<style>body{font:16px/1.55 system-ui;max-width:1150px;margin:40px auto;padding:0 24px;color:#172334}h1,h2{line-height:1.2}table{border-collapse:collapse;font-size:14px;width:100%}th,td{padding:9px;border-bottom:1px solid #ccd5df;text-align:left}th{background:#eaf0f7}.note{padding:18px;background:#fff3d8;border-left:4px solid #ba7100}code{overflow-wrap:anywhere}footer{font-size:13px}</style>
<h1>Frozen classifier impact: reviewed validation results</h1>
<p>500 ISIC images · 444 nonMEL / 56 MEL · 12 cases · 6,000 records · DenseNet121 epoch 3</p>
<div class="note"><strong>Development evidence, not clinical safety or final-test performance.</strong> This experiment operates on original images. It does not measure watermark-induced effects or validate the diagnostic-correction candidate.</div>
<h2>What passed review</h2><p>ZIP CRC/membership, returned Python source identity against the sent notebook, fixed cohort and checkpoint identity, declared protocol, complete image–case matrix, labels, finite probabilities, seeds, recorded change/hash consistency and attack bounds. All summary metrics and 2,000-repetition paired bootstrap intervals were recomputed from stored predictions. Clean-probability maximum difference from the training receipt: <strong>MAXDIFF</strong>.</p>
<h2>Results</h2><p>BA = balanced accuracy; sensitivity is for melanoma. Delta is received minus clean, in percentage points. Intervals are paired class-stratified image-bootstrap 95% intervals. C→W / W→C are correct-to-wrong / wrong-to-correct counts.</p>
<table><thead><tr><th>Case</th><th>BA %</th><th>MEL sensitivity %</th><th>ROC AUC</th><th>Flips /500</th><th>C→W / W→C</th><th>Δ BA pp [95% interval]</th></tr></thead><tbody>TABLE</tbody></table>
<h2>Interpretation that the evidence supports</h2>
<ul><li><strong>Local modifications are not necessarily visible to a global classifier.</strong> The random copy patch yields 4 flips and the local-blur surrogate 1. Neither operator is verified semantic lesion removal. This does not imply tampering is harmless or that authentication is unnecessary.</li>
<li><strong>JPEG70 has a class-dependent effect.</strong> Melanoma sensitivity falls from 33/56 to 22/56, while overall accuracy rises from 86.4% to 89.2% (14 correct→wrong versus 28 wrong→correct). Accuracy alone would conceal the minority-class deterioration. BA falls 7.01 percentage points; its unadjusted paired interval is approximately −13.14 to −1.31 pp.</li>
<li><strong>The frozen model is vulnerable to the adapted white-box attacks.</strong> FGSM makes 80/432 initially correct predictions wrong (18.52%); PGD makes 430/432 wrong (99.54%). Overall wrong predictions are 138/500 and 498/500 respectively. These denominators must not be confused.</li>
<li><strong>PGD is not a universal attacker result.</strong> It uses access to this classifier's input gradients and ground-truth labels, clean-start untargeted cross-entropy ascent, RGB epsilon 4/255, 3 steps of 1/255, and integer output evaluation. No transfer/black-box or exact author attack reproduction is established.</li></ul>
<h2>What this means for the project</h2><p>Integrity detection and classifier impact answer different questions. A content change can matter for authenticity without changing the global diagnosis prediction; a visually modest operation can affect this model's sensitivity. These observations motivate measuring both endpoints separately. They do not establish a benefit for the implemented correction, explain its historical motivation retrospectively, or resolve its additional-distortion limitation. The next extension experiment remains the bounded TRAIN pilot with six controls; independent-model evaluation is needed before transfer claims.</p>
<h2>Limitations and exclusions</h2><ul><li>Stored predictions were audited, not independently rerun on the source images. Image/operator/attack output pixels were not returned for independent replay.</li><li>Validation selected the checkpoint. Intervals are descriptive, conditional on observed class counts, not patient-level; no multiple-comparison correction. Do not infer clinical significance or equivalence from interval overlap with zero.</li><li>The clean model already misses 23/56 melanomas. No calibration, human clinical review, clinical safety, novel mechanism or SOTA claim follows.</li><li>No test-split evaluation was run by this review. The returned summary declares test_evaluated=false and returned source matches the validation-only notebook.</li></ul>
<footer><h2>Provenance</h2><p>Reviewed ZIP SHA256: <code>ZIPHASH</code><br>Checkpoint SHA256: <code>CKHASH</code><br>Sent notebook SHA256: <code>NBHASH</code></p><p>Evidence directory: <code>deliverables/verification-evidence/classifier-impact-return-v1/</code>. Includes review receipt, protocol, returned/recomputed summary, CSV and compressed per-image predictions. Rebuild using <code>.venv/bin/python scripts/build_classifier_impact_report.py</code>.</p></footer></html>'''
    text=text.replace('MAXDIFF',str(review['max_clean_probability_difference_from_training_receipt'])).replace('TABLE',table).replace('ZIPHASH',review['zip_sha256']).replace('CKHASH',review['checkpoint_sha256']).replace('NBHASH',review['sent_notebook_sha256'])
    out=ROOT/'deliverables/classifier-impact-validation500-review.html';out.write_text(text)
    files=sorted(p for p in evidence.iterdir() if p.is_file() and p.name!='artifact-hashes.json')
    (evidence/'artifact-hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n')
    return out

if __name__=='__main__':print(build())
