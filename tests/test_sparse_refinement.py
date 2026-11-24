import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import sparse_refinement as S


def test_single_and_patch_exact_map():
    x=np.random.default_rng(22).integers(0,256,(64,64,3),dtype=np.uint8)
    k=Ed25519PrivateKey.generate();packet=S.sign(x,k,7,256)
    assert S.verify(x,packet,k.public_key(),7).verdict=='VERIFIED'
    y=x.copy();y[9:17,10:21,0]^=1
    result=S.verify(y,packet,k.public_key(),7)
    truth=np.any(x!=y,axis=2).reshape(16,4,16,4).any(axis=(1,3))
    assert result.verdict=='FAILED_INTEGRITY' and result.reason=='fine_map_commitment_checked'
    assert np.array_equal(result.failed_blocks,truth)


def test_over_capacity_fails_closed():
    x=np.zeros((64,64,3),np.uint8);y=np.full_like(x,255)
    k=Ed25519PrivateKey.generate();packet=S.sign(x,k,1,3)
    r=S.verify(y,packet,k.public_key(),1)
    assert r.verdict=='FAILED_INTEGRITY' and r.failed_blocks is None


@pytest.mark.parametrize('attack',['key','id','missing','payload','extra'])
def test_context_evidence_failures(attack):
    x=np.zeros((32,32,3),np.uint8);k=Ed25519PrivateKey.generate();packet=S.sign(x,k,1,64);pub=k.public_key();ident=1
    if attack=='key':pub=Ed25519PrivateKey.generate().public_key()
    if attack=='id':ident=2
    if attack=='missing':packet=None
    if attack=='payload':packet=packet[:50]+bytes([packet[50]^1])+packet[51:]
    if attack=='extra':packet+=b'x'
    r=S.verify(x,packet,pub,ident)
    assert r.verdict=='CANNOT_AUTHENTICATE' and r.failed_blocks is None


def test_root_check_required_even_for_peelable_sketch():
    x=np.zeros((32,32,3),np.uint8);y=x.copy();y[2,3,0]=1
    k=Ed25519PrivateKey.generate();packet=S.sign(x,k,1,128)
    payload=bytearray(packet[:-64]);payload[S.HEADER.size]^=1
    forged=bytes(payload)+k.sign(S.DOMAIN+bytes(payload))
    r=S.verify(y,forged,k.public_key(),1)
    assert r.verdict=='FAILED_INTEGRITY' and r.failed_blocks is None


def test_multiple_random_changes_never_return_incomplete_map():
    k=Ed25519PrivateKey.generate()
    for seed in range(12):
        rng=np.random.default_rng(seed);x=rng.integers(0,256,(32,32,3),dtype=np.uint8)
        packet=S.sign(x,k,seed,64);y=x.copy()
        indices=rng.choice(64,seed+1,replace=False)
        for index in indices:y[(index//8)*4,(index%8)*4,0]^=1
        r=S.verify(y,packet,k.public_key(),seed)
        assert r.verdict=='FAILED_INTEGRITY'
        if r.failed_blocks is not None:
            expected=np.zeros(64,bool);expected[indices]=True
            assert np.array_equal(r.failed_blocks,expected.reshape(8,8))
