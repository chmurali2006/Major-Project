"""Experimental fixed-tag-strength grid control, NOT a novel signature scheme.

8x8 uses one LSB/channel;4x4 uses four. Both carry192 HMAC bits/tile.
Different domains from the production8x8 baseline. Lossless only; freshness and
key trust external. Nominal tag length is not a formal security proof.
"""
import hashlib
import hmac
import struct
import numpy as np

DOMAIN=b'MajorProject/grid-control/v1\0'


def validate(rgb,key,image_id,block):
    x=np.asarray(rgb)
    if block not in (4,8) or type(block) is not int:raise ValueError('block4 or8 required')
    if x.dtype!=np.uint8 or x.ndim!=3 or x.shape[2]!=3 or min(x.shape[:2])<block or any(n%block for n in x.shape[:2]):raise ValueError('aligned uint8 RGB required')
    if not isinstance(key,bytes) or not key:raise ValueError('nonempty secret key required')
    if type(image_id) is not int or not 0<=image_id<2**64:raise ValueError('uint64 trusted version required')
    return x


def tag(tile,key,ident,h,w,r,c,block):
    context=struct.pack('>QIIIIH',ident,h,w,r,c,block)
    return np.unpackbits(np.frombuffer(hmac.new(key,DOMAIN+context+tile.tobytes(),hashlib.sha256).digest()[:24],np.uint8))


def embed(rgb,key,image_id,block=8):
    x=validate(rgb,key,image_id,block);out=x.copy();h,w=x.shape[:2]
    bits=192//(block*block*3);clear=np.uint8(255^((1<<bits)-1))
    for r in range(h//block):
        for c in range(w//block):
            region=np.s_[r*block:(r+1)*block,c*block:(c+1)*block]
            canonical=x[region]&clear
            payload=tag(canonical,key,image_id,h,w,r,c,block).reshape(block,block,3,bits)
            values=(payload*(1<<np.arange(bits-1,-1,-1))).sum(axis=-1).astype(np.uint8)
            out[region]=canonical|values
    return out


def failures(rgb,key,image_id,block=8):
    x=validate(rgb,key,image_id,block);h,w=x.shape[:2];bits=192//(block*block*3)
    clear=np.uint8(255^((1<<bits)-1));failed=np.zeros((h//block,w//block),bool)
    for r in range(h//block):
        for c in range(w//block):
            tile=x[r*block:(r+1)*block,c*block:(c+1)*block]
            actual=((tile[...,None]>>np.arange(bits-1,-1,-1))&1).astype(np.uint8).ravel()
            expected=tag(tile&clear,key,image_id,h,w,r,c,block)
            failed[r,c]=not hmac.compare_digest(actual.tobytes(),expected.tobytes())
    return failed
