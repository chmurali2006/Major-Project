"""Legacy standalone matrix; utilities are imported by the portable ISIC runner.

Standalone use requires explicit legacy opt-in and is not a substitute for matched
constituent ablations under the corrected training recipe. The historical
entrypoint description below is not current scientific/security validation.
See PROTOCOL_V2.md for current method changes and limitations.

Run the C0-C11 configuration matrix and write a receipt per configuration.

This is the script that turns the design into results. Everything else in the
repository exists to make this run trustworthy.

    # prove the whole matrix executes, no dataset and no GPU needed
    python scripts/run_matrix.py --smoke

    # the real run
    python scripts/run_matrix.py --data /kaggle/input/isic2019 --out runs/isic2019-v1

    # one configuration, e.g. the headline
    python scripts/run_matrix.py --data ... --configs C0,C8

Design commitments this script enforces, in code rather than in prose:

  * **The protocol is imported, not restated.** Every configuration, family,
    metric and gate comes from `src/protocol.py`. `audit()` is run first and the
    script refuses to start if it fails.
  * **Evidence is frozen before training.** The precompute stage writes the
    evidence tensors once; training reads them and cannot modify them. That is
    the architectural rule "the network never generates evidence" expressed as a
    filesystem invariant.
  * **The test split is opened once.** `--stage test` is recorded in the receipt,
    and a receipt that reports test numbers without a prior validation selection
    is rejected by `_check_receipt`.
  * **A receipt carries its provenance.** Commit hash and `code_dirty` are
    recorded, and a receipt from a dirty tree is marked `usable: false`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import evidence as ev                                    # noqa: E402
from src import metrics as M                                      # noqa: E402
from src import protocol as P                                     # noqa: E402
from src import tamper as T                                       # noqa: E402

BLOCK = 8
IMAGE_SIZE = 512
REKEY = b"matrix-key-K2"        # the second key for the re-key test


# ================================================================ provenance

def provenance() -> dict:
    """What produced this receipt. A receipt from a dirty tree is worthless."""
    def git(*a):
        try:
            return subprocess.check_output(("git",) + a, cwd=ROOT,
                                           stderr=subprocess.DEVNULL,
                                           text=True).strip()
        except Exception:
            return "unknown"
    dirty = bool(git("status", "--porcelain"))
    return {"commit": git("rev-parse", "--short", "HEAD"),
            "code_dirty": dirty,
            "usable": not dirty,
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S")}


# ================================================================ data

@dataclass
class Item:
    """One watermarked image plus everything needed to score it."""
    image_id: int
    strata: str                   # diagnosis, for stratified reporting
    marked: np.ndarray            # the protected 512x512 RGB image
    clean: np.ndarray             # the same image, untouched (for ceilings)
    key_id: bytes
    group: str = ""               # lesion id: the SPLIT unit, never the image


def load_items(data: Path | None, n: int, seed: int, smoke: bool) -> list[Item]:
    """Load images and protect them. In smoke mode, procedurally textured fields.

    The procedural path is not a stand-in for a dataset -- it is a wiring test.
    Numbers produced from it are not results and the receipt says so.
    """
    import cv2

    rng = np.random.default_rng(seed)
    key = b"matrix-key"
    items: list[Item] = []

    if smoke or data is None:
        for i in range(n):
            coarse = rng.integers(50, 200, (IMAGE_SIZE // 64, IMAGE_SIZE // 64, 3))
            img = cv2.resize(coarse.astype(np.uint8), (IMAGE_SIZE, IMAGE_SIZE),
                             interpolation=cv2.INTER_CUBIC)
            img = np.clip(img.astype(np.float64)
                          + rng.normal(0, 5, img.shape), 0, 255).astype(np.uint8)
            items.append(Item(image_id=i, strata=f"dx{i % 8}",
                              marked=ev.protect(img, key, i),
                              clean=img, key_id=key, group=f"g{i // 2}"))
        return items

    from src import isic_meta

    paths = sorted(data.rglob("*.jpg"))[:n] or sorted(data.rglob("*.png"))[:n]
    if not paths:
        raise SystemExit(f"no images under {data}")

    # ISIC metadata lives in a CSV somewhere under the dataset root. Its schema
    # varies (one-hot columns in some releases, a single 'diagnosis' column in
    # others), which is exactly what `isic_meta.Metadata` auto-detects.
    meta = isic_meta.Metadata(_find_metadata(data))
    print(f"metadata    : {meta.note}")

    for i, p in enumerate(paths):
        img = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
        if img is None:
            continue
        img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE),
                         interpolation=cv2.INTER_AREA)
        items.append(Item(image_id=i, strata=meta.dx_of(p.stem),
                          marked=ev.protect(img, key, i),
                          clean=img, key_id=key,
                          group=meta.group_of(p.stem)))
    return items


def _find_metadata(data: Path) -> Path | None:
    """Locate the ISIC metadata CSV without assuming its slug."""
    for pat in ("*Metadata*.csv", "*GroundTruth*.csv", "*.csv"):
        hits = sorted(data.rglob(pat))
        if hits:
            return hits[0]
    return None


@dataclass
class Sample:
    """A precomputed training/evaluation example. Evidence is FROZEN here.

    Stored compactly on purpose. Holding these as float32 costs 4.4 MB each, so
    200 samples is ~880 MB before the model is even built -- enough to OOM a
    small machine (and it did: exit 137 at n=200). uint8 for the image and bool
    for the pixel mask is lossless here, and the tensors are widened per batch.

    The evidence is float16 rather than float32: it comes from a quantisation
    residual, so the extra mantissa bits carry nothing, and halving it is what
    keeps a full-corpus cache inside a Kaggle working set.
    """
    ev: np.ndarray          # (13, 64, 64) float16
    degrade: np.ndarray     # (4,) float32
    image: np.ndarray       # (3, 512, 512) uint8, 0..255
    gt_block: np.ndarray    # (64, 64) bool
    gt_pixel: np.ndarray    # (512, 512) bool
    cls: int                # 0 intact, 1 tampered
    family: str
    strata: str = "UNKNOWN"  # diagnosis, carried through for stratified reporting

    @property
    def nbytes(self) -> int:
        return (self.ev.nbytes + self.degrade.nbytes + self.image.nbytes
                + self.gt_block.nbytes + self.gt_pixel.nbytes)


def build_sample(item: Item, family: str, rng: np.random.Generator,
                 wrong_key: bool = False,
                 donor: Item | None = None) -> Sample:
    """Apply one tamper family to a marked image, then read the evidence back.

    The mask is **measured by differencing**, never taken from the family's
    parameters. A declared rectangle would score better and mean nothing.
    """
    if family.startswith("B"):
        kind = family.split(":")[-1] if ":" in family else "jpeg75"
        tampered = T.benign_op(item.marked, kind=kind, rng=rng)
    elif family == "none":
        tampered = item.marked
    else:
        # T5 splices a region from a *different* image, so it needs a donor.
        # Passing the image itself would silently turn T5 into T1, which is the
        # gap the classical phase never measured.
        d = donor.marked if (family == "T5" and donor is not None) else None
        tampered, _block_mask = T.make_pair(item.marked, family,
                                            seed=int(rng.integers(1 << 30)),
                                            donor=d)

    # Pixel truth is measured by differencing, never read off the family's
    # parameters. `make_pair` returns a block mask, which is what the verdict
    # layer reasons over; scoring localisation on it would be an 8x upscale of a
    # block decision and could never exceed the block ceiling.
    gt_pixel = M.measured_pixel_mask(item.marked, tampered).astype(np.float32)
    gt_pixel = gt_pixel.reshape(IMAGE_SIZE, IMAGE_SIZE)
    cls = 1 if gt_pixel.any() else 0

    key = b"wrong-key" if wrong_key else item.key_id
    e = ev.read_full(tampered, key, item.image_id)          # profile default: dual
    from src import degradation
    deg = degradation.estimate(tampered)

    ny = nx = IMAGE_SIZE // BLOCK
    gt_block = gt_pixel.reshape(ny, BLOCK, nx, BLOCK).any(axis=(1, 3))
    return Sample(ev=np.stack([e[c] for c in ev.FULL_CHANNELS]).astype(np.float16),
                  degrade=np.asarray(deg, np.float32),
                  image=np.transpose(tampered, (2, 0, 1)).astype(np.uint8),
                  gt_block=gt_block.astype(bool),
                  gt_pixel=(gt_pixel > 0.5), cls=cls, family=family,
                  strata=item.strata)


# ================================================================ classical

def classical_decide(e: np.ndarray, tau: float) -> np.ndarray:
    """The C0 control: threshold the keyed evidence map, nothing else.

    This is deliberately the simplest possible reader of `E`. It is what a
    hand-tuned system does, and it is the baseline the learned half must beat to
    have been worth building.
    """
    return (e[0] > tau).astype(np.float32)          # channel 0 is E


def upsample(block: np.ndarray) -> np.ndarray:
    return np.repeat(np.repeat(block, BLOCK, axis=0), BLOCK, axis=1)


def stratify(samples: list[Sample], pred_pixel: list[np.ndarray]) -> dict:
    """Per-diagnosis and per-area-bucket IoU, each with n and its ceiling.

    An aggregate IoU over a mixed corpus says nothing about any particular scale
    or lesion type: flat naevi and textured carcinomas lose their mark in
    different places, and IoU itself is strongly area-dependent. So every bucket
    is printed, with the block ceiling for its own area bucket beside it. A
    bucket with n below the warning threshold is flagged rather than dropped.
    """
    from src import isic_meta

    ious = [M.iou(pp > 0.5, s.gt_pixel) for s, pp in zip(samples, pred_pixel)]

    by_dx = []
    for diagnosis in sorted({s.strata for s in samples}):
        idx = [i for i,s in enumerate(samples) if s.strata == diagnosis]
        positive = [i for i in idx if samples[i].cls == 1]
        by_dx.append({'dx': diagnosis, 'n': len(positive), 'n_total': len(idx),
                      'n_intact': len(idx)-len(positive),
                      'iou': float(np.mean([ious[i] for i in positive])) if positive else None,
                      'iou_convention': 'tampered images only', 'small_n': len(positive) < 10})

    # tampered-area buckets, with the ceiling each one is bounded by
    tampered = [i for i, s in enumerate(samples) if s.cls == 1]
    areas = [float(samples[i].gt_pixel.mean()) for i in tampered]
    buckets = M.area_buckets(areas) if areas else []
    groups: dict[str, list[int]] = {}
    for i, b in zip(tampered, buckets):
        groups.setdefault(b, []).append(i)

    by_area = []
    for name in sorted(groups):
        idx = groups[name]
        vals = [ious[i] for i in idx]
        # ceiling for this bucket: the best a perfect block classifier could do
        # on a region of the median area in it
        med_area = float(np.median([areas[tampered.index(i)] for i in idx]))
        radius = float(np.sqrt(med_area * IMAGE_SIZE * IMAGE_SIZE / np.pi))
        by_area.append({"bucket": name, "n": len(idx),
                        "median_radius_px": round(radius, 1),
                        "iou": round(float(np.mean(vals)), 4),
                        "ceiling": float(np.mean([M.optimal_block_iou(samples[i].gt_pixel) for i in idx])),
                        "ceiling_convention": "exact per-image block oracle, averaged",
                        "any_overlap_block_iou": float(np.mean([M.block_ceiling(samples[i].gt_pixel) for i in idx])),
                        "small_n": len(idx) < 10})
    return {"by_diagnosis": by_dx, "by_area": by_area}


def score(samples: list[Sample], pred_block: list[np.ndarray],
          pred_pixel: list[np.ndarray], pred_cls: list[int]) -> dict:
    """Score a run. Every ratio carries its denominator."""
    if not len(samples) or any(len(x) != len(samples) for x in (pred_block, pred_pixel, pred_cls)):
        raise ValueError('score requires nonempty aligned predictions and samples')
    for s, pb, pp, pc in zip(samples, pred_block, pred_pixel, pred_cls):
        if np.asarray(pc).ndim != 0 or pc not in (0, 1):
            raise ValueError('verdict must be a scalar binary integer')
        if np.shape(pb) != np.shape(s.gt_block) or np.shape(pp) != np.shape(s.gt_pixel):
            raise ValueError('prediction/ground-truth shapes differ')
        if not np.isfinite(pb).all() or not np.isfinite(pp).all():
            raise ValueError('predictions contain nonfinite values')
        if s.cls not in (0, 1) or bool(s.cls) != bool(s.gt_pixel.any()):
            raise ValueError('ground-truth class disagrees with measured pixel mask')
    ious, accs, dets = [], [], []
    for s, pb, pp, pc in zip(samples, pred_block, pred_pixel, pred_cls):
        ious.append(M.iou(pp > 0.5, s.gt_pixel > 0.5))
        accs.append(float(((pb > 0.5) == (s.gt_block > 0.5)).mean()))
        dets.append(int((pc == 1) == (s.cls == 1)))
    ious = np.asarray(ious, np.float64)
    tampered = [i for i, s in enumerate(samples) if s.cls == 1]
    intact = [i for i, s in enumerate(samples) if s.cls == 0]
    out = {
        "n": len(samples),
        "n_tampered": len(tampered),
        "n_intact": len(intact),
        "iou_mean": float(ious.mean()) if len(ious) else 0.0,
        "iou_tampered_mean": float(ious[tampered].mean()) if tampered else 0.0,
        "block_acc": float(np.mean(accs)) if accs else 0.0,
        "detection": float(np.mean(dets)) if dets else 0.0,
        "detection_denominator": f"{int(np.sum(dets))} / {len(dets)}",
        "false_claims": int(sum(1 for i in intact if pred_cls[i] == 1)),
        "n_intact_denominator": len(intact),
    }
    tp = sum(int(pred_cls[i] == 1) for i in tampered)
    fp = out["false_claims"]
    out.update({"true_positives": tp,
                "tpr": tp / len(tampered) if tampered else None,
                "fpr": fp / len(intact) if intact else None,
                "balanced_accuracy": .5 * (tp / len(tampered) + 1 - fp / len(intact))
                    if tampered and intact else None})
    out['by_family'] = []
    for family in sorted({s.family for s in samples}):
        idx = [i for i,s in enumerate(samples) if s.family == family]
        pos = [i for i in idx if samples[i].cls == 1]
        neg = [i for i in idx if samples[i].cls == 0]
        out['by_family'].append({'family': family, 'n': len(idx), 'n_tampered': len(pos),
            'n_intact': len(neg),
            'iou_tampered_mean': float(ious[pos].mean()) if pos else None,
            'tpr': float(np.mean([pred_cls[i] == 1 for i in pos])) if pos else None,
            'fpr': float(np.mean([pred_cls[i] == 1 for i in neg])) if neg else None})
    out.update(stratify(samples, pred_pixel))
    return out


# ================================================================ training

def build_model(cfg: P.Config, n_ev: int, width: int, binary_verdict_head=False):
    """Map a configuration id onto an architecture.

    C0 is not here: it has no parameters. `components` comes from
    `protocol.MATRIX`, so this function cannot silently disagree with the
    documented matrix.

    The saliency head is built as a real module and trained with the refiner.
    It is NOT passed as zeros or as a proxy of the evidence map -- that mistake
    is exactly F2 in the design review, where row 1 of the table was claimed but
    never implemented. A configuration without `attn` gets a saliency tensor of
    zeros from a module that is frozen and excluded from the optimiser, so the
    ablation is honest rather than a missing flag.
    """
    from src import models

    has = set(cfg.components)
    # C10 and C11 carry only a *test-mode* marker (rekey / heldout_family); their
    # architecture is C8's. Testing "no components left after removing the
    # markers" therefore wrongly made them classical. Only C0 has no components.
    if cfg.cid == "C0":
        return None                              # C0: classical control
    n_cls = 2 if binary_verdict_head else (3 if "three" in has else 2)
    n_ev_in = n_ev + (1 if "ae" in has else 0)   # AE error map is an extra channel
    refine = models.PixelRefineNet(n_ev=n_ev_in, width=width, n_cls=n_cls,
                                   stage_attention="stage_attn" in has)
    sal = models.SaliencyNet(width=width)
    if "attn" not in has and cfg.cid not in ("C9", "C10", "C11"):
        for p in sal.parameters():
            p.requires_grad_(False)
    return {"refine": refine, "saliency": sal,
            # The AE models the manifold of authentic *evidence*, not images --
            # that is the one-class discipline. It therefore takes the same
            # evidence tensor the refiner sees, which is also why C1 can be a
            # clean ablation of it.
            "ae": models.OneClassAE(cin=n_ev) if "ae" in has else None,
            "use_saliency": ("attn" in has) or cfg.cid in ("C9", "C10", "C11"),
            "use_degrade": ("degrad" in has) or cfg.cid in ("C9", "C10", "C11"),
            "use_pixel": ("seg" in has) or cfg.cid in ("C9", "C10", "C11")}


def forward_all(model, t: dict) -> dict:
    """Run the bundle, honouring every configuration flag.

    Each flag changes the computation, not just a label. A matrix whose rows are
    labelled differently but computed identically is the same failure as F2 --
    claiming a component that is not there.
    """
    from src.ablations import mask_evidence
    ev = mask_evidence(model, t["ev"])
    if model["ae"] is not None and model.get("use_ae", True):
        # A reconstruction-residual feature. The portable runner explicitly
        # pretrains this on authentic TRAIN evidence and freezes it; the legacy
        # matrix alone does not enforce that one-class training discipline.
        _rec, err = model["ae"](ev)                 # err: (B,1,h,w)
        ev = torch_cat([ev, F_avg(err, ev.shape[-1])], dim=1)

    elif model['ae'] is not None:
        ev = torch_cat([ev, ev[:, :1]*0.0], dim=1)

    sal = (model["saliency"](t["image"]) if model["use_saliency"]
           else t["image"][:, :1] * 0.0 + 0.5)               # constant, no gradient
    deg = t["deg"] if model["use_degrade"] else t["deg"] * 0.0

    out = model["refine"](ev, deg, sal, t["image"])
    if not model["use_pixel"]:
        # Without the segmentation formulation the model has no pixel head, so
        # localisation is scored on the block decision upsampled -- which is
        # exactly what the block ceiling bounds.
        out["pixel_logits"] = torch_repeat(out["block_logits"])
    return out


def torch_cat(xs, dim=1):
    import torch
    return torch.cat(xs, dim=dim)


def torch_repeat(block_logits):
    """(B,1,64,64) -> (B,1,512,512): the block decision, upsampled.

    This is what a system *without* the segmentation formulation reports. It
    cannot beat the block ceiling, by construction.
    """
    import torch
    return block_logits.repeat_interleave(BLOCK, dim=2).repeat_interleave(BLOCK, dim=3)


def F_avg(x, n):
    import torch.nn.functional as F
    return F.adaptive_avg_pool2d(x, n)


def params_of(model):
    ps = list(model["refine"].parameters())
    if model["use_saliency"]:
        ps += [p for p in model["saliency"].parameters() if p.requires_grad]
    if model["ae"] is not None:
        ps += [p for p in model["ae"].parameters() if p.requires_grad]
    return ps


def to_eval(model):
    model["refine"].eval()
    model["saliency"].eval()
    if model["ae"] is not None:
        model["ae"].eval()


def to_train(model):
    model["refine"].train()
    if model["use_saliency"]:
        model["saliency"].train()
    if model["ae"] is not None:
        if any(p.requires_grad for p in model["ae"].parameters()):
            model["ae"].train()
        else:
            model["ae"].eval()  # frozen BatchNorm statistics must not see edits


def state_of(model):
    st = {"refine": model["refine"].state_dict()}
    if model["use_saliency"]:
        st["saliency"] = model["saliency"].state_dict()
    if model["ae"] is not None:
        st["ae"] = model["ae"].state_dict()
    return st


def load_state(model, st):
    model["refine"].load_state_dict(st["refine"])
    if "saliency" in st:
        model["saliency"].load_state_dict(st["saliency"])
    if "ae" in st and model["ae"] is not None:
        model["ae"].load_state_dict(st["ae"])


def train(model, train_s: list[Sample], val_s: list[Sample], *,
          epochs: int, batch: int, lr: float, smoke: bool,
          pos_weight: float = 1.0, pos_weight_pixel: float = 1.0, log=print,
          checkpoint_path=None, resume=False, run_id=None, device="auto"):
    """Train with the single objective from `models.total_loss`.

    Only the heads named by `total_loss` receive gradient, and the tests assert
    that every parameter does. That test exists because v1 silently left two
    heads untrained.
    """
    import torch
    from src import models

    dev = ("cuda" if torch.cuda.is_available() else "cpu") if device == "auto" else device
    model["refine"] = model["refine"].to(dev)
    model["saliency"] = model["saliency"].to(dev)
    if model["ae"] is not None:
        model["ae"] = model["ae"].to(dev)

    def to_tensor(s: Sample):
        """Widen the compact sample at the point of use, never before."""
        return {"ev": torch.from_numpy(s.ev).float().unsqueeze(0).to(dev),
                "deg": torch.from_numpy(s.degrade).unsqueeze(0).to(dev),
                "image": (torch.from_numpy(s.image).float().unsqueeze(0).to(dev)
                          / 255.0),
                # batch and channel dims: (64,64) -> (1,1,64,64)
                "gt_block": torch.from_numpy(s.gt_block)[None, None].float().to(dev),
                "gt_pixel": torch.from_numpy(s.gt_pixel)[None, None].float().to(dev),
                "cls": torch.tensor([s.cls], device=dev)}

    opt = torch.optim.AdamW(params_of(model), lr=lr)
    n_cls = model["refine"].cls_head[-1].out_features
    best, best_state = -1.0, None

    start_epoch = 0
    if checkpoint_path is not None and resume and Path(checkpoint_path).exists():
        from src.persistence import load_checkpoint
        ck = load_checkpoint(checkpoint_path, dev)
        if ck['run_id'] != run_id:
            raise ValueError('checkpoint configuration/source mismatch')
        load_state(model, ck['model'])
        opt.load_state_dict(ck['optimizer'])
        best, best_state, start_epoch = ck['best'], ck['best_state'], ck['epoch']
        torch.set_rng_state(ck['rng'].cpu())
        if dev.startswith('cuda') and ck.get('cuda_rng') is not None:
            torch.cuda.set_rng_state_all([t.cpu() for t in ck['cuda_rng']])
        log(f'Loaded completed epoch {start_epoch}/{epochs}; restoring training/best state')

    for ep in range(start_epoch, epochs):
        epoch_started = time.monotonic()
        to_train(model)
        order = np.random.default_rng(ep).permutation(len(train_s))
        run = 0.0
        loss_parts = {}
        for b in range(0, len(order), batch):
            chunk = [train_s[i] for i in order[b:b + batch]]
            opt.zero_grad()
            total = 0.0
            for s in chunk:
                t = to_tensor(s)
                out = forward_all(model, t)
                cls_t = t["cls"]  # real INTACT/TAMPERED labels; no fabricated abstain target
                loss, parts = models.total_loss(out, t["gt_block"], t["gt_pixel"], cls_t,
                                            w_pixel=1.0 if model["use_pixel"] else 0.0,
                                            w_consistency=.5 if model["use_pixel"] else 0.0,
                                            pos_weight=pos_weight,
                                            pos_weight_pixel=pos_weight_pixel)
                total = total + loss
                for name, value in parts.items():
                    loss_parts[name] = loss_parts.get(name, 0.) + value
            if not torch.isfinite(total):
                raise FloatingPointError('nonfinite localisation/classification training loss')
            (total / len(chunk)).backward()
            opt.step()
            run += float(total.detach()) / len(chunk)
        # select on validation, never on test
        tau_v, v = tune_learned_tau(model, val_s)
        log(f"    epoch {ep + 1:3d}  loss {run / max(1, len(order) // batch):.4f}"
            f"  val IoU {v['iou_mean']:.4f}  val blk-acc {v['block_acc']:.4f}"
            f"  @tau {tau_v:.2f}  elapsed {(time.monotonic()-epoch_started)/60:.2f} min"
            + '  losses ' + ' '.join(f'{name}={value/len(order):.4f}' for name,value in loss_parts.items()))
        if v["iou_tampered_mean"] > best:
            best, best_state = v["iou_tampered_mean"], {
                k: {n: x.detach().clone() for n, x in sd.items()}
                for k, sd in state_of(model).items()}
        if checkpoint_path is not None:
            from src.persistence import atomic_write
            checkpoint = {'run_id': run_id, 'epoch': ep + 1,
                          'model': state_of(model), 'optimizer': opt.state_dict(),
                          'best': best, 'best_state': best_state,
                          'rng': torch.get_rng_state(),
                          'cuda_rng': torch.cuda.get_rng_state_all() if dev.startswith('cuda') else None}
            atomic_write(checkpoint_path, lambda f: torch.save(checkpoint, f))
            log(f'Checkpoint saved after epoch {ep + 1}')
    if best_state is not None:
        load_state(model, best_state)
    return model


def predict_maps(model, samples: list[Sample]):
    """Raw probabilities, once. Scoring at several thresholds then costs nothing,
    which is what makes a like-for-like threshold comparison possible."""
    import torch
    dev = next(model["refine"].parameters()).device
    to_eval(model)
    blk, pix = [], []
    with torch.no_grad():
        for s in samples:
            t = {"ev": torch.from_numpy(s.ev)[None].float().to(dev),
                 "deg": torch.from_numpy(s.degrade)[None].to(dev),
                 "image": torch.from_numpy(s.image)[None].float().to(dev) / 255.0}
            out = forward_all(model, t)
            if any(not torch.isfinite(out[key]).all() for key in ('block_logits','pixel_logits','cls')):
                raise FloatingPointError('nonfinite model logits during evaluation')
            blk.append(torch.sigmoid(out["block_logits"])[0, 0].cpu().numpy())
            p = torch.sigmoid(out["pixel_logits"])[0, 0].cpu().numpy()
            pix.append(p if p.shape[0] == IMAGE_SIZE else upsample((blk[-1] > 0.5).astype(np.float32)))
    return blk, pix


def score_at(samples, blk, pix, tau: float) -> dict:
    pb = [(b > tau).astype(np.float32) for b in blk]
    pp = [(p > tau).astype(np.float32) for p in pix]
    pc = [int((b > tau).any()) for b in blk]
    return score(samples, pb, pp, pc)


def tune_learned_tau(model, samples: list[Sample]) -> tuple[float, dict]:
    """Choose the learned model's threshold on validation, exactly as the
    classical control's threshold is chosen there.

    Without this the comparison is not a comparison: C0 was scored at its
    validation-optimal tau while C8 was scored at a hard 0.5, and the learned
    model lost by an order of magnitude for a reason that had nothing to do with
    the model.
    """
    blk, pix = predict_maps(model, samples)
    best_tau, best = 0.5, None
    for tau in np.linspace(0.05, 0.95, 19):
        loc, acc = [], []
        for s, b, p in zip(samples, blk, pix):
            if s.cls:
                loc.append(M.iou(p > tau, s.gt_pixel))
            acc.append(float(((b > tau) == s.gt_block).mean()))
        key = (float(np.mean(loc)) if loc else 0., float(np.mean(acc)))
        if best is None or key > best:
            best_tau, best = float(tau), key
    return best_tau, score_at(samples, blk, pix, best_tau)


def evaluate(model, samples: list[Sample], *, learned: bool, tau: float = 0.5) -> dict:
    """Predict and score. `learned=False` is the classical control."""
    if not learned:
        pb = [classical_decide(s.ev, tau) for s in samples]
        pp = [upsample(x) for x in pb]
        pc = [int(x.any()) for x in pb]
        return score(samples, pb, pp, pc)

    blk, pix = predict_maps(model, samples)
    return score_at(samples, blk, pix, tau)


def tune_tau(samples: list[Sample]) -> float:
    """Choose the classical threshold on validation. Test is never touched."""
    best, best_tau = -1.0, 0.5
    for tau in np.linspace(0.2, 0.9, 15):
        r = evaluate(None, samples, learned=False, tau=float(tau))
        if r["block_acc"] > best:
            best, best_tau = r["block_acc"], float(tau)
    return best_tau


# ================================================================ harness

def run_config(cfg: P.Config, split: dict, args, prov: dict) -> dict:
    t0 = time.time()
    print(f"\n=== {cfg.cid}  {cfg.name}   (isolates: {cfg.isolates})")

    rekey = "rekey" in cfg.components
    heldout = "heldout_family" in cfg.components

    def make(pool, fams, base, wk=False):
        out = []
        for i, (it, fam) in enumerate(zip(pool, fams)):
            donor = split["all"][(i + 1) % len(split["all"])]
            out.append(build_sample(it, fam, np.random.default_rng(base + i),
                                    wrong_key=wk, donor=donor))
        return out

    training_families = split["train_families"]
    validation_families = split["val_families"]
    if heldout:
        # Reserve T5 as the unobserved attack, without relabelling other examples.
        training_families = [f if f != "T5" else "T1" for f in training_families]
        validation_families = [f if f != "T5" else "T1" for f in validation_families]
    train_s = make(split["train"], training_families, 0) if cfg.cid != "C0" else []
    val_s = make(split["val"], validation_families, 1000)

    # ------------------------------------------------------------------
    # C10 is the KEY-MEMORISATION test, not the key-dependence test.
    #
    # These are two different experiments and conflating them inverts the
    # conclusion:
    #
    #   memorisation : train on K1, test on images marked with K2 and read with
    #                  K2. The evidence is VALID (E ~ 0.01), just from a
    #                  different key. A large drop means the network learnt
    #                  K1-specific patterns instead of learning to read evidence.
    #                  This is what the protocol gate (<= 0.05 IoU) measures.
    #
    #   dependence   : read K1-marked images with the WRONG key. E ~ 1.0, i.e.
    #                  noise. A collapse here is the security property WORKING:
    #                  it proves the evidence cannot be produced without the key.
    #
    # An earlier version of this script ran only the second and reported it as a
    # gate failure at -0.59 IoU. The number was real; the interpretation was
    # backwards.
    # ------------------------------------------------------------------
    if rekey:
        test_items = [Item(image_id=it.image_id, strata=it.strata,
                           marked=ev.protect(it.clean, REKEY, it.image_id),
                           clean=it.clean, key_id=REKEY, group=it.group)
                      for it in split["test"]]
        test_s = make(test_items, split["test_families"], 2000)
        # the same trained model, shown noise instead of evidence
        noise_s = make(test_items, split["test_families"], 2000, wk=True)
    else:
        test_s = make(split["test"], split["test_families"], 2000)
        noise_s = None

    model = build_model(cfg, n_ev=ev.N_FULL, width=args.width)

    if model is None:
        tau = tune_tau(val_s)
        print(f"    classical: tau = {tau:.2f} chosen on validation")
        result = evaluate(None, test_s, learned=False, tau=tau)
        result["tau"] = tau
    else:
        tau = tune_tau(val_s)
        ltau, _ = None, None
        model = train(model, train_s, val_s, epochs=args.epochs,
                      batch=args.batch, lr=args.lr, smoke=args.smoke,
                      pos_weight=args.pos_weight,
                      pos_weight_pixel=args.pos_weight_pixel)
        ltau, _ = tune_learned_tau(model, val_s)
        result = evaluate(model, test_s, learned=True, tau=ltau)
        result["params_m"] = round(sum(p.numel() for p in params_of(model)) / 1e6, 3)

        if noise_s is not None:
            # Reported as a SECURITY PROPERTY, never as a gate failure.
            denied = evaluate(model, noise_s, learned=True, tau=ltau)
            result["key_dependence"] = {
                "iou_with_denied_key": round(denied["iou_mean"], 4),
                "detection_with_denied_key": round(denied["detection"], 4),
                "drop_vs_valid_key": round(result["iou_mean"] - denied["iou_mean"], 4),
                "meaning": ("A collapse here is the property working: without the "
                            "key the evidence is noise and the reader has nothing "
                            "to amplify. It is not a memorisation failure."),
            }
            result["rekey"] = {
                "iou_trained_k1_tested_k2": round(result["iou_mean"], 4),
                "note": ("Test images re-marked with a second key and read with "
                         "that same key, so the evidence is valid. This is the "
                         "memorisation measurement the protocol gate refers to."),
            }
        result["tau"] = ltau
        result["tau_reference"] = tau

    result.update({"config": cfg.cid, "name": cfg.name,
                   "isolates": cfg.isolates, "gate_coverage": None,
                   "seconds": round(time.time() - t0, 1),
                   "provenance": prov, "smoke": args.smoke})
    return result


def _check_receipt(r: dict) -> list[str]:
    """Gate the result before it is written. A receipt that fails these is not a
    receipt; it is a number someone will quote."""
    bad = []
    if not r["provenance"].get("usable"):
        bad.append("receipt produced from a dirty tree")
    if r.get("smoke"):
        bad.append("smoke run: procedural images, not results")
    if "detection_denominator" in r:
        num, den = r["detection_denominator"].split(" / ")
        if den != str(r["n"]):
            bad.append(f"detection denominator {den} != n {r['n']}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=ROOT / "runs" / "matrix")
    ap.add_argument("--configs", default="C0,C8,C9,C10")
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=2,
                    help="images per optimisation step. 512^2 activations are "
                         "what bounds this, not the data.")
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--width", type=int, default=16)
    ap.add_argument("--pos-weight-pixel", type=float, default=4.0,
                    help="positive-class weight at pixel resolution. Lower than "
                         "the block weight on purpose: positives are <1%% there, "
                         "and an over-weighted BCE drives the head to predict "
                         "tampering everywhere.")
    ap.add_argument("--pos-weight", type=float, default=12.0,
                    help="positive-class weight for the mask losses. Tampered "
                         "blocks are ~1%% of the grid, so an unweighted loss is "
                         "minimised by predicting all-zero. 12 is a starting "
                         "point; tune it on validation, never on test.")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--legacy-unverified", action="store_true", help="explicitly permit the non-audited legacy matrix; results remain unusable")
    ap.add_argument("--smoke", action="store_true",
                    help="procedural images, tiny n: proves the matrix executes")
    ap.add_argument("--families", default="T1,T2,T3,T4,T5,none,B1:jpeg75",
                    help="comma-separated tamper/benign mix. Use organic shapes "
                         "(T2,T3) to test the pixel head: a block-aligned paste "
                         "(T1) is the one case where the block ceiling is 1.000, "
                         "so it cannot show what refinement is worth.")
    args = ap.parse_args()
    if not args.smoke and not args.legacy_unverified:
        raise SystemExit('Use scripts/run_suite.py for the audited protocol; this standalone matrix is legacy/unverified.')
    import random
    import torch
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    torch.use_deterministic_algorithms(True)


    issues = P.audit()
    if issues:
        print("protocol audit FAILED:", issues)
        return 2
    print(f"protocol audit PASSED  ({len(P.MATRIX)} configurations, "
          f"{len(P.TAMPER_FAMILIES)} families)")

    prov = provenance()
    prov['usable'] = False  # legacy CLI is not the audited portable study
    if not prov["usable"]:
        print("WARNING: working tree is dirty; receipts will be marked unusable")

    items = load_items(args.data, args.n, args.seed, args.smoke)
    print(f"loaded {len(items)} images, protected with the dual carrier "
          f"(PSNR {_psnr(items):.2f} dB)")

    rng = np.random.default_rng(args.seed)
    fams = [f.strip() for f in args.families.split(",") if f.strip()]

    # SPLIT BY GROUP, NOT BY IMAGE. The protocol (src/protocol.py SPLIT) requires
    # a lesion to appear in exactly one split: several photographs of the same
    # lesion share texture and pigmentation, so an image-level split leaks the
    # answer from train to test and inflates every number downstream.
    groups = sorted({it.group for it in items})
    gidx = rng.permutation(len(groups))
    n_gtr = int(0.6 * len(groups))
    n_gva = int(0.2 * len(groups))
    assign = {}
    for rank, gi in enumerate(gidx):
        assign[groups[gi]] = ("train" if rank < n_gtr
                              else "val" if rank < n_gtr + n_gva else "test")

    split = {"all": items, "train": [], "val": [], "test": []}
    for it in items:
        split[assign[it.group]].append(it)
    for k in ("train", "val", "test"):
        if not split[k]:
            raise SystemExit(f"empty {k} split: {len(groups)} groups is too few "
                             f"for a 60/20/20 grouped split")
    n_g = {k: len({it.group for it in split[k]}) for k in ("train", "val", "test")}
    print(f"split by lesion group: {n_g['train']} / {n_g['val']} / {n_g['test']} "
          f"groups -> {len(split['train'])} / {len(split['val'])} / "
          f"{len(split['test'])} images  (test opened once)")
    for k in ("train", "val", "test"):
        split[k + "_families"] = [fams[(i + {"train": 0, "val": 1, "test": 2}[k]) % len(fams)]
                                  for i in range(len(split[k]))]


    wanted = [c.strip() for c in args.configs.split(",")]
    args.out.mkdir(parents=True, exist_ok=True)
    written = []
    for cfg in P.MATRIX:
        if cfg.cid not in wanted:
            continue
        r = run_config(cfg, split, args, prov)
        problems = _check_receipt(r)
        r["usable"] = not problems
        r["problems"] = problems
        path = args.out / f"{cfg.cid}.json"
        path.write_text(json.dumps(r, indent=2))
        written.append((cfg.cid, r))
        flag = " (NOT USABLE)" if problems else ""
        print(f"    -> {path.name}  detection {r['detection']:.4f} "
              f"({r['detection_denominator']})  IoU {r['iou_mean']:.4f}"
              f"  false-claims {r['false_claims']}/{r['n_intact_denominator']}{flag}")
        for row in r.get("by_area", []):
            print(f"       area {row['bucket']:<22} n={row['n']:3d} "
                  f"IoU {row['iou']:.3f} / ceiling {row['ceiling']:.3f} "
                  f"(r~{row['median_radius_px']:.0f}px)")
        for row in r.get("by_diagnosis", []):
            if row["n"] and row["dx"] != "UNKNOWN":
                tag = "  [small n]" if row["small_n"] else ""
                print(f"       dx   {row['dx']:<22} n={row['n']:3d} "
                      f"IoU {row['iou']:.3f}{tag}")

    print("\n%-5s %-34s %8s %8s %8s" % ("cfg", "name", "detect", "iou", "usable"))
    for cid, r in written:
        print("%-5s %-34s %8.4f %8.4f %8s"
              % (cid, r["name"][:34], r["detection"], r["iou_mean"], r["usable"]))
    if args.smoke:
        print("\nSMOKE RUN. Procedural images, "
              f"{args.epochs} epochs, n={args.n}. These are not results.")
    return 0


def _psnr(items: list[Item]) -> float:
    vals = []
    for it in items:
        mse = np.mean((it.marked.astype(np.float64) - it.clean) ** 2)
        if mse > 0:
            vals.append(10 * np.log10(255.0 ** 2 / mse))
    return float(np.mean(vals)) if vals else float("inf")


if __name__ == "__main__":
    raise SystemExit(main())
