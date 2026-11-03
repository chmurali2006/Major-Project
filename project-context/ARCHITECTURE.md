# The architecture, and how it works

**What this document is.** The definitive description of the final architecture:
every stage, the order things happen in, what crosses each boundary, which
constants are load-bearing, and what the system is not allowed to do.

**Its authority.** Where this document and any other disagree, this one is
correct, except for `src/protocol.py`, which wins on anything to do with the
evaluation protocol, and a receipt, which wins on any number. Numbers here cite
ids in `facts.json`; no number is stated here that is not in that file.

**Read with.** `POSTER_CONTEXT.md` for how to *present* this; `DESIGN_REVIEW.md`
for the ten flaws that produced it; `SYNTHESIS_STUDY.md` for the argument in its
original form.

---

## 0. The claim

> A keyed, training-free fragile watermark establishes, at acquisition, that an
> image is unaltered. Verification reads only the container and the key — never
> the original — returns INTACT, TAMPERED or CANNOT SAY with a cause for every
> refusal, and localises the change. A learned reader then refines what the
> keyed channel produces, without ever being able to generate evidence itself.

Two sentences, and the second one is where the entire design risk lives, so it
gets a section of its own.

---

## 1. The principle everything else follows from

> ### The network never generates evidence. It only reads it.

Every suspicious signal entering the learned layers originates in the keyed
channel — arithmetic over a secret the network does not have. The network's job
is to resolve ambiguity in that evidence, which is exactly what hand-tuned rules
do badly (two of ours, A-031 and A-033, failed on their own terms).

This yields three consequences that are not obvious:

1. **Accuracy and security do not trade off.** A better reader reads the same
   unforgeable evidence more carefully. Training cannot make the mark forgeable.
2. **A wrong key produces noise, and the reader has nothing to amplify.** The
   failure is safe by construction, not by a check that could be forgotten.
3. **The question "isn't a learned reader just a learned forger?" has a
   structural answer, not an empirical one.** The reader can weigh evidence; it
   cannot invent it.

The principle is enforced in code, not in prose: verification is **frozen** while
the learned layers train, so the evidence channel cannot move underneath them.

---

## 2. The lifecycle

One asymmetry drives the whole shape: **protect happens once; verify happens
forever.**

```
   ACQUISITION                   ANY LATER MOMENT              OFFLINE, AFTER MANY RUNS
  ┌───────────┐                ┌────────────────┐             ┌──────────────────┐
  │  PROTECT  │ ─ container ─► │     VERIFY     │ ─ receipt ─►│      LEARN       │
  └───────────┘  PNG + chunks  └────────────────┘             └──────────────────┘
    once, at the     metadata     every check                  trained once
    source                        needs only bytes              needs no key
    needs the key                 and the key                   at inference
```

The learned layer is **outside the deployment loop**. Deployed verification is
58.6 ms on a CPU with no model loaded. The learned layer improves verification
on the *next* pass; it is not in the path of the current one. That is a
deliberate deployment property, not a limitation to be apologised for.

---

## 3. PROTECT — how marking works

**Input** `image 512×512×3`, `key`, `image_id`.
**Output** a PNG that is visually indistinguishable and carries a verifiable mark.

```
  RGB
   │
   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ 1  Colour transform                        split_rct()        │
 │    RGB → luma 512² + Cb/Cr 256². Exactly invertible.          │
 │    The mark lives in luma only; chroma is never touched.      │
 └──────────────────────────────────────────────────────────────┘
   │ luma
   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ 2  Semi-robust carrier              RobustCarrier.write()     │
 │    DCT band u+v ∈ [3, 6], 22 coefficients per block.          │
 │    Address-keyed signs, β₀ = 8.                               │
 │    WRITTEN FIRST, so Carrier A cannot disturb it.             │
 │    Purpose: survive JPEG, so the verifier can separate        │
 │    "lost its mark to compression" from "someone edited it".   │
 └──────────────────────────────────────────────────────────────┘
   │
   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ 3  Range fitting                          fit_block_luma()    │
 │    Per-block legal gamut window.                              │
 │    A block that cannot host the mark unshifted is REFUSED     │
 │    and transmitted verbatim — never clipped.                  │
 │    ⚑ The refusal is recorded now and re-derived by the        │
 │      verifier from the pixels later. It becomes the reason    │
 │      code capacity_refusal, not a silent gap.                 │
 └──────────────────────────────────────────────────────────────┘
   │
   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ 4  Tag binder                                  Binder.tags() │
 │    digest = f(key, image_id, block's own detail coefficients) │
 │    tag    = key ⊕ address ⊕ digest ⊕ block mean               │
 │    60 bits per block. One bit per Haar detail slot.           │
 └──────────────────────────────────────────────────────────────┘
   │
   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ 5  Fragile carrier                   FragileCarrier.write()   │
 │    QIM in INTEGER Haar detail coefficients.                   │
 │    Δ = 8, residual amplitude ±Δ/4.                            │
 │    60 slots per block · 4096 blocks · written LAST (A-002).   │
 └──────────────────────────────────────────────────────────────┘
   │
   ▼
 ┌──────────────────────────────────────────────────────────────┐
 │ 6  Container                                   png_bytes()   │
 │    PNG + metadata chunks: image_id · key_id · declared size.  │
 │    The key_id is what lets a mismatched key ABSTAIN instead   │
 │    of accusing.                                               │
 └──────────────────────────────────────────────────────────────┘
```

### The three load-bearing decisions

**The tag is bound to address *and* content.** This is the security property in
its entirety:

| attack | why it fails |
|---|---|
| paste a block from elsewhere in the same image | it carries the tag of its **old address** |
| edit a block's pixels | it carries the tag of its **old content** |
| fabricate a region from scratch | requires computing a valid tag, which requires the key |
| re-mark a forged image with a different key | `key_id` mismatch → CANNOT SAY, never TAMPERED |

**Integer Haar, not float.** The quantisation index is *exactly* recoverable
after marking. Verification does not approximate the embedded value; it reads
back the integer that was written. This is why localisation is at 0.9936 block
IoU rather than in the low 0.9s — the residual is a step function, not a noisy
estimate.

**Carrier A is written last.** Amendment A-002 fixes the order, because writing
the fragile carrier before the semi-robust one destroys it. This is the kind of
detail that is invisible in a diagram and fatal in practice.

### Constants

| constant | value | provenance | role |
|---|---|---|---|
| `IMAGE_SIZE` | 512 | chosen | working resolution |
| `BLOCK` | 8 | chosen | decision granularity |
| `GRID` | 64 | derived | `IMAGE_SIZE / BLOCK` |
| `N_BLOCKS` | 4 096 | derived | `GRID²` |
| `N_DETAIL` | 60 | derived | Haar detail slots per block |
| `DELTA_F` | 8.0 | chosen | QIM step for the fragile carrier |
| `OFFSET_F` | Δ/4 | derived | residual amplitude |
| `TAG_BITS` | 60 | derived | one bit per detail slot |
| `BETA0` | 8.0 | chosen | semi-robust embedding strength |
| `LAMBDA_REGION` | 0.0 | **measured** | region weighting bought nothing — A-018 |
| `DCT_LO / DCT_HI` | 3 / 6 | chosen | semi-robust frequency band |
| `TEXTURE_MIN` | 3.0 | chosen | flatness threshold for rung 3 |
| `GATE_ENABLED` | False | **measured** | gating cost more than it bought — A-007 |

Provenance vocabulary — `LIT` (from a paper), `CHOSEN` (a decision), `DERIVED` (a
consequence), `MEASURED` (a value that was tested and kept or rejected) — is
inherited from `dev`'s `config.py` and is the reason 34 amendments could be
recorded without contradicting each other.

---

## 4. VERIFY — how reading works

**Input** container bytes + key. **Nothing else.**

> This is structurally enforced, not promised: `pipeline.verify()` has no
> parameter through which an original image or a mask could arrive. The
> difference between watermarking and image differencing is exactly this
> signature.

```
  container
     │
     ▼
 ┌────────────────────────────────────────────────────────────────┐
 │ A  Metadata gate                                   verify()    │
 │    key_id absent or mismatched → CANNOT SAY (key_mismatch).    │
 │    A wrong key is NEVER reported as tampering.                 │
 └────────────────────────────────────────────────────────────────┘
     │
     ▼
 ┌────────────────────────────────────────────────────────────────┐
 │ B  Read both carriers        FragileCarrier.read() · .score()  │
 │                                                                │
 │    Carrier A  ──►  δf   = tag disagreement   (fragile, 4096)   │
 │    Carrier B  ──►  δsr  = semi-robust error  (survives JPEG)   │
 │    survival   ──►  fraction of the 60 slots still readable     │
 └────────────────────────────────────────────────────────────────┘
     │
     ▼
  evidence  E (64×64), S (64×64)     ← the keyed channel
     │
     ▼
 ┌────────────────────────────────────────────────────────────────┐
 │ C  Decision ladder                            ladder.classify() │
 │    4096 blocks, decided independently                          │
 │                                                                │
 │    1  trip table     δf > τf ⇒ broken; δf > τ_strong ⇒ decisive │
 │                      decisive evidence stands alone, or a      │
 │                      single 8×8 paste is censored              │
 │    2  neighbours     weak evidence accepted only if neighbours │
 │                      agree — applied to WEAK EVIDENCE ONLY, so │
 │                      small edits still localise                │
 │    3  texture        flat block ⇒ may have been refused at     │
 │                      embed time ⇒ capacity_refusal, not accused│
 │    4  erasure        a normalised correlation still scores 1.0 │
 │                      on a DELETED mark; the survival test      │
 │                      catches it, a lone erased block needs     │
 │                      support                                   │
 │    5  attenuation    median tag evidence low ⇒ routine_handling│
 │                      ≥12 scattered 3×3 islands ⇒ routine_      │
 │                      handling: a codec, not surgery            │
 └────────────────────────────────────────────────────────────────┘
     │
     ▼
  per-block verdict   INTACT · TAMPERED · CANNOT SAY
  with a cause        routine_handling · capacity_refusal ·
                      geometry_change · evidence_conflict · key_mismatch
```

### Why it is a ladder and not a threshold

Each rung answers a *different question*, and each failure produces a *different
cause*. A threshold pipeline can only answer "how large is the residual". The
ladder can distinguish:

- *the mark is gone because the block could never hold one* — a property of the
  image, known at embed time
- *the mark is gone because a codec destroyed it* — benign, and detectable by
  its global signature
- *the mark is gone because someone deleted it* — malicious, and detectable
  because deletion leaves the correlation intact at 1.0
- *the mark disagrees with the content* — tampering
- *the key is wrong* — a question, not an accusation

That distinction is the second contribution of this work. No system in the
comparison set reports a cause with a refusal.

### Invariants

1. Verify never receives the original image. (Enforced by signature.)
2. A key mismatch yields CANNOT SAY, never TAMPERED. (Enforced by the gate.)
3. A block that was refused at embed time is not subsequently accused.
   (Enforced by re-deriving the refusal from the pixels.)
4. Every verdict carries a cause. A cause-free verdict is a bug.

---

## 5. LEARNED REFINEMENT — what it does, and what it must not do

This is the layer that does not exist yet. Its position in the flow is the part
worth getting exactly right.

```
  container ──► keyed evidence   (10 ch @ 64×64) ──┐
                E · surv · peak · mag ·            │
                band_LH1 · HL1 · HH1 · LH2 · HL2 · HH2
                                                   │
  container ──► SaliencyNet  (Conv 3×3 / 5×5 / 7×7)┤
                                                   ├──►  PixelRefineNet
  container ──► degradation (4 scalars)  ──────────┤
                jpeginess · noise σ ·              │
                sharpness · clipping               │
                                                   │
  container ──► image at full 512² ────────────────┘
                          │
                          ▼
       ┌──────────────────────────────────────────────────┐
       │  stem    cat(image 3, saliency 1, degrade 4) = 8  │
       │          512 → 256                    w          │
       │  d2     pool → 128                    2w         │
       │  d3     + evidence@128                4w         │
       │  d4     pool + evidence@64            6w         │
       │                                                  │
       │  u4     64 → 128   skip s3                       │
       │  u3     128 → 256  skip s1                       │
       │  u2     256 → 512  no skip                       │
       └──────────────────────────────────────────────────┘
                │                          │
                ▼                          ▼
        pixel_logits 512²            block_logits 64²
        ─────────────────            ─────────────────
        LOCALISATION                 VERDICT + ABSTENTION
        (the ladder cannot            (block-granular by nature,
         express finer than 8 px)     so head and grid agree)
                │                          │
                └──── consistency loss ────┘
                          │
                          ▼
                  cls_head  →  three-way
                  INTACT / TAMPERED / CANNOT SAY
```

**Evidence enters at 64² and is upsampled *nearest*, deliberately.** The
evidence has no sub-block detail to preserve, and nearest-neighbour keeps block
edges crisp — bilinear would invent a gradient that is not in the data. The
projection is applied once at 64² rather than at 512²: projecting at full
resolution would be 64× the work for no extra information.

### What the learned layer adds, and what it does not

It does **not** replace the ladder's verdict. It cannot: on the blocks the ladder
decides, it is right 99.99 % of the time. It adds two things the classical layer
is *structurally* unable to do:

| | why the classical layer cannot | what the learned layer does |
|---|---|---|
| **resolution** | the grid is 8 px; a finer boundary is inexpressible | `pixel_logits` at 512² breaks the quantisation floor (facts C-01) |
| **coverage** | rungs 3–5 abstain when evidence is weak | weighs ambiguous evidence and converts CANNOT SAY into a decision |

Which is why the learned layer is scored on **selective risk at coverage**, not
on raw IoU alone. A system that answers more often *and* answers correctly is
worth more than one that is perfect on 90 % and silent on 10 %. That is also why
the headline comparison is **C0 versus C8** — the classical control against the
assembly — rather than "ours versus theirs".

### The ceiling that motivates all of it

A 64×64 decision grid cannot express a boundary finer than 8 px. Compute what a
**flawless** block classifier scores against an exact pixel mask (facts C-01):

| lesion radius | 8 | 16 | 24 | **32** | 48 | 64 | 128 |
|---|---|---|---|---|---|---|---|
| best possible pixel IoU | 0.513 | 0.692 | 0.757 | **0.809** | 0.854 | 0.889 | 0.937 |

The published localisation bar is 0.832 (fact P-02, on LiTS). At radius 32, a
system with **zero errors** scores 0.809. The gap is architectural. No amount of
training closes it, which is why the pixel head exists — and why the published
+6.2 IoU from refinement is not "a better network" but *reading at full
resolution*, i.e. breaking this floor.

A block-aligned square paste scores 1.000 on the same test (fact C-02). Both
numbers must travel together or the ceiling reads as an excuse.

---

## 6. TRAINING — the flow, and what is frozen

```
  authentic images
        │
        ▼  PROTECT (key K₁)  ──────────────────────► watermarked originals
        │
        ├──► tamper families T1…T5 ──► tampered image + MEASURED mask
        │                              (pixel difference, never a declared rect)
        ├──► benign families B1/B2 ──► unchanged image
        │                              (the system must stay silent)
        ▼
     VERIFY  ──►  E, S, D          [FROZEN — precomputed once, never updated]
        │
        ▼
  PixelRefineNet
        │
        ▼
  total_loss =  block_mask  +  1.0 · pixel_mask
                          +  0.5 · consistency
                          +  0.5 · classification
```

Two structural choices:

**The autoencoder is trained only on authentic watermarked images.** Anomaly is
reconstruction error; it never sees a tamper during training. That is what makes
it able to flag a family invented after deployment — the one-class discipline,
borrowed precisely because it beats a supervised classifier on unseen forgery.

**Verification is frozen during training.** The evidence channel does not move.
This is what makes §1 enforceable in code rather than a promise in a paper.

**One loss function for every head.** `total_loss` returns all four components
and the tests assert each is non-zero and that every parameter receives a
gradient. This exists because it already went wrong once: v1 trained the pixel
branch alone, so the block head and classifier received `grad=None` and would
have looked trained while being random. Found by a test, not by inspection.

---

## 7. EVALUATION — the flow that decides whether any of it counts

```
  protocol written as CODE ──► frozen ──► [ nothing changes after this line ]
   src/protocol.py
        │
        ├── C0   classical only ........................... the control
        ├── C1   + one-class AE ........................... attribution
        ├── C2   + RefineNet
        ├── C3   + AE + RefineNet (no attention)
        ├── C4   + attention (full reproduction)
        ├── C5   + degradation conditioning
        ├── C6   + segmentation formulation
        ├── C7   + three-way head
        ├── C8   full synthesis ........................... the assembly
        ├── C9   C8 minus the key ......................... price of security
        ├── C10  C8 trained K₁, tested K₂ ................. key leakage
        └── C11  C8 on a held-out tamper family ........... negative transfer
        │
        ▼
   select on VALIDATION ──► open TEST once ──► print every row, incl. losses
        │
        ▼
   gates, fixed before any run:
     coverage ≥ 0.90        or the configuration is disqualified
     re-key drop ≤ 0.05 IoU or it is a security failure, not an accuracy one
     test opened once
```

**C9, C10 and C11 are why this is not a reproduction.** They answer *"why not
simply do what the reference paper did"* with measurements instead of adjectives.

**C10 is the test no published system in this field runs.** Train on one key,
evaluate on another. If the network learned the *key* rather than the *evidence*,
this is the only thing that finds out — and the failure is a security failure
that no accuracy number would reveal.

**The coverage gate is the anti-gaming rule.** A configuration whose classical
layer refuses more than 10 % of blocks is disqualified whatever its IoU. It has
not localised; it has abstained its way to a small denominator.

---

## 8. The interfaces

What crosses each boundary, and what is not allowed to.

| boundary | carries | must never carry |
|---|---|---|
| image → PROTECT | pixels, key, image_id | — |
| PROTECT → container | PNG + `{image_id, key_id, size}` | the key, the mask, the original |
| container → VERIFY | bytes + key | the original image, a tamper mask |
| VERIFY → consumer | per-block verdict + cause | a verdict without a cause |
| VERIFY → LEARN | `E`, `S`, `D`, image | any ground truth |
| LEARN → consumer | pixel mask, block mask, three-way class | new evidence |

The last row is the principle of §1 stated as an interface rule.

---

## 9. Status of each layer

Three states. Never blur them.

| layer | state | evidence |
|---|---|---|
| keyed protect, verify, three-way verdict | **built and measured** | 86 tests; receipt `isic-full-v8`; 12 970 images; facts M-01…M-07 |
| protocol, metrics, tamper synthesis, evidence channel | **built** | `src/protocol.py`, `src/metrics.py`, `src/tamper.py`, `src/evidence.py` |
| learned refinement (AE, PixelRefineNet, saliency, three-way head) | **built and unit-tested, never trained** | forward pass verified; gradients asserted; no result |

The third row is why the matrix is labelled *designed, not run*. Any document,
figure or slide that omits that label is claiming twelve results that do not
exist.

---

## 10. What `dev` contributes, honestly

Under the earlier framing `dev` was the product and its number was the
deliverable — and under that framing the panel's verdict was correct. Under this
architecture it is four things, none of which can be produced any other way:

| `dev` asset | role now | replaceable? |
|---|---|---|
| keyed evidence channel (carriers, binder, container) | the substrate the learned layer reads | **no** |
| three-way verdict + reason codes | one of the two genuine contributions | **no** |
| the measured C0 result | the control in the headline C0-vs-C8 comparison | **no** |
| 34 amendments, receipts with `code_dirty: false` | the credibility that "frozen before training" inherits | **no** |
| semi-robust Carrier B | an input feature that survives JPEG, not a decision rule | needs re-purposing |
| `config.py` provenance discipline | the habit that made 34 amendments possible | **no** |

**Written off:** the headline number *as a headline* (wrong corpus, wrong
granularity); much of the hand-tuned threshold work (the learned reader exists to
replace it); any LiTS/CheXpert planning (scope decision); ISIC 2018 metadata
handling (cheap to port).

**The ledger is asymmetric: the system is ~85–90 % reusable; the tuning labour
inside it is roughly half.**

The one thing that would have made it actual waste is if the response to the
panel had been to rebuild as a five-module deep network and discard the keyed
embedder — a reproduction with no contribution, having thrown away the only two
parts that were ours. This architecture keeps both.

---

## 11. Failure modes, and the test that finds each

| failure | mechanism | test that catches it |
|---|---|---|
| negative transfer | the reader overfits training families and mis-weights evidence on unseen ones | C11, held-out family |
| evidence starvation | the classical layer refuses too many blocks, the reader learns nothing | coverage gate 0.90 |
| key leakage through the reader | the network memorises the keyed pattern for the training key | C10, re-key |
| capacity mismatch | losing to a 15.1 M model while running 1.5 M reads as an excuse | width as config; headline at matched capacity |
| a head that receives no gradient | loss covers only some heads; the rest look trained and are random | `total_loss` returns all parts; tests assert gradients |
| a claimed component passed as zeros | a tensor was literally `torch.zeros` at both call sites | non-constant output test on `SaliencyNet` |
| block-locality inversion | `reshape(ny,k,nx,k)` collapses axes in the wrong order | perturb one block, assert exactly one changes |
| an unfalsifiable claim | a comparison across incompatible corpora | the fact base; `forbidden` X-01…X-09 |

The middle three already happened and are recorded because they are the ones a
reader would not believe without being told.

---

## 12. Open questions — do not close them with a guess

These determine whether a head-to-head comparison is valid at all:

1. Is the published 0.832 a per-image mean or a pooled pixel ratio?
2. What is the lesion-size distribution in their synthetic-tumour protocol?
3. Is their localisation ground truth the tumour mask or the paste rectangle?
4. Is their detection accuracy per-image or per-region, and at what class balance?
5. Are their benign conditions applied before or after embedding?

Until these are settled from the source's full text or code, the only defensible
statement about the published bar is: *we reproduce the protocol; our number on
their corpus and their tamper family will be reported beside theirs, with the
ceiling attached.*

The highest remaining **design** risk, as opposed to an open question, is that
the semi-robust carrier is currently approximated by four hand-built degradation
scalars. The reference ablation prices its carrier at −0.067 IoU when removed —
more than its attention module. A carrier designed to survive JPEG is a strictly
stronger signal than an estimate of JPEG quality, and `dev` is ahead of the
sandbox branch on it.

---

## Appendix A — constants, by provenance

| constant | value | provenance | note |
|---|---|---|---|
| `IMAGE_SIZE` | 512 | CHOSEN | |
| `BLOCK` / `GRID` | 8 / 64 | CHOSEN / DERIVED | the decision granularity, and the source of fact C-01 |
| `N_BLOCKS` | 4 096 | DERIVED | `GRID²` |
| `N_DETAIL` / `TAG_BITS` | 60 / 60 | DERIVED | one tag bit per Haar detail slot |
| `DELTA_F` / `OFFSET_F` | 8.0 / Δ÷4 | CHOSEN / DERIVED | QIM step and residual amplitude |
| `BETA0` | 8.0 | CHOSEN | semi-robust strength |
| `LAMBDA_REGION` | 0.0 | **MEASURED** | region weighting bought nothing — A-018 |
| `DCT_LO / DCT_HI` | 3 / 6 | CHOSEN | semi-robust band |
| `TEXTURE_MIN` | 3.0 | CHOSEN | rung-3 flatness threshold |
| `GATE_ENABLED` | False | **MEASURED** | cost exceeded benefit — A-007 |
| `N_RICH` | 10 | DERIVED | evidence channels, order fixed by `RICH_CHANNELS` |
| `N_DEGRADE` | 4 | CHOSEN | jpeginess, σ, sharpness, clipping |
| loss weights | block 1 · pixel 1 · consistency 0.5 · cls 0.5 | CHOSEN | one objective, four heads |
| `width` | 16 (0.22 M) · 32 (1.54 M) · 96 (13.74 M) | CHOSEN | capacity is a config (fact M-15) |

Constants above `N_RICH` are read from `dev` at `a794cef`, `src/config.py`.

## Appendix B — file map

| path | holds |
|---|---|
| `src/protocol.py` | the frozen protocol: corpora, splits, families, metrics, bars, C0–C11, gates |
| `src/metrics.py` | IoU/Dice/F1/detection, `block_ceiling`, `selective_risk`, `aurc`, `stratified_iou` |
| `src/tamper.py` | the eight families; masks measured by differencing |
| `src/evidence.py` | the keyed channel; `read_rich` → 10 channels |
| `src/degradation.py` | the four scalars |
| `src/models.py` | `OneClassAE`, `RefineNet`, `FusionNet`, `SaliencyNet`, `PixelRefineNet`, `total_loss` |
| `src/isic_meta.py` | layout detection, lesion grouping, stratification |
| `docs/poster/architecture.pdf` | the figure, vector |
| `docs/DESIGN_REVIEW.md` | the ten flaws and their measurements |
| `project-context/facts.json` | every number, with provenance and status |
