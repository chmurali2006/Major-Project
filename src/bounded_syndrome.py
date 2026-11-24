"""Classical GF16 power-sum syndrome baseline, not a new error-correcting code.

2t moments per16bit hash lane uniquely determine <=t changed tile symbols with
known distinct nonzero locations (standard bounded-distance algebra). BM locates
errors, Vandermonde solve recovers full leaf differences. Signed ordered root
must match before any map is exposed. No proof of implementation/security audit;
finite tests do not establish the theorem. <=65535tiles, t<=320 in this prototype.
"""
import struct
import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from .index_syndrome import EXP,LOG,mul
from .binary_signed_grid import image
from .sparse_refinement import leaves,root
from .signed_manifest import Verification

HEADER=struct.Struct('>8sQIIHH');MAGIC=b'BOUND16\0';DOMAIN=b'MajorProject/bounded-syndrome/v1\0'
MAX_T=320


def multiply(a,b):return int(EXP[int(LOG[a])+int(LOG[b])]) if a and b else 0

def inverse(a):
    if not a:raise ValueError('zero field inverse')
    return int(EXP[(65535-int(LOG[a]))%65535])


def moments(hashes,t):
    values=np.frombuffer(b''.join(hashes),dtype='>u2').astype(np.uint16).reshape(-1,16)
    positions=np.arange(1,len(hashes)+1,dtype=np.uint16)
    power=np.ones(len(hashes),np.uint16);result=np.zeros((2*t,16),np.uint16)
    for j in range(2*t):
        result[j]=np.bitwise_xor.reduce(mul(values,power[:,None]),axis=0)
        power=mul(power,positions)
    return result


def locator(sequence,t):
    c=[1]+[0]*(2*t);b=list(c);length=0;shift=1;last=1
    for n in range(2*t):
        discrepancy=int(sequence[n])
        for j in range(1,length+1):discrepancy^=multiply(c[j],int(sequence[n-j]))
        if discrepancy==0:shift+=1;continue
        prior=list(c);factor=multiply(discrepancy,inverse(last))
        for j in range(2*t+1-shift):c[j+shift]^=multiply(factor,b[j])
        if 2*length<=n:length=n+1-length;b=prior;last=discrepancy;shift=1
        else:shift+=1
    if length>t:return None
    return c[:length+1]


def recover(delta,n,t):
    support=set();points=np.arange(1,n+1,dtype=np.uint16)
    invpoints=EXP[(65535-LOG[points])%65535]
    for lane in range(16):
        if not delta[:,lane].any():continue
        polynomial=locator(delta[:,lane],t)
        if polynomial is None:return None
        value=np.zeros(n,np.uint16)
        for coefficient in reversed(polynomial):value=mul(value,invpoints)^np.uint16(coefficient)
        found=np.flatnonzero(value==0)
        if len(found)!=len(polynomial)-1:return None
        support.update(map(int,found))
        if len(support)>t:return None
    if not support:return None
    indices=sorted(support);k=len(indices);alphas=np.array(indices,np.uint16)+1
    matrix=np.zeros((k,k+16),np.uint16);powers=np.ones(k,np.uint16)
    for row in range(k):matrix[row,:k]=powers;powers=mul(powers,alphas)
    matrix[:,k:]=delta[:k]
    for column in range(k):
        candidates=np.flatnonzero(matrix[column:,column])
        if not len(candidates):return None
        pivot=column+int(candidates[0]);matrix[[column,pivot]]=matrix[[pivot,column]]
        matrix[column]=mul(matrix[column],inverse(int(matrix[column,column])))
        for row in range(k):
            if row!=column and matrix[row,column]:matrix[row]^=mul(matrix[column],matrix[row,column])
    return indices,matrix[:,k:]


def sign(rgb,key,ident,t=8,block=4,*,backend="reference"):
    moment_fn,_=functions(backend)
    x=image(rgb,ident,block)
    if type(t) is not int or not 1<=t<=MAX_T:raise ValueError('t1..320 required')
    if not isinstance(key,Ed25519PrivateKey):raise ValueError('Ed25519 private key required')
    hashes=leaves(x,ident,block)
    if len(hashes)>65535:raise ValueError('at most65535tiles')
    payload=HEADER.pack(MAGIC,ident,*x.shape[:2],block,t)+root(hashes)+moment_fn(hashes,t).astype('>u2').tobytes()
    return payload+key.sign(DOMAIN+payload)


def verify(rgb,packet,key,ident,block=4,*,backend="reference"):
    moment_fn,recover_fn=functions(backend)
    x=image(rgb,ident,block);n=(x.shape[0]//block)*(x.shape[1]//block)
    if n>65535:raise ValueError('at most65535tiles')
    no=lambda reason:Verification('CANNOT_AUTHENTICATE',reason)
    fail=lambda:Verification('FAILED_INTEGRITY','fine_localisation_unavailable')
    if not isinstance(key,Ed25519PublicKey) or not isinstance(packet,bytes):return no('trusted_evidence_missing')
    if not HEADER.size+160<=len(packet)<=HEADER.size+96+64*MAX_T:return no('invalid_size')
    try:
        magic,i,h,w,b,t=HEADER.unpack(packet[:HEADER.size])
        if magic!=MAGIC or not 1<=t<=MAX_T or len(packet)!=HEADER.size+96+64*t:return no('invalid_header')
        key.verify(packet[-64:],DOMAIN+packet[:-64])
    except (ValueError,InvalidSignature,struct.error):return no('invalid_signature')
    if (i,h,w,b)!=(ident,*x.shape[:2],block):return no('context_mismatch')
    hashes=leaves(x,ident,block);commitment=packet[HEADER.size:HEADER.size+32]
    if root(hashes)==commitment:return Verification('VERIFIED','signed_root_matches',np.zeros((h//b,w//b),bool))
    original=np.frombuffer(packet[HEADER.size+32:-64],dtype='>u2').astype(np.uint16).reshape(2*t,16)
    decoded=recover_fn(original^moment_fn(hashes,t),n,t)
    if decoded is None:return fail()
    indices,errors=decoded;reconstructed=list(hashes)
    for index,error in zip(indices,errors):
        reconstructed[index]=(np.frombuffer(hashes[index],dtype='>u2').astype(np.uint16)^error).astype('>u2').tobytes()
    if root(reconstructed)!=commitment:return fail()
    mask=np.zeros(n,bool);mask[indices]=True
    return Verification('FAILED_INTEGRITY','bounded_fine_map_commitment_checked',mask.reshape(h//b,w//b))


def functions(backend):
    if backend=="reference":return moments,recover
    if backend=="accelerated":
        from .bounded_acceleration import moments_fast,recover_fast
        return moments_fast,recover_fast
    raise ValueError("reference or accelerated backend required")
