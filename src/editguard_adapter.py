"""Minimal EditGuard clean-checkpoint inference adapter, not vendored upstream code.

Loads a user-supplied reviewed checkout. Only unused BasicSR imports and one
CUDA-only allocation are patched in a temporary copy; weights load strictly.
No generative edit pipeline, training loop or global CUDA monkeypatch is used.
"""
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import numpy as np

PINNED_COMMIT='174778fb371640bb31b32fcb9f7bfd440c88766b'
CLEAN_MD5='fd8c6987d67071d3e629133499b44765'


def residual_mask(recovered, threshold=.2):
    if not isinstance(recovered,np.ndarray) or recovered.dtype!=np.uint8 or recovered.ndim!=3 or recovered.shape[2]!=3:
        raise ValueError('quantized recovered HWC RGB uint8 required')
    if not np.isfinite(threshold) or not 0<=threshold<=1:raise ValueError('threshold must be in [0,1]')
    template=np.zeros_like(recovered);template[:,:,2]=255
    # Official maskextract.py thresholds channels separately then sums them.
    # Use boolean any, avoiding its uint8 wraparound when multiple channels fire.
    score=np.abs(recovered.astype(np.float64)-template)/255.
    return score.max(2),np.any(score>threshold,axis=2)


class EditGuard:
    def __init__(self,checkout,checkpoint,device='cpu'):
        import torch
        import yaml
        self.torch=torch;self.device=device
        checkout=Path(checkout).resolve();checkpoint=Path(checkpoint).resolve()
        commit=subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip()
        if commit!=PINNED_COMMIT:raise ValueError('reviewed pinned EditGuard commit required')
        dirty=subprocess.check_output(['git','-C',str(checkout),'diff','HEAD','--','code'],text=True)
        if dirty:raise ValueError('upstream code checkout must have no tracked changes')
        digest=hashlib.md5(checkpoint.read_bytes()).hexdigest()
        if digest!=CLEAN_MD5:raise ValueError('expected reviewed official clean checkpoint bytes')
        if 'models' in sys.modules:raise RuntimeError('upstream models module namespace already occupied; use a fresh process')
        self.temp=tempfile.TemporaryDirectory(prefix='editguard-adapter-')
        root=Path(self.temp.name);shutil.copytree(checkout/'code'/'models',root/'models',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        patches={
            'modules/Inv_arch.py':('from basicsr.archs.arch_util import flow_warp',''),
            'modules/Subnet_constructor.py':('from basicsr.archs.arch_util import flow_warp, ResidualBlockNoBN',''),
            'modules/common.py':('torch.zeros([out_batch, out_channel, out_height, out_width]).float().cuda()',
                                 'x.new_zeros([out_batch, out_channel, out_height, out_width])')}
        original_hashes={}
        for p in (root/'models').rglob('*.py'):
            original_hashes[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
        for relative,(old,new) in patches.items():
            p=root/'models'/relative;s=p.read_text()
            if s.count(old)!=1:raise ValueError('upstream compatibility patch did not match exactly once')
            p.write_text(s.replace(old,new))
        sys.path.insert(0,str(root))
        from models.networks import define_G_v2
        from models.modules.common import DWT,IWT
        with (checkout/'code/options/test_editguard.yml').open() as f:opt=yaml.safe_load(f)
        # Upstream options/options.py copies top-level scale into network_G.
        opt['network_G']['scale']=opt['scale']
        self.model=define_G_v2(opt).to(device).eval()
        state=torch.load(checkpoint,map_location='cpu',weights_only=True)
        self.model.load_state_dict(state,strict=True)
        self.dwt=DWT().to(device);self.iwt=IWT().to(device)
        self.provenance={'repository':'https://github.com/xuanyuzhang21/EditGuard','commit':commit,
                         'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                         'checkpoint_md5':digest,'checkpoint_kind':'official clean.pth',
                         'strict_state_dict':True,'network_scale':opt['network_G']['scale'],
                         'option_parser_parity':'top-level scale overrides network_G scale, as in upstream options.parse',
                         'compatibility_patches':patches,
                         'upstream_python_sha256':original_hashes,'torch':torch.__version__,
                         'device':device,'parameter_count':sum(p.numel() for p in self.model.parameters()),
                         'mask_rule':'official saved-image residual: any RGB channel > 0.2 against blue template',
                         'copyright_message_policy':'deterministic per-image random +/-0.5, 64 bits',
                         'license_status':'No root licence found in inspected upstream tree; review redistribution permission before distributing upstream code/weights.'}

    def tensor(self,rgb):
        if rgb.dtype!=np.uint8 or rgb.shape!=(512,512,3):raise ValueError('EditGuard reviewed protocol requires prepared 512x512 uint8 RGB')
        return self.torch.from_numpy(rgb.transpose(2,0,1).copy()).float().unsqueeze(0).to(self.device)/255.

    def quantize(self,x):
        return x.detach().clamp(0,1).mul(255).round().to(self.torch.uint8)[0].permute(1,2,0).cpu().numpy()

    def embed(self,rgb,seed=0):
        torch=self.torch;x=self.tensor(rgb)
        template=torch.zeros_like(x);template[:,2]=1
        message=torch.from_numpy(np.random.default_rng(seed).choice([-.5,.5],(1,64)).astype(np.float32)).to(self.device)
        with torch.inference_mode():
            _,container=self.model(x=self.dwt(x),x_h=[self.dwt(template)],message=message)
        return self.quantize(container)

    def localize(self,rgb,threshold=.2):
        with self.torch.inference_mode():
            _,recovered,_,_=self.model(x=self.tensor(rgb),rev=True)
            recovered=self.quantize(self.iwt(recovered[0]))
        return residual_mask(recovered,threshold)
