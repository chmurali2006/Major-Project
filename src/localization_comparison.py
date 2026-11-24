"""Shared localisation operators/metrics; method-specific protected RGB truth.

No claim that fragile exact-match authentication and robust learned localisation
have equivalent trust contracts. JPEG is reported separately, not pooled with edits.
"""
import hashlib
import io
import time
import numpy as np
from PIL import Image
from .showcase import confusion,mask_iou


def operators(rgb,seed):
    if rgb.dtype!=np.uint8 or rgb.shape!=(512,512,3):raise ValueError('prepared 512x512 RGB required')
    rng=np.random.default_rng(seed)
    y,x=map(int,rng.integers(64,384,2))
    yield 'intact','intact',rgb.copy()
    one=rgb.copy();one[y,x,0]^=np.uint8(1)
    yield 'one-bit','edit',one
    local=rgb.copy();local[y:y+32,x:x+32]=np.clip(local[y:y+32,x:x+32].astype(np.int16)+30,0,255).astype(np.uint8)
    yield 'brightness32','edit',local
    patch=rgb.copy();patch[y:y+64,x:x+64]=np.array([32,224,64],np.uint8)
    yield 'replace64','edit',patch
    copy=rgb.copy();copy[y:y+64,x:x+64]=rgb[0:64,0:64]
    yield 'copy64','edit',copy
    buf=io.BytesIO();Image.fromarray(rgb).save(buf,format='JPEG',quality=75,subsampling=0)
    with Image.open(io.BytesIO(buf.getvalue())) as im:jpeg=np.array(im.convert('RGB'))
    yield 'jpeg75','benign-lossy',jpeg


def evaluate(rgb,reference,localize,seed):
    if reference.dtype!=np.uint8 or reference.shape!=rgb.shape:raise ValueError('protected reference geometry/dtype mismatch')
    delta=reference.astype(float)-rgb
    mse=float(np.mean(delta**2))
    rows=[];maps={}
    for ident,kind,received in operators(reference,seed):
        start=time.perf_counter();score,pred=localize(received)
        seconds=time.perf_counter()-start
        if pred.dtype!=np.bool_ or pred.shape!=reference.shape[:2] or score.shape!=pred.shape or not np.isfinite(score).all():
            raise ValueError('finite score and boolean same-size prediction required')
        truth=np.any(received!=reference,axis=2)
        counts=confusion(pred,truth);den=2*counts['tp']+counts['fp']+counts['fn']
        rows.append({'case':ident,'family':kind,'source_operator_seed':seed,
                     'received_rgb_sha256':hashlib.sha256(received.tobytes()).hexdigest(),
                     'truth_sha256':hashlib.sha256(truth.tobytes()).hexdigest(),
                     'changed_pixels':int(truth.sum()),'highlighted_pixels':int(pred.sum()),
                     'confusion':counts,'pixel_iou':mask_iou(pred,truth),
                     'pixel_f1':2*counts['tp']/den if den else None,
                     'missed_edit_fraction':counts['fn']/int(truth.sum()) if truth.any() else None,
                     'localization_seconds':seconds,'predicted_image_positive':bool(pred.any())})
        maps[ident+'_truth']=truth;maps[ident+'_prediction']=pred;maps[ident+'_score']=score
    return {'source_rgb_sha256':hashlib.sha256(rgb.tobytes()).hexdigest(),
            'reference_rgb_sha256':hashlib.sha256(reference.tobytes()).hexdigest(),
            'embedding_mse':mse,'embedding_psnr_db':10*np.log10(255**2/mse) if mse else None,
            'maximum_channel_change':int(abs(delta).max()),'cases':rows},maps
