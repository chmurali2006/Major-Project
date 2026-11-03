"""End-to-end smoke run: keyed embed -> tamper -> evidence -> localise -> score.

Purpose is plumbing, not results. It runs the whole chain on synthetic images so
that every wire is proven before a GPU hour is spent. The numbers it prints are
NOT results and must never be quoted: the images are procedural textures, the
model is untrained, and n is tiny. It exists to fail loudly if a shape, a
convention or a denominator is wrong.

Usage:
    python scripts/smoke_pipeline.py --n 24
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evidence import embed, read                      # noqa: E402
from src.metrics import iou, summarise                    # noqa: E402
from src.models import FusionNet                          # noqa: E402
from src.tamper import make_pair                          # noqa: E402

KEY = b"smoke-key"


def synthetic_image(seed: int, size: int = 512) -> np.ndarray:
    """A textured field, not a photo. Enough structure for the mark to live in."""
    rng = np.random.default_rng(seed)
    coarse = rng.integers(50, 200, (size // 32, size // 32, 3)).astype(np.uint8)
    img = cv2.resize(coarse, (size, size), interpolation=cv2.INTER_CUBIC)
    grain = rng.normal(0, 6, (size, size, 3))
    return np.clip(img.astype(np.float64) + grain, 0, 255).astype(np.uint8)


def degrade_scalars(rgb: np.ndarray) -> np.ndarray:
    """Cheap proxies for the four degradation channels.

    A real implementation estimates JPEG quality from the blockiness spectrum.
    Here the proxies only need to be monotone in 'how much has this been
    touched', which is enough to prove the channel is wired.
    """
    lap = cv2.Laplacian(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), cv2.CV_64F).var()
    blockiness = float(lap / (lap + 100.0))
    grad = np.abs(np.diff(rgb.astype(np.float64), axis=1)).mean()
    return np.array([blockiness, grad / 32.0, 1.0, 1.0], np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--train-steps", type=int, default=40)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    families = ["T1", "T2", "T3", "T4"]

    print(f"building {args.n} protected images...")
    t0 = time.time()
    items = []
    for i in range(args.n):
        raw = synthetic_image(args.seed + i)
        marked = embed(raw, KEY, image_id=i)
        fam = families[i % len(families)]
        tampered, mask = make_pair(marked, fam, seed=args.seed + i)
        ev = read(tampered, KEY, image_id=i)
        items.append({
            "family": fam,
            "image": tampered,
            "gt": mask,
            "evidence": np.stack([ev["E"], ev["S"]]).astype(np.float32),
            "degrade": degrade_scalars(tampered),
        })
    print(f"  {time.time() - t0:.1f}s")

    # ---- the classical floor: threshold the evidence map, no learning
    print("\nclassical floor (E > tau, no network):")
    for tau in (0.30, 0.50, 0.70):
        results = []
        for it in items:
            pred = it["evidence"][0] > tau
            results.append({"kind": "tamper", "family": it["family"],
                            "pred": pred, "gt": it["gt"]})
        s = summarise(results)
        print(f"  tau={tau:.2f}  IoU={s['iou_mean']:.4f}  benefit@0.5={s['benefit_at_0.5']:.3f}")

    # ---- the learned path: short training run to prove gradients flow
    print(f"\ntraining FusionNet for {args.train_steps} steps (plumbing only)...")
    model = FusionNet(width=32)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3)
    ev_all = torch.from_numpy(np.stack([it["evidence"] for it in items]))
    deg_all = torch.from_numpy(np.stack([it["degrade"] for it in items]))
    gt_all = torch.from_numpy(np.stack([it["gt"] for it in items])).float()[:, None]
    img_all = torch.from_numpy(
        np.stack([cv2.resize(it["image"], (128, 128)) for it in items])
    ).permute(0, 3, 1, 2).float() / 255.0

    from src.models import mask_loss
    t0 = time.time()
    model.train()
    for step in range(args.train_steps):
        logits = model(ev_all, deg_all, torch.zeros_like(ev_all[:, :1]), img_all)["mask_logits"]
        loss = mask_loss(logits, gt_all)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % 10 == 0 or step == args.train_steps - 1:
            print(f"  step {step:3d}  loss {loss.item():.4f}")
    print(f"  {time.time() - t0:.1f}s")

    model.eval()
    with torch.no_grad():
        logits = model(ev_all, deg_all, torch.zeros_like(ev_all[:, :1]), img_all)["mask_logits"]
        probs = torch.sigmoid(logits).numpy()[:, 0]

    results = []
    for i, it in enumerate(items):
        results.append({"kind": "tamper", "family": it["family"],
                        "pred": probs[i] > 0.5, "gt": it["gt"]})
    s = summarise(results)
    print("\nlearned (UNTRAINED-BASELINE, not a result):")
    print(f"  IoU={s['iou_mean']:.4f}  benefit@0.5={s['benefit_at_0.5']:.3f}")
    for fam, v in sorted(s["per_family"].items()):
        print(f"    {fam}: n={v['n']:2d} IoU={v['iou_mean']:.4f} tp={v['tp']} fp={v['fp']} fn={v['fn']}")

    print("\nREMINDER: synthetic images, untrained-scale model, tiny n.")
    print("These numbers are a plumbing check and must not be quoted as results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
