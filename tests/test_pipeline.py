"""The six pre-flight checks, plus the binding ablation.

If any of these fail, no number produced afterwards means anything
(04_PITFALLS_AND_TRAPS.md, the two-minute pre-flight check).
"""

import numpy as np
import pytest

from src.config import DEFAULT
from src.container import png_bytes, png_read, png_text
from src.fixtures import phantom
from src.ladder import CANNOT_SAY, INTACT, KEY_MISMATCH, TAMPERED
from src.pipeline import System

KEY = b"preflight-key"


def reencode(rgb, like: bytes) -> bytes:
    """An attacker who keeps the file's metadata chunks."""
    return png_bytes(rgb, text=png_text(like))


def paste(png: bytes, src_block, dst_block, blocks=1) -> bytes:
    rgb = png_read(png)
    r0, c0 = src_block
    r1, c1 = dst_block
    n = blocks * 8
    rgb[r1 * 8:r1 * 8 + n, c1 * 8:c1 * 8 + n] = rgb[r0 * 8:r0 * 8 + n, c0 * 8:c0 * 8 + n]
    return reencode(rgb, png)


@pytest.fixture(scope="module")
def protected():
    rgb, mask = phantom(seed=11)
    sysm = System(KEY)
    p = sysm.protect(rgb, mask, image_id=101)
    return sysm, p


def test_check1_clean_image_is_exactly_intact(protected):
    sysm, p = protected
    res = sysm.verify(p.png)
    assert p.refusal_rate == 0.0, "phantom should need no capacity refusals"
    assert np.nanmax(res.delta_f) == 0.0, f"clean delta_f max {np.nanmax(res.delta_f)}"
    assert not res.ladder.tampered.any()
    assert res.coverage == 1.0


def test_check2_png_roundtrip_identical(protected):
    sysm, p = protected
    a = sysm.verify(p.png)
    b = sysm.verify(png_bytes(png_read(p.png), text=png_text(p.png)))
    assert np.array_equal(a.delta_f, b.delta_f)
    assert np.array_equal(a.ladder.verdict, b.ladder.verdict)


def test_check3_single_block_edit_is_localised(protected):
    """Restated per A-003: block scale, not pixel scale."""
    sysm, p = protected
    tampered = paste(p.png, src_block=(8, 8), dst_block=(40, 40), blocks=1)
    res = sysm.verify(tampered)
    assert res.ladder.verdict[40, 40] == TAMPERED
    assert res.delta_f[40, 40] > 0.4
    untouched = res.ladder.verdict[20, 20]
    assert untouched == INTACT


def test_check4_copy_move_source_stays_intact(protected):
    sysm, p = protected
    tampered = paste(p.png, src_block=(8, 8), dst_block=(40, 40), blocks=4)
    res = sysm.verify(tampered)
    assert (res.ladder.verdict[40:44, 40:44] == TAMPERED).mean() > 0.75
    assert (res.ladder.verdict[8:12, 8:12] == INTACT).mean() > 0.9


def test_check5_wrong_key_never_reports_tampering(protected):
    _, p = protected
    wrong = System(b"a-different-key")
    res = wrong.verify(p.png)
    assert not res.ladder.tampered.any()
    assert (res.ladder.verdict == CANNOT_SAY).all()
    assert (res.ladder.reason == KEY_MISMATCH).all()


def test_check5b_stripped_metadata_abstains(protected):
    _, p = protected
    bare = png_bytes(png_read(p.png))          # no tEXt chunks
    sysm = System(KEY)
    res = sysm.verify(bare)
    assert not res.ladder.tampered.any()
    assert (res.ladder.verdict == CANNOT_SAY).all()


def test_check6_same_input_same_bytes():
    rgb, mask = phantom(seed=12)
    a = System(KEY).protect(rgb, mask, image_id=7)
    b = System(KEY).protect(rgb, mask, image_id=7)
    assert a.png == b.png


def test_ablation_binding_removed_goes_blind():
    """Falsification check 1: without the address, copy-move is invisible."""
    rgb, mask = phantom(seed=13)
    blind = System(KEY, DEFAULT.with_(bind_address=False))
    p = blind.protect(rgb, mask, image_id=9)
    tampered = paste(p.png, src_block=(8, 8), dst_block=(40, 40), blocks=4)
    res = blind.verify(tampered)
    assert res.delta_f[40:44, 40:44].mean() < 0.05
    assert not res.ladder.tampered[40:44, 40:44].any()


def test_carrier_b_is_address_keyed():
    """A-004: a moved block must lose its semi-robust reference too."""
    rgb, mask = phantom(seed=14)
    sysm = System(KEY)
    p = sysm.protect(rgb, mask, image_id=21)
    clean = sysm.verify(p.png)
    moved = sysm.verify(paste(p.png, (8, 8), (40, 40), blocks=4))
    assert clean.delta_sr[40:44, 40:44].mean() < 0.25
    assert moved.delta_sr[40:44, 40:44].mean() > 0.25
