import numpy as np
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src import coarse_fallback as C


def test_fine_and_exhausted_fallback():
    x=np.zeros((64,64,3),np.uint8);k=Ed25519PrivateKey.generate();p=C.sign(x,k,7,64,16)
    intact=C.verify(x,p,k.public_key(),7)
    assert intact.verdict=='VERIFIED' and intact.resolution==4
    y=x.copy();y[5,7,0]=1;r=C.verify(y,p,k.public_key(),7)
    assert r.verdict=='FAILED_INTEGRITY' and r.resolution==4
    y=x^np.uint8(1);r=C.verify(y,p,k.public_key(),7)
    assert r.verdict=='FAILED_INTEGRITY' and r.resolution==16 and r.failed_blocks.all()


def test_mixed_components_and_missing_evidence_rejected():
    x=np.zeros((32,32,3),np.uint8);y=x.copy();y[1,1,0]=1;k=Ed25519PrivateKey.generate()
    p=C.sign(x,k,9,64);q=C.sign(y,k,9,64)
    _,na,nb=C.HEADER.unpack(p[:C.HEADER.size])
    mixed=p[:C.HEADER.size+na]+q[C.HEADER.size+na:-64]+p[-64:]
    for invalid in (mixed,None,p[:-1],p+b'x'):
        r=C.verify(x,invalid,k.public_key(),9)
        assert r.verdict=='CANNOT_AUTHENTICATE' and r.failed_blocks is None
    assert C.verify(x,p,k.public_key(),10).verdict=='CANNOT_AUTHENTICATE'
