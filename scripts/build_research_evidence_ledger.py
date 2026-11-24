"""Link review claims to existing results; reject unsupported causal narrative."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def build():
    paths={
        'classical_validation':'deliverables/verification-evidence/adapted-validation500-v1/analysis.json',
        'refiner_failures':'deliverables/verification-evidence/refiner-failure-diagnostic-v3/findings.json',
        'candidate_mechanism':'deliverables/verification-evidence/diagnostic-embedding-mechanism-v1.json'}
    evidence={k:json.loads((ROOT/v).read_text()) for k,v in paths.items()}
    a=evidence['classical_validation'];g={(r['case'],r['method']):r for r in a['groups']}
    if a['images']!=500 or a['rows']!=15000 or a['signatures_checked']!=1500:raise ValueError('unexpected validation evidence')
    for method in ('full4','full8','bounded289'):
        if g['copy32',method]['fine_maps']!=500:raise ValueError('local coverage claim no longer supported')
    if any(g[case,'bounded289']['fine_maps'] for case in ('jpeg70','jpeg85','jpeg95','resize90_restore','contrast90','contrast110','gaussian05')):raise ValueError('global abstention claim differs')
    smoke=evidence['candidate_mechanism'];r={row['variant']:row for row in smoke['rows']}
    if not smoke['synthetic'] or smoke['medical_data']:raise ValueError('fixture must never be relabelled medical')
    if not (r['diagnostic_correction']['guide_kl']<r['fixed']['guide_kl'] and r['diagnostic_correction']['unseen_kl']>r['fixed']['unseen_kl']):raise ValueError('transfer counterexample changed')
    if r['energy_matched_random']['mse']!=r['diagnostic_correction']['mse']:raise ValueError('energy control mismatch')
    return {'schema':'study-to-candidate-evidence-ledger-v1',
        'artifacts':{k:{'path':v,'sha256':hashlib.sha256((ROOT/v).read_bytes()).hexdigest()} for k,v in paths.items()},
        'claims':[
            {'claim':'Compact classical evidence trades storage against speed and global localisation coverage.','status':'measured_validation_development','evidence':'classical_validation'},
            {'claim':'Existing refiners require a more careful failure hypothesis, not an attention-based success claim.','status':'measured_synthetic_diagnostic_plus_earlier_development_failures','evidence':'refiner_failures'},
            {'claim':'The studies proved that our medical images suffer clinically significant diagnostic disruption from watermark embedding.','status':'NOT_ESTABLISHED','reason':'Current compact validation is nonembedding; classifier and embedding-specific medical results are pending.'},
            {'claim':'Diagnostic-constrained embedding is a new medical-watermarking idea.','status':'NOT_ESTABLISHED_PRIOR_ART_OVERLAP','reason':'PFF-WM uses diagnostic saliency/explanation alignment; MedSign already uses pathology-aware embedding preservation.'},
            {'claim':'A payload-preserving quantized correction mechanism is implemented with controlled baselines.','status':'implemented_fixture_tested_not_medically_validated','evidence':'candidate_mechanism'},
            {'claim':'Reducing guide-model KL establishes diagnostic preservation or transfer.','status':'REFUTED_AS_GENERAL_CLAIM','evidence':'candidate_mechanism','reason':'Explicit toy counterexample improves guide KL while worsening unseen-model KL; random control can tie the guide result.'},
            {'claim':'Our study motivated testing diagnostic-constrained embedding under fixed payload constraints.','status':'prospective_research_rationale_NOT_proven_causal_medical_result'},
            {'claim':'The candidate is SOTA-superior or clinically safe.','status':'NOT_ESTABLISHED'}],
        'prior_art':[
            {'title':'Explainable and proactive fragile watermarking for medical Deepfake detection','url':'https://www.sciencedirect.com/science/article/pii/S2667305326000591','local_text':'project-context/papers/pff-wm.txt','verified_overlap':'Diagnostic saliency guides embedding; frozen-classifier Grad-CAM alignment loss in explainability.'},
            {'title':'Pathology-Aware Adaptive Watermarking for Text-Driven Medical Image Synthesis (MedSign)','url':'https://arxiv.org/html/2503.08346v1','verified_overlap':'Primary abstract/introduction: pathology localization maps adapt watermark strength and preserve critical regions during diffusion-decoder fine-tuning.'}],
        'next_required_evidence':['Reviewed diagnostic classifier with adequate reported class-wise performance, no automatic approval.',
            'Training-only pilot for numerical feasibility; count no-improvement, increased distortion and recovery failures.',
            'Second classifier not used in correction; this is not yet available.',
            'Freeze comparison protocol before validation/final testing; compare payload, margin, distortion, compute and entire authentication evidence cost.',
            'Do not use a saliency/KL objective alone as a human clinical-fidelity guarantee.']}

if __name__=='__main__':
    out=ROOT/'deliverables/verification-evidence/study-to-candidate-evidence-ledger-v1.json'
    out.write_text(json.dumps(build(),indent=2)+'\n');print(out)
