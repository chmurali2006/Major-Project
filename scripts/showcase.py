"""Generate a self-contained, CPU-only demonstration of current RGB verification.

Outputs contain pixels. They MUST be written outside the Git workspace.
Example: python scripts/showcase.py --synthetic --out /tmp/keyswm-showcase
Real input: --image /outside/repo/ISIC.jpg --resize 512 (explicit preprocessing).
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image
from src.persistence import source_digest
from src.showcase import build_report, render_html
from src.security_showcase import build_security_report, render_security_html


def main():
    ap = argparse.ArgumentParser(__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--synthetic', action='store_true', help='labelled fixture, never ISIC evidence')
    mode.add_argument('--image', type=Path, help='authorised, de-identified 8-bit RGB image outside the repo')
    ap.add_argument('--resize', type=int, help='explicit square resize before embedding; e.g. 512')
    ap.add_argument('--out', type=Path, required=True, help='new directory OUTSIDE the repository')
    args = ap.parse_args()
    out = args.out.resolve()
    if out == ROOT or ROOT in out.parents:
        ap.error('outputs contain pixels: choose a directory outside the repository')
    if out.exists():
        ap.error('use a new output directory; existing evidence is not overwritten')
    if args.resize is not None and (args.resize < 32 or args.resize > 1024 or args.resize % 8):
        ap.error('--resize must be a multiple of 8 between 32 and 1024')
    if args.synthetic and args.resize is not None:
        ap.error('--resize applies only to real inputs')
    preprocessing = 'none'
    source_sha = None
    if args.synthetic:
        from src.fixtures import phantom
        rgb, _ = phantom(seed=7)
        label = 'Procedural fixture, seed 7. Not a medical acquisition.'
        input_shape = list(rgb.shape)
    else:
        source_sha = hashlib.sha256(args.image.read_bytes()).hexdigest()
        with Image.open(args.image) as im:
            if im.mode != 'RGB':
                ap.error('provide an 8-bit RGB image; grayscale/16-bit/palette conversion is not implicit')
            if getattr(im, 'n_frames', 1) != 1:
                ap.error('provide a single-frame image')
            input_shape = [im.height, im.width, 3]
            if args.resize is not None:
                im = im.resize((args.resize, args.resize), Image.Resampling.BICUBIC)
                preprocessing = f'explicit bicubic square resize to {args.resize}; may distort aspect ratio'
            if im.width * im.height > 1024**2:
                ap.error('use an explicitly prepared image <=1 megapixel or --resize 512')
            if min(im.size) < 32 or any(n % 8 for n in im.size):
                ap.error('dimensions must be >=32 and divisible by 8; prepare input explicitly or use --resize 512')
            rgb = np.array(im)
        label = 'User-supplied RGB image; no dataset membership or clinical claim.'
    report, protected, views, original_uri, protected_uri = build_report(rgb, label, args.synthetic)
    report.update({'source_sha256': source_digest(ROOT), 'input_file_sha256': source_sha,
                   'input_shape_before_preprocessing': input_shape, 'preprocessing': preprocessing})
    security, security_views = build_security_report(rgb)
    security.update({'source_sha256': source_digest(ROOT), 'synthetic': args.synthetic,
                     'input_file_sha256': source_sha, 'preprocessing': preprocessing})
    if not security['all_checks_passed']:
        raise RuntimeError('Security scenario regression failed; refusing successful showcase export')
    page = render_html(report, views, original_uri, protected_uri)
    page = page.replace('</header>', '<p><a href="security.html">Inspect signed-evidence failures and replay limitations</a></p></header>', 1)
    out.mkdir(parents=True)
    (out/'protected.png').write_bytes(protected)
    (out/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    (out/'index.html').write_text(page)
    (out/'security-report.json').write_text(json.dumps(security, indent=2, allow_nan=False)+'\n')
    (out/'security.html').write_text(render_security_html(security, security_views))
    print('Open:', out/'index.html')
    print('Scope:', report['scope'])
    print('Synthetic:', report['synthetic'])
    print('Lossless storage required; no learned model is used.')


if __name__ == '__main__':
    main()
