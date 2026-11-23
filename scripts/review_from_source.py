"""Fresh synthetic probes with independent numeric oracles; reads no saved run receipts.

Exit 2 means the watermark challenge found an unresolved design blocker.
Passing engineering probes is deliberately not reported as authentication proof.
"""
import argparse
import csv
import json
from pathlib import Path
import sys
import tempfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))


def brightness_challenge(profile="authenticated"):
    from src import evidence as E
    from src.classical import CountRule
    image = np.random.default_rng(4).integers(65, 110, (128, 128, 3), dtype=np.uint8)
    marked = E.protect(image, b'fresh-review-key', 41, profile=profile)
    changed = marked.copy()
    patch = changed[32:64, 48:80].astype(np.int16) + 64
    assert patch.max() < 256  # no clipping or uint8 wrap can explain the result
    changed[32:64, 48:80] = patch.astype(np.uint8)
    before = E.full_tensor(marked, b'fresh-review-key', 41, profile=profile)
    after = E.full_tensor(changed, b'fresh-review-key', 41, profile=profile)
    mask_a, verdict_a = CountRule(.4, 0 if profile.startswith("authenticated") else 64).predict(before)
    mask_b, verdict_b = CountRule(.4, 0 if profile.startswith("authenticated") else 64).predict(after)
    if profile.startswith('authenticated'):
        from src.metrics import measured_mask
        assert verdict_a==0 and verdict_b==1
        assert np.array_equal(after[0]>0,measured_mask(marked,changed))
    differences = {name: float(np.max(np.abs(a-b)))
                   for name, a, b in zip(E.FULL_CHANNELS, before, after)}
    blind = np.allclose(before, after, rtol=0, atol=1e-10)
    return {'blocking': bool(blind), 'changed_pixel_fraction': float(np.any(marked != changed, axis=2).mean()),
            'rgb_offset': 64, 'patch': [32, 64, 48, 80], 'clipping': False,
            'max_map_differences': differences, 'same_classical_mask': bool(np.array_equal(mask_a, mask_b)),
            'classical_verdict_before': verdict_a, 'classical_verdict_after': verdict_b,
            'profile': profile, 'scope': 'Tests evidence response; no neural-model performance claim.'}


def chroma_challenge(profile="authenticated"):
    from src import evidence as E
    from src.classical import CountRule
    image=np.random.default_rng(4).integers(65,110,(128,128,3),dtype=np.uint8)
    marked=E.protect(image,b'fresh-review-key',41,profile=profile)
    yy,xx=np.mgrid[:128,:128]
    region=(yy-65)**2+(xx-61)**2<17**2
    changed=marked.copy()
    pixels=changed[region].astype(np.int16)+[15,-9,7]
    assert pixels.min()>=0 and pixels.max()<256
    changed[region]=pixels.astype(np.uint8)
    before,after=E.full_tensor(marked,b'fresh-review-key',41,profile=profile),E.full_tensor(changed,b'fresh-review-key',41,profile=profile)
    ma,va=CountRule(.4,0 if profile.startswith("authenticated") else 64).predict(before);mb,vb=CountRule(.4,0 if profile.startswith("authenticated") else 64).predict(after)
    if profile.startswith('authenticated'):
        from src.metrics import measured_mask
        assert va==0 and vb==1
        assert np.array_equal(after[0]>0,measured_mask(marked,changed))
    return {'blocking':bool(np.allclose(before,after,atol=1e-10,rtol=0)),
            'rgb_offset':[15,-9,7],'region':'non-block-aligned disk: (y-65)^2+(x-61)^2 < 17^2',
            'changed_pixel_fraction':float(region.mean()),'clipping':False,
            'max_luma_roundoff':float(np.max(np.abs(E.luma(marked)-E.luma(changed)))),
            'max_map_difference':float(np.max(np.abs(before-after))),
            'all_maps_bitwise_equal':bool(np.array_equal(before,after)),
            'same_classical_mask':bool(np.array_equal(ma,mb)),
            'classical_verdict_before':va,'classical_verdict_after':vb,
            'profile':profile, 'scope':'Tests colour-edit verification; neural-model behaviour unmeasured.'}


def scalar_haar(plane):
    def level(x):
        out = [np.zeros((x.shape[0]//2, x.shape[1]//2)) for _ in range(4)]
        for i in range(out[0].shape[0]):
            for j in range(out[0].shape[1]):
                a,b,c,d = x[2*i,2*j],x[2*i,2*j+1],x[2*i+1,2*j],x[2*i+1,2*j+1]
                for arr,value in zip(out, ((a+b+c+d)/2,(a+b-c-d)/2,(a-b+c-d)/2,(a-b-c+d)/2)):
                    arr[i,j] = value
        return out
    low,lh1,hl1,hh1 = level(plane)
    low,lh2,hl2,hh2 = level(low)
    return dict(LL2=low,LH1=lh1,HL1=hl1,HH1=hh1,LH2=lh2,HL2=hl2,HH2=hh2)


def fresh_checks():
    from src import evidence as E, carriers, metrics
    from src.isic_meta import Metadata
    from summarize_isic_study import summarize
    from src.calibration import risk_coverage
    rng = np.random.default_rng(617)
    plane = rng.normal(100, 20, (16, 24))
    expected = scalar_haar(plane)
    observed = E.haar2(plane)
    haar_error = max(float(np.max(np.abs(expected[k]-observed[k]))) for k in expected)
    assert haar_error < 1e-10
    # Direct cosine definition, not SciPy's FFT implementation.
    C = np.array([[np.sqrt(2/8)*np.cos(np.pi*(2*x+1)*u/16) for x in range(8)] for u in range(8)])
    C[0] /= np.sqrt(2)
    dct_observed = carriers.dct_blocks(plane)
    dct_error = 0.
    for i in range(2):
        for j in range(3):
            direct = C @ plane[i*8:(i+1)*8,j*8:(j+1)*8] @ C.T
            dct_error = max(dct_error, float(np.max(np.abs(direct-dct_observed[i,j]))))
    assert dct_error < 1e-9
    for _ in range(100):
        p,g = rng.random((5,7))>.6, rng.random((5,7))>.6
        a,b = set(map(tuple,np.argwhere(p))),set(map(tuple,np.argwhere(g)))
        direct = len(a&b)/len(a|b) if a|b else 1.
        assert abs(metrics.iou(p,g)-direct)<1e-12
    confidence, correct = [.8,.8,.3,.1],[True,False,True,False]
    last, integral = 0.,0.
    for threshold in sorted(set(confidence),reverse=True):
        accepted=[i for i,c in enumerate(confidence) if c>=threshold]
        coverage=len(accepted)/4
        risk=sum(not correct[i] for i in accepted)/len(accepted)
        integral+=(coverage-last)*risk
        last=coverage
    assert abs(risk_coverage(confidence,correct)['aurc']-integral)<1e-12
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'labels.csv'
        p.write_text('image,MEL,NV,BCC,AK,BKL,DF,VASC,SCC\nISIC_x,0.00,1.00,0.00,0.00,0.00,0.00,0.00,0.00\n')
        assert Metadata(p).dx_of('ISIC_x')=='NV'
        root=Path(d)/'runs'; (root/'seed-0').mkdir(parents=True)
        (root/'seed-0'/'C8.json').write_text('{broken')
        summary=summarize(root)
        assert not summary['complete'] and summary['invalid_receipts']
    return {'scalar_haar_max_error':haar_error,'direct_cosine_dct_max_error':dct_error,
            'set_based_iou_cases':100,'manual_tied_risk_integral':'matched',
            'numeric_label_formatting':'correct','malformed_receipt_handling':'reported, not crash'}


def source_observations():
    """Expose unresolved implementation choices without silently redefining them."""
    from unittest.mock import patch
    from src import degradation, evidence as E
    import run_matrix as R
    flat=np.full((64,64,3),100,np.uint8)
    striped=np.repeat(np.tile(((np.arange(64)//2)%2)*255,(64,1))[...,None],3,axis=2).astype(np.uint8)
    feature_a,feature_b=degradation.estimate(flat),degradation.estimate(striped)
    clean=np.full((512,512,3),100,np.uint8)
    marked=E.protect(clean,b'fresh-label-probe',9)
    edited=marked.copy(); edited[12,20,0]+=1
    item=R.Item(9,'NV',marked,clean,b'fresh-label-probe')
    # Isolate actual label construction from the attack generator. The injected
    # edit changes exactly one pixel; no claim is made about a natural T1 edit.
    with patch.object(R.T,'make_pair',return_value=(edited,None)):
        sample=R.build_sample(item,'T1',np.random.default_rng(1))
    assert int(sample.gt_pixel.sum())==1
    return {'sharpness_feature':{
        'flat_raw_sharpness':degradation.sharpness(flat),
        'striped_raw_sharpness':degradation.sharpness(striped),
        'default_sharpness_feature':[float(feature_a[2]),float(feature_b[2])],
        'interpretation':'Default uses a fixed analytic Sobel bound; no corpus statistics are fitted.'},
        'sparse_pixel_block_label':{'changed_pixels':int(sample.gt_pixel.sum()),
            'positive_block_labels':int(sample.gt_block.sum()),'image_class':sample.cls,
            'interpretation':'Block truth now uses any changed pixel, including a single payload-bit edit.'}}


def crash_resume_probe():
    """New subprocesses: uninterrupted run versus a real process death + restart."""
    import subprocess
    import torch
    worker = r'''import os,signal,sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,sys.argv[1]); sys.path.insert(0,str(Path(sys.argv[1])/'scripts'))
import run_matrix as R
from run_isic_study import build_paired_model
from src import metrics
mode,output=sys.argv[2],Path(sys.argv[3])
torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
model=build_paired_model('C8',4,109)
for p in model['ae'].parameters(): p.requires_grad_(False)
model['ae'].eval()
rng=np.random.default_rng(210)
samples=[]
for i in range(4):
    gt=np.zeros((512,512),bool)
    if i%2: gt[32:64,40:72]=True
    block=gt.reshape(64,8,64,8).any(axis=(1,3))
    samples.append(R.Sample(rng.normal(size=(13,64,64)).astype(np.float16),np.zeros(4,np.float32),
        rng.integers(0,256,(3,512,512),dtype=np.uint8),block,gt,i%2,'toy','NV'))
def log(message):
    if mode=='crash' and message=='Checkpoint saved after epoch 1':
        if hasattr(signal,'SIGKILL'): os.kill(os.getpid(),signal.SIGKILL)
        os._exit(73)
R.train(model,samples[:2],samples[2:],epochs=2,batch=1,lr=.001,smoke=True,
        checkpoint_path=output,resume=mode=='resume',run_id='fresh-crash-probe',device='cpu',log=log)
'''
    with tempfile.TemporaryDirectory() as temp:
        a,b=Path(temp)/'full.pt',Path(temp)/'interrupted.pt'
        for mode,path in [('full',a),('crash',b),('resume',b)]:
            result=subprocess.run([sys.executable,'-c',worker,str(ROOT),mode,str(path)],capture_output=True,text=True)
            if mode=='crash':
                assert result.returncode in (-9,73), result.stderr
            else:
                assert result.returncode==0, result.stdout+result.stderr
        aa=torch.load(a,map_location='cpu',weights_only=False)
        bb=torch.load(b,map_location='cpu',weights_only=False)
        assert aa['epoch']==bb['epoch']==2
        def same(x,y):
            if isinstance(x,torch.Tensor): return torch.equal(x,y)
            if isinstance(x,dict): return x.keys()==y.keys() and all(same(x[k],y[k]) for k in x)
            if isinstance(x,(list,tuple)): return len(x)==len(y) and all(same(u,v) for u,v in zip(x,y))
            return x==y
        assert same(aa,bb)
    return 'bitwise identical checkpoint after new-process crash/restart (CPU toy training only)'


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--exercise-crash',action='store_true')
    args=ap.parse_args()
    from src.persistence import source_digest, atomic_json
    checks=fresh_checks()
    if args.exercise_crash:
        checks['fresh_process_crash_resume']=crash_resume_probe()
    observations=source_observations()
    challenge=brightness_challenge()
    chroma=chroma_challenge()
    blocked=challenge['blocking'] or chroma['blocking']
    result={'method':'source inspection and newly generated inputs; no previous run evidence loaded',
            'source_sha256':source_digest(ROOT),'fresh_engineering_checks':checks,
            'source_observations':observations,
            'watermark_brightness_challenge':challenge,
            'watermark_chroma_challenge':chroma,
            'legacy_challenges_retained':{'brightness':brightness_challenge('dual'), 'chroma':chroma_challenge('dual')},
            'verdict':'NO-GO for submission-readiness claim' if blocked else 'v2 counterexamples closed; full ISIC/CUDA study and external security review not established',
            'not_established':['Kaggle/CUDA operation','clinical validity','adaptive-attack resistance','patient independence','paper parity']}
    atomic_json(args.out,result)
    print(json.dumps(result,indent=2))
    return 2 if blocked else 0


if __name__=='__main__':
    raise SystemExit(main())
