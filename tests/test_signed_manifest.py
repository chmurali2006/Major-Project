"""Non-embedding baselines: refuse untrusted evidence before exposing any map."""
import json
import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from src import signed_manifest as S


@pytest.fixture
def case():
    rgb = np.random.default_rng(123).integers(0, 256, (32, 40, 3), dtype=np.uint8)
    key = Ed25519PrivateKey.generate()
    return rgb, key, S.sign(rgb, key, 77)


def test_rfc8032_vector_1_library_primitive():
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex('9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60'))
    assert key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex() == 'd75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a'
    signature = key.sign(b'')
    assert signature.hex() == ('e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555f'
                               'b8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b')
    key.public_key().verify(signature, b'')


@pytest.mark.parametrize('scope', ['tiles', 'whole-image'])
def test_non_embedding_and_intact(case, scope):
    rgb, key, _ = case
    before = rgb.copy()
    evidence = S.sign(rgb, key, 77, scope)
    assert np.array_equal(rgb, before)
    result = S.verify(rgb, evidence, key.public_key(), 77, scope)
    assert result.verdict == 'VERIFIED'
    assert (result.failed_blocks is None) == (scope == 'whole-image')


def test_one_bit_edit_exact_tile(case):
    rgb, key, evidence = case
    received = rgb.copy()
    received[9, 18, 2] ^= 1
    check = S.verify(received, evidence, key.public_key(), 77)
    assert check.verdict == 'FAILED_INTEGRITY'
    assert check.failed_blocks.sum() == 1
    assert check.failed_blocks[1, 2]


@pytest.mark.parametrize('attack', ['digest', 'signature', 'wrong-key', 'wrong-id', 'missing', 'self-supplied-key', 'scope', 'shape', 'duplicate', 'oversize', 'invalid-utf8', 'non-json', 'nan'])
def test_untrusted_evidence_never_produces_map(case, attack):
    rgb, key, evidence = case
    public, ident = key.public_key(), 77
    envelope = json.loads(evidence)
    if attack == 'digest':
        envelope['payload']['digests'][0] = '0'*64
        evidence = json.dumps(envelope).encode()
    elif attack == 'signature':
        envelope['signature'] = '0'*128
        evidence = json.dumps(envelope).encode()
    elif attack == 'wrong-key':
        public = Ed25519PrivateKey.generate().public_key()
    elif attack == 'wrong-id':
        ident += 1
    elif attack == 'missing':
        evidence = None
    elif attack == 'self-supplied-key':
        envelope['public_key'] = 'untrusted'
        evidence = json.dumps(envelope).encode()
    elif attack == 'scope':
        envelope['payload']['scope'] = 'whole-image'
        evidence = json.dumps(envelope).encode()
    elif attack == 'shape':
        envelope['payload']['shape'] = [40, 32, 3]
        evidence = json.dumps(envelope).encode()
    elif attack == 'duplicate':
        evidence = b'{"payload":{},"payload":{},"signature":"x"}'
    elif attack == 'oversize':
        evidence = b'x'*(S.MAX_EVIDENCE_BYTES+1)
    elif attack == 'invalid-utf8':
        evidence = b'\xff'
    elif attack == 'non-json':
        evidence = b'null'
    elif attack == 'nan':
        envelope['payload']['block'] = float('nan')
        evidence = json.dumps(envelope).encode()
    result = S.verify(rgb, evidence, public, ident)
    assert result.verdict == 'CANNOT_AUTHENTICATE'
    assert result.failed_blocks is None


def test_block_relocation_detected(case):
    rgb, key, evidence = case
    received = rgb.copy()
    received[8:16, 8:16] = rgb[:8, :8]
    check = S.verify(received, evidence, key.public_key(), 77)
    assert check.failed_blocks.sum() == 1
    assert check.failed_blocks[1, 1]


def test_whole_signature_detects_edit_but_cannot_localise(case):
    rgb, key, _ = case
    evidence = S.sign(rgb, key, 77, 'whole-image')
    received = rgb.copy()
    received[1, 2, 0] ^= 1
    check = S.verify(received, evidence, key.public_key(), 77, 'whole-image')
    assert check.verdict == 'FAILED_INTEGRITY'
    assert check.failed_blocks is None


def test_freshness_is_external_not_magic(case):
    rgb, key, evidence = case
    assert S.verify(rgb, evidence, key.public_key(), 77).verdict == 'VERIFIED'
    assert S.verify(rgb, evidence, key.public_key(), 78).verdict == 'CANNOT_AUTHENTICATE'
    # Re-accepting the OLD identifier would re-accept the old valid pair.
    assert S.verify(rgb, evidence, key.public_key(), 77).verdict == 'VERIFIED'


def test_comparison_uses_independent_reference_truth():
    from scripts.compare_integrity import experiment
    rgb = np.random.default_rng(321).integers(0, 256, (32, 32, 3), dtype=np.uint8)
    results = experiment(rgb)
    assert len(results) == 3
    for result in results:
        if result['method'] != 'Embedded HMAC':
            assert result['mse'] == result['maximum_absolute_channel_change'] == 0
            assert result['sidecar_bytes'] > 0
        rows = {c['scenario']: c for c in result['cases']}
        assert rows['intact']['verdict'] == 'VERIFIED'
        assert rows['one-pixel']['verdict'] == 'FAILED_INTEGRITY'
        assert rows['one-pixel']['changed_pixels'] == 1
        if result['method'] == 'Whole-image signature':
            assert rows['one-pixel']['localisation'] is None
        else:
            assert rows['one-pixel']['localisation']['expanded_block_pixel_iou'] == 1/64
        for name in ('wrong-key', 'wrong-id'):
            assert rows[name]['localisation'] is None
            if result['method'] != 'Embedded HMAC':
                assert rows[name]['verdict'] == 'CANNOT_AUTHENTICATE'
        if result['method'] != 'Embedded HMAC':
            assert rows['missing-evidence']['verdict'] == 'CANNOT_AUTHENTICATE'
            assert rows['modified-evidence']['verdict'] == 'CANNOT_AUTHENTICATE'


@pytest.mark.parametrize('channel', range(3))
@pytest.mark.parametrize('bit', range(8))
def test_each_channel_bit_is_authenticated(case, channel, bit):
    rgb, key, evidence = case
    received = rgb.copy()
    received[10, 10, channel] ^= np.uint8(1 << bit)
    result = S.verify(received, evidence, key.public_key(), 77)
    assert result.verdict == 'FAILED_INTEGRITY'
    assert result.failed_blocks.sum() == 1


def test_distinct_expected_image_id_prevents_cross_image_acceptance(case):
    rgb, key, old = case
    assert S.verify(rgb, old, key.public_key(), 79).verdict == 'CANNOT_AUTHENTICATE'
    new = S.sign(rgb, key, 79)
    assert S.verify(rgb, new, key.public_key(), 79).verdict == 'VERIFIED'


def test_comparison_cli_and_offline_report(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    from PIL import Image
    rgb = np.random.default_rng(99).integers(0, 256, (32, 32, 3), dtype=np.uint8)
    Image.fromarray(rgb).save(tmp_path/'fixture.png')
    root = Path(__file__).resolve().parents[1]
    output = tmp_path/'comparison.json'
    command = [sys.executable, str(root/'scripts/compare_integrity.py'), '--image',
               str(tmp_path/'fixture.png'), '--out', str(output)]
    subprocess.run(command, check=True)
    r = json.loads(output.read_text())
    assert r['usable_as_isic_study'] is False
    assert len(r['samples']) == 1
    assert r['environment']['cryptography']
    assert output.with_suffix('.html').exists()
    assert subprocess.run(command, capture_output=True).returncode != 0
