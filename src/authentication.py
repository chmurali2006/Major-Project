"""Versioned, block-local RGB authentication carried in RGB least-significant bits.

Each 8x8 RGB block carries a 192-bit truncated HMAC-SHA256. The message binds
all 7 upper bits of every sample, image geometry, trusted image identifier and
block coordinates. ALL 192 low bits are the tag, so editing a payload bit is
also checked. No quantised content is excluded other than the tag itself.

Lossless storage is required. A verification failure means failed integrity,
not proof of malicious intent. Keys must be secret outside public benchmarks.
An old valid block at the same address/id can be replayed: freshness requires
an externally trusted unique image/version identifier; it is not supplied here.
This construction is not a clinical validation or a formal security audit.
"""
import hashlib
import hmac
import struct
import numpy as np

SCHEME = 'rgb-lsb-hmac-sha256-192-v1'
DOMAIN = b'MajorProject/RGB-block-authentication/v1\x00'
BLOCK = 8
TAG_BYTES = 24


def _validate(rgb, key, image_id):
    x = np.asarray(rgb)
    if x.dtype != np.uint8 or x.ndim != 3 or x.shape[2] != 3:
        raise ValueError('authentication requires HxWx3 uint8 RGB')
    if min(x.shape[:2]) < BLOCK or any(d % BLOCK for d in x.shape[:2]):
        raise ValueError('authentication geometry must be positive multiples of 8')
    if not isinstance(key, bytes) or not key:
        raise ValueError('nonempty bytes key required')
    if isinstance(image_id, (bool, np.bool_)) or not isinstance(image_id, (int, np.integer)) or not 0 <= int(image_id) < 2**64:
        raise ValueError('trusted image/version identifier must be an unsigned 64-bit integer')
    return x


def _tag(canonical_block, key, context, row, col):
    message = DOMAIN + context + struct.pack('>II', row, col) + canonical_block.tobytes(order='C')
    return hmac.new(key, message, hashlib.sha256).digest()[:TAG_BYTES]


def embed(rgb, key, image_id):
    x = _validate(rgb, key, image_id)
    out = x.copy()
    h, w = x.shape[:2]
    context = struct.pack('>QII', int(image_id), h, w)
    for row in range(h//BLOCK):
        for col in range(w//BLOCK):
            tile = x[row*8:(row+1)*8,col*8:(col+1)*8]
            canonical = tile & np.uint8(254)
            bits = np.unpackbits(np.frombuffer(_tag(canonical,key,context,row,col),np.uint8))
            out[row*8:(row+1)*8,col*8:(col+1)*8] = canonical | bits.reshape(8,8,3)
    return out


def failures(rgb, key, image_id):
    """True iff the received block's full tag does not verify. No learned rule."""
    x = _validate(rgb, key, image_id)
    h,w = x.shape[:2]
    context = struct.pack('>QII', int(image_id), h, w)
    failed = np.zeros((h//8,w//8),bool)
    for row in range(h//8):
        for col in range(w//8):
            tile = x[row*8:(row+1)*8,col*8:(col+1)*8]
            expected = _tag(tile & np.uint8(254),key,context,row,col)
            received = np.packbits((tile & np.uint8(1)).ravel()).tobytes()
            failed[row,col] = not hmac.compare_digest(expected,received)
    return failed


def verify(rgb, key, image_id):
    """Strict whole-image integrity; models/count thresholds cannot override it."""
    return not bool(failures(rgb,key,image_id).any())
