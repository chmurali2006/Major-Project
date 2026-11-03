"""Check runtime and dataset BEFORE reserving a long training session."""
import argparse
import json
from pathlib import Path
import platform
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--data',type=Path)
    ap.add_argument('--metadata',type=Path)
    ap.add_argument('--require-gpu',action='store_true')
    args=ap.parse_args()
    import cv2, numpy, scipy, torch, filelock
    from src.isic_meta import Metadata
    from src import evidence as E, authentication as A, protocol as P
    import run_matrix as R
    # A forward-only Torch check can pass even if its NumPy ABI bridge is broken.
    numpy.testing.assert_array_equal(torch.from_numpy(numpy.array([1.,2.],dtype=numpy.float32)).numpy(),[1.,2.])
    device='cuda' if torch.cuda.is_available() else 'cpu'
    if args.require_gpu and device != 'cuda':
        raise SystemExit('No usable CUDA GPU. Enable Kaggle GPU or install the appropriate PyTorch CUDA wheel locally.')
    torch.set_num_threads(2)
    model=R.build_model(next(c for c in P.MATRIX if c.cid=='C8'),E.N_FULL,4,binary_verdict_head=True)
    for name in ('ae','saliency','refine'): model[name].to(device)
    R.to_eval(model)
    with torch.no_grad():
        result=R.forward_all(model,{'ev':torch.zeros(1,E.N_FULL,8,8,device=device),
            'deg':torch.zeros(1,4,device=device),'image':torch.zeros(1,3,64,64,device=device)})
    marked=E.protect(numpy.full((64,64,3),100,numpy.uint8),b'public-preflight-key',0)
    assert A.verify(marked,b'public-preflight-key',0)
    marked[12,20,0]^=1
    assert A.failures(marked,b'public-preflight-key',0).sum()==1
    report={'python':platform.python_version(),'torch':torch.__version__,
            'numpy':numpy.__version__,'device':device,
            'gpu':torch.cuda.get_device_name() if device=='cuda' else None,
            'pixel_forward_shape':list(result['pixel_logits'].shape),
            'evidence_channels':E.N_FULL,'classifier_outputs':int(result['cls'].shape[1]),
            'authentication_scheme':A.SCHEME,'intact_and_single_bit_authentication_check':True,
            'free_disk_gib_here':round(shutil.disk_usage('.').free/2**30,1)}
    if args.data:
        paths=list(args.data.rglob('*.jpg'))
        if not paths: raise SystemExit('No JPEGs found under --data')
        if not args.metadata: raise SystemExit('Pass the ground-truth CSV with --metadata')
        meta=Metadata(args.metadata)
        if not meta.has_diagnosis: raise SystemExit('No recognised diagnosis labels in metadata')
        report.update({'image_files':len(paths),'labelled_resolving_images':sum(p.stem in meta.diagnosis for p in paths),
                       'metadata':meta.note})
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
