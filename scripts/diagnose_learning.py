"""TRAIN-only memorisation diagnostic. Never a benchmark or study receipt.

Use --synthetic for local plumbing, or --data/--metadata for the fixed ISIC
training partition. No validation/test images are decoded. New output required.
"""
import argparse
import hashlib
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import numpy as np
import run_matrix as R
import run_isic_study as S
from src.authentic_training import pretrain_authentic
from src.isic_meta import Metadata
from src.names import model_name
from src.persistence import atomic_json, atomic_write, source_digest
from src.prediction_diagnostics import map_diagnostics, collapse_summary


def training_indices(n, count):
    if count < 7 or count > int(.7 * n):
        raise ValueError('need >=7 examples, within fixed TRAIN partition')
    return np.random.default_rng(20261103).permutation(n)[:int(.7 * n)][:count]


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--synthetic', action='store_true')
    ap.add_argument('--data', type=Path)
    ap.add_argument('--metadata', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--n', type=int, default=7)
    ap.add_argument('--epochs', type=int, default=20)
    ap.add_argument('--width', type=int, default=4)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--device', choices=('cpu', 'cuda', 'auto'), default='auto')
    args = ap.parse_args()
    if args.out.exists():
        raise ValueError('new diagnostic output directory required')
    if args.n < 7 or not 1 <= args.epochs <= 100 or args.width < 1:
        raise ValueError('invalid bounded diagnostic settings')
    if args.synthetic == bool(args.data or args.metadata):
        raise ValueError('choose --synthetic OR --data and --metadata')
    import torch
    torch.set_num_threads(2)
    torch.manual_seed(args.seed)
    torch.use_deterministic_algorithms(True)
    families = ['T1', 'T2', 'T3', 'T4', 'T5', 'none', 'B1:jpeg75']
    args.out.mkdir(parents=True)
    if args.synthetic:
        items = R.load_items(None, args.n, args.seed, True)
        samples = [R.build_sample(it, families[j % 7], np.random.default_rng(10000+j),
                                 donor=items[(j+1) % len(items)] if families[j % 7] == 'T5' else None)
                   for j, it in enumerate(items)]
        ids = ['synthetic-' + str(i) for i in range(args.n)]
    else:
        if args.data is None or args.metadata is None:
            raise ValueError('--data and --metadata required')
        from src.dataset_audit import label_rows
        label_rows(args.metadata)
        S.META = Metadata(args.metadata)
        paths = sorted(p for p in args.data.rglob('*.jpg') if p.stem in S.META.diagnosis)
        if len({p.stem for p in paths}) != len(paths):
            raise ValueError('duplicate image IDs')
        indices = training_indices(len(paths), args.n)
        ids = [paths[i].stem for i in indices]
        cache_dir = tempfile.TemporaryDirectory(prefix='keyswm-diagnostic-')
        samples = S.cache(paths, indices, Path(cache_dir.name) / 'train', families, 10000)
    report = {'usable': False, 'purpose': 'TRAIN-only memorisation; not generalisation',
              'synthetic': args.synthetic, 'source_sha256': source_digest(ROOT),
              'settings': vars(args) | {'out': str(args.out), 'data': str(args.data) if args.data else None, 'metadata': str(args.metadata) if args.metadata else None},
              'training_ids': ids,
              'input_sha256': {} if args.synthetic else {paths[i].stem: hashlib.sha256(paths[i].read_bytes()).hexdigest() for i in indices},
              'metadata_sha256': None if args.synthetic else hashlib.sha256(args.metadata.read_bytes()).hexdigest(),
              'torch': torch.__version__, 'cuda_runtime': torch.version.cuda,
              'gpu': torch.cuda.get_device_name() if torch.cuda.is_available() else None,
              'determinism': 'strict; unsupported operations raise', 'models': {}}
    atomic_json(args.out / 'diagnostic.json', report)
    for cid in ('C8', 'C12'):
        model = S.build_paired_model(cid, args.width, args.seed)
        ae = pretrain_authentic(model, samples, 2, args.out / f'{cid}_ae.pt', False,
                                'diagnostic:' + cid, device=args.device)
        # Zero epochs only moves modules to the requested device.
        R.train(model, samples, samples, epochs=0, batch=1, lr=3e-4,
                smoke=args.synthetic, device=args.device)
        stages = {}
        for phase in ('before', 'after'):
            if phase == 'after':
                # Selection deliberately uses the SAME TRAIN examples, not VAL.
                # Loss weights/LR match study; only diagnostic epoch budget differs.
                R.train(model, samples, samples, epochs=args.epochs, batch=1, lr=3e-4,
                        pos_weight=12., pos_weight_pixel=4., smoke=args.synthetic, device=args.device,
                        log=lambda line: print(line.replace('val ', 'TRAIN(in-sample) '), flush=True))
            b, p = R.predict_maps(model, samples)
            tau, k = S.learned_rule(samples, list(zip(b,p)))
            metrics, pred = S.verdicts(samples, list(zip(b,p)), tau, k)
            packet = map_diagnostics(samples, b, p, tau)
            atomic_write(args.out / f'{cid}_{phase}.npz', lambda f: np.savez_compressed(
                f, image_id=ids, prediction=pred, tampered=[s.cls for s in samples], tau=tau, k=k, **packet))
            # Compare heads on TRAIN only; this does not replace the joint rule.
            loc_tau = max(np.linspace(.05, .95, 19), key=lambda t: np.mean(
                [R.M.iou(prob > t, sample.gt_pixel) for prob, sample in zip(p, samples) if sample.cls]))
            loc_iou = float(np.mean([R.M.iou(prob > loc_tau, sample.gt_pixel)
                                     for prob, sample in zip(p, samples) if sample.cls]))
            stages[phase] = {'tau': tau, 'k': k, 'metrics': metrics, 'collapse': collapse_summary(packet),
                             'pixel_only_training_tau': float(loc_tau), 'pixel_only_training_iou': loc_iou}
        report['models'][model_name(cid)] = {'authentic_training': ae, **stages}
        atomic_json(args.out / 'diagnostic.json', report)
    # Cached pixels are not benchmark evidence and must stay outside Git.
    print('Diagnostic saved:', args.out / 'diagnostic.json', flush=True)


if __name__ == '__main__':
    main()
