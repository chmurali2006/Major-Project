from compare_bounded_budget import CONFIGS,CEILING,cases,summarise
from src.index_syndrome import addresses


def test_matched_config_accounting_and_actual_target():
    sizes={name:module.HEADER.size+96+(64*parameter if name!='set-peeling' else 56*parameter)
           for name,module,parameter in CONFIGS}
    assert sizes=={'bounded':4220,'index-peeling':4158,'set-peeling':4214}
    assert max(sizes.values())<=CEILING
    selected=[indices for label,indices in cases(601) if label=='targeted-index-63']
    assert len(selected)==1
    a,b=selected[0]
    assert set(addresses(a,63))==set(addresses(b,63))


def test_unavailable_maps_stay_in_denominator():
    rows=[]
    for name,_,_ in CONFIGS:
        for targeted in (False,True):
            for available in (False,True):
                rows.append({'method':name,'pattern':'targeted-x' if targeted else 'clustered',
                    'sidecar_bytes':4000,'fine_map_available':available,'map_matches_truth':True if available else None,
                    'verdict':'FAILED_INTEGRITY','verification_seconds':.1})
    for group in summarise(rows):
        assert group['trials']==2 and group['fine_maps']==1
        assert group['incorrect_maps']==0 and group['false_acceptances']==0
