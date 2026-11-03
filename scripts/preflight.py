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
    from src.models import PixelRefineNet, N_RICH
    device='cuda' if torch.cuda.is_available() else 'cpu'
    if args.require_gpu and device != 'cuda':
        raise SystemExit('No usable CUDA GPU. Enable Kaggle GPU or install the appropriate PyTorch CUDA wheel locally.')
    torch.set_num_threads(2)
    model=PixelRefineNet(width=4).to(device).eval()
    with torch.no_grad():
        result=model(torch.zeros(1,N_RICH,8,8,device=device),torch.zeros(1,4,device=device),
                     torch.zeros(1,1,64,64,device=device),torch.zeros(1,3,64,64,device=device))
    report={'python':platform.python_version(),'torch':torch.__version__,
            'numpy':numpy.__version__,'device':device,
            'gpu':torch.cuda.get_device_name() if device=='cuda' else None,
            'pixel_forward_shape':list(result['pixel_logits'].shape),
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
