"""Exploratory probability analysis of previously inspected validation receipts.

A clean-derived threshold is frozen across received conditions; received
specificity is allowed to change and is reported. No calibration/causality claim.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from src.diagnostic_impact import scores,binary_auc


def threshold_for_specificity(labels,probabilities,target=.9):
    y=np.asarray(labels);p=np.asarray(probabilities,dtype=float)
    if y.shape!=p.shape or not np.isin(y,[0,1]).all() or not np.isfinite(p).all() or not (y==0).any() or not 0<target<=1:
        raise ValueError('finite binary data with negatives and valid target required')
    negatives=p[y==0]
    # predict MEL for score >= threshold; nextafter handles ties conservatively.
    candidates=np.r_[0.,np.nextafter(np.unique(negatives),np.inf)]
    return float(next(t for t in sorted(candidates) if np.mean(negatives<t)>=target))


def analyse(rows,repetitions=2000):
    intact=[r for r in rows if r['case']=='intact'];ids=[r['image_id'] for r in intact]
    index={(r['image_id'],r['case']):r for r in rows}
    if len(index)!=len(rows) or not ids:raise ValueError('duplicate or empty rows')
    y=np.array([r['label'] for r in intact]);a=np.array([r['clean_probabilities'][1] for r in intact]);t=threshold_for_specificity(y,a)
    result={};rng=np.random.default_rng(7201)
    for case in dict.fromkeys(r['case'] for r in rows):
        if not all((i,case) in index for i in ids):raise ValueError('incomplete pairs')
        b=np.array([index[i,case]['received_probabilities'][1] for i in ids]);delta=b-a
        class_shift={}
        for label in (0,1):
            values=delta[y==label]
            if not len(values):raise ValueError('both classes required')
            draws=values[rng.integers(0,len(values),(repetitions,len(values)))].mean(1)
            class_shift[str(label)]={'n':len(values),'mean_MEL_probability_shift':float(values.mean()),'paired_image_mean95':np.quantile(draws,[.025,.975]).tolist()}
        fixed=scores(y,(b>=t).astype(int),2);argmax=scores(y,np.array([index[i,case]['received_probabilities'] for i in ids]).argmax(1),2)
        result[case]={'class_specific_shift':class_shift,'fixed_clean_threshold_metrics':fixed,'argmax_metrics':argmax,'auc':binary_auc(y,b)}
    return {'schema':'exploratory-class-sensitive-drift-v1','threshold':t,'threshold_selection':'smallest nonnegative score cutoff attaining >=90% intact validation specificity; predict MEL if score>=cutoff; same cutoff all operations',
            'bootstrap_repetitions':repetitions,'bootstrap_seed':7201,'cases':result,
            'limits':['Post-hoc descriptive validation analysis after seeing original results; not an independently preregistered clinical operating point.',
                      'Specificity is targeted only on intact validation, not re-fitted on each operation. Actual received specificity is reported.',
                      'Probability drift/AUC do not establish feature destruction, calibration error or causal mechanism.',
                      'Paired image intervals conditional on class support, not patient-level; no multiplicity correction.']}

def drift_figure(result,path):
    import matplotlib.pyplot as plt
    cases=result['cases'];names=[n for n in cases if n!='intact']
    base=cases['intact']['argmax_metrics']
    x=[];y=[]
    for case in names:
        m=cases[case]['argmax_metrics'];x.append(100*(m['accuracy']-base['accuracy']))
        y.append(100*(m['per_class_sensitivity'][1]-base['per_class_sensitivity'][1]))
    fig,ax=plt.subplots(figsize=(9,6));ax.axhline(0,color='#777',lw=1);ax.axvline(0,color='#777',lw=1)
    colors=['#b23a48' if n.startswith(('fgsm','pgd')) else '#276FBF' for n in names]
    ax.scatter(x,y,c=colors,s=48,zorder=3)
    for xx,yy,n in zip(x,y,names):ax.annotate(n,(xx,yy),xytext=(5,4),textcoords='offset points',fontsize=8)
    ax.set_xlabel('Change in accuracy vs. intact (percentage points)')
    ax.set_ylabel('Change in MEL sensitivity vs. intact (percentage points)')
    ax.set_title('Validation-set diagnostic drift by operator (exploratory)')
    ax.text(.01,.01,'Blue: image operations; red: adapted white-box attacks. Accuracy can hide MEL sensitivity changes.',transform=ax.transAxes,fontsize=8,color='#444')
    ax.grid(alpha=.2);fig.tight_layout();fig.savefig(path,dpi=180);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    source=ROOT/'deliverables/verification-evidence/classifier-impact-return-v1/predictions.jsonl.gz'
    rows=[json.loads(r) for r in gzip.decompress(source.read_bytes()).splitlines()]
    result=analyse(rows);result['source_gzip_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    args.out.mkdir(parents=True,exist_ok=False);(args.out/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    drift_figure(result,args.out/'accuracy-vs-melanoma-sensitivity.png')
    lines=['CLASS-SENSITIVE PROBABILITY DRIFT — EXPLORATORY VALIDATION ANALYSIS',*result['limits'],'',f"Fixed clean-derived threshold: {result['threshold']:.12f}",'Case | mean dP(MEL), true nonMEL | mean dP(MEL), true MEL | sensitivity at frozen threshold | actual specificity at frozen threshold']
    for case,r in result['cases'].items():
        sens=r['fixed_clean_threshold_metrics']['per_class_sensitivity'];lines.append(f"{case} | {r['class_specific_shift']['0']['mean_MEL_probability_shift']:+.6f} | {r['class_specific_shift']['1']['mean_MEL_probability_shift']:+.6f} | {sens[1]:.6f} | {sens[0]:.6f}")
    (args.out/'findings.txt').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
