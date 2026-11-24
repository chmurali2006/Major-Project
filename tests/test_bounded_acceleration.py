import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import bounded_syndrome as B
from src.bounded_acceleration import moments_fast,recover_fast


@pytest.mark.parametrize('t',[1,2,8,32,64])
def test_moments_and_recovery_exact(t):
    rng=np.random.default_rng(800+t);n=257
    original=[rng.bytes(32) for _ in range(n)];changed=list(original)
    support=sorted(map(int,rng.choice(n,t,replace=False)))
    for index in support:changed[index]=rng.bytes(32)
    for hashes in (original,changed,[bytes(32)]*n):
        assert np.array_equal(B.moments(hashes,t),moments_fast(hashes,t))
    delta=B.moments(original,t)^B.moments(changed,t)
    a=B.recover(delta,n,t);b=recover_fast(delta,n,t)
    assert a[0]==b[0]==support and np.array_equal(a[1],b[1])


def test_heterogeneous_lanes_and_unavailable():
    hashes=[bytes(32)]*64;changed=list(hashes)
    for index in range(8):
        data=bytearray(32);data[index*2]=index+1;changed[index]=bytes(data)
    for t in (2,8):
        delta=B.moments(hashes,t)^B.moments(changed,t)
        a=B.recover(delta,64,t);b=recover_fast(delta,64,t)
        if a is None:assert b is None
        else:assert a[0]==b[0] and np.array_equal(a[1],b[1])


def test_packet_identity_and_verdicts():
    rng=np.random.default_rng(99);x=rng.integers(0,256,(32,32,3),dtype=np.uint8)
    key=Ed25519PrivateKey.generate()
    p=B.sign(x,key,1,8);q=B.sign(x,key,1,8,backend='accelerated')
    assert p==q
    for count in (0,1,8,9,64):
        y=x.copy()
        for index in range(count):y[(index//8)*4,(index%8)*4,0]^=1
        a=B.verify(y,p,key.public_key(),1);b=B.verify(y,p,key.public_key(),1,backend='accelerated')
        assert (a.verdict,a.reason)==(b.verdict,b.reason)
        assert np.array_equal(a.failed_blocks,b.failed_blocks)
    with pytest.raises(ValueError):B.verify(x,p,key.public_key(),1,backend='invalid')


def test_extended_patch_radius_dense_lanes():
    # Large-radius algebra independent of image fixture texture.
    rng=np.random.default_rng(1101);n=320;t=289
    original=[rng.bytes(32) for _ in range(n)];changed=list(original)
    support=sorted(map(int,rng.choice(n,t,replace=False)))
    for index in support:changed[index]=rng.bytes(32)
    delta=moments_fast(original,t)^moments_fast(changed,t)
    result=recover_fast(delta,n,t)
    assert result is not None and result[0]==support
    for index,error in zip(*result):
        assert (np.frombuffer(changed[index],dtype='>u2').astype(np.uint16)^error).astype('>u2').tobytes()==original[index]


def test_extended_wire_capacity_and_limit_validation():
    x=np.zeros((32,32,3),np.uint8);key=Ed25519PrivateKey.generate()
    for t in (289,320):
        p=B.sign(x,key,1,t,backend='accelerated')
        assert len(p)==124+64*t
        assert B.verify(x,p,key.public_key(),1,backend='accelerated').verdict=='VERIFIED'
    for t in (0,321,1.5,True):
        with pytest.raises(ValueError):B.sign(x,key,1,t,backend='accelerated')
