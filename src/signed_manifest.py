"""Non-embedding Ed25519 baselines over decoded RGB pixels, NOT DICOM profiles.

The receiver supplies a trusted public key and expected image/version identifier.
A self-supplied public key in an untrusted sidecar is never accepted. Unknown or
invalid evidence yields CANNOT_AUTHENTICATE without a localisation map. Signatures
are checked before any signed digest is used to classify received pixels.

This is a research baseline, not a new signature construction or a security audit.
Freshness, revocation, key custody and patient metadata are outside its scope.
"""
import hashlib
import json
import re
import struct
from dataclasses import dataclass

import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

SCHEME = 'rgb-ed25519-manifest-v1'
DOMAIN = b'MajorProject/signed-rgb-manifest/v1\0'
MAX_PIXELS = 1024**2
MAX_EVIDENCE_BYTES = 2**21


@dataclass(frozen=True)
class Verification:
    verdict: str
    reason: str
    failed_blocks: object = None


def _image(rgb, image_id):
    x = np.asarray(rgb)
    if x.dtype != np.uint8 or x.ndim != 3 or x.shape[2] != 3:
        raise ValueError('8-bit HxWx3 RGB required')
    if min(x.shape[:2]) < 8 or any(d % 8 for d in x.shape[:2]) or x.shape[0]*x.shape[1] > MAX_PIXELS:
        raise ValueError('dimensions must be multiples of 8 and <=1 megapixel')
    if type(image_id) is not int or not 0 <= image_id < 2**64:
        raise ValueError('expected unsigned 64-bit image/version identifier required')
    return x


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def _digests(x, image_id, scope):
    h, w = x.shape[:2]
    context = DOMAIN + scope.encode('ascii') + struct.pack('>QII', image_id, h, w)
    if scope == 'whole-image':
        return [hashlib.sha256(context+x.tobytes(order='C')).hexdigest()]
    return [hashlib.sha256(context+struct.pack('>II', r, c)+x[r*8:(r+1)*8, c*8:(c+1)*8].tobytes(order='C')).hexdigest()
            for r in range(h//8) for c in range(w//8)]


def sign(rgb, private_key, image_id, scope='tiles'):
    x = _image(rgb, image_id)
    if not isinstance(private_key, Ed25519PrivateKey) or scope not in ('tiles', 'whole-image'):
        raise ValueError('Ed25519 signing key and supported scope required')
    payload = {'scheme': SCHEME, 'scope': scope, 'image_id': image_id,
               'shape': list(x.shape), 'block': 8, 'digests': _digests(x, image_id, scope)}
    signature = private_key.sign(DOMAIN+_canonical(payload)).hex()
    return _canonical({'payload': payload, 'signature': signature})


def _no_duplicates(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('duplicate JSON key')
        result[k] = v
    return result


def verify(rgb, evidence, trusted_public_key, expected_image_id, scope='tiles'):
    x = _image(rgb, expected_image_id)
    if scope not in ('tiles', 'whole-image'):
        raise ValueError('supported expected scope required')
    cannot = lambda reason: Verification('CANNOT_AUTHENTICATE', reason)
    if not isinstance(trusted_public_key, Ed25519PublicKey):
        return cannot('trusted_public_key_missing')
    if not isinstance(evidence, bytes) or not evidence or len(evidence) > MAX_EVIDENCE_BYTES:
        return cannot('missing_or_oversized_evidence')
    try:
        envelope = json.loads(evidence, object_pairs_hook=_no_duplicates)
        if not isinstance(envelope, dict) or set(envelope) != {'payload', 'signature'}:
            return cannot('malformed_envelope')
        p, signature = envelope['payload'], envelope['signature']
        if not isinstance(signature, str) or re.fullmatch('[0-9a-f]{128}', signature) is None:
            return cannot('malformed_signature')
        if not isinstance(p, dict) or set(p) != {'scheme', 'scope', 'image_id', 'shape', 'block', 'digests'}:
            return cannot('malformed_payload')
        if p['scheme'] != SCHEME or p['scope'] != scope or type(p['block']) is not int or p['block'] != 8:
            return cannot('unsupported_scheme_or_scope')
        if type(p['image_id']) is not int or p['image_id'] != expected_image_id:
            return cannot('identifier_mismatch')
        if not isinstance(p['shape'], list) or any(type(n) is not int for n in p['shape']) or p['shape'] != list(x.shape):
            return cannot('geometry_mismatch')
        n = 1 if scope == 'whole-image' else (x.shape[0]//8)*(x.shape[1]//8)
        digests = p['digests']
        if not isinstance(digests, list) or len(digests) != n or any(not isinstance(d, str) or re.fullmatch('[0-9a-f]{64}', d) is None for d in digests):
            return cannot('malformed_digest_list')
        trusted_public_key.verify(bytes.fromhex(signature), DOMAIN+_canonical(p))
    except InvalidSignature:
        return cannot('invalid_signature_or_untrusted_key')
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return cannot('malformed_evidence')
    changed = np.array([a != b for a, b in zip(digests, _digests(x, expected_image_id, scope))])
    failed = changed.reshape(x.shape[0]//8, x.shape[1]//8) if scope == 'tiles' else None
    return Verification('FAILED_INTEGRITY' if changed.any() else 'VERIFIED',
                        'received_pixels_differ' if changed.any() else 'signed_pixels_match', failed)
