"""Persist deterministic synthetic fairness checks, not medical evidence."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts.smoke_diagnostic_embedding import Toy
from src.diagnostic_constrained_embedding import Settings,embed_guided,decode
from src.diagnostic_correction_controls import query_matched_random,distortion_noninferiority

if __name__=='__main__':
    x=np.full((8,8,3),128,np.uint8);bits=np.ones((1,1),np.uint8);s=Settings(steps=8);m=Toy().eval()
    guided=embed_guided(m,x,bits,(0,0,0),(1,1,1),s)
    control=query_matched_random(m,x,bits,(0,0,0),(1,1,1),s,seed=11)
    gate=distortion_noninferiority(x,guided['base'],guided['received'])
    out=ROOT/'deliverables/verification-evidence/correction-controls-v2.json'
    report={'synthetic':True,'medical_data':False,'source_sha256':hashlib.sha256(x.tobytes()).hexdigest(),
        'settings':s.__dict__,'guided_forward_queries':2*s.steps+3,'guided_backward_queries':s.steps,
        'random':{k:v for k,v in control.items() if k not in ('base','received')},
        'distortion_gate':{k:v for k,v in gate.items() if k!='received'},
        'all_clean_payloads_recovered':all(np.array_equal(decode(a),bits) for a in (guided['received'],control['received'],gate['received'])),
        'finding':'Locking carrier values and changing only previously untouched non-carrier samples strictly increases squared distortion for any nonzero correction. Equal-distortion improvement over this fixed embedding is impossible under these constraints.',
        'limits':['Random and guided are forward-query matched, not gradient-compute or energy matched.',
                  'The gate returning baseline is a structural limitation, not successful diagnostic correction.',
                  'No medical efficacy, SOTA, clinical safety or novelty result.']}
    with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2))
