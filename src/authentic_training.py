"""Reconstruct only intact TRAIN evidence, then freeze the evidence autoencoder."""
import time
import numpy as np
import torch
from .persistence import atomic_write, load_checkpoint


def pretrain_authentic(model, samples, epochs, checkpoint, resume, run_id, device='auto', log=print):
    ae = model['ae']
    if ae is None:
        return {'epochs': 0, 'n_authentic_train': 0}
    device = ('cuda' if torch.cuda.is_available() else 'cpu') if device == 'auto' else device
    ae.to(device)
    for p in ae.parameters():
        p.requires_grad_(True)
    authentic = [i for i in range(len(samples)) if samples[i].cls == 0 and not samples[i].gt_pixel.any()]
    if not authentic or epochs < 1:
        raise ValueError('authentic-only pretraining requires intact TRAIN examples and positive epochs')
    opt = torch.optim.AdamW(ae.parameters(), lr=3e-4)
    start = 0
    if resume and checkpoint.exists():
        ck = load_checkpoint(checkpoint, device)
        if ck['run_id'] != run_id:
            raise ValueError('authentic pretraining checkpoint mismatch')
        ae.load_state_dict(ck['model'])
        opt.load_state_dict(ck['optimizer'])
        start = ck['epoch']
        torch.set_rng_state(ck['rng'].cpu())
        if device.startswith('cuda') and ck['cuda_rng'] is not None:
            torch.cuda.set_rng_state_all([x.cpu() for x in ck['cuda_rng']])
    loss_value = None
    for ep in range(start, epochs):
        ae.train()
        losses = []
        began = time.monotonic()
        for i in np.random.default_rng(ep).permutation(authentic):
            sample = samples[int(i)]
            if sample.cls != 0 or sample.gt_pixel.any():
                raise ValueError('tampered example reached authentic-only reconstruction training')
            x = torch.from_numpy(sample.ev).float().unsqueeze(0).to(device)
            opt.zero_grad()
            rec, _ = ae(x)
            # Scale-normalised squared residual avoids a high-scale carrier channel
            # dominating all low-scale keyed channels in reconstruction training.
            scale = x.square().mean(dim=(2,3), keepdim=True).sqrt().clamp_min(1.)
            loss = ((rec-x) / scale).square().mean()
            if not torch.isfinite(loss):
                raise ValueError('nonfinite reconstruction loss')
            loss.backward()
            opt.step()
            losses.append(float(loss.detach()))
        loss_value = float(np.mean(losses))
        ck = {'run_id': run_id, 'model': ae.state_dict(), 'optimizer': opt.state_dict(),
              'epoch': ep+1, 'rng': torch.get_rng_state(),
              'cuda_rng': torch.cuda.get_rng_state_all() if device.startswith('cuda') else None}
        atomic_write(checkpoint, lambda f: torch.save(ck, f))
        log(f'Authentic reconstruction epoch {ep+1}/{epochs}: loss={loss_value:.5f}, '
            f'n={len(authentic)}, elapsed={(time.monotonic()-began)/60:.2f} min')
    for p in ae.parameters():
        p.requires_grad_(False)
        p.grad = None
    ae.eval()
    return {'epochs': epochs, 'n_authentic_train': len(authentic),
            'selection': 'cls=0 and empty measured pixel mask, TRAIN partition only',
            'frozen_during_localisation_training': True}
