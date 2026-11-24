"""Compact detached Ed25519/SHA256 tile baseline; standard primitives, no novelty.

Wire format: fixed26-byte header, row-major32-byte digests,64-byte signature.
Trusted public key and expected version supplied externally. Hashes bind geometry,
version, grid and coordinates. No original pixels required for verification.
Not a DICOM signature, freshness service or clinical security certification.
"""
import hashlib
import struct
import hmac
import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from .signed_manifest import Verification

HEADER=struct.Struct('>8sBQIIB')
MAGIC=b'RGBGRID\0'
DOMAIN=b'MajorProject/binary-signed-grid/v1\0'
MAX_PIXELS=1024**2
MAX_BYTES=HEADER.size+(MAX_PIXELS//16)*32+64


def image(rgb,ident,block):
    x=np.asarray(rgb)
    if type(block) is not int or block not in (4,8,16,32):raise ValueError('expected block4/8/16/32')
    if type(ident) is not int or not 0<=ident<2**64:raise ValueError('expected uint64 version')
    if x.dtype!=np.uint8 or x.ndim!=3 or x.shape[2]!=3 or min(x.shape[:2])<block or any(n%block for n in x.shape[:2]) or x.shape[0]*x.shape[1]>MAX_PIXELS:
        raise ValueError('aligned uint8 RGB <=1megapixel required')
    return x


def digests(x,header,block):
    h,w=x.shape[:2]
    return b''.join(hashlib.sha256(DOMAIN+header+struct.pack('>II',r,c)+
                    x[r:r+block,c:c+block].tobytes()).digest()
                    for r in range(0,h,block) for c in range(0,w,block))


def sign(rgb,private_key,image_id,block=4):
    x=image(rgb,image_id,block)
    if not isinstance(private_key,Ed25519PrivateKey):raise ValueError('Ed25519 private key required')
    header=HEADER.pack(MAGIC,1,image_id,*x.shape[:2],block)
    payload=header+digests(x,header,block)
    return payload+private_key.sign(DOMAIN+payload)


def verify(rgb,evidence,trusted_public_key,expected_image_id,block=4):
    x=image(rgb,expected_image_id,block)
    cannot=lambda reason:Verification('CANNOT_AUTHENTICATE',reason)
    if not isinstance(trusted_public_key,Ed25519PublicKey):return cannot('trusted_public_key_missing')
    if not isinstance(evidence,bytes) or not HEADER.size+64<=len(evidence)<=MAX_BYTES:return cannot('missing_or_oversized_evidence')
    try:
        magic,version,ident,h,w,stored_block=HEADER.unpack(evidence[:HEADER.size])
        if magic!=MAGIC or version!=1 or stored_block not in (4,8,16,32):return cannot('unsupported_format')
        if not 0<h*w<=MAX_PIXELS or min(h,w)<stored_block or h%stored_block or w%stored_block:return cannot('invalid_geometry')
        expected=HEADER.size+(h//stored_block)*(w//stored_block)*32+64
        if len(evidence)!=expected:return cannot('invalid_length')
        trusted_public_key.verify(evidence[-64:],DOMAIN+evidence[:-64])
    except (InvalidSignature,ValueError,struct.error):return cannot('invalid_signature_or_format')
    if ident!=expected_image_id:return cannot('identifier_mismatch')
    if (h,w)!=x.shape[:2] or stored_block!=block:return cannot('geometry_or_grid_mismatch')
    received=digests(x,evidence[:HEADER.size],block)
    original=evidence[HEADER.size:-64]
    mismatch=np.array([not hmac.compare_digest(original[i:i+32],received[i:i+32]) for i in range(0,len(original),32)],dtype=bool)
    mask=mismatch.reshape(h//block,w//block)
    return Verification('FAILED_INTEGRITY' if mask.any() else 'VERIFIED',
                        'received_pixels_differ' if mask.any() else 'signed_pixels_match',mask)
