"""Memory-bounded ISIC study: paired controls, seeded C8/C12, key probes.

Pixels and cached samples stay outside Git. Split manifests and numerical
receipts are written to --out. No external paper numbers are imported.
"""
import argparse
from dataclasses import asdict, fields
import hashlib
import json
from pathlib import Path
import random
import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
import run_matrix as R
from src import evidence as E, protocol as P
from src.classical import fit_count_rule
from src.calibration import fit_selective_rule, risk_coverage
from src.persistence import source_digest, atomic_write, atomic_json
from src.isic_meta import Metadata
META = Metadata(None)


class DiskSamples:
    def __init__(self, paths):
        self.paths = paths

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        with np.load(self.paths[i], allow_pickle=False) as z:
            data = {f.name: z[f.name] for f in fields(R.Sample)}
        for name in ('family', 'strata'):
            data[name] = str(data[name])
        data['cls'] = int(data['cls'])
        return R.Sample(**data)


def item(path, ident, key):
    import cv2
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise ValueError(f'unreadable image: {path}')
    rgb = cv2.cvtColor(cv2.resize(bgr, (512, 512)), cv2.COLOR_BGR2RGB)
    return R.Item(ident, META.dx_of(path.stem), E.protect(rgb, key, ident), rgb, key, META.group_of(path.stem))


def cache(paths, indices, out, families, seed, key=b'isic-study-key', wrong=False):
    out.mkdir(parents=True, exist_ok=True)
    result = []
    for j, idx in enumerate(indices):
        dst = out / f'{idx}.npz'
        if dst.exists():
            try:
                DiskSamples([dst])[0]
                result.append(dst)
                continue
            except (ValueError, OSError, KeyError, EOFError):
                pass  # a corrupt cache entry is rebuilt, never trusted
        it = item(paths[idx], int(idx), key)
        fam = families[j % len(families)]
        # Donors stay within this partition; no train/test content leakage.
        donor = item(paths[indices[(j + 1) % len(indices)]],
                     int(indices[(j + 1) % len(indices)]), key) if fam == 'T5' else None
        s = R.build_sample(it, fam, np.random.default_rng(seed + int(idx)),
                           wrong_key=wrong, donor=donor)
        atomic_write(dst, lambda f: np.savez(f, **asdict(s)))
        result.append(dst)
        if j % 100 == 0:
            print(f'cache {out.name}: {j}/{len(indices)}', flush=True)
    return DiskSamples(result)


def verdicts(samples, maps, tau, k):
    pb = [(b > tau) for b, p in maps]
    pp = [(p > tau) for b, p in maps]
    pc = [int(b.sum() > k) for b in pb]
    return R.score(samples, pb, pp, pc), pc


def learned_rule(samples, maps):
    best = None
    for tau in np.arange(.05, 1, .05):
        loc = np.mean([R.M.iou(p > tau, s.gt_pixel) for s, (b, p) in zip(samples, maps) if s.cls])
        if best is None or loc > best[0]:
            best = loc, float(tau)
    tau = best[1]
    labels = np.array([s.cls for s in samples])
    counts = np.array([(b > tau).sum() for b, p in maps])
    if not labels.any() or labels.all():
        raise ValueError('validation must include both classes')
    ks = (0, 1, 2, 4, 8, 16, 32, 64, 128, 256)
    k = max(ks, key=lambda k: .5 * ((counts[labels == 1] > k).mean() +
                                    (counts[labels == 0] <= k).mean()))
    return tau, k


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--metadata', type=Path, default=None)
    ap.add_argument('--cache', type=Path, required=True)
    ap.add_argument('--train-n', type=int, default=2000)
    ap.add_argument('--val-n', type=int, default=150)
    ap.add_argument('--test-n', type=int, default=1000)
    ap.add_argument('--epochs', type=int, default=3)
    ap.add_argument('--width', type=int, default=16)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--configs', default='C8,C12')
    ap.add_argument('--probes', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--sanity', action='store_true', help='wiring check only; receipts marked not usable as results')
    ap.add_argument('--device', choices=['auto','cpu','cuda'], default='auto')
    ap.add_argument('--threads', type=int, default=2)
    ap.add_argument('--heldout', choices=['T1','T2','T3','T4','T5'], default=None)
    args = ap.parse_args()
    if ROOT == args.cache.resolve() or ROOT in args.cache.resolve().parents:
        raise ValueError('cache contains pixels and must be outside the repository')
    cache_path, output_path = args.cache.resolve(), args.out.resolve()
    if cache_path == output_path or output_path in cache_path.parents:
        raise ValueError('cache must not be inside the persistent output directory')
    if args.data.resolve() == output_path or output_path in args.data.resolve().parents:
        raise ValueError('dataset must not be inside the persistent output directory')
    if args.epochs < 1:
        raise ValueError('epochs must be positive')
    import torch
    torch.set_num_threads(args.threads)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA requested but no usable GPU is available")
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    # CUDA pooling/interpolation kernels vary by Torch release. Prefer
    # deterministic implementations, but surface warnings rather than make a
    # supported GPU unusable. CPU remains strict and bitwise-resume tested.
    gpu_run = args.device != 'cpu' and torch.cuda.is_available()
    torch.use_deterministic_algorithms(True, warn_only=gpu_run)
    if min(args.train_n, args.val_n, args.test_n) < 7:
        raise ValueError('each partition requires at least 7 images')
    if args.out.exists() and any(args.out.iterdir()) and not args.resume:
        raise ValueError('refusing to overwrite an existing experiment')
    args.out.mkdir(parents=True, exist_ok=True)
    global META
    metadata = args.metadata or args.data / 'ISIC_2019_GroundTruth_deduplicated.csv'
    META = Metadata(metadata if metadata.exists() else None)
    if not META.has_diagnosis:
        raise ValueError('ISIC ground-truth CSV required; pass --metadata')
    paths = sorted(args.data.rglob('*.jpg'))
    if META.has_diagnosis:
        paths = [p for p in paths if p.stem in META.diagnosis]
    print(f'corpus: {len(paths)} images; {META.note}', flush=True)
    if len({META.group_of(p.stem) for p in paths}) != len(paths):
        raise ValueError('lesion grouping present: image-level runner refuses to leak groups')
    if len({p.stem for p in paths}) != len(paths):
        raise ValueError('duplicate image identifiers')
    # Fixed 70/15/15 corpus partitions. Training seed never changes membership.
    order = np.random.default_rng(20261103).permutation(len(paths))
    tr_end, va_end = int(.7 * len(paths)), int(.85 * len(paths))
    partitions = [order[:tr_end], order[tr_end:va_end], order[va_end:]]
    sizes = [args.train_n, args.val_n, args.test_n]
    if any(n > len(ids) for n, ids in zip(sizes, partitions)):
        raise ValueError('requested sample size exceeds fixed corpus partition')
    selected = [ids[:n] for n, ids in zip(sizes, partitions)]
    manifest = {name: [paths[i].stem for i in ids] for name, ids in zip(('train','val','test'), selected)}
    manifest['metadata_schema'] = META.schema
    manifest['corpus_images'] = len(paths)
    manifest['limitations'] = ['Image-level split: lesion/patient grouping unavailable.',
                               'Diagnosis labels are used when supplied; otherwise strata are UNK.',
                               'JPEG75 is a tamper event under fragile-integrity semantics.']
    source = source_digest(ROOT)
    # Bind selected image bytes, not host-specific absolute paths or mtimes.
    images_hash = hashlib.sha256()
    for idx in sorted(set(int(i) for ids in selected for i in ids)):
        images_hash.update(paths[idx].stem.encode())
        images_hash.update(hashlib.sha256(paths[idx].read_bytes()).digest())
    manifest['selected_images_sha256'] = images_hash.hexdigest()
    manifest['diagnoses_sha256'] = hashlib.sha256(json.dumps(
        {paths[i].stem: META.dx_of(paths[i].stem) for ids in selected for i in ids},
        sort_keys=True).encode()).hexdigest()
    settings = {k:v for k,v in vars(args).items()
                if k not in ('data','out','cache','metadata','resume','device','threads')}
    spec = {'source_sha256': source, 'settings': settings, 'manifest': manifest}
    spec_path = args.out / 'experiment.json'
    if spec_path.exists():
        if json.loads(spec_path.read_text()) != spec:
            raise ValueError('resume refused: source, data, split or settings changed; use a new output directory')
    elif args.resume and any(args.out.iterdir()):
        raise ValueError('legacy output has no resume contract; use a new output directory')
    atomic_json(spec_path, spec)
    atomic_json(args.out / 'manifest.json', manifest)
    run_id = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
    import platform
    import subprocess
    environment = {'python': sys.version, 'platform': platform.platform(),
                   'torch': torch.__version__, 'numpy': np.__version__,
                   'cuda_available': torch.cuda.is_available(),
                   'cuda_runtime': torch.version.cuda,
                   'determinism': 'best-effort-warn' if gpu_run else 'strict',
                   'gpu': torch.cuda.get_device_name() if torch.cuda.is_available() else None,
                   'command': sys.argv, 'source_sha256': source,
                   'packages': subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True).splitlines()}
    env_name = f'environment-resume-{time.time_ns()}.json' if args.resume else 'environment.json'
    atomic_json(args.out / env_name, environment)
    # Separate caches by input bytes, metadata, code and attack schedule.
    cache_id = hashlib.sha256(json.dumps({'source': source, 'manifest': manifest,
                                         'heldout': args.heldout}, sort_keys=True).encode()).hexdigest()[:24]
    args.cache = args.cache / cache_id
    prov = R.provenance()
    if prov['commit'] == 'unknown':
        # Portable source bundles have no Git checkout; still content-addressed.
        prov.update({'usable': True, 'code_dirty': None, 'versioning': 'source_sha256'})
    if args.sanity:
        prov['usable'] = False
    prov.update({'sanity': args.sanity, 'source_sha256': source, 'seed': args.seed, 'torch': torch.__version__,
                 'split_seed': 20261103,
                 'manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()})
    families = ['T1','T2','T3','T4','T5','none','B1:jpeg75']
    observed = [f for f in families if f != args.heldout]
    datasets = [cache(paths, ids, args.cache / name,
                      observed if name in ('train','val') else families, 10000)
                for name, ids in zip(('train','val','test'), selected)]
    train, val, test = datasets
    def save(name, receipt):
        receipt.update({'provenance': prov, 'usable': prov['usable'], 'protocol': 'isic-study-v3-portable',
                        'parameters': {k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items()}})
        atomic_json(args.out / f'{name}.json', receipt)
        print(name, receipt.get('iou_tampered_mean'), receipt.get('balanced_accuracy'), flush=True)
    for carrier_b in (False, True):
        name = 'C0_B' if carrier_b else 'C0_count'
        if args.resume and (args.out / f'{name}.json').exists() and (args.out / f'{name}_verdicts.npz').exists():
            print(f'Skipping completed {name}', flush=True)
            continue
        rule = fit_count_rule(val, carrier_b)
        outputs = [rule.predict(s.ev) for s in test]
        r = R.score(test, [m for m,c in outputs], [R.upsample(m) for m,c in outputs], [c for m,c in outputs])
        r['rule'] = rule.to_dict()
        name = 'C0_B' if carrier_b else 'C0_count'
        np.savez(args.out / f'{name}_verdicts.npz', image_id=manifest['test'],
                 prediction=[c for m,c in outputs], tampered=[s.cls for s in test],
                 iou=[R.M.iou(R.upsample(m),s.gt_pixel) for (m,c),s in zip(outputs,test)])
        save(name, r)
    for cid in args.configs.split(','):
        if cid not in ('C8', 'C12'):
            raise ValueError('this paired runner supports C8,C12 only; use --heldout/--probes for probes')
        if args.resume and (args.out / f'{cid}.json').exists() and all(
            (args.out / f'{cid}_{suffix}').exists() for suffix in ('state.pt','validation.npz','verdicts.npz')):
            print(f'Skipping completed {cid}', flush=True)
            continue
        cfg = next(c for c in P.MATRIX if c.cid == cid)
        torch.manual_seed(args.seed)  # paired initialisation discipline
        model = R.build_model(cfg, E.N_FULL, args.width)
        t0 = time.time()
        model = R.train(model, train, val, epochs=args.epochs, batch=1, lr=3e-4,
                        smoke=False, pos_weight=12., pos_weight_pixel=4.,
                        checkpoint_path=args.out / f'{cid}_checkpoint.pt',
                        resume=args.resume, run_id=f'{run_id}:{cid}', device=args.device)
        atomic_write(args.out / f'{cid}_state.pt', lambda f: torch.save(R.state_of(model), f))
        vb, vp = R.predict_maps(model, val)
        tau, k = learned_rule(val, list(zip(vb, vp)))
        _, vpc = verdicts(val, list(zip(vb, vp)), tau, k)
        tb, tp = R.predict_maps(model, test)
        r, tpc = verdicts(test, list(zip(tb, tp)), tau, k)
        # Margin to the frozen count boundary; NOT a posterior probability.
        confidence = lambda blocks: np.array([abs((b > tau).sum() - (k + .5)) /
                                  (abs((b > tau).sum() - (k + .5)) + 64) for b in blocks])
        vc, tc = confidence(vb), confidence(tb)
        vy = np.array([pc == s.cls for pc,s in zip(vpc,val)])
        ty = np.array([pc == s.cls for pc,s in zip(tpc,test)])
        rule = fit_selective_rule(vc, vy)
        accept = rule.accept(tc)
        np.savez(args.out / f'{cid}_validation.npz', image_id=manifest['val'],
                 confidence=vc, correct=vy)
        if args.heldout:
            idx = [i for i,s in enumerate(test) if s.family == args.heldout]
            r['heldout'] = {'family': args.heldout, 'n': len(idx),
                'iou_tampered_mean': float(np.mean([R.M.iou(tp[i]>tau,test[i].gt_pixel) for i in idx])) if idx else None,
                'training_families': observed}
        r.update({'tau': tau, 'k': k, 'seconds': time.time()-t0,
                  'aurc': risk_coverage(tc,ty)['aurc'],
                  'selective': {'feasible_on_validation': rule.feasible,
                      'threshold': rule.threshold if rule.feasible else None,
                      'test_coverage': float(accept.mean()),
                      'test_risk': float((~ty[accept]).mean()) if accept.any() else None}})
        np.savez(args.out / f'{cid}_verdicts.npz', image_id=manifest['test'],
                 confidence=tc, correct=ty, prediction=tpc,
                 iou=[R.M.iou(p>tau,s.gt_pixel) for p,s in zip(tp,test)],
                 tampered=[s.cls for s in test])
        if args.probes:
            for name,key,wrong in [('rekey',b'isic-study-key-2',False), ('wrong_key',b'isic-study-key',True)]:
                probe = cache(paths, selected[2], args.cache/name, families,10000,key,wrong)
                b,p = R.predict_maps(model,probe)
                result,_ = verdicts(probe,list(zip(b,p)),tau,k)
                r[name] = result
        save(cid, r)


if __name__ == '__main__':
    from filelock import FileLock, Timeout
    # Lock sits beside the output so it does not invalidate an empty-run check.
    lock_parser = argparse.ArgumentParser(add_help=False)
    lock_parser.add_argument('--out', type=Path)
    lock_args, _ = lock_parser.parse_known_args()
    if lock_args.out is None:
        main()
    else:
        output = lock_args.out
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with FileLock(str(output) + '.lock', timeout=0):
                main()
        except Timeout:
            raise SystemExit('another process is already writing this output directory')
