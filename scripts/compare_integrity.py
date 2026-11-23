"""Compare embedded HMAC and non-embedding signatures, with no training/test tuning.

Engineering trade-off experiment, not a claim of novel cryptography or clinical
safety. Operators are matched but embedded/non-embedded references differ: each
method's pixel truth is measured separately. Public reproducible keys are ONLY
for this experiment. Decoded RGB, not file bytes, DICOM headers or patient identity,
is authenticated. JSON output contains numerical evidence, not image pixels.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import sys
import time
import platform
import cryptography
import PIL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import authentication as A, signed_manifest as S
from src.persistence import atomic_json, source_digest
from src.showcase import DEMO_KEY, IMAGE_ID, scenarios, block_truth, confusion, mask_iou, png_bytes


def experiment(rgb, image_id=IMAGE_ID):
    private = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b'PUBLIC benchmark signing seed').digest())
    wrong_public = Ed25519PrivateKey.from_private_bytes(hashlib.sha256(b'PUBLIC wrong benchmark seed').digest()).public_key()
    methods = []
    for method, scope in [('Embedded HMAC', None), ('Whole-image signature', 'whole-image'), ('Signed tile manifest', 'tiles')]:
        t0 = time.perf_counter()
        reference = A.embed(rgb, DEMO_KEY, image_id) if scope is None else rgb.copy()
        sidecar = S.sign(reference, private, image_id, scope) if scope else None
        setup_ms = (time.perf_counter()-t0)*1000
        delta = reference.astype(float)-rgb.astype(float)
        mse = float(np.mean(delta**2))
        result = {'method': method, 'reference_rgb_sha256': hashlib.sha256(reference.tobytes()).hexdigest(),
                  'mse': mse, 'psnr_db': float(10*np.log10(255**2/mse)) if mse else None,
                  'maximum_absolute_channel_change': int(abs(delta).max()),
                  'setup_ms': setup_ms, 'sidecar_bytes': len(sidecar) if sidecar else 0,
                  'reference_png_bytes': len(png_bytes(reference)),
                  'embedded_tag_payload_bits': reference.shape[0]*reference.shape[1]*3 if scope is None else 0,
                  'trust': 'shared secret key plus trusted version ID' if scope is None else 'trusted public key plus trusted version ID and authentic sidecar',
                  'cases': []}
        for ident, label, received, key, expected_id, kind in scenarios(reference, image_id=image_id):
            began = time.perf_counter()
            if scope:
                public = wrong_public if ident == 'wrong-key' else private.public_key()
                check = S.verify(received, sidecar, public, expected_id, scope)
                verdict, failed, reason = check.verdict, check.failed_blocks, check.reason
            else:
                failed = A.failures(received, key, expected_id)
                verdict = 'FAILED_INTEGRITY' if failed.any() else 'VERIFIED'
                reason = 'cannot distinguish pixel alteration from wrong key/context'
            elapsed = (time.perf_counter()-began)*1000
            changed = np.any(received != reference, axis=2)
            loc = None
            if kind == 'content' and failed is not None:
                truth = block_truth(changed)
                expanded = failed.repeat(8, 0).repeat(8, 1)
                loc = {'block_confusion': confusion(failed, truth), 'block_iou': mask_iou(failed, truth),
                       'expanded_block_pixel_iou': mask_iou(expanded, changed)}
            result['cases'].append({'scenario': ident, 'label': label, 'scenario_type': kind,
                                    'verdict': verdict, 'reason': reason,
                                    'changed_pixels': int(changed.sum()), 'verification_ms': elapsed,
                                    'received_rgb_sha256': hashlib.sha256(received.tobytes()).hexdigest(),
                                    'failed_blocks': int(failed.sum()) if failed is not None else None,
                                    'localisation': loc})
        if scope:
            packet = json.loads(sidecar)
            packet['payload']['digests'][0] = '0'*64
            altered = json.dumps(packet).encode()
            for name, evidence in [('missing-evidence', None), ('modified-evidence', altered)]:
                check = S.verify(reference, evidence, private.public_key(), image_id, scope)
                result['cases'].append({'scenario': name, 'scenario_type': 'evidence', 'verdict': check.verdict,
                                        'reason': check.reason, 'changed_pixels': 0, 'failed_blocks': None,
                                        'localisation': None})
        methods.append(result)
    return methods


def render_report(report):
    esc = lambda x: html.escape(str(x))
    sections = []
    for sample in report['samples']:
        rows = []
        for method in sample['methods']:
            rows.append('<tr>' + ''.join('<td>'+esc(v)+'</td>' for v in (
                method['method'], method['mse'], method['maximum_absolute_channel_change'],
                method['sidecar_bytes'], method['reference_png_bytes'], method['embedded_tag_payload_bits'])) + '</tr>')
        cases = []
        for method in sample['methods']:
            for row in method['cases']:
                loc = row.get('localisation')
                pixel_iou = loc['expanded_block_pixel_iou'] if loc else None
                cases.append('<tr>' + ''.join('<td>'+esc(v)+'</td>' for v in (
                    method['method'], row['scenario'], row['verdict'], row['changed_pixels'],
                    row['failed_blocks'] if row['failed_blocks'] is not None else 'not available',
                    round(pixel_iou, 5) if pixel_iou is not None else 'not applicable')) + '</tr>')
        sections.append('<h2>'+esc(sample['id'])+'</h2><div class="scroll"><table><tr><th>Method</th><th>MSE</th><th>Max channel change</th><th>Sidecar bytes</th><th>Reference PNG bytes</th><th>Embedded tag bits</th></tr>' + ''.join(rows) + '</table></div><details><summary>All scenarios, including evidence/context failures</summary><div class="scroll"><table><tr><th>Method</th><th>Scenario</th><th>Verdict</th><th>Changed pixels</th><th>Failed blocks</th><th>Expanded-block pixel IoU</th></tr>'+''.join(cases)+'</table></div></details>')
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Integrity mechanisms: measured trade-offs</title><style>body{max-width:1200px;margin:30px auto;padding:0 20px;font:16px/1.5 system-ui;color:#151515;background:white}h1,h2{font-family:Georgia,serif}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px;text-align:left;border-bottom:1px solid #bbb}details{margin:20px 0}.scroll{overflow-x:auto}header{border-bottom:1px solid #333}strong{color:#921c1c}</style><header><h1>Does watermarking add value over signatures?</h1><p>Measured engineering trade-offs. No method is declared superior by assumption.</p><strong>'+('SYNTHETIC FIXTURES — not ISIC evidence' if report['synthetic'] else 'USER-SUPPLIED IMAGES — dataset/native-original status unverified')+'</strong><p>'+esc(report['scope'])+'</p></header><p>'+esc(report['pairing'])+'</p><p>Whole-image signatures detect pixel changes without a localisation map. Signed tile manifests also localise without altering the image, but require authentic external evidence and a trusted public key. Embedded HMAC changes pixels, carries tags in-image and requires a shared secret. These trust models are not equivalent.</p>'+''.join(sections)+'<h2>Limits</h2><ul>'+''.join('<li>'+esc(x)+'</li>' for x in report['limitations'])+'</ul><p>Deep learning must improve sub-block localisation to justify additional complexity; no such improvement is established here. Reports contain results computed at generation time, not browser-side inference.</p></html>'


def main():
    ap = argparse.ArgumentParser(__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--synthetic', action='store_true')
    mode.add_argument('--image', type=Path, help='authorised RGB input; prepare geometry explicitly')
    mode.add_argument('--data', type=Path, help='convenience subset of local JPG/PNG images, NOT an ISIC study split')
    ap.add_argument('--n', type=int, default=4, help='synthetic fixtures only')
    ap.add_argument('--out', type=Path, required=True, help='new JSON receipt path')
    args = ap.parse_args()
    if args.out.exists() or args.out.with_suffix('.html').exists() or args.out.suffix != '.json' or not 1 <= args.n <= 32:
        ap.error('require a new output path and 1<=n<=32')
    report = {'protocol': 'integrity-tradeoffs-v1', 'source_sha256': source_digest(ROOT),
              'synthetic': args.synthetic, 'usable_as_isic_study': False,
              'environment': {'python': sys.version, 'platform': platform.platform(),
                              'machine': platform.machine(), 'numpy': np.__version__,
                              'Pillow': PIL.__version__, 'cryptography': cryptography.__version__,
                              'command': sys.argv},
              'scope': 'engineering trade-off comparison; not novelty, DICOM conformance or clinical validation',
              'pairing': 'same source/operator/coordinates; method-specific reference and measured truth; masks are NOT assumed identical',
              'key_policy': 'public deterministic benchmark keys; never production secrets',
              'limitations': ['Signed digests authenticate decoded RGB, not image file metadata.',
                              'No PKI, revocation, freshness authority or blockchain integration.',
                              'Tile hashes and signatures are standard baselines, not new cryptography.',
                              'Sidecar bytes are this JSON encoding, not an optimised storage lower bound.',
                              'Key distribution, certificates and trusted version-registry overhead are excluded for all methods.',
                              'No learned localisation, clinical fidelity or population accuracy inferred.',
                              'Replay is possible if the receiver accepts an old image and old signed manifest at a reused version ID.',
                              'Timings are single local CPU executions, not statistically stable benchmarks.'],
              'samples': []}
    paths = sorted(p for p in args.data.rglob('*') if p.suffix.lower() in ('.jpg','.jpeg','.png'))[:args.n] if args.data else ([args.image] if args.image else [])
    if not args.synthetic and not paths:
        ap.error('no image inputs found')
    for i in range(args.n if args.synthetic else len(paths)):
        if args.synthetic:
            from src.fixtures import phantom
            rgb, _ = phantom(seed=i)
            input_hash = None
        else:
            with Image.open(paths[i]) as im:
                if im.mode != 'RGB' or getattr(im, 'n_frames', 1) != 1:
                    ap.error('single-frame 8-bit RGB image required; conversion is not implicit')
                if im.width*im.height > S.MAX_PIXELS:
                    ap.error('prepare an image <=1 megapixel explicitly')
                rgb = np.array(im)
            input_hash = hashlib.sha256(paths[i].read_bytes()).hexdigest()
        if min(rgb.shape[:2]) < 32 or any(n % 8 for n in rgb.shape[:2]):
            ap.error('prepare RGB dimensions >=32 and divisible by 8; no implicit resize')
        report['samples'].append({'id': f'fixture-{i}' if args.synthetic else f'user-supplied-{i}: dataset unverified',
                                  'input_name': None if args.synthetic else paths[i].name,
                                  'input_file_sha256': input_hash,
                                  'input_rgb_sha256': hashlib.sha256(rgb.tobytes()).hexdigest(),
                                  'trusted_image_id': IMAGE_ID+2*i,
                                  'shape': list(rgb.shape), 'methods': experiment(rgb, IMAGE_ID+2*i)})
        atomic_json(args.out, report)
    args.out.with_suffix('.html').write_text(render_report(report))
    print('Saved:', args.out, 'and', args.out.with_suffix('.html'))
    print('Non-embedding signatures are alternatives, not inferior baselines by assumption.')


if __name__ == '__main__':
    main()
