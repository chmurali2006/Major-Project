# Recovery Plan: from classical-only to a full PFF-WM-class system

Status: draft for decision, 2026-10-24.
Supersedes nothing. Extends the existing dossier; the 34-amendment record stays.

---

## 1. What the panel actually said, decoded

Three distinct complaints hide inside "childish":

| what they said | what they mean | is it fair? |
|---|---|---|
| "match top standards" | compare against published SOTA on a shared protocol | **yes** |
| "the research paper's datasets" | we used ISIC 2018; PFF-WM uses ISIC 2019, LiTS, CheXpert | **yes** |
| "use training / deep learning" | the reference work is a DL system; ours is not | **yes** |
| "childish" | hand-tuned thresholds read as a lab exercise | partly — see §2 |

The methodological record (held-out split, 34 amendments, falsification, abstention)
is genuinely above B.Tech norm. It was not enough, because it was defending the
wrong system.

## 2. The finding that reframes everything

**PFF-WM is a deep-learning paper. We implemented one of its five modules.**

Its architecture, from the paper:

1. multi-scale attention module — Conv 3x3/5x5/7x7 -> diagnostic saliency map
2. dual watermark embedding — fragile in wavelet details + semi-robust in DCT
3. **stacked autoencoder detector** — 4 conv layers (64/128/256/512), trained
   *only on authentic watermarked images*, anomaly = reconstruction error
4. **RefineNet localiser** — 3 encoder levels + skips, input
   `Concat(error_map, attention_map, downsample(image))`
5. explainability layer via Grad-CAM on a frozen classifier

We built **module 2 only**. Then we compared our module-2-only numbers against
their five-module system's headline. That is the root cause of the verdict, and
it is a precise, fixable error — not a vague "we need AI".

Their own ablation prices the missing modules exactly:

| configuration | AUC | IoU |
|---|---|---|
| Full PFF-WM | 0.989 | **0.832** |
| minus RefineNet (raw AE error) | 0.989* | **0.770** |
| minus stacked autoencoder | 0.963 | 0.744 |
| minus dual watermark (fragile only) | 0.952 | 0.765 |
| minus attention guidance | 0.971 | 0.801 |

\*reported as 0.989 in the main ablation row block; inconsistency in the
source tables, to be noted if we cite it.

**The RefineNet alone is worth +6.2 IoU points.** That is the module the panel
is asking for, and it is worth more than the attention module and the dual
carrier combined.

## 3. The target table we must be able to print

Verified from the source paper's Tables 2, 4 and 6:

### Detection (CheXpert, 512x512)

| method | acc % | AUC | latency | params |
|---|---|---|---|---|
| SECURENet | 90.8 | 0.951 | 78 ms | 22.1 M |
| TFPDD (no DL) | 91.2 | 0.958 | 12 ms | 0 |
| ConMark | 93.5 | 0.965 | 42 ms | 9.3 M |
| DeepMark | 94.1 | 0.971 | 61 ms | 18.4 M |
| ASFW | 95.2 | 0.978 | 53 ms | 12.7 M |
| **PFF-WM** | **97.6** | **0.989** | **44 ms** | **15.1 M** |
| ours | ? | ? | ? | ? |

### Localisation (LiTS, synthetic lesion insertion)

| method | IoU % | pix acc % | F1 % |
|---|---|---|---|
| SECURENet | 71.2 | 95.1 | 82.3 |
| DeepMark | 75.4 | 96.2 | 85.1 |
| ASFW | 76.1 | 96.5 | 85.6 |
| PFF-WM raw | 77.0 | 96.8 | 86.0 |
| **PFF-WM + RefineNet** | **83.2** | **98.1** | **90.4** |
| ours | ? | ? | ? |

**Beating this requires running on LiTS and CheXpert.** Not ISIC 2018. There is
no honest shortcut: an IoU of 0.994 measured on our own copy-move protocol over
a different corpus is not evidence against 0.832 on LiTS lesion insertion.

Datasets:
- ISIC 2019 — Kaggle, 25,331 images, free, no approval
- LiTS — Kaggle (`andrewmvd/liver-tumor-segmentation`), 131 CT volumes, free
- CheXpert — **requires a Stanford research-use form**. Free but not instant.
  Fallback if it stalls: NIH ChestX-ray14 (Kaggle, free) — must be *disclosed*
  as a substitute, never labelled CheXpert.

## 4. What we build

Three systems, one protocol, one table.

### S0 — classical (we have this)
Keyed fragile QIM over Haar details, no learning. Reproduces at 0.994 IoU on
our ISIC 2018 copy-move protocol. **Keep it: it is the control.**

### S1 — PFF-WM-faithful (the comparison)
Reimplement modules 1, 3, 4 on top of our existing embedder:

```
I  -> attention/knowledge head -> saliency A          (module 1)
I  -> classical keyed embed    -> protected I'        (module 2, ours)
I' -> recover tags             -> error tensor E      (module 3 input)
E  -> stacked AE (authentic-only training) -> anomaly (module 3)
concat(E, A, I'/4) -> RefineNet -> tamper mask        (module 4)
```

This is the system the panel thinks we should have. It is also our baseline.

### S2 — ours (the contribution)
S1 plus the three things no DL paper in this space does:

1. **A key.** Our evidence map is produced by a keyed, training-free binder
   (`tag_i = pad_i xor sel[(sig_i + dc) mod 16]`). Forging a block costs 2^-59
   with the key unknown. A learned embedder has no key: an attacker who
   observes enough input/output pairs trains an inverter. **This is measurable**
   — forge against S1 and against S2 and report the forgery success rate.
2. **Calibrated abstention.** INTACT / TAMPERED / CANNOT_SAY with causal reason
   codes. Every DL paper here outputs a mask and a class; none outputs "I
   cannot tell you, and here is why". Measured as selective risk vs coverage.
3. **Falsification discipline.** The 34 amendments survive as the ablation
   programme — now pointed at the learned components. A-031/A-032/A-033 showed
   our instruments lied to us three times. The same instruments get pointed at
   the RefineNet.

The claim we can then defend:

> "The learned protocol, faithfully reproduced, reaches PFF-WM-class accuracy.
> Adding the keyed prior costs nothing in accuracy and makes forging
> measurable; adding abstention lets the system refuse, which pure-DL
> localisers cannot do. We measure all three deltas."

That is a genuine two-part contribution and it is what the panel is asking for.

## 5. Compute plan (Kaggle free tier)

Free tier: 2x T4 (16 GB each) or 1x P100, **30 GPU-hours/week**, 12 h max
session, 20 GB dataset quota.

| stage | what | est. GPU-h |
|---|---|---|
| data prep (CPU) | ISIC 2019 + LiTS + CheXpert/NIH -> 512x512 PNG, protected set via key | 0 |
| tamper synthesis (CPU) | 6 edit families x N images, masks on disk | 0 |
| E1 attention head | train saliency (or fixed, if we reuse ours) | 2 |
| E2 stacked AE | authentic-only, 20k crops, 40 ep | 3 |
| E3 RefineNet | 512x512, batch 8, 30 ep on 2xT4 DDP | 5 |
| E4 ablations | 5 configs, short runs | 10 |
| E5 S2 keyed variant | 1 run + forgery eval | 5 |
| **total** | | **~25 h** |

Fits in one week with headroom. Long runs go in a Kaggle notebook with
`nohup`-style save-to-dataset checkpoints so a 12 h cut does not lose work.

## 6. Timeline

Realistic for one person, assuming ~15 h/week of work:

| week | deliverable |
|---|---|
| 1 | data on Kaggle, tamper synthesiser ported, S0 numbers reproduced on ISIC 2019 + LiTS |
| 2 | AE detector trained and reported (module 3) |
| 3 | RefineNet trained, first head-to-head table on LiTS |
| 4 | attention module + integration; full S1 = PFF-WM-faithful |
| 5 | S2 keyed variant + forgery experiment |
| 6 | abstention/selective-risk evaluation; ablations |
| 7 | CheXpert (or NIH) detection table; latency + params |
| 8 | write-up, deck, repo |

Eight weeks to a defensible final-review package. Mid-review re-do at week 3-4
with a real partial result (AE + RefineNet on LiTS), which is far stronger than
a promise.

## 7. What this costs us

- **The "zero-training" selling point is gone.** It was never a selling point to
  this panel; it was a liability. The classical layer stays, but as one module.
- **The pure-classical paper is dead.** Do not try to publish the current system
  as a methods contribution. It is a control condition now.
- **Risk of imitation.** If S1 is a faithful reimplementation and S2 does not
  clearly win, we have built PFF-WM from scratch and added a footnote. §4's three
  differentiators must be *measured*, not asserted, or this fails.

## 8. Immediate next actions

1. Decide S1 scope: full reimplementation vs "RefineNet + AE only, skip
   attention" (cheaper, and the ablation says attention is worth only +3.1 IoU
   vs RefineNet's +6.2).
2. Confirm dataset access: LiTS + ISIC 2019 on Kaggle today; start the CheXpert
   form immediately because it is the long-latency item.
3. Get the repo back into a working state — the sandbox copy is currently empty
   (`README.md` only) and GitHub is unreachable, so no existing code can be seen
   or extended.
4. Freeze the new protocol *before* training: the tamper families, the metrics,
   the splits. The one thing that must not repeat is measuring on one protocol
   and citing another.
