import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import fingerprint_grid as F
from src.sparse_refinement import leaves


@pytest.mark.parametrize('width',[1,4,8,16,32])
def test_integrity_and_explicit_map_contract(width):
    x=np.zeros((32,32,3),np.uint8);k=Ed25519PrivateKey.generate();packet=F.sign(x,k,5,width)
    assert len(packet)==F.HEADER.size+96+64*width
    assert F.verify(x,packet,k.public_key(),5,width).verdict=='VERIFIED'
    y=x.copy();y[7,9,0]=1;r=F.verify(y,packet,k.public_key(),5,width)
    assert r.verdict=='FAILED_INTEGRITY' and not r.localisation_certified_complete
    assert F.verify(y,packet,k.public_key(),6,width).verdict=='CANNOT_AUTHENTICATE'
    changed=bytearray(packet);changed[-1]^=1
    assert F.verify(y,bytes(changed),k.public_key(),5,width).estimated_blocks is None


def test_constructed_short_collision_hides_edit_but_not_integrity():
    x=np.zeros((32,32,3),np.uint8);k=Ed25519PrivateKey.generate();packet=F.sign(x,k,9,1)
    target=leaves(x,9,4)[0][:1]
    for counter in range(1,10001):
        y=x.copy();y[0,:2,:].flat[:4]=np.frombuffer(counter.to_bytes(4,'big'),np.uint8)
        if leaves(y,9,4)[0][:1]==target:break
    else:raise AssertionError('deterministic collision fixture not found')
    r=F.verify(y,packet,k.public_key(),9,1)
    assert not np.array_equal(x,y)
    assert r.verdict=='FAILED_INTEGRITY'
    assert not r.estimated_blocks.any() and not r.localisation_certified_complete
