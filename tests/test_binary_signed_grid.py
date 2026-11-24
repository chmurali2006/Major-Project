import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import binary_signed_grid as B


@pytest.mark.parametrize('block',[4,8])
def test_roundtrip_all_planes_storage_and_relocation(block):
    x=np.random.default_rng(12).integers(0,256,(32,40,3),dtype=np.uint8);before=x.copy()
    k=Ed25519PrivateKey.generate();p=B.sign(x,k,19,block)
    assert len(p)==26+(32//block)*(40//block)*32+64
    assert np.array_equal(x,before) and B.verify(x,p,k.public_key(),19,block).verdict=='VERIFIED'
    for bit in range(8):
        y=x.copy();y[9,17,0]^=1<<bit;r=B.verify(y,p,k.public_key(),19,block)
        assert r.verdict=='FAILED_INTEGRITY' and r.failed_blocks.sum()==1 and r.failed_blocks[9//block,17//block]
    y=x.copy();y[block:2*block,block:2*block]=x[:block,:block]
    assert B.verify(y,p,k.public_key(),19,block).failed_blocks[1,1]


@pytest.mark.parametrize('attack',['missing','key','id','header','digest','signature','short','extra','grid','shape'])
def test_rejected_evidence_never_exposes_map(attack):
    x=np.zeros((32,32,3),np.uint8);k=Ed25519PrivateKey.generate();p=B.sign(x,k,1,4);pub=k.public_key();ident=1;block=4
    if attack=='missing':p=None
    if attack=='key':pub=Ed25519PrivateKey.generate().public_key()
    if attack=='id':ident=2
    if attack in ('header','digest','signature'):
        data=bytearray(p);data[{'header':10,'digest':30,'signature':-1}[attack]]^=1;p=bytes(data)
    if attack=='short':p=p[:-1]
    if attack=='extra':p+=b'x'
    if attack=='grid':block=8
    if attack=='shape':x=np.zeros((40,32,3),np.uint8)
    r=B.verify(x,p,pub,ident,block)
    assert r.verdict=='CANNOT_AUTHENTICATE' and r.failed_blocks is None


def test_replay_requires_external_version():
    x=np.zeros((32,32,3),np.uint8);k=Ed25519PrivateKey.generate();p=B.sign(x,k,1)
    assert B.verify(x,p,k.public_key(),1).verdict=='VERIFIED'
    assert B.verify(x,p,k.public_key(),2).verdict=='CANNOT_AUTHENTICATE'


def test_binary_experiment_and_notebook():
    import ast,sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
    from experiment_binary_grid import run
    from build_binary_grid_notebook import build_binary
    result=run(n=1)
    assert result['synthetic'] is True and len(result['rows'])==2
    assert [r['sidecar_bytes'] for r in result['rows']]==[131162,524378]
    assert all(r['embedding_mse']==0 for r in result['rows'])
    nb=build_binary()
    for cell in nb['cells']:
        if cell['cell_type']=='code':ast.parse(''.join(cell['source']))
    last=''.join(nb['cells'][-1]['source'])
    assert "CODE/'scripts/experiment_binary_grid.py'" in last
    assert 'binary-grid32-results.zip' in last
