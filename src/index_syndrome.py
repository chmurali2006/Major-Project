"""Fixed-index XOR/finite-field syndrome probe; established coding ingredients.

WARNING: targeted2-tile stopping sets found at112/448buckets.
Ordinary-case capacity gains do not imply adversarial localisation availability.

Each bucket stores XOR leaf digests and index-weighted XOR digests (64bytes).
Completeness requires reconstruction of signed full leaf root. Not a security
proof, novel code claim, adaptive-adversary guarantee or freshness mechanism.
"""
import hashlib
import struct
import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from .binary_signed_grid import image
from .sparse_refinement import leaves,root
from .signed_manifest import Verification

HEADER=struct.Struct('>8sQIIHI');MAGIC=b'IDXGF16\0';DOMAIN=b'MajorProject/index-syndrome/v1\0'
MAX_BUCKETS=16384
EXP=np.zeros(131070,dtype=np.uint16);LOG=np.zeros(65536,dtype=np.int32)
x=1
for i in range(65535):
    EXP[i]=x;LOG[x]=i;x<<=1
    if x&65536:x^=0x1100b
EXP[65535:]=EXP[:65535]


def mul(a,b):
    a,b=np.broadcast_arrays(np.asarray(a,dtype=np.uint16),np.asarray(b,dtype=np.uint16))
    return np.where((a==0)|(b==0),0,EXP[LOG[a]+LOG[b]]).astype(np.uint16)


def addresses(index,m):
    d=hashlib.sha256(DOMAIN+struct.pack('>I',index)).digest();result=[]
    for j in range(3):
        v=int.from_bytes(d[j*8:j*8+8],'big')%m
        while v in result:v=(v+1)%m
        result.append(v)
    return result


def table(hashes,m):
    values=np.frombuffer(b''.join(hashes),dtype='>u2').astype(np.uint16).reshape(-1,16)
    weights=mul(values,np.arange(1,len(hashes)+1,dtype=np.uint16)[:,None])
    indices=np.array([addresses(i,m) for i in range(len(hashes))])
    out=np.zeros((m,32),np.uint16)
    for j in range(3):
        np.bitwise_xor.at(out[:,:16],indices[:,j],values)
        np.bitwise_xor.at(out[:,16:],indices[:,j],weights)
    return out


def sign(rgb,key,ident,buckets=448,block=4):
    x=image(rgb,ident,block)
    if type(buckets) is not int or not 3<=buckets<=MAX_BUCKETS:raise ValueError('invalid bucket budget')
    if (x.shape[0]//block)*(x.shape[1]//block)>65535:raise ValueError('GF16 supports at most65535tiles')
    if not isinstance(key,Ed25519PrivateKey):raise ValueError('Ed25519 key required')
    hashes=leaves(x,ident,block)
    payload=HEADER.pack(MAGIC,ident,*x.shape[:2],block,buckets)+root(hashes)+table(hashes,buckets).astype('>u2').tobytes()
    return payload+key.sign(DOMAIN+payload)


def verify(rgb,packet,key,ident,block=4):
    x=image(rgb,ident,block);n=(x.shape[0]//block)*(x.shape[1]//block)
    no=lambda reason:Verification('CANNOT_AUTHENTICATE',reason)
    fail=lambda:Verification('FAILED_INTEGRITY','fine_localisation_unavailable')
    if n>65535:raise ValueError('GF16 supports at most65535tiles')
    if not isinstance(key,Ed25519PublicKey) or not isinstance(packet,bytes):return no('trusted_evidence_missing')
    if not HEADER.size+96<=len(packet)<=HEADER.size+96+64*MAX_BUCKETS:return no('invalid_size')
    try:
        magic,i,h,w,b,m=HEADER.unpack(packet[:HEADER.size])
        if magic!=MAGIC or not 3<=m<=MAX_BUCKETS or len(packet)!=HEADER.size+96+64*m:return no('invalid_header')
        key.verify(packet[-64:],DOMAIN+packet[:-64])
    except (ValueError,InvalidSignature,struct.error):return no('invalid_signature')
    if (i,h,w,b)!=(ident,*x.shape[:2],block):return no('context_mismatch')
    hashes=leaves(x,ident,block);commitment=packet[HEADER.size:HEADER.size+32]
    if root(hashes)==commitment:return Verification('VERIFIED','signed_root_matches',np.zeros((h//b,w//b),bool))
    t=np.frombuffer(packet[HEADER.size+32:-64],dtype='>u2').astype(np.uint16).reshape(m,32)^table(hashes,m)
    queue=list(range(m));decoded={}
    while queue:
        bucket=queue.pop();values=t[bucket,:16].copy();weighted=t[bucket,16:]
        nz=np.flatnonzero(values)
        if not len(nz):continue
        j=int(nz[0]);a=int(values[j]);v=int(weighted[j])
        if not v:continue
        factor=int(EXP[(int(LOG[v])-int(LOG[a]))%65535]);index=factor-1
        if not 0<=index<n or bucket not in addresses(index,m):continue
        expected=mul(values,factor)
        if not np.array_equal(expected,weighted):continue
        if index in decoded:return fail()
        decoded[index]=values
        for target in addresses(index,m):
            t[target,:16]^=values;t[target,16:]^=expected;queue.append(target)
        if len(decoded)>n:return fail()
    if t.any() or not decoded:return fail()
    reconstructed=list(hashes)
    for index,delta in decoded.items():
        received=np.frombuffer(hashes[index],dtype='>u2').astype(np.uint16)
        reconstructed[index]=(received^delta).astype('>u2').tobytes()
    if root(reconstructed)!=commitment:return fail()
    mask=np.zeros(n,bool);mask[list(decoded)]=True
    return Verification('FAILED_INTEGRITY','fine_map_commitment_checked',mask.reshape(h//b,w//b))
