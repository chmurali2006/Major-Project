import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import bounded_syndrome as B


@pytest.mark.parametrize('t',[1,2,4,8])
def test_decode_within_budget(t):
    k=Ed25519PrivateKey.generate()
    for seed in range(4):
        rng=np.random.default_rng(seed);x=rng.integers(0,256,(32,32,3),dtype=np.uint8)
        packet=B.sign(x,k,seed,t)
        assert len(packet)==B.HEADER.size+96+64*t
        assert B.verify(x,packet,k.public_key(),seed).verdict=='VERIFIED'
        for count in set((1,t)):
            y=x.copy();indices=rng.choice(64,count,replace=False)
            for index in indices:y[(index//8)*4,(index%8)*4,seed%3]^=np.uint8(1<<seed)
            r=B.verify(y,packet,k.public_key(),seed)
            expected=np.zeros(64,bool);expected[indices]=True
            assert r.verdict=='FAILED_INTEGRITY' and np.array_equal(r.failed_blocks,expected.reshape(8,8))


def test_zero_lane_and_boundary_positions():
    hashes=[bytes(32) for _ in range(16)];changed=list(hashes)
    for i in (0,15):changed[i]=bytes(30)+bytes([i+1,7])
    delta=B.moments(hashes,2)^B.moments(changed,2)
    result=B.recover(delta,16,2)
    assert result is not None and result[0]==[0,15]


def test_over_capacity_and_invalid_evidence():
    x=np.zeros((32,32,3),np.uint8);k=Ed25519PrivateKey.generate();p=B.sign(x,k,9,2)
    y=x.copy();y[::4,::4,0]=1
    r=B.verify(y,p,k.public_key(),9)
    assert r.verdict=='FAILED_INTEGRITY' and r.failed_blocks is None
    for packet in (None,p[:-1],p+b'x'):
        assert B.verify(x,packet,k.public_key(),9).verdict=='CANNOT_AUTHENTICATE'
    assert B.verify(x,p,k.public_key(),10).failed_blocks is None
    assert B.verify(x,p,Ed25519PrivateKey.generate().public_key(),9).failed_blocks is None


def test_exhaustive_two_error_positions_on_small_vector():
    from itertools import combinations
    rng=np.random.default_rng(44)
    hashes=[bytes(rng.integers(0,256,32,dtype=np.uint8)) for _ in range(16)]
    original=B.moments(hashes,2)
    for positions in list(combinations(range(16),1))+list(combinations(range(16),2)):
        changed=list(hashes)
        for i in positions:
            h=bytearray(changed[i]);h[i%32]^=i+1;changed[i]=bytes(h)
        result=B.recover(original^B.moments(changed,2),16,2)
        assert result is not None and result[0]==list(positions)
        for index,error in zip(*result):
            reconstructed=(np.frombuffer(changed[index],dtype='>u2').astype(np.uint16)^error).astype('>u2').tobytes()
            assert reconstructed==hashes[index]


def test_root_mismatch_never_exposes_map():
    x=np.zeros((32,32,3),np.uint8);y=x.copy();y[5,7,0]=1;k=Ed25519PrivateKey.generate()
    packet=B.sign(x,k,1,2);payload=bytearray(packet[:-64]);payload[B.HEADER.size]^=1
    inconsistent=bytes(payload)+k.sign(B.DOMAIN+bytes(payload))
    r=B.verify(y,inconsistent,k.public_key(),1)
    assert r.verdict=='FAILED_INTEGRITY' and r.failed_blocks is None


def test_radius64_dense_errors_and_last_field_position():
    # Exercise all hash lanes, not just single-pixel edits and sparse lanes.
    rng=np.random.default_rng(700)
    n=257;t=64
    before=[rng.bytes(32) for _ in range(n)];after=list(before)
    support=sorted(map(int,rng.choice(n,t,replace=False)))
    for index in support:after[index]=rng.bytes(32)
    result=B.recover(B.moments(before,t)^B.moments(after,t),n,t)
    assert result is not None and result[0]==support
    for index,error in zip(*result):
        assert (np.frombuffer(after[index],dtype='>u2').astype(np.uint16)^error).astype('>u2').tobytes()==before[index]
    # GF16 maximum index must not wrap to zero.
    delta=np.zeros((4,16),np.uint16);alpha=np.uint16(65535);power=np.uint16(1)
    for row in range(4):delta[row,0]=B.mul(17,power);power=B.mul(power,alpha)
    result=B.recover(delta,65535,2)
    assert result is not None and result[0]==[65534]
