"""Standard composite control: signed coarse grid plus signed sparse refinement.

Outer signature binds both components to prevent mixing same-ID evidence pairs.
No novelty claim. All signatures/headers count toward evidence size. Never treats
missing/invalid fine evidence as benign decoder exhaustion.
"""
from dataclasses import dataclass
import struct
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from . import binary_signed_grid as B
from . import sparse_refinement as S

HEADER=struct.Struct('>8sII')
MAGIC=b'FALLBK1\0'
DOMAIN=b'MajorProject/coarse-fallback-control/v1\0'
MAX_BYTES=B.MAX_BYTES+S.HEADER.size+96+S.MAX_BUCKETS*S.RECORD.size+80


@dataclass(frozen=True)
class Result:
    verdict:str
    reason:str
    failed_blocks:object=None
    resolution:object=None


def sign(rgb,key,ident,buckets=512,coarse=16):
    if coarse not in (16,32):raise ValueError('coarse16 or32 required')
    a=B.sign(rgb,key,ident,coarse);b=S.sign(rgb,key,ident,buckets,4)
    payload=HEADER.pack(MAGIC,len(a),len(b))+a+b
    return payload+key.sign(DOMAIN+payload)


def verify(rgb,packet,key,ident,coarse=16):
    no=lambda reason:Result('CANNOT_AUTHENTICATE',reason)
    if not isinstance(key,Ed25519PublicKey) or not isinstance(packet,bytes):return no('trusted_evidence_missing')
    if not HEADER.size+64<=len(packet)<=MAX_BYTES:return no('invalid_length')
    try:
        magic,na,nb=HEADER.unpack(packet[:HEADER.size])
        if magic!=MAGIC or HEADER.size+na+nb+64!=len(packet):return no('invalid_envelope')
        key.verify(packet[-64:],DOMAIN+packet[:-64])
    except (ValueError,InvalidSignature,struct.error):return no('invalid_outer_signature')
    a=packet[HEADER.size:HEADER.size+na];b=packet[HEADER.size+na:-64]
    rough=B.verify(rgb,a,key,ident,coarse);fine=S.verify(rgb,b,key,ident,4)
    if rough.verdict=='CANNOT_AUTHENTICATE' or fine.verdict=='CANNOT_AUTHENTICATE':return no('invalid_component')
    if rough.verdict!=fine.verdict:return no('inconsistent_components')
    if fine.failed_blocks is not None:return Result(fine.verdict,'fine_commitment_checked',fine.failed_blocks,4)
    return Result(rough.verdict,'coarse_fallback',rough.failed_blocks,coarse)
