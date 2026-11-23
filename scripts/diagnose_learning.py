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


def operating_point_audit(samples, blocks, pixels):
    """Compare two TRAIN-only objectives, never replace the frozen shared rule.

    Kept separate from training: independent thresholds are a diagnostic contrast,
    not an approved study amendment or evidence of generalisation.
    """
    tau, k = S.learned_rule(samples, list(zip(blocks, pixels)))
    metrics, _ = S.verdicts(samples, list(zip(blocks, pixels)), tau, k)
    choices = [(float(np.mean([R.M.iou(p > t, sample.gt_pixel)
                               for p, sample in zip(pixels, samples) if sample.cls])), float(t))
               for t in np.linspace(.05, .95, 19)]
    best_iou, pixel_tau = max(choices, key=lambda item: (item[0], -item[1]))
    intact = [int((p > pixel_tau).sum()) for p,sample in zip(pixels, samples) if not sample.cls]
    local_ious = [R.M.iou(p > pixel_tau, sample.gt_pixel) for p,sample in zip(pixels, samples)
                  if sample.cls and sample.family != 'B1:jpeg75']
    by_family = {family: float(np.mean([R.M.iou(p > pixel_tau, sample.gt_pixel)
                                      for p,sample in zip(pixels, samples) if sample.cls and sample.family == family]))
                 for family in sorted({sample.family for sample in samples if sample.cls})}
    return {'shared_rule': {'tau': tau, 'k': k, 'balanced_accuracy': metrics['balanced_accuracy'],
                             'tampered_pixel_iou': metrics['iou_tampered_mean'],
                             'collapse': collapse_summary(map_diagnostics(samples, blocks, pixels, tau))},
            'pixel_only_training_diagnostic': {'tau': pixel_tau, 'tampered_pixel_iou': best_iou,
                                               'intact_positive_pixel_counts': intact,
                                               'non_jpeg_tampered_pixel_iou': float(np.mean(local_ious)) if local_ious else None,
                                               'tampered_pixel_iou_by_family': by_family},
            'warning': 'TRAIN-only operating-point contrast, not alternative benchmark results'}


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--synthetic', action='store_true')
    ap.add_argument('--data', type=Path)
    ap.add_argument('--metadata', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--n', type=int, default=7)
    ap.add_argument('--epochs', type=int, default=20)
    ap.add_argument('--width', type=int, default=4)
    ap.add_argument('--model', choices=('main','attention','both'), default='both',
                    help='diagnostic selection only, not a study config change')
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
    baseline_blocks = [sample.ev[0] > .5 for sample in samples]
    baseline_pixels = [R.M.upsample_to(b, sample.gt_pixel.shape) for b,sample in zip(baseline_blocks,samples)]
    report['classical_reference'] = {
        'method': 'strict failed-block expansion on the same protected TRAIN samples',
        'metrics': R.score(samples, baseline_blocks, baseline_pixels, [int(b.any()) for b in baseline_blocks])}
    atomic_json(args.out / 'diagnostic.json', report)
    configs = {'main': ('C8',), 'attention': ('C12',), 'both': ('C8','C12')}[args.model]
    for cid in configs:
        model = S.build_paired_model(cid, args.width, args.seed)
        ae = pretrain_authentic(model, samples, 2, args.out / f'{cid}_ae.pt', False,
                                'diagnostic:' + cid, device=args.device)
        # Zero epochs only moves modules to the requested device.
        R.train(model, samples, samples, epochs=0, batch=1, lr=3e-4,
                smoke=args.synthetic, device=args.device)
        stages, epoch_trace = {}, []
        name = model_name(cid)
        report['models'][name] = {'status': 'running', 'epoch_trace': epoch_trace}
        def observe(current, record):
            eb, ep = R.predict_maps(current, samples)
            record['operating_points'] = operating_point_audit(samples, eb, ep)
            epoch_trace.append(record)
            atomic_json(args.out / 'diagnostic.json', report)
        for phase in ('before', 'after'):
            if phase == 'after':
                # Selection deliberately uses the SAME TRAIN examples, not VAL.
                # Loss weights/LR match study; only diagnostic epoch budget differs.
                R.train(model, samples, samples, epochs=args.epochs, batch=1, lr=3e-4,
                        pos_weight=12., pos_weight_pixel=4., smoke=args.synthetic, device=args.device,
                        log=lambda line: print(line.replace('val ', 'TRAIN(in-sample) '), flush=True),
                        epoch_observer=observe)
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
        training_audit = model['training_audit']
        report['models'][name] = {'status': 'complete', 'authentic_training': ae,
                                 'epoch_trace': epoch_trace, 'selected_epoch': training_audit['selected_epoch'],
                                 'last_completed_epoch': training_audit['last_completed_epoch'],
                                 'selection_scope': 'TRAIN-only, in-sample localisation epoch selection', **stages}
        atomic_json(args.out / 'diagnostic.json', report)
    # Cached pixels are not benchmark evidence and must stay outside Git.
    print('Diagnostic saved:', args.out / 'diagnostic.json', flush=True)


if __name__ == '__main__':
    main()
