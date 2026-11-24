import numpy as np
import pytest
from src.authentication_grid import embed,failures


@pytest.mark.parametrize('block',[4,8])
def test_all_bitplanes_and_coordinates(block):
    x=np.random.default_rng(11).integers(0,256,(16,24,3),dtype=np.uint8)
    before=x.copy();y=embed(x,b'secret',77,block)
    assert np.array_equal(x,before)
    assert not failures(y,b'secret',77,block).any()
    bits=192//(block*block*3)
    assert np.abs(y.astype(int)-x).max()<2**bits
    for bit in range(8):
        z=y.copy();z[5,9,1]^=np.uint8(1<<bit)
        f=failures(z,b'secret',77,block)
        assert f.sum()==1 and f[5//block,9//block]
    assert failures(y,b'wrong',77,block).all()
    assert failures(y,b'secret',78,block).all()
    z=y.copy();z[block:2*block,block:2*block]=y[:block,:block]
    assert failures(z,b'secret',77,block)[1,1]


def test_invalid_configuration_refused():
    with pytest.raises(ValueError):embed(np.zeros((16,16,3),np.uint8),b'key',1,2)
    with pytest.raises(ValueError):embed(np.zeros((17,16,3),np.uint8),b'key',1,4)
