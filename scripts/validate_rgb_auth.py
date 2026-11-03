"""Fresh RGB-authentication/fidelity probes; no learned accuracy claims or pixels saved."""
import argparse
import hashlib
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src import authentication as A, evidence as E, metrics as M
from src.persistence import atomic_json, source_digest


def check(images):
    rows=[]
    for name,image in images:
        for profile in ('authenticated','authenticated-single'):
            marked=E.protect(image,b'public-validation-key',41,profile=profile)
            assert A.verify(marked,b'public-validation-key',41)
            assert not E.read_full(marked,b'public-validation-key',41,profile=profile)['E'].any()
            edits={}
            z=marked.copy();z[12,20,2]^=1;edits['single-payload-bit']=z
            z=marked.copy();z[12,20,0]^=2;edits['single-content-bit']=z
            z=marked.copy();z[32:64,48:80]=marked[:32,:32];edits['copy-move']=z
            for label,offset in [('brightness',[64,64,64]),('chroma',[15,-9,7])]:
                candidate=marked.astype(np.int16)+offset
                mask=np.zeros(marked.shape[:2],bool);mask[32:64,48:80]=True
                eligible=((candidate>=0)&(candidate<=255)).all(axis=2)
                mask&=eligible
                if not mask.any():
                    mask.ravel()[np.flatnonzero(eligible.ravel())[:1024]]=True
                if not mask.any(): raise ValueError(f'no unclipped {label} pixels: {name}')
                z=marked.copy();z[mask]=candidate[mask].astype(np.uint8);edits[label]=z
            measurements={}
            for label,edited in edits.items():
                truth=M.measured_mask(marked,edited)
                failed=A.failures(edited,b'public-validation-key',41)
                assert truth.any() and np.array_equal(failed,truth),(name,profile,label)
                measurements[label]={'changed_pixels':int(M.measured_pixel_mask(marked,edited).sum()),
                                     'failed_blocks':int(failed.sum()),'matches_changed_blocks':True}
            assert A.failures(marked,b'wrong-validation-key',41).all()
            assert A.failures(marked,b'public-validation-key',42).all()
            mse=float(np.mean((marked.astype(float)-image.astype(float))**2))
            rows.append({'image':name,'input_sha256':hashlib.sha256(image.tobytes()).hexdigest(),
                         'profile':profile,'psnr_db':float(10*np.log10(255**2/mse)) if mse else None,
                         'intact_failed_blocks':0,'wrong_key_all_blocks_failed':True,
                         'wrong_id_all_blocks_failed':True,'edits':measurements})
    return rows


def main():
    ap=argparse.ArgumentParser(__doc__)
    ap.add_argument('--data',type=Path)
    ap.add_argument('--images',type=int,default=16)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.images<1:raise ValueError('positive image count required')
    import cv2
    if args.data:
        paths=sorted(args.data.rglob('*.jpg'))
        if len(paths)<args.images:raise ValueError('insufficient JPEGs')
        selected=np.random.default_rng(20261103).choice(len(paths),args.images,replace=False)
        def images():
            for i in selected:
                bgr=cv2.imread(str(paths[i]))
                if bgr is None:raise ValueError(f'unreadable {paths[i]}')
                yield paths[i].stem,cv2.cvtColor(cv2.resize(bgr,(512,512)),cv2.COLOR_BGR2RGB)
    else:
        def images():
            for seed in range(args.images):
                yield f'synthetic-{seed}',np.random.default_rng(seed).integers(60,130,(128,128,3),dtype=np.uint8)
    rows=check(images())
    report={'source_sha256':source_digest(ROOT),'scheme':A.SCHEME,
            'input_kind':'local JPEG sample; corpus authenticity/patient independence not established' if args.data else 'synthetic',
            'images':args.images,'protected_cases':len(rows),'rows':rows,
            'scope':'Integrity/fidelity probes only; no learned-model, clinical, adversarial-rate or paper-parity claim.'}
    atomic_json(args.out,report)
    print(f"{args.images} images; {len(rows)} protected cases; all intact/edited/key/id checks passed.")


if __name__=='__main__':main()
