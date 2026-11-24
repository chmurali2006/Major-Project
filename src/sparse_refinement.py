"""Experimental signed IBLT-style tile reconciliation; NOT novel cryptography.

Signed root commits to the complete ordered leaf vector. Successful peeling alone
is insufficient: reconstructed original leaves MUST match that root before any
fine map is exposed. Failed decoding returns no fine map. Research prototype;
assumes SHA256/Ed25519 security, trusted external version/key, no freshness service.
"""
import hashlib
import struct
import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from .signed_manifest import Verification
from .binary_signed_grid import image

DOMAIN=b'MajorProject/sparse-grid-probe/v1\0'
HEADER=struct.Struct('>8sQIIHI')
MAGIC=b'SKETCH1\0'
RECORD=struct.Struct('>i36s16s')
MAX_BUCKETS=16384


def leaves(x,ident,block):
    h,w=x.shape[:2];context=DOMAIN+struct.pack('>QIIH',ident,h,w,block)
    return [hashlib.sha256(context+struct.pack('>I',i)+x[r:r+block,c:c+block].tobytes()).digest()
            for i,(r,c) in enumerate((r,c) for r in range(0,h,block) for c in range(0,w,block))]


def check(token):return hashlib.sha256(DOMAIN+b'check'+token).digest()[:16]


def addresses(token,m):
    digest=hashlib.sha256(DOMAIN+b'buckets'+token).digest()
    indices=[]
    for j in range(3):
        v=int.from_bytes(digest[j*8:j*8+8],'big')%m
        while v in indices:v=(v+1)%m
        indices.append(v)
    return indices


def update(table,token,sign):
    value=int.from_bytes(token,'big');checksum=int.from_bytes(check(token),'big')
    for j in addresses(token,len(table)):
        table[j][0]+=sign;table[j][1]^=value;table[j][2]^=checksum


def build_table(hashes,m):
    t=[[0,0,0] for _ in range(m)]
    for i,d in enumerate(hashes):update(t,struct.pack('>I',i)+d,1)
    return t


def root(hashes):return hashlib.sha256(DOMAIN+b'ordered-root'+b''.join(hashes)).digest()


def sign(rgb,key,ident,buckets=1024,block=4):
    x=image(rgb,ident,block)
    if type(buckets) is not int or not 3<=buckets<=MAX_BUCKETS:raise ValueError('bucket budget3..16384')
    if not isinstance(key,Ed25519PrivateKey):raise ValueError('Ed25519 private key required')
    hashes=leaves(x,ident,block);table=build_table(hashes,buckets)
    payload=HEADER.pack(MAGIC,ident,*x.shape[:2],block,buckets)+root(hashes)
    payload+=b''.join(RECORD.pack(c,v.to_bytes(36,'big'),s.to_bytes(16,'big')) for c,v,s in table)
    return payload+key.sign(DOMAIN+payload)


def verify(rgb,evidence,key,ident,block=4):
    x=image(rgb,ident,block)
    no=lambda reason:Verification('CANNOT_AUTHENTICATE',reason)
    failed=lambda reason:Verification('FAILED_INTEGRITY',reason)
    if not isinstance(key,Ed25519PublicKey):return no('trusted_key_missing')
    if not isinstance(evidence,bytes) or not HEADER.size+96<=len(evidence)<=HEADER.size+96+MAX_BUCKETS*RECORD.size:return no('invalid_evidence_size')
    try:
        magic,version,h,w,b,m=HEADER.unpack(evidence[:HEADER.size])
        if magic!=MAGIC or not 3<=m<=MAX_BUCKETS or len(evidence)!=HEADER.size+96+m*RECORD.size:return no('invalid_header')
        key.verify(evidence[-64:],DOMAIN+evidence[:-64])
    except (InvalidSignature,ValueError,struct.error):return no('invalid_signature_or_format')
    if version!=ident or (h,w)!=x.shape[:2] or b!=block:return no('context_mismatch')
    hashes=leaves(x,ident,block);commitment=evidence[HEADER.size:HEADER.size+32]
    if root(hashes)==commitment:return Verification('VERIFIED','signed_root_matches',np.zeros((h//b,w//b),bool))
    table=[];offset=HEADER.size+32
    for i in range(m):
        c,v,s=RECORD.unpack_from(evidence,offset+i*RECORD.size)
        table.append([c,int.from_bytes(v,'big'),int.from_bytes(s,'big')])
    received=build_table(hashes,m)
    for a,z in zip(table,received):a[0]-=z[0];a[1]^=z[1];a[2]^=z[2]
    queue=list(range(m));decoded=[];limit=2*len(hashes)
    while queue:
        j=queue.pop();c,v,s=table[j]
        if abs(c)!=1:continue
        token=v.to_bytes(36,'big')
        if int.from_bytes(check(token),'big')!=s:continue
        if j not in addresses(token,m):return failed('fine_localisation_unavailable')
        decoded.append((c,token))
        if len(decoded)>limit:return failed('fine_localisation_unavailable')
        update(table,token,-c);queue.extend(addresses(token,m))
    if any(any(row) for row in table):return failed('fine_localisation_unavailable')
    old={};new={}
    for direction,token in decoded:
        index=int.from_bytes(token[:4],'big');target=old if direction==1 else new
        if index>=len(hashes) or index in target:return failed('fine_localisation_unavailable')
        target[index]=token[4:]
    if not old or old.keys()!=new.keys():return failed('fine_localisation_unavailable')
    reconstructed=list(hashes)
    for index,digest in old.items():
        if hashes[index]!=new[index]:return failed('fine_localisation_unavailable')
        reconstructed[index]=digest
    if root(reconstructed)!=commitment:return failed('fine_localisation_unavailable')
    mask=np.zeros(len(hashes),bool);mask[list(old)]=True
    return Verification('FAILED_INTEGRITY','fine_map_commitment_checked',mask.reshape(h//b,w//b))
