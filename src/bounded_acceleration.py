"""Equivalent NumPy implementation optimisations, not a new coding construction.

Reuse hash logarithms, reuse identical per-lane locators within a call, vectorise
row elimination. No persistent image-dependent caches, probabilistic lane sampling,
shortened hashes or changes to signed-root acceptance.
"""
import numpy as np
from .index_syndrome import EXP,LOG,mul
from .bounded_syndrome import locator,inverse


def moments_fast(hashes,t):
    values=np.frombuffer(b''.join(hashes),dtype='>u2').astype(np.uint16).reshape(-1,16)
    logarithms=LOG[values];zero=values==0
    log_positions=LOG[np.arange(1,len(hashes)+1,dtype=np.uint16)]
    result=np.empty((2*t,16),np.uint16)
    # Bounded temporary allocation: one moment at a time, no n*t*16 tensor.
    for j in range(2*t):
        product=EXP[logarithms+((j*log_positions)%65535)[:,None]]
        product[zero]=0
        result[j]=np.bitwise_xor.reduce(product,axis=0)
    return result


def recover_fast(delta,n,t):
    points=np.arange(1,n+1,dtype=np.uint16)
    invpoints=EXP[(65535-LOG[points])%65535]
    support=set();seen=set()
    for lane in range(16):
        if not delta[:,lane].any():continue
        polynomial=locator(delta[:,lane],t)
        if polynomial is None:return None
        coefficients=tuple(polynomial)
        if coefficients in seen:continue
        seen.add(coefficients)
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
        factors=matrix[:,column].copy();factors[column]=0
        matrix^=mul(factors[:,None],matrix[column][None,:])
    return indices,matrix[:,k:]
