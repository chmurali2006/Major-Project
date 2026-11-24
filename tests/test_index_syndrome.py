import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import index_syndrome as I


def test_field_and_arithmetic():
    assert len(set(map(int,I.EXP[:65535])))==65535
    for a in (0,1,2,17,65535):
        assert I.mul(a,1)==a and I.mul(a,0)==0
    assert I.mul(15,27)^I.mul(15,32)==I.mul(15,27^32)


def test_random_edit_maps_context_and_exhaustion():
    k=Ed25519PrivateKey.generate()
    for seed in range(8):
        rng=np.random.default_rng(seed);x=rng.integers(0,256,(64,64,3),dtype=np.uint8)
        p=I.sign(x,k,seed,112)
        assert I.verify(x,p,k.public_key(),seed).verdict=='VERIFIED'
        indices=rng.choice(256,16+seed,replace=False);y=x.copy()
        for index in indices:y[(index//16)*4,(index%16)*4,0]^=1
        r=I.verify(y,p,k.public_key(),seed)
        assert r.verdict=='FAILED_INTEGRITY'
        if r.failed_blocks is not None:
            expected=np.zeros(256,bool);expected[indices]=True
            assert np.array_equal(r.failed_blocks,expected.reshape(16,16))
        assert I.verify(y,p,k.public_key(),seed+1).failed_blocks is None
        altered=bytearray(p);altered[-1]^=1
        assert I.verify(y,bytes(altered),k.public_key(),seed).verdict=='CANNOT_AUTHENTICATE'
    p=I.sign(x,k,1,3);r=I.verify(x^np.uint8(1),p,k.public_key(),1)
    assert r.verdict=='FAILED_INTEGRITY' and r.failed_blocks is None


def test_root_check_blocks_incorrect_commitment():
    x=np.zeros((32,32,3),np.uint8);y=x.copy();y[0,0,0]=1
    k=Ed25519PrivateKey.generate();p=I.sign(x,k,1,112)
    payload=bytearray(p[:-64]);payload[I.HEADER.size]^=1
    forged=bytes(payload)+k.sign(I.DOMAIN+bytes(payload))
    r=I.verify(y,forged,k.public_key(),1)
    assert r.verdict=='FAILED_INTEGRITY' and r.failed_blocks is None


def test_equal_byte_budgets_and_all_bitplanes():
    from src import sparse_refinement as S
    k=Ed25519PrivateKey.generate();x=np.random.default_rng(99).integers(0,256,(32,32,3),dtype=np.uint8)
    for old,new in ((128,112),(512,448),(2048,1792)):
        assert len(S.sign(x,k,1,old))==len(I.sign(x,k,1,new))
    p=I.sign(x,k,1,112)
    for bit in range(8):
        y=x.copy();y[5,9,2]^=np.uint8(1<<bit)
        r=I.verify(y,p,k.public_key(),1)
        assert r.failed_blocks.sum()==1 and r.failed_blocks[1,2]
    for invalid in (None,p[:-1],p+b'x'):
        r=I.verify(x,invalid,k.public_key(),1)
        assert r.verdict=='CANNOT_AUTHENTICATE' and r.failed_blocks is None


def test_public_two_tile_stopping_set_is_recorded_not_hidden():
    # Availability regression: do not reinterpret ordinary-case gains as robustness.
    from probe_index_stopping_sets import duplicate_neighbours
    k=Ed25519PrivateKey.generate();x=np.random.default_rng(401).integers(0,256,(512,512,3),dtype=np.uint8)
    for budget in (112,448):
        attack=duplicate_neighbours(budget)
        assert attack is not None
        a,b=attack['indices']
        assert set(I.addresses(a,budget))==set(I.addresses(b,budget))
        y=x.copy()
        for index in (a,b):y[(index//128)*4,(index%128)*4,0]^=1
        packet=I.sign(x,k,7,budget);result=I.verify(y,packet,k.public_key(),7)
        assert result.verdict=='FAILED_INTEGRITY' and result.failed_blocks is None
