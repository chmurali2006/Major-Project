"""Paired image bootstrap for coding-development results, not patient inference.

Each resample draws complete source-image units, preserving all method pairings.
Coverage includes unavailable maps; runtime includes both success and abstention.
Observed100%coverage can produce degenerate bootstrap intervals: Wilson intervals
are also reported and neither corrects development selection or patient dependence.
"""
import math
import numpy as np

METHODS=('bounded289','index288','set330','full4')
CASES=('intact','one-bit','brightness32','replace64','copy64','jpeg75')


def wilson(successes,n):
    if type(n) is not int or n<1 or type(successes) is not int or not 0<=successes<=n:raise ValueError('invalid binomial counts')
    z=1.959963984540054;p=successes/n;den=1+z*z/n
    centre=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0.,centre-half),min(1.,centre+half)]


def paired_interval(a,b,draws):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    if a.ndim!=1 or a.shape!=b.shape or not len(a) or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('aligned finite vectors required')
    if draws.ndim!=2 or draws.shape[1]!=len(a) or draws.min()<0 or draws.max()>=len(a):raise ValueError('invalid paired bootstrap indices')
    difference=a-b;means=difference[draws].mean(axis=1)
    return {'mean_difference':float(difference.mean()),'paired_percentile95':list(map(float,np.quantile(means,[.025,.975])))}


def analyse(result,preparation,repetitions=10000,seed=1201):
    if type(repetitions) is not int or repetitions<100:raise ValueError('at least100 bootstrap resamples required')
    selected=preparation['selected'];ids=[r['image_id'] for r in selected]
    if not ids or len(set(ids))!=len(ids):raise ValueError('unique nonempty source list required')
    rows=result['rows'];indexed={(r['source_id'],r['case'],r['method']):r for r in rows}
    expected={(ident,case,method) for ident in ids for case in CASES for method in METHODS}
    if len(indexed)!=len(rows) or set(indexed)!=expected:raise ValueError('complete unique paired matrix required')
    draws=np.random.default_rng(seed).integers(0,len(ids),size=(repetitions,len(ids)))
    groups=[];comparisons=[];classwise=[]
    for case in CASES:
        for method in METHODS:
            rs=[indexed[ident,case,method] for ident in ids]
            for r in rs:
                if type(r['fine_map_available']) is not bool or not np.isfinite(r['verification_seconds']) or r['verification_seconds']<0:raise ValueError('invalid row')
                if r['fine_map_available'] and r['map_matches_truth'] is not True:raise ValueError('incorrect or unchecked exposed map')
            successes=sum(r['fine_map_available'] for r in rs)
            groups.append({'method':method,'case':case,'n':len(rs),'fine_maps':successes,'coverage':successes/len(rs),
                'coverage_wilson95_descriptive':wilson(successes,len(rs)),
                'mean_verify_seconds_all_cases':float(np.mean([r['verification_seconds'] for r in rs]))})
            for diagnosis in sorted({r['diagnosis'] for r in selected}):
                subset=[indexed[r['image_id'],case,method] for r in selected if r['diagnosis']==diagnosis]
                classwise.append({'method':method,'case':case,'diagnosis':diagnosis,'n':len(subset),
                    'fine_maps':sum(r['fine_map_available'] for r in subset)})
        for comparator in ('index288','set330','full4'):
            a=[indexed[ident,case,'bounded289'] for ident in ids]
            b=[indexed[ident,case,comparator] for ident in ids]
            comparisons.append({'case':case,'method':'bounded289','minus':comparator,'n':len(ids),
                'coverage_difference':paired_interval([r['fine_map_available'] for r in a],[r['fine_map_available'] for r in b],draws),
                'verification_seconds_difference_all_cases':paired_interval([r['verification_seconds'] for r in a],[r['verification_seconds'] for r in b],draws),
                'timing_warning':'Peeling may abstain; total verification time is not time to a successful fine map.'})
    return {'schema':'paired-coding-development-analysis-v1','resampling_unit':'source_image_NOT_patient',
        'bootstrap_repetitions':repetitions,'bootstrap_seed':seed,'groups':groups,'paired_comparisons':comparisons,'classwise':classwise,
        'limitations':['Development selection: all intervals descriptive, not confirmatory final-study inference.',
        'Patient/lesion independence unverified; image resampling cannot resolve clustering or selection bias.',
        'Wilson intervals assume independent Bernoulli units and are descriptive here.',
        'Bootstrap intervals can be degenerate for all-success/failure samples, not proof of guaranteed coverage.',
        'No multiplicity correction; do not turn these comparisons into significance-based SOTA claims.',
        'One timing per input/method/case, no technical-repeat or machine-independent latency guarantee.',
        'Saved truth consistency is not independent decoding, clinical utility or novelty.']}
