"""Supported subset of PFF-WM4.1.2, explicitly adapted implementation choices.

Returns exact RGB-change truth, not semantic lesion-removal ground truth.
No adversarial/generative attacks: these require independently frozen models.
Resize interpolation, contrast implementation, Gaussian kernel/boundary and local
blur strength were not established from the paper; pinned below as OUR choices.
"""
import io
import numpy as np
from PIL import Image,ImageEnhance

SETTINGS={'copy_patch':32,'jpeg_quality':[70,85,95],'jpeg_subsampling':0,
    'resize_scale':.9,'resize_rounding':'round','resize_interpolation':'Pillow bicubic down and restore',
    'contrast_factors':[.9,1.1],'contrast_operator':'Pillow ImageEnhance.Contrast (mean-grey pivot)',
    'global_blur_sigma':.5,'local_blur_sigma':2.,'gaussian_truncate':4.,'gaussian_boundary':'reflect',
    'local_blur_note':'32square Gaussian-blurred surrogate; NOT verified semantic lesion removal'}


def gaussian(rgb,sigma):
    # Separable Gaussian on RGB spatial axes only; explicit kernel, no channel blur.
    radius=int(4*sigma+.5);coords=np.arange(-radius,radius+1)
    weights=np.exp(-coords**2/(2*sigma*sigma));weights/=weights.sum()
    result=rgb.astype(np.float64)
    for axis in (0,1):
        pads=[(0,0)]*3;pads[axis]=(radius,radius)
        padded=np.pad(result,pads,mode='reflect');out=np.zeros_like(result)
        for i,w in enumerate(weights):
            slices=[slice(None)]*3;slices[axis]=slice(i,i+result.shape[axis]);out+=w*padded[tuple(slices)]
        result=out
    return np.clip(np.rint(result),0,255).astype(np.uint8)


def operators(rgb,seed):
    x=np.asarray(rgb)
    if x.dtype!=np.uint8 or x.shape!=(512,512,3):raise ValueError('512square uint8RGB required')
    rng=np.random.default_rng(seed)
    dy,dx=map(int,rng.integers(0,481,2))
    # Disjoint source/destination prevents trivial self-copy. Texture can still match.
    while True:
        sy,sx=map(int,rng.integers(0,481,2))
        if abs(sy-dy)>=32 or abs(sx-dx)>=32:break
    def packet(name,family,y,parameters,region=None):
        truth=np.any(x!=y,axis=2)
        return {'case':name,'family':family,'received':y,'pixel_truth':truth,
                'requested_region':region,'parameters':parameters,'operator_seed':seed}
    yield packet('intact','intact',x.copy(),{})
    region=np.zeros((512,512),bool);region[dy:dy+32,dx:dx+32]=True
    copy=x.copy();copy[dy:dy+32,dx:dx+32]=x[sy:sy+32,sx:sx+32]
    yield packet('copy32','classic_tamper',copy,{'destination':[dy,dx],'source':[sy,sx],'patch_size':32},region.copy())
    local=x.copy();blurred=gaussian(x,2.);local[region]=blurred[region]
    yield packet('local_blur32_surrogate','classic_surrogate',local,{'sigma':2.,'destination':[dy,dx],'patch_size':32},region.copy())
    for quality in (70,85,95):
        buffer=io.BytesIO();Image.fromarray(x).save(buffer,format='JPEG',quality=quality,subsampling=0)
        with Image.open(io.BytesIO(buffer.getvalue())) as im:y=np.array(im.convert('RGB'))
        yield packet('jpeg'+str(quality),'paper_benign',y,{'quality':quality,'subsampling':0})
    im=Image.fromarray(x);size=round(512*.9)
    resized=im.resize((size,size),Image.Resampling.BICUBIC).resize((512,512),Image.Resampling.BICUBIC)
    yield packet('resize90_restore','paper_benign',np.array(resized),{'intermediate_size':size,'interpolation':'bicubic'})
    for factor in (.9,1.1):
        yield packet('contrast'+str(round(100*factor)),'paper_benign',np.array(ImageEnhance.Contrast(im).enhance(factor)),{'factor':factor})
    yield packet('gaussian05','paper_benign',gaussian(x,.5),{'sigma':.5,'boundary':'reflect','truncate':4.})
