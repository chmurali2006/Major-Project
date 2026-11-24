import importlib.util
from pathlib import Path
import numpy as np
import pytest
spec=importlib.util.spec_from_file_location('workspace',Path(__file__).resolve().parents[1]/'scripts/interactive_showcase.py')
W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)


def test_real_roundtrip_edit_and_expiry():
    rgb=np.random.default_rng(7).integers(0,256,(32,40,3),dtype=np.uint8)
    before=rgb.copy();packet=W.protect(rgb)
    protected=W.decode(packet['png'])
    assert np.array_equal(rgb,before)
    assert W.verify(protected,packet['session'])['verdict']=='VERIFIED'
    protected[9,18,0]^=1
    result=W.verify(protected,packet['session'])
    assert result['verdict']=='FAILED_INTEGRITY' and result['failed_blocks']==1
    assert result['map'][1][2]==1
    with pytest.raises(ValueError,match='missing/expired'):W.verify(protected,'unknown')
    W.SESSIONS[packet['session']]['created']-=W.TTL+1
    with pytest.raises(ValueError,match='missing/expired'):W.verify(protected,packet['session'])


def test_geometry_and_input_contract():
    rgb=np.zeros((32,32,3),np.uint8);packet=W.protect(rgb)
    with pytest.raises(ValueError,match='geometry'):W.verify(np.zeros((40,32,3),np.uint8),packet['session'])
    with pytest.raises(ValueError):W.decode('not base64')
    with pytest.raises(ValueError):W.decode(W.encode(np.zeros((33,32,3),np.uint8)))
