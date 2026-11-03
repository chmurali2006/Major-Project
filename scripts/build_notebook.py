"""Assemble the Kaggle notebook from the tested source tree.

Why generate it rather than hand-write it: a notebook that reimplements the
library is a second implementation, and the two will diverge on the first bug
fix. This script base64-embeds the exact files that `pytest tests/` covers, so
the notebook cannot run code that was never tested.

    python scripts/build_notebook.py

Writes notebooks/keyswm_isic2019.ipynb.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ["protocol", "metrics", "evidence", "carriers", "tamper",
           "degradation", "models", "isic_meta"]
OUT = ROOT / "notebooks" / "keyswm_isic2019.ipynb"


def embed_modules() -> dict[str, str]:
    out = {}
    for m in MODULES:
        src = (ROOT / "src" / f"{m}.py").read_bytes()
        out[m] = base64.b64encode(src).decode("ascii")
    return out


def md(text: str):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text: str):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": text.strip("\n").splitlines(True)}


TITLE = r"""
# Keyed fragile watermarking for medical image tamper detection
### The synthesis study, ISIC 2019 run

This notebook assembles the best published finding for each sub-problem of
tamper detection into one system, and measures the assembly against every
constituent on a **protocol frozen before any training**.

| row | sub-problem | best answer | source |
|---|---|---|---|
| 1 | where to spend embedding energy | attention-weighted strength | PFF-WM |
| 2 | what the verifier reads | **keyed** QIM residual, integer Haar | this work |
| 3 | is anything wrong | one-class AE, authentic-only | PFF-WM |
| 4 | error map to mask | RefineNet, 3 levels + skips | PFF-WM |
| 5 | output formulation | segmentation, not a scalar | WAM |
| 6 | survive routine processing | degradation conditioning | OmniGuard |
| 7 | benign vs malicious vs unknown | residual features to classifier | post-quantum DCT |
| 8 | when evidence is weak | **calibrated abstention + reason codes** | this work |

**What this notebook does NOT claim.** The published localisation bar — IoU
0.832 — was measured on **LiTS** with *lesion-insertion* tampering. This
notebook runs on **ISIC 2019** with a wider family set. Numbers from here are
therefore not directly comparable to that bar, and the receipt labels them
`protocol: isic2019-synthesis-v1`. Any table that puts them side by side must
carry that label.
"""

SETUP = r"""
import base64, os, sys, json, glob, time, hashlib, random
from pathlib import Path

import numpy as np
import torch

PKG_ROOT = "/kaggle/working/_keyswm" if os.path.isdir("/kaggle/working") else "/tmp/_keyswm"
os.makedirs(os.path.join(PKG_ROOT, "keyswm"), exist_ok=True)

FILES = __FILES__

for _name, _b64 in FILES.items():
    with open(os.path.join(PKG_ROOT, "keyswm", _name + ".py"), "wb") as fh:
        fh.write(base64.b64decode(_b64))
open(os.path.join(PKG_ROOT, "keyswm", "__init__.py"), "w").write("")
if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)

import keyswm.protocol as protocol
import keyswm.metrics as metrics
import keyswm.evidence as evidence
import keyswm.tamper as tamper
import keyswm.degradation as degradation
import keyswm.models as models
import keyswm.isic_meta as isic_meta

print("package      :", PKG_ROOT)
print("modules      :", sorted(FILES))
print("protocol     :", len(protocol.MATRIX), "configurations,",
      len(protocol.TAMPER_FAMILIES), "families,", len(protocol.METRICS), "metrics")
print("audit        :", protocol.audit() or "PASS")
print("torch        :", torch.__version__, "| cuda:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu          :", torch.cuda.get_device_name(0))
"""

CONFIG = r"""
import torch

SEED = 20261024

CFG = dict(
    seed=SEED,
    size=512,
    key=b"isic2019-synthesis-v1",
    n_total=9000,
    n_smoke=120,           # images used when no dataset is mounted
    split=(0.70, 0.15, 0.15),
    # batch 8 at 512x512 fits a T4 (16 GB) with room to spare. On CPU the
    # activations dominate and a small box will OOM, so shrink it there; this
    # changes only throughput, never a code path.
    batch=8 if torch.cuda.is_available() else 2,
    lr=2e-4,
    epochs=30,             # ~6.3 GPU-h at n=9000; see docs/KAGGLE_RUNBOOK.md
    width=32,              # 1.54M params; width 96 = 13.7M to match PFF-WM
    ablation_n=400,
    pixel_size=512,
)

os.environ["PYTHONHASHSEED"] = str(SEED)
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

WORK = Path("/kaggle/working") if os.path.isdir("/kaggle/working") else Path("/tmp/keyswm_work")
WORK.mkdir(parents=True, exist_ok=True)
IMG_DIR = WORK / "tampered"; MASK_DIR = WORK / "masks"
IMG_DIR.mkdir(exist_ok=True); MASK_DIR.mkdir(exist_ok=True)
print("device:", DEVICE, "| work:", WORK)
for k, v in CFG.items():
    print(f"  {k:12s} {v}")
"""

DISCOVER = r"""
# Kaggle mounts datasets under /kaggle/input/<slug>/. Slugs vary, so discover.
CANDIDATES = [
    "/kaggle/input/isic-2019",
    "/kaggle/input/isic2019",
    "/kaggle/input/skin-cancer-malignant-vs-benign",
    "/kaggle/input/isic-2019-skin-cancer",
]
ROOTS = [p for p in CANDIDATES if os.path.isdir(p)]
if not ROOTS:
    found = glob.glob("/kaggle/input/*")
    ROOTS = [p for p in found if os.path.isdir(p)]

FILES = []
for root in ROOTS:
    FILES += glob.glob(os.path.join(root, "**", "*.jpg"), recursive=True)
    FILES += glob.glob(os.path.join(root, "**", "*.JPG"), recursive=True)
FILES = sorted(set(FILES))

META = {}
for root in ROOTS:
    for cand in glob.glob(os.path.join(root, "**", "*Metadata*.csv"), recursive=True):
        META.setdefault("metadata_csv", cand)
    for cand in glob.glob(os.path.join(root, "**", "*GroundTruth*.csv"), recursive=True):
        META.setdefault("groundtruth_csv", cand)
    for cand in glob.glob(os.path.join(root, "**", "*.csv"), recursive=True):
        META.setdefault("any_csv", cand)

META_PATH = META.get("metadata_csv") or META.get("groundtruth_csv") or META.get("any_csv")
METAOBJ = isic_meta.Metadata(META_PATH)
print("metadata   :", META_PATH)
print("schema     :", METAOBJ.schema, "|", METAOBJ.note)
if not METAOBJ.has_diagnosis:
    print()
    print("!! No diagnosis column found. Per-diagnosis stratification will be")
    print("!! skipped and labelled as unavailable. It will NOT be reported as a")
    print("!! single silent 'unknown' bucket.")

MODE = "real" if len(FILES) >= 200 else "smoke"
print("roots      :", ROOTS)
print("jpg files  :", len(FILES))
print("meta       :", META)
print("MODE       :", MODE)
if MODE == "smoke":
    print()
    print("!! No dataset found. Running on PROCEDURAL images so that every cell")
    print("!! executes. Numbers from a smoke run are not results and the receipt")
    print("!! records the mode so they cannot be quoted by accident.")

print("lesion ids :", len(METAOBJ.lesion))
"""

PREP = r"""
SIZE = CFG["size"]
N = CFG["n_total"] if MODE == "real" else CFG["n_smoke"]
N = min(N, len(FILES)) if MODE == "real" else N

FAMILY_PLAN = ["clean", "B1", "B2", "T1", "T2", "T3", "T4", "T5"]
BENIGN = {"clean", "B1", "B2"}
TAMPERING = {"T1", "T2", "T3", "T4", "T5"}


def load_image(path):
    import cv2
    bgr = cv2.imread(path, cv2.IMREAD_COLOR)
    if bgr is None:
        return None
    return cv2.cvtColor(cv2.resize(bgr, (SIZE, SIZE), interpolation=cv2.INTER_AREA),
                        cv2.COLOR_BGR2RGB)


def procedural(seed):
    import cv2
    rng = np.random.default_rng(seed)
    coarse = rng.integers(50, 200, (16, 16, 3)).astype(np.uint8)
    im = cv2.resize(coarse, (SIZE, SIZE), interpolation=cv2.INTER_CUBIC)
    return np.clip(im + rng.normal(0, 6, im.shape), 0, 255).astype(np.uint8)


# ---- split by lesion, not by image
rng = np.random.default_rng(CFG["seed"])
keys = []
for i in range(N):
    stem = Path(FILES[i]).stem if MODE == "real" else f"synth{i:05d}"
    keys.append(METAOBJ.group_of(stem))
uniq = sorted(set(keys)); rng.shuffle(uniq)
n_tr = int(len(uniq) * CFG["split"][0]); n_va = int(len(uniq) * CFG["split"][1])
assign = {k: ("train" if i < n_tr else ("val" if i < n_tr + n_va else "test"))
          for i, k in enumerate(uniq)}
SPLIT_OF = np.array([assign[k] for k in keys])
print("split:", {s: int((SPLIT_OF == s).sum()) for s in ("train", "val", "test")})

FAMILY_OF = np.array([FAMILY_PLAN[k] for k in rng.permutation(np.arange(N) % len(FAMILY_PLAN))])

import cv2
E_list, D_list, F_list, P_list, B_list = [], [], [], [], []
DX_list = []
t_start = time.time()

for i in range(N):
    rgb = load_image(FILES[i]) if MODE == "real" else procedural(CFG["seed"] + i)
    if rgb is None:
        continue
    family = str(FAMILY_OF[i])
    donor = procedural(CFG["seed"] + i + 100000) if family == "T5" else None

    marked = evidence.protect(rgb, CFG["key"], image_id=i)   # dual carrier
    if family in TAMPERING:
        changed, _blk = tamper.make_pair(marked, family, seed=CFG["seed"] + i, donor=donor)
    elif family == "clean":
        changed = marked
    else:
        changed, _ = tamper.make_pair(marked, family, seed=CFG["seed"] + i)

    # Block mask drives the verdict head; pixel mask drives localisation.
    # Keeping both means the reported pixel IoU is a real pixel IoU.
    pmask = metrics.measured_pixel_mask(marked, changed)
    bmask = metrics.measured_mask(marked, changed)

    rich = evidence.read_full(changed, CFG["key"], image_id=i)
    E_list.append(np.stack([rich[c] for c in evidence.FULL_CHANNELS]).astype(np.float16))
    D_list.append(degradation.estimate(changed))
    F_list.append(FAMILY_PLAN.index(family))
    P_list.append(np.packbits(pmask.reshape(-1)))
    B_list.append(bmask)

    stem_i = Path(FILES[i]).stem if MODE == "real" else f"synth{i:05d}"
    DX_list.append(METAOBJ.dx_of(stem_i))
    cv2.imwrite(str(IMG_DIR / f"{i:06d}.png"), cv2.cvtColor(changed, cv2.COLOR_RGB2BGR))
    np.save(MASK_DIR / f"{i:06d}.npy", bmask)

    if (i + 1) % 500 == 0 or i == N - 1:
        el = time.time() - t_start
        print(f"  {i+1}/{N}  {el:6.1f}s  eta {el/(i+1)*(N-i-1):6.1f}s", flush=True)

E = np.stack(E_list); D = np.stack(D_list); F = np.array(F_list)
P = np.stack(P_list); BM = np.stack(B_list)
DX = np.array(DX_list)
print("evidence", E.shape, E.dtype, "| degrade", D.shape, "| packed pixel truth", P.shape)
"""

CACHE = r"""
CACHE_F = WORK / "cache_v1.npz"
np.savez_compressed(CACHE_F, E=E, D=D, F=F, P=P, BM=BM, DX=DX, SPLIT=SPLIT_OF,
                    FAMILY_PLAN=np.array(FAMILY_PLAN))
print("cache:", CACHE_F, f"{CACHE_F.stat().st_size/1e6:.1f} MB")

assert E.shape[1] == evidence.N_FULL and E.shape[2:] == (64, 64)
assert np.isfinite(E).all()

# ---- separation check. Averaging E over the whole map is useless: tampered
# blocks are ~1% of the grid. Compare E ON tampered blocks to E on the rest.
print()
print(f"  {'fam':6s} {'n':>4s} {'E_tamp':>9s} {'E_clean':>9s} {'sep':>9s}")
SEP = {}
for fi, fam in enumerate(FAMILY_PLAN):
    m = F == fi
    if m.sum() == 0:
        continue
    gt = BM[m].astype(bool)
    e = E[m][:, 0].astype(np.float32)
    if gt.sum() == 0:
        print(f"  {fam:6s} {int(m.sum()):4d} {'-':>9s} {e.mean():9.4f} {'-':>9s}")
    else:
        SEP[fam] = float(e[gt].mean() - e[~gt].mean())
        print(f"  {fam:6s} {int(m.sum()):4d} {e[gt].mean():9.4f} {e[~gt].mean():9.4f} {SEP[fam]:9.4f}")
_bad = [f for f, v in SEP.items() if v < 0.10]
print("families whose keyed evidence does not separate (sep < 0.10):", _bad or "none")
print("B1/B2 raise E EVERYWHERE -- routine handling destroying the mark. That is")
print("precisely why the system needs a CANNOT_SAY verdict.")
"""

DATA = r"""
NCLS = 3
CLS_OF = np.full(len(F), 2, np.int64)          # CANNOT_SAY
CLS_OF[F == 0] = 0                             # clean  -> INTACT
for _fi, _fam in enumerate(FAMILY_PLAN):
    if _fam in ("T1", "T2", "T3", "T4", "T5"):
        CLS_OF[F == _fi] = 1                   # tampered
print("class balance:", {n: int((CLS_OF == c).sum())
                        for c, n in enumerate(["INTACT", "TAMPERED", "CANNOT_SAY"])})


# Loads the tampered image and both masks on demand. Images stay on disk: 9000
# frames at 512x512 in uint8 is 7 GB and would not survive beside the model.
class FullSet(torch.utils.data.Dataset):
    def __init__(self, idx, train=False):
        self.idx = idx; self.train = train
    def __len__(self):
        return len(self.idx)
    def __getitem__(self, k):
        j = int(self.idx[k])
        import cv2
        img = cv2.imread(str(IMG_DIR / f"{j:06d}.png"), cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pm = np.unpackbits(P[j])[:SIZE*SIZE].reshape(SIZE, SIZE).astype(np.float32)
        bm = np.load(MASK_DIR / f"{j:06d}.npy").astype(np.float32)
        return (torch.from_numpy(img.transpose(2, 0, 1).copy()).float() / 255.0,
                torch.from_numpy(E[j].astype(np.float32)),
                torch.from_numpy(D[j]),
                torch.from_numpy(bm).unsqueeze(0),
                torch.from_numpy(pm).unsqueeze(0),
                int(CLS_OF[j]))


tr_idx = np.where(SPLIT_OF == "train")[0]
va_idx = np.where(SPLIT_OF == "val")[0]
te_idx = np.where(SPLIT_OF == "test")[0]
tr = torch.utils.data.DataLoader(FullSet(tr_idx), batch_size=CFG["batch"], shuffle=True, drop_last=True, num_workers=2)
va = torch.utils.data.DataLoader(FullSet(va_idx), batch_size=CFG["batch"], shuffle=False, num_workers=2)
te = torch.utils.data.DataLoader(FullSet(te_idx), batch_size=CFG["batch"], shuffle=False, num_workers=2)
print("train", len(tr_idx), "| val", len(va_idx), "| test", len(te_idx))
print("TEST IS NOT TOUCHED UNTIL THE FINAL CELL.")
"""

TRAIN_AE = r"""
# ---- C1: one-class autoencoder, authentic images only (row 3)
authentic = np.where((SPLIT_OF == "train") & np.isin(F, [0, 1, 2]))[0]
print("authentic training images:", len(authentic))


class EvOnly(torch.utils.data.Dataset):
    def __init__(self, idx):
        self.idx = idx
    def __len__(self):
        return len(self.idx)
    def __getitem__(self, k):
        return torch.from_numpy(E[int(self.idx[k])].astype(np.float32))


ae_loader = torch.utils.data.DataLoader(EvOnly(authentic), batch_size=64, shuffle=True, drop_last=True)
ae = models.OneClassAE(evidence.N_FULL, width=max(8, CFG["width"] // 2)).to(DEVICE)
opt = torch.optim.AdamW(ae.parameters(), lr=1e-3)
t0 = time.time()
for ep in range(15):
    ae.train(); tot = 0.0
    for ev in ae_loader:
        ev = ev.to(DEVICE)
        rec, _ = ae(ev)
        loss = torch.nn.functional.mse_loss(rec, ev)
        opt.zero_grad(); loss.backward(); opt.step()
        tot += float(loss.detach()) * ev.shape[0]
    if ep % 5 == 0 or ep == 14:
        print(f"  epoch {ep:2d}  mse {tot/max(len(authentic),1):.6f}  {time.time()-t0:.1f}s")
print("AE trained on clean and benignly processed images only.")
"""

TRAIN_FUSION = r"""
# ---- C8: the assembled system
sal_net = models.SaliencyNet().to(DEVICE)
model = models.PixelRefineNet(n_ev=evidence.N_FULL,
                              width=CFG["width"]).to(DEVICE)
assert evidence.N_FULL == len(evidence.FULL_CHANNELS) == 13
params = list(model.parameters()) + list(sal_net.parameters())
opt = torch.optim.AdamW(params, lr=CFG["lr"], weight_decay=1e-4)
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=CFG["epochs"])
best = {"val_pixel_iou": -1.0, "epoch": -1}


def predict(model, sal_net, loader):
    model.eval(); sal_net.eval()
    pix, blk, cls = [], [], []
    with torch.no_grad():
        for img, ev, d, _bm, _pm, _c in loader:
            img, ev, d = img.to(DEVICE), ev.to(DEVICE), d.to(DEVICE)
            s = sal_net(img)
            out = model(ev, d, s, img)
            pix.append(torch.sigmoid(out["pixel_logits"]).cpu().numpy()[:, 0])
            blk.append(torch.sigmoid(out["block_logits"]).cpu().numpy()[:, 0])
            cls.append(out["cls"].cpu().numpy())
    return (np.concatenate(pix), np.concatenate(blk), np.concatenate(cls))


def val_scores(model, sal_net, loader, idx):
    pix, blk, _ = predict(model, sal_net, loader)
    pix_iou = []; blk_iou = []; ceil_ = []
    for k, j in enumerate(idx):
        pm = np.unpackbits(P[j])[:SIZE*SIZE].reshape(SIZE, SIZE).astype(bool)
        bm = np.load(MASK_DIR / f"{j:06d}.npy").astype(bool)
        pix_iou.append(metrics.iou(pix[k] > 0.5, pm))
        blk_iou.append(metrics.iou(blk[k] > 0.5, bm))
        ceil_.append(metrics.block_ceiling(pm))
    return float(np.mean(pix_iou)), float(np.mean(blk_iou)), float(np.mean(ceil_))


t0 = time.time()
for ep in range(CFG["epochs"]):
    model.train(); sal_net.train(); tot = 0.0; nseen = 0; parts = {}
    for img, ev, d, bm, pm, c in tr:
        img, ev, d = img.to(DEVICE), ev.to(DEVICE), d.to(DEVICE)
        bm, pm, c = bm.to(DEVICE), pm.to(DEVICE), c.to(DEVICE)
        s = sal_net(img)
        out = model(ev, d, s, img)
        # Separate imbalance weights per resolution: a few percent of blocks are
        # positive, under one percent of pixels. One shared weight drove the
        # pixel head to predict tampering everywhere.
        loss, comp = models.total_loss(out, bm, pm, c,
                                       pos_weight=CFG.get("pos_weight", 12.0),
                                       pos_weight_pixel=CFG.get("pos_weight_pixel", 4.0))
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 5.0)
        opt.step()
        tot += float(loss.detach()) * img.shape[0]; nseen += img.shape[0]
        for k, v in comp.items():
            parts[k] = parts.get(k, 0.0) + v * img.shape[0]
    sched.step()
    if ep % 5 == 0 or ep == CFG["epochs"] - 1:
        vp, vb, vc = val_scores(model, sal_net, va, va_idx)
        flag = ""
        if vp > best["val_pixel_iou"]:
            best = {"val_pixel_iou": vp, "epoch": ep}
            torch.save({"model": model.state_dict(), "sal": sal_net.state_dict()}, WORK / "best.pt")
            flag = " *"
        print(f"  ep {ep:3d} loss {tot/nseen:.4f} "
              f"(blk {parts['block']/nseen:.3f} px {parts['pixel']/nseen:.3f} "
              f"con {parts['consistency']/nseen:.3f} cls {parts['cls']/nseen:.3f})  "
              f"val px-IoU {vp:.4f} blk-IoU {vb:.4f} | {time.time()-t0:.0f}s{flag}")

print("best val pixel IoU", round(best["val_pixel_iou"], 4), "at epoch", best["epoch"])
print("selection used VALIDATION only. Test remains closed.")
"""

ABLATIONS = r"""
print("=== C0: classical floor, two versions ===")
print()
print("C0a raw threshold, no abstention. NOT our classical system: it flags")
print("    every block of a JPEG-75 image, because routine handling destroys the")
print("    mark everywhere. Scoring this as the baseline inflates the learned half.")
raw_blk, raw_px = [], []
for j in va_idx:
    pm = np.unpackbits(P[j])[:SIZE*SIZE].reshape(SIZE, SIZE).astype(bool)
    bm = np.load(MASK_DIR / f"{j:06d}.npy").astype(bool)
    raw_blk.append(metrics.iou(E[j][0].astype(np.float32) > 0.5, bm))
    raw_px.append(metrics.iou(metrics.upsample_to(E[j][0].astype(np.float32) > 0.5, (SIZE, SIZE)), pm))
print(f"    val block IoU {np.mean(raw_blk):.4f} | pixel IoU {np.mean(raw_px):.4f}")
print()
print("C0b threshold + the abstention rule the classical system actually has.")
print("    Compare C8 against this at equal coverage, never against C0a.")
for floor in (0.60, 0.70, 0.85):
    keep = [j for j in va_idx if E[j][1].astype(np.float32).mean() >= floor]
    if not keep:
        print(f"    survival floor {floor:.2f}  coverage 0.000  (nothing survives)")
        continue
    ious = []
    for j in keep:
        bm = np.load(MASK_DIR / f"{j:06d}.npy").astype(bool)
        ious.append(metrics.iou(E[j][0].astype(np.float32) > 0.5, bm))
    print(f"    survival floor {floor:.2f}  coverage {len(keep)/len(va_idx):.3f}  "
          f"block IoU(covered) {np.mean(ious):.4f}")

print()
print("=== C9 / C10: the key ===")
print("Recomputing evidence under a different key on held-out images.")
import cv2 as _cv
ladder = []
for k, j in enumerate(te_idx[:200]):
    im = _cv.cvtColor(_cv.imread(str(IMG_DIR / f"{j:06d}.png")), _cv.COLOR_BGR2RGB)
    a = evidence.read(im, CFG["key"], image_id=int(j))["E"]
    b = evidence.read(im, b"isic2019-synthesis-v1-WRONG", image_id=int(j))["E"]
    ladder.append((float(a.mean()), float(b.mean())))
if ladder:
    la, lb = np.array(ladder).mean(axis=0)
    print(f"  same key  mean E {la:.4f}")
    print(f"  wrong key mean E {lb:.4f}")
    print("  A wrong key must look like noise. If it looked like a weaker tamper")
    print("  signal the mark would not be keyed at all.")
"""

FINAL = r"""
# ================= TEST SET — OPENED ONCE =================
ck = torch.load(WORK / "best.pt", map_location=DEVICE)
model.load_state_dict(ck["model"]); sal_net.load_state_dict(ck["sal"])

pix, blk, cls_logits = predict(model, sal_net, te)
SIZE = CFG["size"]

rows = []
for k, j in enumerate(te_idx):
    fam = FAMILY_PLAN[F[j]]
    pm_true = np.unpackbits(P[j])[:SIZE*SIZE].reshape(SIZE, SIZE).astype(bool)
    bm_true = np.load(MASK_DIR / f"{j:06d}.npy").astype(bool)
    rows.append({
        "kind": "benign" if fam in BENIGN else "tamper",
        "family": fam,
        "pred": blk[k] > 0.5,
        "gt": bm_true,
        "pred_pixels": pix[k] > 0.5,
        "gt_pixels": pm_true,
    })

print("TEST RESULTS")
print()
print("A note on the two IoU columns. The block number is what the verdict layer")
print("decides on. The pixel number is what a localisation paper reports. They are")
print("not interchangeable, and the pixel number is bounded from above by the")
print("capability of the output grid -- see the ceiling column below.")
print()
det = metrics.detection_accuracy(rows)
print(f"  n images              {len(rows)}")
print(f"  detection accuracy    {det['detection_acc']:.4f}   (any-block-flagged; n tamper {det['n_tamper']})")
print(f"  false positives       {det['false_positive_rate']:.4f}   (n benign {det['n_benign']})")
print(f"  benefit @ pixel IoU .5 {metrics.benefit_at(rows, 0.5):.4f}")

strat = metrics.stratified_iou(rows)
print()
print("stratified by tampered area -- the only IoU table that means anything:")
print(f"  {'bucket':22s} {'n':>4s} {'blk IoU':>8s} {'px IoU':>8s} {'ceiling':>8s}")
for b, v in strat.items():
    print(f"  {b:22s} {v['n']:4d} {v['iou_block']:8.4f} "
          f"{v.get('iou_pixel', float('nan')):8.4f} {v.get('ceiling', float('nan')):8.4f}")

print()
print("per family:")
for fam in FAMILY_PLAN:
    m = [r for r in rows if r["family"] == fam]
    if not m:
        continue
    print(f"  {fam:5s} n={len(m):4d}  blk-IoU={np.mean([metrics.iou(r['pred'], r['gt']) for r in m]):.4f}"
          f"  px-IoU={np.mean([metrics.iou(r['pred_pixels'], r['gt_pixels']) for r in m]):.4f}"
          f"  flagged={np.mean([r['pred'].any() for r in m]):.3f}")

# ---- per-diagnosis strata. This is the dimension an ISIC-only study can add
# that a multi-corpus headline cannot: does localisation survive across lesion
# types, or does it only work on the textured ones?
print()
if METAOBJ.has_diagnosis:
    print("by ISIC diagnosis (tampered images only):")
    items = [{"dx": DX[j]} for j in te_idx]
    vals = [metrics.iou(r["pred"], r["gt"]) if r["kind"] == "tamper" else float("nan")
            for r in rows]
    strata = isic_meta.stratify_by(items, "dx")
    print(f"  {'dx':6s} {'n':>5s} {'blk IoU':>8s}  flag")
    for row in isic_meta.report(strata, [0.0 if v != v else v for v in vals]):
        star = "  small n" if row["small_n"] else ""
        print(f"  {row['stratum']:6s} {row['n']:5d} {row['mean']:8.4f}{star}")
    print("  A bucket with n<10 is not evidence and is marked as such.")
else:
    print("by ISIC diagnosis: UNAVAILABLE - the corpus carries no diagnosis column.")
    print("  Reported as unavailable rather than as one silent 'unknown' bucket.")

# ---- abstention: does answering less mean answering better?
print()
print("selective risk against coverage (tampered images, block level):")
confs, correct = [], []
for k, j in enumerate(te_idx):
    if rows[k]["kind"] != "tamper":
        continue
    p_ = blk[k]
    conf = np.abs(p_ - 0.5) * 2.0          # confidence in whichever side it chose
    confs.append(conf.ravel())
    correct.append((p_ > 0.5).ravel() == rows[k]["gt"].ravel())
if confs:
    confs = np.concatenate(confs); correct = np.concatenate(correct)
    for c in (1.0, 0.9, 0.75, 0.5, 0.25):
        k_ = max(1, int(round(c * confs.size)))
        sel = np.argsort(-confs)[:k_]
        print(f"  coverage {c:.2f}  risk {1.0 - correct[sel].mean():.4f}")
    print(f"  AURC {metrics.aurc(confs, correct):.4f}  (raw error {1.0 - correct.mean():.4f})")
    print("  If AURC is close to the raw error rate, the confidence carries no")
    print("  information and the abstention is decoration.")

CLS_NAMES = ["INTACT", "TAMPERED", "CANNOT_SAY"]
cls_pred = cls_logits.argmax(axis=1); cls_true = CLS_OF[te_idx]
cls_acc = float((cls_pred == cls_true).mean())
print()
print(f"three-way verdict accuracy {cls_acc:.4f}")
for a, name in enumerate(CLS_NAMES):
    m = cls_true == a
    if m.sum():
        print(f"  true {name:11s} n={int(m.sum()):4d} recall={float((cls_pred[m]==a).mean()):.3f}")

conf = np.zeros((3, 3), int)
for t_, p_ in zip(cls_true, cls_pred):
    conf[t_, p_] += 1

receipt = {
    "protocol": "isic2019-synthesis-v1",
    "mode": MODE,
    "architecture": "PixelRefineNet + SaliencyNet + keyed evidence (10ch)",
    "config": {k: (v if not isinstance(v, bytes) else v.decode()) for k, v in CFG.items()},
    "n_images": int(len(rows)) + int(len(tr_idx)) + int(len(va_idx)),
    "splits": {s: int((SPLIT_OF == s).sum()) for s in ("train", "val", "test")},
    "detection_definition": "an image is detected if any block is flagged; FPR is the fraction of benign images with any flag",
    "detection": det,
    "stratified": strat,
    "three_way_accuracy": cls_acc,
    "confusion": conf.tolist(),
    "comparable_to_published": False,
    "why_not_comparable": (
        "The 0.832 IoU bar is LiTS + lesion insertion with pixel ground truth. This run is "
        "ISIC 2019 with an eight-family protocol. Even at matched corpus the pixel IoU is "
        "bounded by the tamper size; report the ceiling column beside it."
    ),
    "claimable": MODE == "real",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
if MODE != "real":
    receipt["results"] = {"withheld": "smoke mode - no dataset, numbers are not results"}
OUT_F = WORK / "receipt.json"
OUT_F.write_text(json.dumps(receipt, indent=2))
print()
print("receipt:", OUT_F, "| claimable:", receipt["claimable"])
"""


def build() -> dict:
    files = embed_modules()
    cells = [
        md(TITLE),
        md("## 1. Setup\n\nThe package below is byte-identical to the module that `pytest tests/` covers. It is embedded rather than reimplemented so the two cannot drift."),
        code(SETUP.replace("__FILES__", repr(files))),
        md("## 2. Configuration\n\nEvery value here is frozen before training. Changing one after a run means a new protocol label."),
        code(CONFIG),
        md("## 3. Data\n\nISIC 2019 if mounted, procedural images otherwise so the notebook still executes end to end."),
        code(DISCOVER),
        md("### 3.1 Preprocess: embed, tamper, extract evidence\n\nOne pass. The cache holds evidence maps, not images, so the working set is ~150 MB instead of ~7 GB."),
        code(PREP),
        code(CACHE),
        code(DATA),
        md("## 4. Training\n\nRows 3 and 4 of the table. The autoencoder sees **only authentic images**; the fusion model sees everything."),
        code(TRAIN_AE),
        code(TRAIN_FUSION),
        md("## 5. Ablations\n\nC0 is the control. C9/C10 ask what the key costs and whether the network has learned it."),
        code(ABLATIONS),
        md("## 6. Test set — opened once\n\nSelection happened on validation. This cell runs exactly once per genuine experiment."),
        code(FINAL),
        md(r"""
## What to do with these numbers

1. **If `claimable` is false**, the run found no dataset. Do not quote anything.
2. **ISIC 2019 numbers are not comparable to the 0.832 IoU bar.** That bar is
   LiTS with lesion insertion. A side-by-side table must carry the protocol
   label or it is misleading.
3. **The comparison that *is* fair** is inside this notebook: C0 vs C8 on the
   same split. The gap between them is the contribution of the learned half, and
   it is measurable without any external dataset.
4. **To clear the published bar on its own terms**, the LiTS run is required —
   same corpus, same tamper family, same metric. That is the next notebook.
"""),
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
            "accelerator": "GPU",
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> int:
    nb = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(nb, indent=1))
    size = OUT.stat().st_size
    n_code = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
    print(f"wrote {OUT}  ({size/1024:.0f} kB, {n_code} code cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
