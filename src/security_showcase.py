"""Executable signed-evidence failure demonstration; no dataset or clinical claim."""
import hashlib
import html
import json
import time
import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from . import signed_manifest as S
from .showcase import data_uri, overlay, scenarios


def build_security_report(rgb):
    key = Ed25519PrivateKey.generate()
    public = key.public_key()
    evidence = S.sign(rgb, key, 4242)
    other = rgb.copy()
    other[0, 0, 0] ^= np.uint8(1)
    swapped = S.sign(other, key, 4243)
    same_id = S.sign(other, key, 4242)
    altered = json.loads(evidence)
    altered['payload']['digests'][0] = '0'*64
    cases = [(name, image, evidence, public, 4242,
              'FAILED_INTEGRITY' if np.any(image != rgb) else 'VERIFIED')
             for name, _, image, _, _, kind in scenarios(rgb) if kind == 'content']
    cases += [
        ('missing-evidence', rgb, None, public, 4242, 'CANNOT_AUTHENTICATE'),
        ('altered-evidence', rgb, json.dumps(altered).encode(), public, 4242, 'CANNOT_AUTHENTICATE'),
        ('wrong-key', rgb, evidence, Ed25519PrivateKey.generate().public_key(), 4242, 'CANNOT_AUTHENTICATE'),
        ('missing-trusted-key', rgb, evidence, None, 4242, 'CANNOT_AUTHENTICATE'),
        ('swapped-evidence', rgb, swapped, public, 4242, 'CANNOT_AUTHENTICATE'),
        ('swapped-content-same-id', rgb, same_id, public, 4242, 'FAILED_INTEGRITY'),
        ('old-pair-new-expected-version', rgb, evidence, public, 4243, 'CANNOT_AUTHENTICATE'),
        ('old-pair-old-expected-version', rgb, evidence, public, 4242, 'VERIFIED'),
    ]
    rows, views = [], []
    for name, image, packet, trusted, ident, expected in cases:
        started = time.perf_counter()
        result = S.verify(image, packet, trusted, ident)
        elapsed = time.perf_counter()-started
        mask = result.failed_blocks
        changed = np.any(image != rgb, axis=2)
        passed = result.verdict == expected and (result.verdict != 'CANNOT_AUTHENTICATE' or mask is None)
        rows.append({'case': name, 'expected': expected, 'verdict': result.verdict,
                     'reason': result.reason, 'check_passed': passed,
                     'failed_blocks': int(mask.sum()) if mask is not None else None,
                     'changed_pixels': int(changed.sum()), 'verification_ms': elapsed*1000})
        views.append({'received': data_uri(image), 'overlay': data_uri(overlay(image, mask.repeat(8, 0).repeat(8, 1))) if mask is not None else None})
    return {'schema': 'signed-evidence-showcase-v1', 'all_checks_passed': all(r['check_passed'] for r in rows),
            'scope': 'Controlled single-input security regression, not a cryptographic security proof',
            'evidence_bytes': len(evidence), 'input_rgb_sha256': hashlib.sha256(rgb.tobytes()).hexdigest(),
            'limitations': ['Public key and expected version must come from a trusted external source.',
                           'An old valid image/evidence pair verifies if its old version remains accepted.',
                           'Sidecar contains per-tile hashes; storage, key custody and transport are deployment costs.',
                           'No embedding: received pixels are unchanged by signing. No clinical safety claim.',
                           'FAILED_INTEGRITY means valid evidence but different pixels; CANNOT_AUTHENTICATE has no localisation map.'],
            'cases': rows}, views


def render_security_html(report, views):
    scope = 'SYNTHETIC FIXTURE — not medical evidence' if report.get('synthetic', True) else 'USER-SUPPLIED IMAGE — provenance unverified'
    notes = ''.join('<li>'+html.escape(x)+'</li>' for x in report['limitations'])
    cards = []
    for row, view in zip(report['cases'], views):
        picture = ('<img alt="Failed 8 by 8 blocks, not pixel segmentation" src="'+view['overlay']+'">') if view['overlay'] else '<p>No localisation map: evidence was not accepted.</p>'
        cards.append('<article><h2>'+html.escape(row['case'])+'</h2><strong>'+row['verdict']+'</strong><p>'+html.escape(row['reason'])+'</p>'+picture+'<p>Changed pixels: '+str(row['changed_pixels'])+' · Failed blocks: '+str(row['failed_blocks'])+' · '+format(row['verification_ms'], '.3f')+' ms</p></article>')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Evidence failure checks</title><style>body{max-width:1100px;margin:32px auto;padding:24px;font:16px/1.5 system-ui;color:#171717}h1,h2{font-family:Georgia,serif}a{color:#8d1717}article{border-top:1px solid #aaa;padding:16px 0}img{max-width:260px;width:100%}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px}strong{color:#8d1717}</style><h1>Trusted evidence and replay checks</h1><p><strong>'''+scope+'''</strong></p><p><a href="index.html">Classical watermark demonstration</a> · <a href="security-report.json">Numerical receipt</a></p><p>Separate non-embedding Ed25519 signed-grid control. These are not the classical HMAC watermark verdicts. Red marks failed8×8 blocks, never estimated sub-block segmentation.</p><p>Evidence size: '''+str(report['evidence_bytes'])+''' bytes. Timing: one local call per case, not a latency benchmark.</p><ul>'''+notes+'</ul><div class="grid">'+''.join(cards)+'</div></html>'
