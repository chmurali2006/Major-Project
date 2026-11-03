> **Historical / pre-audit material.** This file is not evidence for the current audited recipe. See root `VERIFICATION.md` and use fresh measured receipts for submission. In particular, any-overlap block IoU is not a universal ceiling.

# The synthesis study

**Bringing the best finding from each work into one system, and proving on a
shared frozen protocol that the assembly beats every constituent.**

Draft 2026-10-24. Supersedes `DL_PIVOT_PLAN.md` (kept for the compute plan).

---

## 1. Thesis

Every paper in this space solves one sub-problem well and the others badly.

PFF-WM has the best *localiser* and a weak *security* story.
WAM has the best *formulation* and no key.
OmniGuard has the best *degradation handling* and the heaviest model.
The post-quantum DCT paper has the best *three-way decision* and a crude mask.
We have the best *evidence* and no learned refinement.

No paper states the problem as a decomposition. Each one optimises the whole
pipeline end-to-end and reports an aggregate, so the field cannot say which
component is carrying the result. PFF-WM is the only one that even prices its
own parts — and its own table shows **the RefineNet is worth more than the
attention module and the dual carrier combined**.

So the study is not "we added deep learning". It is:

> Decompose tamper detection into eight sub-problems. Take the measured best
> answer to each. Assemble. Measure the assembly against every constituent on
> one frozen protocol. Report which components survive and which do not.

A panel cannot call a factorial ablation with a held-out split "childish".

---

## 2. The map: best finding per sub-problem

Every number below is quoted from the source, not estimated.

| # | sub-problem | best finding | from | evidence it is best | what it beats |
|---|---|---|---|---|---|
| 1 | where to spend embedding energy | attention-weighted strength β on a diagnostic saliency map | PFF-WM §3.2 | +3.1 IoU, +0.018 AUC | uniform β |
| 2 | what signal the verifier reads | keyed QIM residual in **integer** Haar details — exact, address-bound, content-bound | ours (A-024) | 180/180 blocks forged under address-only binder vs 0/180 under keyed | learned embedder: no key, invertible |
| 3 | is anything wrong at all | one-class stacked AE trained **only on authentic watermarked images** | PFF-WM §3.3 | +0.026 AUC over fragile-only, +0.037 over fixed threshold | thresholding δf and δsr independently |
| 4 | turn an error map into a mask | RefineNet, 3 encoder levels + skips, input `concat(E, A, ↓I)` | PFF-WM §3.4 | **+6.2 IoU** (0.770 → 0.832) | raw threshold on AE error |
| 5 | how to formulate the output | **segmentation**, not image-level classification | WAM (ICLR 2025) | >85% mIoU on 10%-area watermarks | scalar detection |
| 6 | survive routine processing | degradation-aware extraction | OmniGuard (CVPR 2025) | localises under AIGC/compression | degradation-blind extraction |
| 7 | benign vs malicious vs unknown | residual-code features → classifier | post-quantum DCT 2026 | 98.1% three-class accuracy | binary tamper/no-tamper |
| 8 | what to do when evidence is weak | calibrated abstention with causal reason codes | ours (A-021, A-031, A-032) | measured coverage/selective-risk curve | forced binary answer |

Two rows (2, 8) are ours. Six are borrowed. That ratio is the honest shape of a
synthesis: mostly assembly, with two components that no published system has.

**Row 2 is the load-bearing one.** It is the only row where our contribution is
not a refinement of someone else's idea but a property nobody else has: the
evidence map is keyed, so an attacker cannot construct a valid mark for content
they fabricated. Every DL system in this table is invertible in principle — an
attacker with the model and enough image pairs trains the inverse.

## 3. The fused architecture

```
                     ┌─────────────── keyed path (ours) ───────────────┐
  received image ──► │ integer Haar → QIM residual → tag compare        │──► E  (error map, 64×64)
                     │                           → evidence  (slots ok) │──► S  (survival map)
                     └─────────────────────────────────────────────────┘
                                     │
  received image ──► degradation estimator (JPEG q, σ, resample) ──────► D  (3 scalars, broadcast)
  received image ──► attention / saliency head ────────────────────────► A  (64×64)
                                     │
                                    ▼
                    ┌───────────────────────────────────┐
                    │  RefineNet  (3 levels + skips)     │
                    │  in: concat(E, S, A, D, ↓I)        │
                    └───────────────────────────────────┘
                          │                    │
                          ▼                    ▼
                   mask logits (64×64)   one-class AE anomaly score
                          │                    │
                          └────────┬───────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │ decision head (3-way)         │
                    │ INTACT / TAMPERED / CANNOT_SAY│
                    │ + reason code                 │
                    └──────────────────────────────┘
```

**The architectural principle that makes this defensible:**

> The network never *replaces* the keyed evidence. It *reads* it.

E is produced by arithmetic the attacker cannot influence without the key. The
network's job is to resolve ambiguity in E — which is exactly the thing a
hand-tuned threshold does badly (our own A-031 and A-033 were both failures of
hand-tuned rules on E). This is why the fused system can be strictly better than
either part, and why it keeps the security property: no key, no forgeable mark,
no matter how good the network is.

That principle is also the answer to the obvious attack on the whole idea —
"isn't a learned reader just a learned forger?" No: the reader cannot invent
evidence, it can only weigh it.

## 4. Can the assembly be worse than a constituent? Yes — here is when

Being honest about this is what separates a study from a demo. Three failure
modes, each with a test:

| failure mode | why it happens | how we detect it |
|---|---|---|
| negative transfer | the learned reader overfits to training tamper families and mis-weights E on unseen ones | held-out **tamper family**, not just held-out images |
| evidence starvation | if the classical carrier refuses too many blocks, E is empty and the net learns nothing | report coverage alongside every IoU; a config with coverage < 0.9 is disqualified |
| key leakage through the reader | if the net memorises the keyed pattern for the training key, it fails on a fresh key | **re-key test**: train on key K₁, evaluate on K₂ |

The re-key test is the one no published system runs, and it is the sharpest
possible check on whether the learned path has quietly learned the key. Run it
at every evaluation, not once.

## 5. The frozen protocol

Frozen before training. Any change is an amendment, disclosed, with the old
number retired — the same discipline that produced 34 amendments, now applied to
a bigger system.

**Corpora — scope decision, 2026-10-24: ISIC 2019 only.**

- **ISIC 2019 — 25,331 images — the only corpus in this phase.** Train,
  validate and test. Free on Kaggle, no approval. It is one of the three corpora
  PFF-WM evaluates on, so the run is on shared ground.
- LiTS — **deferred.** 131 CT volumes. PFF-WM's 0.832 IoU was measured here, so
  this is the only corpus that unlocks a localisation comparison.
- CheXpert — **deferred.** PFF-WM's 97.6% detection was measured here, so this
  is the only corpus that unlocks a detection comparison. Needs a Stanford form.

What the deferral costs, stated once so it cannot surface later as a surprise:
**no number from this phase can be placed in their Table 2 or Table 4.** Every
external comparison is stated as "this work's protocol, on a corpus both systems
can run on". The result that stands without any external corpus is the internal
**C0 vs C8** comparison — the contribution of the learned half — and that is
therefore the headline.

Two things an ISIC-only study must carry to be worth more than one number:

1. **Per-diagnosis strata.** The eight ISIC categories behave differently.
   A flat naevus and a textured carcinoma lose their mark in different places,
   and an aggregate IoU hides precisely the effect a reviewer looks for.
2. **Per-area strata with the block ceiling.** A perfect block detector tops out
   at 0.809 pixel IoU on a radius-32 lesion, so an absolute IoU says nothing
   without the target size beside it.

**Tamper families** — 8, each a function producing `(image, mask)`, mask from
measured pixel difference, never a declared rectangle:

| id | family | note |
|---|---|---|
| T1 | copy-move, 8/16/32/64 px | our existing conditions 1-6 |
| T2 | lesion insertion (synthetic tumour paste) | **the LiTS protocol PFF-WM used** |
| T3 | lesion removal by inpainting (Telea) | our condition 22 |
| T4 | burned-in text | our condition 21 |
| T5 | splicing from a *different* image | the gap we never measured |
| T6 | GAN/substitution edit | out of scope unless a generator is available — declared, not faked |
| B1 | benign: JPEG 90/75/50, σ=1, resize 90% | must stay silent |
| B2 | benign chain | must abstain, never accuse |

**Splits** — by *patient where available*, never by image. Train / val / test.
Test is opened once.

**Metrics** — IoU, Dice, pixel accuracy, pixel F1, image-level detection
accuracy, benefit-at-0.5, block F1, and **selective risk at coverage** for the
abstention path. Every number from a receipt.

**Bars** — PFF-WM's published: 97.6% detection, 0.832 IoU, FPR < 0.5%, 44 ms,
15.1 M params. We report params and latency alongside, because beating an IoU
with a 100 M model is not beating it.

## 6. The experiment matrix

This is the study. Twelve configurations, one protocol, one table.

| row | configuration | isolates |
|---|---|---|
| C0 | classical only (our current system) | the control |
| C1 | + AE detector | row 3 |
| C2 | + RefineNet, no AE | row 4 |
| C3 | + AE + RefineNet (PFF-WM-faithful, no attention) | rows 3+4 |
| C4 | + attention (full PFF-WM reproduction) | row 1 |
| C5 | + degradation-aware conditioning | row 6 |
| C6 | + segmentation formulation | row 5 |
| C7 | + three-way decision head | row 7 |
| **C8** | **full synthesis** | all |
| C9 | C8 with the key removed | row 2 — what security costs |
| C10 | C8 trained on K₁, tested on K₂ | key-leakage test |
| C11 | C8 on the held-out tamper family | negative transfer |

C9 and C10 are the two rows that make this a contribution rather than a
reproduction. They answer "why not just do what PFF-WM did" with measurements
instead of adjectives.

## 7. What "guarantee the best" can honestly mean

It cannot mean a theorem. It can mean something a panel accepts:

1. **The protocol is frozen before training**, so the reported number is not the
   best of many tries.
2. **Every constituent is in the table**, so "best" is a comparison, not a claim.
3. **The test split is opened once**, and the selection was made on validation.
4. **The losing configurations are printed.** If C4 beats C8, we report C4.

The guarantee is that the *procedure* cannot produce an inflated number. That is
what a falsification record buys, and it is exactly the asset the panel did not
see because it was attached to the wrong system.

What it must NOT become: "we achieve SOTA". On a shared protocol we can say
"we outperform PFF-WM on LiTS localisation at equal params" *if and only if* the
number comes back that way. Otherwise we say what came back.

## 8. Cost

| item | estimate |
|---|---|
| data prep + tamper synthesis (CPU) | 2 days |
| C1–C2 (AE, RefineNet) | 8 GPU-h |
| C3–C6 (attention, degradation, segmentation) | 12 GPU-h |
| C7–C8 (decision head, full) | 6 GPU-h |
| C9–C11 (three transfer tests) | 9 GPU-h |
| ablations + reruns | 10 GPU-h |
| **total** | **~45 GPU-h** — 1.5 weeks of Kaggle free tier |

Wall clock: **6–8 weeks** for one person at ~15 h/week, which is what a
B.Tech final review needs anyway.

## 9. Non-negotiable sequencing

1. Repo restored to the sandbox — nothing can be built on an empty tree.
2. Frozen protocol committed **before** the first training run.
3. ISIC 2019 attached on Kaggle. LiTS and CheXpert are deferred; nothing else
   is needed for this phase.
4. C0 reproduced on the new corpora — if our own classical number does not
   travel from ISIC 2018 to ISIC 2019/LiTS, that is the first finding and it
   changes the story.
5. Only then, training.

Step 4 is the one people skip. If the classical system's IoU drops on LiTS,
everything downstream is measured against a different baseline and the whole
comparison shifts.
