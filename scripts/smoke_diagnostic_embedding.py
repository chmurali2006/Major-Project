"""Analytic synthetic mechanism evidence, including a transfer counterexample.

Not medical data, not classifier accuracy, not a novelty or robustness result.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import binary_signed_grid as G
from src.diagnostic_constrained_embedding import Settings,embed_fixed,embed_guided,decode,carrier_mask,energy_matched_random


class Toy(torch.nn.Module):
    def __init__(self,opposite=False):
        super().__init__();self.register_buffer('scale',torch.tensor(20.));self.opposite=opposite
    def forward(self,x):
        value=(x[:,0,0,0]-x[:,2,0,1]) if self.opposite else (x[:,0,0,0]+x[:,2,0,1]-256/255.)
        value=value*self.scale
        return torch.stack((value,-value),1)


def run(out):
    torch.set_num_threads(2)
    x=np.full((8,8,3),128,np.uint8);payload=np.ones((1,1),np.uint8)
    guide=Toy().eval();unseen=Toy(True).eval();s=Settings(steps=8)
    result=embed_guided(guide,x,payload,(0,0,0),(1,1,1),s)
    variants={'fixed':(result['base'],8),'uniform_weaker':(embed_fixed(x,payload,qim_step=4),4),
        'diagnostic_correction':(result['received'],8),
        'energy_matched_random':(energy_matched_random(x,result['received'],result['base'],seed=7),8)}
    def predict(model,image):
        with torch.no_grad():return model(torch.tensor(image.transpose(2,0,1).copy()).float()[None]/255.).softmax(1)[0].numpy()
    def kl(a,b):return float(np.sum(a*np.log(a/b)))
    key=Ed25519PrivateKey.generate();rows=[]
    for name,(y,step) in variants.items():
        delta=y.astype(int)-x.astype(int);packet=G.sign(y,key,1)
        row={'variant':name,'qim_step':step,'payload_bits':1,'clean_bit_errors':int((decode(y,qim_step=step)!=payload).sum()),
            'mse':float(np.mean(delta**2)),'linf_rgb':int(np.abs(delta).max()),'guide_kl':kl(predict(guide,x),predict(guide,y)),
            'unseen_kl':kl(predict(unseen,x),predict(unseen,y)),
            'same_carrier_as_fixed':bool(np.array_equal(y[carrier_mask(x)],result['base'][carrier_mask(x)])),
            'signed_evidence_bytes':len(packet),'clean_signed_verdict':G.verify(y,packet,key.public_key(),1).verdict}
        tampered=y.copy();tampered[5,5,1]^=1
        row['noncarrier_edit_bit_errors']=int((decode(tampered,qim_step=step)!=payload).sum())
        row['noncarrier_edit_signed_verdict']=G.verify(tampered,packet,key.public_key(),1).verdict
        rows.append(row)
    report={'schema':'diagnostic-embedding-synthetic-mechanism-v1','synthetic':True,'medical_data':False,
        'source_generator':'8x8 RGB constant128; payload1; two explicit linear toy guides in this script',
        'source_sha256':hashlib.sha256(x.tobytes()).hexdigest(),'settings':result['settings'],'trace':result['trace'],'rows':rows,
        'findings':['Fixed carrier samples/payload remain unchanged under guided correction.',
        'Guiding-model KL can decrease while unseen-model KL increases: a concrete counterexample to automatic transfer/clinical preservation.',
        'A non-carrier edit leaves watermark payload unchanged but fails separate signed RGB authentication.',
        'Random-direction control has exactly the guided squared pixel distortion, but is not compute-matched.',
        'No medical-image efficacy, robustness, novelty, clinical-safety or SOTA evidence follows from these synthetic values.']}
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.out),indent=2))
