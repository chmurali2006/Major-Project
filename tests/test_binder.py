import numpy as np

from src.binder import Binder, dc_code, signature
from src.carriers import FragileCarrier
from src.config import TAG_BITS
from src.transform import Haar2, Haar2Int


def _content(seed=0, shape=(16, 16)):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, (shape[0] * 8, shape[1] * 8)).astype(np.int64)


def test_signature_is_exact_under_the_mark():
    """The tag names the lattice point, and the mark never leaves its cell.

    This is the property the whole content binding rests on: what the verifier
    reads back must be what the embedder signed.
    """
    plane = _content(1)
    haar = Haar2Int(plane.shape)
    c = haar.forward(plane)
    flat = Haar2.details_flat(c)
    carrier = FragileCarrier(8.0)
    bits = np.random.default_rng(0).integers(0, 2, flat.shape).astype(np.uint8)
    marked = carrier.write(flat, bits)
    rebuilt = haar.inverse({**c, **Haar2.details_unflat(c, marked)})
    again = Haar2.details_flat(haar.forward(rebuilt))
    assert np.array_equal(signature(again, 8.0, 64.0), signature(flat, 8.0, 64.0))


def test_signature_changes_when_content_changes():
    plane = _content(2)
    haar = Haar2Int(plane.shape)
    other = plane.copy()
    other[32:64, 32:64] = 250                      # repaint two blocks
    a = signature(Haar2.details_flat(haar.forward(plane)), 8.0, 64.0)
    b = signature(Haar2.details_flat(haar.forward(other)), 8.0, 64.0)
    assert not np.array_equal(a[4:8, 4:8], b[4:8, 4:8])
    assert np.array_equal(a[:4, :4], b[:4, :4])     # untouched blocks unchanged


def test_tag_names_content():
    """Two different contents at the same address must not share a tag."""
    b = Binder(b"k" * 16, image_id=42)
    rng = np.random.default_rng(5)
    sig_a = rng.integers(-40, 40, 60).astype(np.int8)
    sig_b = rng.integers(-40, 40, 60).astype(np.int8)
    flips = int((b.tag(7, sig_a) != b.tag(7, sig_b)).sum())
    assert 10 < flips < 50, f"content change moved {flips} of {TAG_BITS} slots"


def test_tag_is_deterministic_and_balanced():
    b = Binder(b"k" * 16, image_id=42)
    sig = np.random.default_rng(3).integers(-40, 40, (64, 64, 60)).astype(np.int8)
    addr = np.arange(4096).reshape(64, 64)
    t = b.tags(addr, sig)
    assert np.array_equal(t, b.tags(addr, sig))
    assert abs(float(t.mean()) - 0.5) < 0.01
    assert np.array_equal(t[3, 4], b.tag(int(addr[3, 4]), sig[3, 4]))


def test_address_avalanche():
    b = Binder(b"k" * 16, image_id=42)
    sig = np.zeros(60, np.int8)
    t0 = b.tag(0, sig)
    flips = [int((b.tag(a, sig) != t0).sum()) for a in range(1, 200)]
    assert min(flips) >= 15, f"weak avalanche: min {min(flips)} of {TAG_BITS}"
    assert 18 <= float(np.mean(flips)) <= 42


def test_different_keys_disagree():
    a = Binder(b"key-a", image_id=1)
    b = Binder(b"key-b", image_id=1)
    assert (a.tag(3, np.zeros(60, np.int8)) != b.tag(3, np.zeros(60, np.int8))).sum() > 20


def test_different_image_ids_disagree():
    a = Binder(b"key", image_id=1)
    b = Binder(b"key", image_id=2)
    assert (a.tag(3, np.zeros(60, np.int8)) != b.tag(3, np.zeros(60, np.int8))).sum() > 20


def test_ablation_ignores_address():
    bound = Binder(b"k" * 16, image_id=42, bind_address=True)
    loose = Binder(b"k" * 16, image_id=42, bind_address=False)
    sig = np.zeros(60, np.int8)
    assert not np.array_equal(bound.tag(1, sig), bound.tag(2, sig))
    assert np.array_equal(loose.tag(1, sig), loose.tag(2, sig))


# ---------------------------------------------------------------- A-030: mean

def test_dc_code_is_exact_under_the_mark():
    """LL2 is the block's mean and gradients; the mark never touches it.

    This is what makes the mean binding free: the embedder signs the mean, the
    verifier re-reads the mean, and the mark - which lives in the detail
    subbands - cannot move it.
    """
    plane = _content(7)
    haar = Haar2Int(plane.shape)
    c = haar.forward(plane)
    flat = Haar2.details_flat(c)
    bits = np.random.default_rng(1).integers(0, 2, flat.shape).astype(np.uint8)
    marked = FragileCarrier(8.0).write(flat, bits)
    rebuilt = haar.inverse({**c, **Haar2.details_unflat(c, marked)})
    assert np.array_equal(haar.forward(rebuilt)["LL2"], c["LL2"])
    assert np.array_equal(dc_code(haar.forward(rebuilt)["LL2"], 4.0),
                          dc_code(c["LL2"], 4.0))


def test_dc_code_moves_when_a_block_mean_moves():
    """A repaint that only moves the average is invisible to the details."""
    plane = _content(8, (8, 8))
    haar = Haar2Int(plane.shape)
    before = haar.forward(plane)["LL2"]
    moved = plane.copy()
    moved[0:8, 0:8] += 12                          # one block, mean only
    after = haar.forward(moved)["LL2"]
    assert np.array_equal(after[0, 1:], before[0, 1:])          # neighbours
    assert np.array_equal(after[1:], before[1:])
    assert not np.array_equal(dc_code(after, 4.0)[0, 0],
                              dc_code(before, 4.0)[0, 0])


def test_dc_binding_changes_the_tag():
    """Same address, same details, different mean -> a different tag."""
    b = Binder(b"k" * 16, image_id=42)
    sig = np.random.default_rng(11).integers(-40, 40, (4, 4, 60)).astype(np.int8)
    addr = np.arange(16).reshape(4, 4)
    plain = b.tags(addr, sig)
    dc = np.zeros((4, 4), np.int64)
    dc[2, 3] = 7
    bound = b.tags(addr, sig, dc=dc)
    assert np.array_equal(plain[2, 3], bound[2, 3]) is False
    assert int((plain[2, 3] != bound[2, 3]).sum()) > 10
    mask = np.ones((4, 4), bool)
    mask[2, 3] = False
    assert np.array_equal(plain[mask], bound[mask])            # others untouched
