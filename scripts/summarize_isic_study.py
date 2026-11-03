"""Summarise current files defensively; malformed/mixed results never imply completion."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.names import model_name
from src.persistence import artifacts_valid, atomic_json


def summarize(root):
    root = Path(root)
    rows, missing, integrity, invalid, comparisons = [], [], [], [], []
    versions, manifests, settings = set(), set(), set()

    def read(path):
        try:
            value = json.loads(path.read_text())
            if not isinstance(value, dict):
                raise ValueError('expected object')
            return value
        except (OSError, ValueError, TypeError) as exc:
            invalid.append({'path': str(path), 'error': str(exc)})
            return None

    def receipt(folder, config, seed):
        path = folder / f'{config}.json'
        if not path.exists():
            missing.append(str(path))
            return None
        r = read(path)
        if r is None:
            return None
        try:
            for field in ('iou_tampered_mean', 'balanced_accuracy', 'tpr', 'fpr'):
                if not np.isscalar(r[field]) or not np.isfinite(r[field]) or not 0 <= r[field] <= 1:
                    raise ValueError(f'invalid metric: {field}')
            if r['provenance']['seed'] != seed or not r['provenance']['source_sha256'] or not r['provenance']['manifest_sha256']:
                raise ValueError('missing or inconsistent provenance')
            for field in ('source_sha256','manifest_sha256'):
                fingerprint=r['provenance'][field]
                if not isinstance(fingerprint,str) or len(fingerprint)!=64 or any(c not in '0123456789abcdef' for c in fingerprint):
                    raise ValueError(f'invalid fingerprint: {field}')
            frozen = {key: r['parameters'][key] for key in
                      ('train_n','val_n','test_n','epochs','ae_epochs','width','sanity')}
            if r['n'] != r['n_tampered'] + r['n_intact'] or min(r['n_tampered'], r['n_intact']) <= 0:
                raise ValueError('invalid class denominators')
        except (KeyError, ValueError, TypeError) as exc:
            invalid.append({'path': str(path), 'error': str(exc)})
            return None
        suffixes = ['.json', '_verdicts.npz'] if config.startswith('C0') else ['.json', '_verdicts.npz', '_state.pt', '_validation.npz']
        valid = artifacts_valid(folder, config, suffixes)
        if not valid:
            integrity.append(str(path))
        versions.add(r['provenance']['source_sha256'])
        manifests.add(r['provenance']['manifest_sha256'])
        settings.add(json.dumps(frozen,sort_keys=True))
        r['_verified'] = valid
        return r

    from src.ablations import ABLATIONS
    study=read(root/'study.json') if (root/'study.json').exists() else {}
    variants=ABLATIONS if study and study.get('ablations') else ()
    for seed in (0, 1, 2):
        folder = root / f'seed-{seed}'
        for config in ('C0_count', 'C0_B', 'C8', 'C12', *variants):
            r = receipt(folder, config, seed)
            if r is None:
                continue
            row = {'seed': seed, 'config': config, 'model': model_name(config),
                   'usable': bool(r.get('usable')) and r['_verified'], 'artifacts_verified': r['_verified'],
                   'iou_tampered': r['iou_tampered_mean'], 'balanced_accuracy': r['balanced_accuracy'],
                   'tpr': r['tpr'], 'fpr': r['fpr']}
            if 'selective' in r:
                row['selective'] = r['selective']
            if 'rekey' in r:
                try:
                    delta = float(r['iou_tampered_mean'] - r['rekey']['iou_tampered_mean'])
                    if not np.isfinite(delta):
                        raise ValueError('invalid rekey metric')
                    row.update(rekey_drop_iou=delta, rekey_gate_pass=delta <= .05)
                except (KeyError, ValueError, TypeError) as exc:
                    invalid.append({'path': str(folder / f'{config}.json'), 'error': str(exc)})
                    row['usable'] = False
            rows.append(row)
        for a, b in [('C0_count', 'C0_B'), ('C0_count', 'C8'), ('C8', 'C12')] + [('C8',v) for v in variants]:
            path = folder / f'{b}_vs_{a}.json'
            if not path.exists():
                comparisons.append({'path': str(path), 'error': 'missing'})
                continue
            value = read(path)
            try:
                expected = {side: hashlib.sha256((folder / f'{name}_verdicts.npz').read_bytes()).hexdigest()
                            for side, name in [('a', a), ('b', b)]}
                if value is None or not value.get('measured_masks_verified') or value.get('input_sha256') != expected:
                    raise ValueError('comparison is not bound to these current measured-mask packets')
            except (OSError, ValueError) as exc:
                comparisons.append({'path': str(path), 'error': str(exc)})

    heldout_record = receipt(root / 'heldout-T5', 'C8', 0)
    heldout = None if heldout_record is None else heldout_record.get('heldout')
    if heldout_record is not None:
        try:
            if not isinstance(heldout,dict) or heldout.get('family') != 'T5':
                raise ValueError('heldout family is not T5')
            if heldout['n'] <= 0 or not np.isfinite(heldout['iou_tampered_mean']) or not 0 <= heldout['iou_tampered_mean'] <= 1:
                raise ValueError('invalid heldout metric/denominator')
            if not heldout['training_families'] or 'T5' in heldout['training_families']:
                raise ValueError('T5 was not held out from training')
        except (KeyError,ValueError,TypeError) as exc:
            invalid.append({'path': str(root / 'heldout-T5' / 'C8.json'), 'error': str(exc)})
    aggregates = {}
    homogeneous = len(versions) == 1 and len(manifests) == 1 and len(settings) == 1
    if homogeneous and not invalid and not integrity:
        for config in ('C8', 'C12', *variants):
            rr = [r for r in rows if r['config'] == config and r['usable']]
            if len(rr) == 3:
                aggregates[model_name(config)] = {
                    metric: {'mean': float(np.mean([r[metric] for r in rr])),
                             'seed_sd': float(np.std([r[metric] for r in rr], ddof=1))}
                    for metric in ('iou_tampered', 'balanced_accuracy', 'tpr', 'fpr')}
    return {'complete': not (missing or integrity or invalid or comparisons) and homogeneous,
            'completion_meaning': 'execution/artifact completeness only; not scientific or security approval',
            'missing': missing, 'integrity_failures': integrity, 'invalid_receipts': invalid,
            'comparison_failures': comparisons, 'mixed_source_versions': len(versions) > 1,
            'mixed_split_manifests': len(manifests) > 1, 'mixed_training_settings': len(settings) > 1,
            'source_versions': sorted(versions), 'runs': rows,
            'three_seed_aggregates': aggregates, 'heldout_T5': heldout,
            'limitations': ['Image-level split cannot establish patient independence without identifiers.',
                           'Image-bootstrap intervals do not measure training-seed uncertainty.',
                           'Validation risk constraints are empirical, not a population guarantee.',
                           'RGB MAC needs lossless storage, secret keys and a trusted image/version identifier; no clinical or paper-parity approval.']}


def main():
    ap = argparse.ArgumentParser(__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = summarize(args.root)
    atomic_json(args.out, result)
    print(f"complete={result['complete']}; completed receipts={len(result['runs'])}; missing={len(result['missing'])}")


if __name__ == '__main__':
    main()
