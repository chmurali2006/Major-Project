"""Cross-check follow-up declarations; never substitutes for saved-map audit."""
from collections import Counter
from .comparison_results_audit import CASES
from .dataset_audit import CLASSES


def check_protocol(config, grouping, report, known_prior_ids):
    def require(ok, message):
        if not ok:raise ValueError(message)
    require(config.get('schema')=='followup32-config-v1','unsupported config')
    require(grouping.get('schema')=='supplied-grouping-audit-v1','unsupported grouping audit')
    require(report.get('complete') is True and report.get('synthetic') is False,'complete real-input receipt required')
    prep=report.get('input_preparation') or {}
    require(prep.get('complete') is True,'complete preparation required')
    require(type(config.get('per_class')) is int and config['per_class']==4,'expected four per class')
    require(config.get('seed')==73 and prep.get('seed')==73,'frozen selection seed mismatch')
    require(prep.get('per_class')==4,'preparation count mismatch')
    require(config.get('threshold')==.2 and report.get('threshold',{}).get('value')==.2,'threshold mismatch')
    require(config.get('checkpoint')=='official clean','checkpoint declaration mismatch')
    require(config.get('cases')==list(CASES),'case list mismatch')
    for field in ('labels_sha256','metadata_sha256'):
        require(config.get(field)==grouping.get(field)==prep.get(field),field+' mismatch')
    exclusions=config.get('prior_ids')
    require(isinstance(exclusions,list) and all(isinstance(i,str) for i in exclusions),'invalid exclusions')
    require(len(exclusions)==len(set(exclusions)),'duplicate exclusions')
    require(set(known_prior_ids)<=set(exclusions),'known development IDs omitted')
    require(set(exclusions)==set(prep.get('excluded_ids',[])),'preparation exclusions differ')
    selected=prep.get('selected',[])
    require(len(selected)==32 and len(report.get('samples',[]))==32,'expected32 evaluated sources')
    ids=[s['image_id'] for s in selected]
    require(len(set(ids))==32 and not set(ids)&set(exclusions),'selected duplicate or prior source')
    require(Counter(s['diagnosis'] for s in selected)==Counter({c:4 for c in CLASSES}),'class balance mismatch')
    groups=[s['group'] for s in selected]
    require(len(set(groups))==32,'selected groups are not distinct')
    field=config.get('group_field')
    if field is None:
        require(config.get('allow_image_level') is True,'explicit image-level acknowledgement required')
        require(prep.get('metadata_sha256') is None and prep.get('grouping')=='image only; patient/lesion dependence unknown','image-only declaration mismatch')
        scope='image-level only; patient/lesion dependence unknown'
    else:
        require(field in ('patient_id','lesion_id') and field in grouping.get('ready_fields',[]),'complete supplied grouping unavailable')
        require(prep.get('grouping')==field+' supplied by caller, not independently verified','grouping declaration mismatch')
        scope=field+' supplied, not independently verified; no clinical/population inference'
    prefix='image:' if field is None else field+':'
    require(all(isinstance(g,str) and g.startswith(prefix) and len(g)>len(prefix) for g in groups),'group namespace mismatch')
    return {'schema':'followup32-protocol-check-v1','declarations_consistent':True,'sample_count':32,
            'scope':scope,'limitations':['Must additionally pass independent saved-map audit.',
            'Configuration hash does not prove pre-execution registration or authentic execution.',
            'Original pixel identity and metadata semantics remain unverified.',
            'Balanced32-image comparison cannot establish population superiority or clinical safety.']}
