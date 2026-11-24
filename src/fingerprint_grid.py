"""Signed truncated-fingerprint control, NOT certified-complete localisation.

Full SHA256 ordered-leaf commitment controls integrity. Truncated per-tile hashes
only estimate changed tiles; adversaries can search collisions in short hashes.
No independent randomness/collision probability guarantee for adaptive attacks.
This control must not be labelled equivalent to root-checked reconciliation.
"""
from dataclasses import dataclass
import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from .binary_signed_grid import image
from .sparse_refinement import leaves,root
import struct

HEADER=struct.Struct('>8sQIIHB')
DOMAIN=b'MajorProject/fingerprint-control/v1\0'
MAGIC=b'FPGRID1\0'


@dataclass(frozen=True)
class Result:
    verdict:str
    reason:str
    estimated_blocks:object=None
    localisation_certified_complete:bool=False


def sign(rgb,key,ident,fingerprint_bytes=8,block=4):
    x=image(rgb,ident,block)
    if fingerprint_bytes not in (1,4,8,16,32):raise ValueError('fingerprint bytes1/4/8/16/32')
    if not isinstance(key,Ed25519PrivateKey):raise ValueError('Ed25519 private key required')
    hashes=leaves(x,ident,block)
    payload=HEADER.pack(MAGIC,ident,*x.shape[:2],block,fingerprint_bytes)+root(hashes)+b''.join(h[:fingerprint_bytes] for h in hashes)
    return payload+key.sign(DOMAIN+payload)


def verify(rgb,evidence,key,ident,fingerprint_bytes=8,block=4):
    x=image(rgb,ident,block)
    no=lambda reason:Result('CANNOT_AUTHENTICATE',reason)
    if not isinstance(key,Ed25519PublicKey) or not isinstance(evidence,bytes):return no('missing_trusted_evidence')
    n=(x.shape[0]//block)*(x.shape[1]//block)
    if fingerprint_bytes not in (1,4,8,16,32):raise ValueError('unsupported fingerprint length')
    if len(evidence)!=HEADER.size+96+n*fingerprint_bytes:return no('invalid_length')
    try:
        magic,i,h,w,b,f=HEADER.unpack(evidence[:HEADER.size])
        key.verify(evidence[-64:],DOMAIN+evidence[:-64])
    except (ValueError,InvalidSignature,struct.error):return no('invalid_signature_or_format')
    if (magic,i,h,w,b,f)!=(MAGIC,ident,*x.shape[:2],block,fingerprint_bytes):return no('context_mismatch')
    hashes=leaves(x,ident,block);commitment=evidence[HEADER.size:HEADER.size+32]
    if root(hashes)==commitment:
        return Result('VERIFIED','signed_root_matches',np.zeros((h//b,w//b),bool),True)
    fingerprints=evidence[HEADER.size+32:-64]
    mask=np.array([digest[:f]!=fingerprints[j*f:(j+1)*f] for j,digest in enumerate(hashes)],bool)
    return Result('FAILED_INTEGRITY','fingerprint_map_not_certified_complete',mask.reshape(h//b,w//b),False)
