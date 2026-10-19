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
    # delta_f is a normalised correlation deficit, not an exact bit count. A
    # block whose pixels touch the RGB gamut loses part of its mark to
    # saturation and scores a small non-zero deficit. The guarantee a fragile
    # watermark can actually make is that no block reaches the detection
    # threshold, so that is what is asserted.
    assert np.nanmax(res.delta_f) < DEFAULT.tau_f, f"clean delta_f max {np.nanmax(res.delta_f)}"
    assert not res.ladder.tampered.any()
    # Coverage is abstention, not failure. A handful of blocks sit against the
    # RGB gamut on every image and are refused at embed, so the honest bar is
    # "almost everything is decided", not "everything".
    assert res.coverage >= 0.99, f"coverage {res.coverage}"


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
    # Assert the contrast, not a constant: the absolute level of Carrier B's
    # error depends on the mark Carrier A writes, while what A-004 claims is
    # that moving content costs the block its semi-robust reference.
    a = clean.delta_sr[40:44, 40:44].mean()
    b = moved.delta_sr[40:44, 40:44].mean()
    assert a < 0.35
    assert b - a > 0.15, f"clean {a:.3f} moved {b:.3f}"


# ---------------------------------------------------------------- A-021
def test_resize_on_a_smooth_image_does_not_claim_tampering():
    """The ISIC condition-11 failure, pinned as a regression.

    On a smooth image most blocks carry almost no detail, so a +-2 level mark
    survives a 90% resize round trip and only the blocks containing an edge
    break. Few broken blocks, scattered along edges, look exactly like
    localised tampering: measured 79-96% false claims on pre-blurred phantoms
    and 27.3% on ISIC-300, against 0.0% on PH2. The global-attenuation rule
    (A-021) must abstain on all of them.
    """
    import io

    from PIL import Image, ImageFilter

    from src.battery.conditions import resize_roundtrip

    sysm = System(KEY)
    claims = 0
    for seed in (21, 22, 23, 24):
        rgb, mask = phantom(seed=seed)
        smooth = np.array(Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(0.9)))
        p = sysm.protect(smooth, mask, image_id=700 + seed)
        out = resize_roundtrip(p.png, 0.90)
        data = out[0] if isinstance(out, tuple) else out
        claims += int(sysm.verify(data).ladder.tampered.any())
    assert claims == 0, f"{claims}/4 smooth images claimed tampering after a resize"


def test_attenuation_rule_does_not_hide_a_real_edit_on_a_smooth_image():
    """A-021 must abstain on transforms without blinding the detector.

    The attenuation rule keys on the tag's amplitude. A copy-move pastes
    already-marked pixels, so it cannot lower that measure - but this test
    exists because a rule that abstains is one bad threshold away from
    abstaining on everything.
    """
    from PIL import Image, ImageFilter

    sysm = System(KEY)
    hits = 0
    for seed in (31, 32, 33):
        rgb, mask = phantom(seed=seed)
        smooth = np.array(Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(0.9)))
        p = sysm.protect(smooth, mask, image_id=800 + seed)
        tampered = paste(p.png, src_block=(6, 6), dst_block=(36, 36), blocks=4)
        hits += int(sysm.verify(tampered).ladder.tampered.any())
    assert hits == 3, f"detected {hits}/3 edits on smooth images"
