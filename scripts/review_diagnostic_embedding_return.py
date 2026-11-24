"""Audit TRAIN12 pilot receipts and signatures; never execute returned sources.

Does not replay image pixels or independently verify claimed carrier/recovery data.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from scripts.review_isic_classifier_return import notebook_sources
from scripts.review_classifier_impact_return import close,require,CASES
from src.diagnostic_impact import analyse
from src import binary_signed_grid as G

VARIANTS=('fixed_qim','uniform_weaker_qim','energy_matched_random','diagnostic_correction','query_matched_random','distortion_gated_correction')


def probability(p):
    a=np.asarray(p,dtype=float)
    require(a.shape==(2,) and np.isfinite(a).all() and (a>0).all() and (a<=1).all() and abs(a.sum()-1)<1e-6,'invalid binary probabilities')
    return a


def kl(row):
    # Renormalise tiny softmax sum roundoff for descriptive KL; receipts use torch.
    a=probability(row['original_probabilities']['guide']);b=probability(row['probabilities']['guide'])
    a=a/a.sum();b=b/b.sum()
    return max(0.,float(np.sum(a*np.log(a/b))))


def validate_rows(rows,selected):
    require(len(rows)==len(selected)*6,'incomplete row count');indexed={}
    ids={r['image_id']:r for r in selected}
    for r in rows:
        i=r['image_id'];v=r['variant'];require(i in ids and v in VARIANTS and (i,v) not in indexed,'unknown or duplicate row')
        require(r['label']==ids[i]['melanoma_label'] and r['source_rgb_sha256']==ids[i]['prepared_rgb_sha256'],'label/source mismatch')
        require(set(r['probabilities'])==set(r['original_probabilities'])=={'guide'},'unexpected evaluator/probability keys')
        probability(r['probabilities']['guide']);probability(r['original_probabilities']['guide'])
        require(r['payload_bits']==4096 and r['qim_step']==(4 if v=='uniform_weaker_qim' else 8),'payload settings differ')
        require(r['signed_evidence_bytes']==524378,'evidence byte mismatch')
        require(np.isfinite(r['embedding_mse']) and r['embedding_mse']>=0 and type(r['linf_rgb']) is int and 0<=r['linf_rgb']<=8,'invalid distortion')
        recovery=r['recovery'];require(len(recovery)==10 and {a['case'] for a in recovery}==set(CASES[:10]),'recovery matrix differs')
        for a in recovery:
            require(type(a['changed_pixels']) is int and 0<=a['changed_pixels']<=512**2,'invalid change count')
            require(type(a['payload_bit_errors']) is int and 0<=a['payload_bit_errors']<=4096 and a['payload_bits']==4096,'invalid recovery count')
            require(a['signed_rgb_verdict']==('FAILED_INTEGRITY' if a['changed_pixels'] else 'VERIFIED'),'integrity receipt inconsistent')
            if a['case']=='intact':require(a['changed_pixels']==a['payload_bit_errors']==0,'intact recovery failed')
        if v!='uniform_weaker_qim':require(r['same_carrier_values_as_fixed'] is True,'reported carrier constraint failure')
        if v in ('diagnostic_correction','query_matched_random'):
            require(r['optimization_forward_queries']==27 and r['optimization_backward_queries']==(12 if v=='diagnostic_correction' else 0),'query budget differs')
        indexed[i,v]=r
    require(set(indexed)=={(i,v) for i in ids for v in VARIANTS},'incomplete variant matrix')
    for i in ids:
        fixed=indexed[i,'fixed_qim'];guided=indexed[i,'diagnostic_correction'];random=indexed[i,'energy_matched_random'];gate=indexed[i,'distortion_gated_correction']
        require(all(indexed[i,v]['original_probabilities']==fixed['original_probabilities'] and indexed[i,v]['payload_sha256']==fixed['payload_sha256'] for v in VARIANTS),'unpaired inputs')
        require(random['embedding_mse']==guided['embedding_mse'],'energy mismatch')
        require(gate['received_rgb_sha256']==fixed['received_rgb_sha256'] and gate['embedding_mse']==fixed['embedding_mse'],'distortion gate differs from baseline')
        trace=guided['guide_trace'];require(len(trace)==13 and [r['step'] for r in trace]==list(range(13)),'guided trace differs')
        search=indexed[i,'query_matched_random']['random_search'];require(search['forward_queries']==27 and search['backward_queries']==0 and len(search['trace'])==26,'random trace differs')
        for t in (trace,search['trace']):require(all(np.isfinite(r['guide_kl']) and r['guide_kl']>=0 for r in t),'invalid objective trace')
        require(kl(guided)<=kl(fixed)+1e-6,'guide selection inconsistent')
    return indexed


def review(archive,out):
    archive=Path(archive);out=Path(out)
    sent=ROOT/'deliverables/diagnostic_embedding_train12_v2.ipynb';bundle=notebook_sources(sent)
    cohort_bytes=(ROOT/'deliverables/verification-evidence/adapted-isic2019-cohort-v1.json').read_bytes()
    prior=ROOT/'deliverables/verification-evidence/adapted-classifier-return-v1'
    identity=json.loads((prior/'review.json').read_text())
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();require(len(names)==len(set(names)) and z.testzip() is None,'duplicate/corrupt ZIP')
        p=json.loads(z.read('protocol.json'));prep=json.loads(z.read('preparation.json'));summary=json.loads(z.read('summary.json'))
        require(z.read('cohort.json')==cohort_bytes==bundle['cohort.json'],'cohort differs')
        require(p['schema']=='diagnostic-constrained-embedding-train-pilot-v2' and p['split']=='train','wrong pilot version/split')
        require(p['settings']=={'block':8,'qim_step':8,'correction_linf_rgb':4,'steps':12,'step_rgb':1.},'settings differ')
        require(p['variants']==list(VARIANTS) and p['evaluator'] is None,'variant/evaluator mismatch')
        require(p['cohort_sha256']==identity['cohort_sha256']==prep['cohort_sha256'],'cohort receipt differs')
        require(p['guide']['checkpoint_sha256']==identity['checkpoint_sha256'] and p['guide']['selected_epoch']==3,'guide differs')
        close(p['guide']['protocol'],json.loads((prior/'protocol.json').read_text()),'guide protocol')
        require(prep==json.loads((ROOT/'deliverables/verification-evidence/adapted-isic2500-preparation-v2/preparation.json').read_text()),'preparation differs')
        selected=[r for r in prep['selected'] if r['split']=='train'][:12];ids=[r['image_id'] for r in selected]
        require(p['image_ids']==ids,'not fixed first12 TRAIN')
        expected={'protocol.json','rows.jsonl','summary.json','public-key.bin','cohort.json','preparation.json'}|{'code/'+n for n in bundle if n.endswith('.py')}|{f'artifacts/{i:03d}-{v}.bin' for i in range(12) for v in VARIANTS}
        require(set(names)==expected,'unexpected/incomplete archive')
        for name,raw in bundle.items():
            if name.endswith('.py'):require(z.read('code/'+name)==raw,'sent source differs: '+name)
        rows=[json.loads(line) for line in z.read('rows.jsonl').splitlines()];index=validate_rows(rows,selected)
        public=Ed25519PublicKey.from_public_bytes(z.read('public-key.bin'));packet_hashes={}
        for i in range(12):
            bits=np.random.default_rng(8001+i).integers(0,2,(64,64),dtype=np.uint8);digest=hashlib.sha256(bits.tobytes()).hexdigest()
            for v in VARIANTS:
                require(index[ids[i],v]['payload_sha256']==digest,'payload seed mismatch')
                name=f'artifacts/{i:03d}-{v}.bin';packet=z.read(name)
                require(len(packet)==524378 and G.HEADER.unpack(packet[:G.HEADER.size])==(G.MAGIC,1,i,512,512,4),'packet header differs')
                public.verify(packet[-64:],G.DOMAIN+packet[:-64]);packet_hashes[name]=hashlib.sha256(packet).hexdigest()
        labels=np.array([r['melanoma_label'] for r in selected]);original=np.array([index[i,'fixed_qim']['original_probabilities']['guide'] for i in ids])
        impact={}
        for v in VARIANTS:
            probs=np.array([index[i,v]['probabilities']['guide'] for i in ids])
            impact['guide/'+v]=analyse(labels,original,probs,['nonMEL','MEL'],repetitions=1000)
        close(summary,{'completed':True,'images':12,'rows':72,'test_evaluated':False,'independent_evaluator_tested':False,'diagnostic_impact':impact})
        results={}
        for v in VARIANTS:
            rr=[index[i,v] for i in ids]
            results[v]={'mean_mse':float(np.mean([r['embedding_mse'] for r in rr])),
                'mean_guide_kl_recomputed_normalized':float(np.mean([kl(r) for r in rr])),
                'guide_label_flips':sum(np.argmax(r['probabilities']['guide'])!=np.argmax(r['original_probabilities']['guide']) for r in rr),
                'outputs_identical_to_fixed':sum(r['received_rgb_sha256']==index[r['image_id'],'fixed_qim']['received_rgb_sha256'] for r in rr),
                'recovery':{c:{'bit_errors':sum(a['payload_bit_errors'] for r in rr for a in r['recovery'] if a['case']==c),'total_bits':12*4096} for c in CASES[:10]}}
        report={'schema':'diagnostic-embedding-train12-return-review-v1','zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'sent_notebook_sha256':hashlib.sha256(sent.read_bytes()).hexdigest(),'images':12,'class_counts':dict(Counter(map(str,labels.tolist()))),
            'rows':72,'recovery_entries':720,'packet_signatures_checked':72,'total_packet_bytes':72*524378,
            'results':results,'guided_improves_kl_over_fixed_count':sum(kl(index[i,'diagnostic_correction'])<kl(index[i,'fixed_qim'])-1e-7 for i in ids),
            'distortion_gate_rejections':sum(not index[i,'distortion_gated_correction']['distortion_gate']['accepted'] for i in ids),
            'decision':'Do not scale this unchanged candidate to validation/test. Guide-only changes on TRAIN do not demonstrate useful medical benefit.',
            'limits':['No source or received image pixels returned: carrier lock, MSE, bit recovery and operator outputs are receipt checks, not independent pixel replay.',
                      '72 packet signatures checked against the returned key, not an independently trusted issuer identity; no independent binding to unavailable image bytes.',
                      '12 classifier TRAIN images, only2 melanoma; no unseen-model evaluation, no clinical/generalization claim.',
                      'Guide KL selection is not an independent endpoint; random search is forward-query, not gradient-compute or energy matched.',
                      'Strict fixed-carrier non-carrier correction necessarily adds squared error for any nonzero change.']}
        out.mkdir(parents=True,exist_ok=False)
        for n in ('protocol.json','summary.json','public-key.bin'):(out/n).write_bytes(z.read(n))
        (out/'rows.jsonl.gz').write_bytes(gzip.compress(z.read('rows.jsonl'),mtime=0))
        (out/'review.json').write_text(json.dumps(report,indent=2,default=lambda v:int(v))+'\n')
        (out/'packet-hashes.json').write_text(json.dumps(packet_hashes,indent=2)+'\n')
        return report

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('archive',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    print(json.dumps(review(a.archive,a.out),indent=2,default=lambda v:int(v)))
