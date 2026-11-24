"""Paired classifier-impact measurements, not evidence of clinical safety.

The caller must freeze classifier/checkpoint and class order independently.
Inputs are paired probabilities from the SAME classifier and images before/after
one operation. Balanced accuracy/macroF1 require every declared class to occur;
missing class metrics are null, never silently dropped to improve a result.
"""
import numpy as np


def scores(labels, prediction, classes):
    truth=np.asarray(labels);pred=np.asarray(prediction)
    cm=np.zeros((classes,classes),dtype=np.int64)
    np.add.at(cm,(truth,pred),1)
    support=cm.sum(1);tp=cm.diagonal();den=2*tp+cm.sum(0)-tp+support-tp
    recall=np.divide(tp,support,out=np.zeros(classes,float),where=support>0)
    f1=np.divide(2*tp,den,out=np.zeros(classes,float),where=den>0)
    complete=bool((support>0).all())
    return {'confusion_matrix':cm.tolist(),'support':support.tolist(),
        'accuracy':float(tp.sum()/support.sum()),
        'balanced_accuracy':float(recall.mean()) if complete else None,
        'macro_f1':float(f1.mean()) if complete else None,
        'per_class_sensitivity':[float(v) if n else None for v,n in zip(recall,support)]}


def binary_auc(labels, positive_scores):
    """Mann–Whitney ROC AUC with half credit for tied positive/negative pairs."""
    y=np.asarray(labels);v=np.asarray(positive_scores,dtype=float)
    if y.ndim!=1 or not len(y) or v.shape!=y.shape or y.dtype.kind not in 'biu' or not np.isin(y,[0,1]).all() or not np.isfinite(v).all():
        raise ValueError('finite paired scores and binary labels required')
    positives=int((y==1).sum());negatives=len(y)-positives
    if not positives or not negatives:return None
    order=np.argsort(v,kind='stable');ys=y[order];vs=v[order]
    starts=np.r_[0,np.flatnonzero(vs[1:]!=vs[:-1])+1]
    ends=np.r_[starts[1:],len(y)]
    p=np.add.reduceat((ys==1).astype(np.int64),starts);n=ends-starts-p
    before=np.cumsum(n)-n
    return float(np.sum(p*(before+.5*n))/(positives*negatives))


def analyse(labels,clean,received,class_names,*,repetitions=2000,seed=3101):
    a=np.asarray(clean,dtype=float);b=np.asarray(received,dtype=float);y=np.asarray(labels)
    c=len(class_names)
    if c<2 or len(set(class_names))!=c or not all(isinstance(n,str) and n for n in class_names):raise ValueError('unique class names required')
    if a.ndim!=2 or a.shape!=b.shape or a.shape[1]!=c or not len(a):raise ValueError('paired nonempty NxC probabilities required')
    if y.shape!=(len(a),) or y.dtype.kind not in 'iu' or (y<0).any() or (y>=c).any():raise ValueError('integer ground truth outside class order')
    for p in (a,b):
        if not np.isfinite(p).all() or (p<0).any() or (p>1).any() or not np.allclose(p.sum(1),1,atol=1e-6,rtol=0):raise ValueError('finite normalized probabilities required')
    if type(repetitions) is not int or repetitions<100:raise ValueError('at least100 bootstrap repetitions required')
    pa=a.argmax(1);pb=b.argmax(1);sa=scores(y,pa,c);sb=scores(y,pb,c)
    sa['binary_roc_auc']=binary_auc(y,a[:,1]) if c==2 else None
    sb['binary_roc_auc']=binary_auc(y,b[:,1]) if c==2 else None
    strata=[np.flatnonzero(y==k) for k in range(c)];rng=np.random.default_rng(seed)
    differences={k:[] for k in ('accuracy','balanced_accuracy','macro_f1','binary_roc_auc')}
    flips=[]
    for _ in range(repetitions):
        # Paired class-stratified image bootstrap preserves class support.
        idx=np.concatenate([rng.choice(s,len(s),replace=True) for s in strata if len(s)])
        left=scores(y[idx],pa[idx],c);right=scores(y[idx],pb[idx],c)
        left['binary_roc_auc']=binary_auc(y[idx],a[idx,1]) if c==2 else None
        right['binary_roc_auc']=binary_auc(y[idx],b[idx,1]) if c==2 else None
        for k in differences:
            if left[k] is not None:differences[k].append(right[k]-left[k])
        flips.append(float((pa[idx]!=pb[idx]).mean()))
    delta={}
    for k,values in differences.items():
        delta[k]={'received_minus_clean':sb[k]-sa[k] if sa[k] is not None else None,
                  'paired_percentile95':np.quantile(values,[.025,.975]).tolist() if values else None}
    original_correct=pa==y;after_correct=pb==y
    return {'schema':'paired-diagnostic-impact-v1','class_names':list(class_names),'n':len(y),'clean':sa,'received':sb,
        'paired_differences':delta,'prediction_flips':int((pa!=pb).sum()),
        'flip_rate':float((pa!=pb).mean()),'flip_rate_percentile95':np.quantile(flips,[.025,.975]).tolist(),
        'correct_to_wrong':int((original_correct&~after_correct).sum()),
        'wrong_to_correct':int((~original_correct&after_correct).sum()),
        'mean_probability_l1_shift':float(np.abs(b-a).sum(1).mean()),
        'mean_true_class_probability_shift':float((b[np.arange(len(y)),y]-a[np.arange(len(y)),y]).mean()),
        'bootstrap':{'unit':'paired image within true class, NOT patient','repetitions':repetitions,'seed':seed},
        'limits':['Classifier identity, training provenance, split independence and calibration must be established externally.',
        'Image bootstrap does not establish patient independence; small classes yield unstable intervals.',
        'Intervals descriptive, conditional on class counts; no multiplicity correction or clinical safety claim.',
        'Ties use first declared class. Agreement or small probability shift alone is not diagnostic utility.']}
