# Poster context — the whole project, in a form you can generate from

**What this file is.** The complete context for this project: what it is, what it
has actually measured, what it is going to do, and how each piece becomes a
poster panel. Written so that a person — or a tool — can produce a poster, a
slide deck, an abstract or a viva answer *from this file alone*, without
re-deriving anything and without inventing a number.

**What this file is not.** It is not a second copy of the results. Every number
here has an id and lives in `facts.json` beside it, with its provenance and a
status. If a number is not in `facts.json`, it does not exist and must not be
printed. That rule is the whole point: this project's credibility rests on the
claim that no figure was ever rounded, borrowed or remembered.

**Read order.** §1 for the thesis. §4 for the panels you will actually set.
§5 for the plan behind them. §6 before you open a layout tool.

---

## 0. The generation contract

Anything generated from this file obeys these six rules. They are not stylistic.

1. **Print only facts with status `verified`, `computed` or `published`.**
   `planned` may appear, but only under a heading that says *planned*.
   `unverified` and `forbidden` never appear.
2. **Every number carries its corpus.** `0.9936` alone is a lie by omission;
   `0.9936, block-level, ISIC 2018` is a fact. The three corpora in play —
   ISIC 2018 (what we measured), ISIC 2019 (what we are moving to), LiTS and
   CheXpert (what the published bars come from) — must never be mixed in one
   column.
3. **A ratio is printed with its denominator.** `12 969 / 12 970`, not
   `99.99 %`.
4. **An IoU is printed with its granularity and, when pixel truth exists, its
   ceiling.** `0.9936 block-level` and `0.809 at radius 32` are the same
   sentence.
5. **Losing results are printed.** The JPEG Q100 envelope failure is on the
   poster. Removing it is the one edit that would make the poster dishonest.
6. **Nothing is described as achieved that has not run.** The learned half is
   implemented and unit-tested. It is not trained, not evaluated, and not a
   result.

---

## 1. The project in three lengths

**25 words.**
A keyed, training-free fragile watermark that localises image tampering and
refuses to answer when it cannot — measured on 12 970 images.

**80 words.**
Medical images are edited and re-submitted: a lesion removed before a claim, a
mole retouched before publication. This work marks a 512×512 image at
acquisition with a mark bound to a secret key, the pixel address and the
content, so that any region pasted or altered no longer carries a consistent
mark. Verification returns INTACT, TAMPERED or CANNOT SAY with a reason code,
localises the change to an 8×8 block, and never needs the original image.

**150 words — the version a panel hears first.**
Published systems in this area optimise one component each and report a single
aggregate, so the field cannot say which component is carrying the result. This
project does the opposite. It freezes the protocol in code before any run, prices
every component against the others on one split, and prints the configurations
that lose. Two things in it are not reproductions. The evidence channel is keyed
and training-free, so a mark cannot be forged — and that is measured in a control
that removes the key, not asserted. And the verifier is allowed to abstain, with
a causal reason code for every refusal — something no system in the comparison
set does. Underneath both is an arithmetic result that reframes the published
gap: a perfect 8×8-block classifier cannot score above 0.809 pixel IoU on a
radius-32 lesion, which is below the 0.832 bar, at zero errors.

---

## 2. The title block

| field | content |
|---|---|
| title | **A Fragile Watermarking for Medical Image Tamper Detection** |
| subtitle (optional) | Keyed, training-free, with tamper localisation and honest abstention |
| author | *the user's name* — leave a placeholder, do not invent an affiliation |
| affiliation | Department of Electronics and Communication Engineering |
| takeaway line | **The gap to the published bar is partly arithmetic, not learning.** |

The takeaway line is the poster. Everything else supports it. If only one
sentence survives at A3 thumbnail size, it is that one.

---

## 3. The argument the poster makes

A poster is not a paper shrunk. It is one argument with evidence arranged around
it. This poster's argument has four moves:

**Move 1 — the problem is real and specific.** Not "medical images are
important". A lesion disappears before a claim; a mole is retouched before a
publication. The question a clinician or an insurer actually asks is *where* the
image changed, and the honest answer is sometimes *I cannot tell*.

**Move 2 — published work is strong but silent on two things.** Every system in
the comparison set is a learned embedder, therefore invertible in principle by an
attacker with the model; and every one of them returns a binary verdict rather
than an abstention. Neither is a criticism of their accuracy — it is a statement
about what they do not report.

**Move 3 — the surprising result.** The published localisation bar (0.832) is not
reachable by a block-granular system at small lesion sizes, *even if every single
block is classified correctly*. That is pure arithmetic. It means two years of
reported IoU gains in this field are partly a quantisation artefact, and it means
comparisons across papers at different lesion sizes are not comparisons. This is
the most interesting thing on the poster and it is a computation, so it cannot be
argued with.

**Move 4 — what we built, and what we refuse to say.** A keyed verifier that
localises and abstains, measured on 12 970 images with a clean receipt. And a
list of the claims we decline to make, because the corpora that would license
them were not run.

Move 3 is the one to rehearse. It is the move a panel will interrupt.

---

## 4. The panels

Eight panels. Each is given as: heading, the content ready to set, the facts it
may use, and the failure mode to avoid.

---

### P1 — Problem

**Heading.** A medical image can be edited and re-submitted.

**Set this.**

> Dermoscopic and radiological images are evidence. They are also files. A
> lesion can be removed with an inpainting tool in seconds; a pigmented area
> can be softened; text can be burned in. In each case the image remains
> visually plausible and metadata proves nothing.
>
> Two questions follow, and published systems answer only the first:
>
> 1. **Has this image been altered?**
> 2. **Where — and if you cannot tell, can you say so?**

**Facts.** None. This panel carries no numbers, deliberately. A poster whose
first panel has no number reads as a question, not a pitch.

**Avoid.** Do not open with prevalence statistics for medical-image fraud. No
number for them is in `facts.json`, and inventing an attention-grabbing one is
how the first thirty seconds go wrong.

---

### P2 — Gap

**Heading.** What the comparison set does not report.

**Set this as a three-line table, not prose.**

| system | family | keyed? | may abstain? |
|---|---|---|---|
| SECURENet, TFPDD, ConMark | classifier + learned embedder | no | no |
| DeepMark | end-to-end deep watermark | no | no |
| ASFW | attention-guided fragile | no | no |
| PFF-WM | 5-module DL system, 15.1 M | no | no |
| WAM (ICLR 2025) | segmentation formulation | no | no |
| OmniGuard (CVPR 2025) | degradation-aware | no | no |
| **this work** | keyed fragile + learned reader | **yes** | **yes, with reason codes** |

Footnote under the table, small type:

> "Keyed" means the evidence cannot be produced without a secret. Every learned
> embedder above is invertible in principle: an attacker with the model and
> enough image pairs trains the inverse. None of these systems reports an
> abstention, so a wrong-key or recompressed image is forced into a binary
> verdict.

**Facts.** P-01…P-04 for the family descriptions; nothing quantitative in the
table itself.

**Avoid.** Do not put their accuracy numbers in this table. The moment a
0.832 sits next to our 0.9936, we have made a comparison we cannot defend
(X-05). Accuracy belongs in P5 with the corpus named, or nowhere.

---

### P3 — Method

**Heading.** One mark, three bindings.

**This panel is the architecture figure.** `docs/poster/architecture.*`. See §6
for sizing — read it before placing.

**Set one caption line beside it, nothing more.**

> The tag written into a block is a function of the key, the block's address and
> the block's own quantised detail coefficients. Change the content and the tag
> stops matching. Paste a block from elsewhere and it carries the tag of its old
> address. Neither forgery is available without the key.

**Facts.** C-01 (the ceiling note inside the figure), M-02 (the measured result
printed on the figure).

**Avoid.** Do not re-explain the figure in the panel text. The figure has a
caption; duplicating it wastes the largest area on the poster.

---

### P4 — Study design

**Heading.** Twelve configurations, one frozen protocol.

**Set this.** A one-line statement, then the matrix as a single row of chips or
a small table — never a paragraph.

> The protocol was written as code and frozen before the first training run.
> Every configuration below is the same system with one component added or
> removed, evaluated on the same split with the same metrics.

Then C0–C11, in the order they are computed. Mark **C8** and **C0** visually —
they are the comparison the whole study exists to make.

**Under it, three lines that matter more than the matrix:**

> **C9** removes the key. It prices the security property instead of asserting it.
> **C10** trains on one key and tests on another. A drop above 0.05 IoU means the
> network learned the key — a security failure, not an accuracy one. No published
> system runs this test.
> **C11** holds out an entire tamper family, so the reader is tested on a kind of
> edit it never saw.

**Facts.** T-01, T-02, T-03. Status is **planned**. The panel heading or a
corner label must say so — `DESIGNED, NOT YET RUN`. A poster that shows a matrix
without that label is claiming twelve results it does not have.

**Avoid.** Do not draw the matrix as a results heatmap. Empty cells coloured in
is the single most tempting dishonest thing on this poster.

---

### P5 — What is measured today

**Heading.** Measured on the established system.

**Set this as one ruled row of six statistics, large.**

| detection | localisation IoU | benign false claims | PSNR | verify | disclosed failure |
|---|---|---|---|---|---|
| **0.99992** | **0.9936** | **0 / 12 970** | **40.47 dB** | **58.6 ms** | **2 / 300** |
| 12 969 / 12 970 images | block level, 8×8 | 0.000 | mean | per 512², isolated | JPEG Q100, 0.67 % |

Line under it, small:

> ISIC 2018 Task 1 · n = 2 594 · `code_dirty = false` · commit `28e4e6e`.

**Facts.** M-01 … M-07, M-09.

**The sixth column is the important one.** Most posters put their best foot
forward and hide the failure in a footnote. Putting `2 / 300 — above our own
0.5 % bound` at the same size as the successes changes what the panel thinks of
the other five. It is also true, which is the only reason it is allowed.

**Avoid.**
- Do not print `0.987` coverage. It is not in any receipt (U-01).
- Do not print `35.75 dB` worst-image PSNR (U-02).
- Do not call 0.9936 comparable to 0.832. Different granularity, different
  corpus, different tamper family. If a reviewer asks, the answer is P6.

---

### P6 — The ceiling argument

**Heading.** Why a perfect system misses the published bar.

**This is the panel that wins the poster. Give it the most space after P3.**

Set the numbers as a small table or a line chart — a chart is better here,
because the crossing point is the argument:

| lesion radius | 8 | 16 | 24 | **32** | 48 | 64 | 128 |
|---|---|---|---|---|---|---|---|
| best possible pixel IoU at 8×8 granularity | 0.513 | 0.692 | 0.757 | **0.809** | 0.854 | 0.889 | 0.937 |

Then, in large type, the sentence:

> **A flawless block classifier scores 0.809 on a radius-32 lesion. The
> published bar is 0.832. The gap is architectural, not a learning deficit — no
> amount of training closes it at that size.**

And the second sentence, which is what makes it a contribution rather than a
complaint:

> The published RefineNet gain of +6.2 IoU is not a better network. It is
> reading the image at full resolution and therefore breaking a quantisation
> floor. §3 of our design review records the same computation for our v1
> architecture and the pixel-resolution redesign that follows from it.

**Facts.** C-01, C-02, P-03.

**Guard rail.** A ceiling of 1.000 for a block-aligned square paste must appear
somewhere in this panel or its footnote. Without it the ceiling looks like an
excuse rather than arithmetic. With it, it looks like what it is.

**Avoid.** Do not claim the published authors are wrong. They are not: they use
pixel-resolution refinement, which is exactly why their number is above the
ceiling. The claim is narrower and stronger — *the floor exists, and comparisons
that ignore lesion size are not comparisons.*

---

### P7 — Honest abstention

**Heading.** The verifier is allowed to say it does not know.

**Set this.**

> Three outcomes, and every one of them carries a cause.

| verdict | meaning | example reason code |
|---|---|---|
| **INTACT** | the mark is consistent with the content | — |
| **TAMPERED** | the mark is inconsistent, with decisive support | — |
| **CANNOT SAY** | the evidence is insufficient, and we can say why | `capacity_refusal`, `geometry_change`, `evidence_conflict`, `key_mismatch`, `routine_handling` |

> An abstention is not a failure of the system; it is a claim about the
> evidence. The poster-level discipline that makes it defensible is that a
> refusal is *scored*: selective risk is reported against coverage, so a system
> that answers less must be shown to answer better.

**Facts.** No quantitative claim yet — the calibrated-abstention curve comes
from the v2 run, and on the smoke check the AURC (0.0036) was better than raw
block error (0.0052) but not by enough to call it calibrated. So this panel
makes the *design* claim, not a performance claim.

**Avoid.** Do not claim "calibrated abstention" as a result. It is a mechanism
with a measurement still owed. The words that are safe: *refusal carries a cause,
and refusals are scored against coverage.*

---

### P8 — What we claim and what we refuse to claim

**Heading.** Claims and refusals.

**Two columns. Equal visual weight. This is the panel that ends the viva.**

| we claim | we do not claim |
|---|---|
| a keyed mark that cannot be forged without the key | that the released notebook is secure — it publishes its key (F10) |
| block-level localisation, 0.9936 on ISIC 2018 | that this beats 0.832 — that bar is LiTS with lesion insertion, not run here |
| 0.99992 detection, 12 969 / 12 970 | that this beats 97.6 % — that figure is CheXpert, not run here |
| zero false claims on 12 970 benign-processed images | that false claims are impossible — 2 in 300 failed at JPEG Q100 |
| a verifier that abstains with a cause | that the abstention is calibrated — that measurement is owed |
| a protocol frozen before training | state of the art, in any form |

**Facts.** The left column M-01…M-03, M-09; the right column X-01…X-09.

**Avoid.** Do not soften the right column with hedges like "not yet fully
explored". The right column's force comes from being flat statements of fact
about what was not run. Hedge it and it reads as an excuse; state it and it
reads as discipline.

---

## 5. The extended plan, in full

This is what P4 refers to and what the next two terms consist of.

### 5.1 Where the project actually stands

Three layers, three states. Never blur them.

| layer | state | evidence |
|---|---|---|
| keyed fragile watermark, protect + verify + 3-way verdict | **built and measured** | 86 tests; receipt `isic-full-v8`; 12 970 images |
| protocol, metrics, tamper synthesis, evidence channel | **built** | `src/protocol.py`, `src/metrics.py`, `src/tamper.py`, `src/evidence.py` |
| learned refinement: AE, PixelRefineNet, saliency, three-way head | **built and unit-tested, never trained** | forward pass verified, gradients asserted, no result |

The third row is the entire reason a panel called the earlier version childish.
It is also the row that cannot be faked, which is why the poster labels it.

### 5.2 Why a synthesis study and not a rebuild

The reference system is a five-module deep network. The classical phase
implemented one of the five — the keyed embedder — and then compared its numbers
to the five-module headline. That is the root cause of the earlier verdict, and
it is precise and fixable.

The reference paper's own ablation prices its parts, and the pricing is the
argument for how to respond: the RefineNet localiser is worth **+6.2 IoU**, more
than the attention module (+3.1) and the dual carrier combined. So the response
is not "add a neural network". It is: take the measured best answer to each of
eight sub-problems, assemble them, then prove which survive assembly.

| # | sub-problem | best available answer | source | ours? |
|---|---|---|---|---|
| 1 | where to spend embedding energy | attention-weighted strength on a saliency map | PFF-WM | no |
| 2 | what the verifier reads | keyed QIM residual in integer Haar details | this work | **yes** |
| 3 | is anything wrong at all | one-class AE trained on authentic-only | PFF-WM | no |
| 4 | error map → mask | RefineNet, 3 levels + skips | PFF-WM | no |
| 5 | output formulation | segmentation, not image-level classification | WAM | no |
| 6 | survive routine processing | degradation-aware extraction | OmniGuard | no |
| 7 | benign vs malicious vs unknown | three-way head | post-quantum DCT work | no |
| 8 | what to do when evidence is weak | abstention with causal reason codes | this work | **yes** |

Two of eight are ours. That ratio is the honest shape of the work, and stating
it is stronger than implying otherwise.

### 5.3 The architectural rule

> **The network never generates evidence. It only reads it.**

Every suspicious signal entering the learned layers originates in the keyed
channel. With a wrong key the evidence is noise and the reader has nothing to
amplify. This is why the system can become more accurate without becoming
forgeable, and it is the answer to the question a sharp examiner will ask:
*isn't a learned reader just a learned forger?* No — the reader can weigh
evidence; it cannot invent it.

### 5.4 Scope, decided

**ISIC 2019 only, for this phase.** It is free on Kaggle, needs no approval, and
is one of the three corpora the reference system evaluates on, so the run is on
shared ground.

**Deferred, by explicit decision: LiTS and CheXpert.** What the deferral costs,
stated once so it cannot surface later as a surprise: the reference numbers for
detection (97.6 %) are CheXpert and for localisation (0.832) are LiTS. **No
number from this phase can be placed in either of their tables.** The result
that needs no external corpus is the internal **C0 versus C8** comparison on the
same split — that is the headline of the next phase, not of this poster.

Two things an ISIC-only study must carry to be worth more than one number:

1. **Per-diagnosis strata.** Flat lesions and textured lesions lose their mark
   in different places; an aggregate hides exactly the effect a reviewer looks
   for. Every bucket reported with its n; an empty bucket reported as empty.
2. **Per-area strata with the ceiling.** An absolute IoU says nothing without
   the target size beside it. This is P6, and it is not optional.

### 5.5 Tamper families

Eight, each producing `(image, mask)` with the mask **measured by pixel
difference**, never a declared rectangle.

| id | family | note |
|---|---|---|
| T1 | copy-move 8/16/32/64 px | carried from the classical battery |
| T2 | lesion insertion (synthetic mass) | the protocol the reference paper used |
| T3 | lesion removal by inpainting | the clinically realistic one |
| T4 | burned-in text | our weakest family |
| T5 | splicing from a different image | the gap the classical phase never measured |
| T6 | generative substitution | **declared out of scope**, not faked |
| B1 | benign: JPEG 90/75/50, noise, resize | must stay silent |
| B2 | benign chain | must abstain, never accuse |

### 5.6 The matrix

| row | configuration | isolates |
|---|---|---|
| C0 | classical only | the control |
| C1 | + one-class AE | sub-problem 3 |
| C2 | + RefineNet | sub-problem 4 |
| C3 | + AE + RefineNet | 3+4, no attention |
| C4 | + attention (full reproduction) | sub-problem 1 |
| C5 | + degradation conditioning | sub-problem 6 |
| C6 | + segmentation formulation | sub-problem 5 |
| C7 | + three-way head | sub-problem 7 |
| **C8** | **full synthesis** | all eight |
| C9 | C8 with the key removed | sub-problem 2 — what security costs |
| C10 | C8 trained K₁, tested K₂ | key leakage |
| C11 | C8 on a held-out tamper family | negative transfer |

**Gates, fixed before any run:** coverage floor 0.90 (a configuration that
refuses more than 10 % of blocks is disqualified whatever its IoU); re-key drop
≤ 0.05 IoU; the test split is opened once.

### 5.7 Sequencing — non-negotiable

1. Protocol committed **before** the first training run.
2. ISIC 2019 attached on Kaggle.
3. **C0 reproduced on ISIC 2019 before any training.** If the classical number
   does not travel from ISIC 2018 to ISIC 2019, that is the first finding and it
   changes the story.
4. Training, in the order of the compute plan.
5. Test opened once. Numbers reported as they come back, including the ones that
   lose.

Step 3 is the one people skip.

### 5.8 Compute

Measured, not estimated: **~6.3 GPU-h per 30-epoch configuration**, **~75 GPU-h
for the full matrix**. Kaggle T4 at 30 GPU-h/week therefore covers:

| week | runs |
|---|---|
| 1 | C0 (free), C8 headline, C3, C9 |
| 2 | C1, C2, C4, C10 |
| 3 | C5, C6, C7, C11 + reruns |

### 5.9 Known risks

| risk | if it happens | mitigation already built |
|---|---|---|
| negative transfer | the learned reader overfits training families and mis-weights evidence on unseen ones | C11 holds out a family |
| evidence starvation | the classical layer refuses too many blocks, the reader learns nothing | coverage floor 0.90 disqualifies the configuration |
| key leakage through the reader | the network memorises the keyed pattern for the training key | C10 re-key test at every evaluation |
| capacity mismatch | losing to a 15.1 M model while running 1.5 M reads as an excuse | width is a config; headline reported at matched capacity |
| the semi-robust second carrier is currently approximated by four hand-built scalars | a weaker signal than a carrier designed to survive JPEG | **open — highest remaining design risk.** The reference ablation prices this at −0.037 AUC / −0.067 IoU |

### 5.10 Open questions — not to be closed with a guess

These determine whether a head-to-head comparison is valid, and each must be
settled from the source's full text or code before any claim:

1. Is the 0.832 a per-image mean or a pooled pixel ratio?
2. What is the lesion-size distribution in their synthetic-tumour protocol?
3. Is their localisation ground truth the tumour mask or the paste rectangle?
4. Is their detection accuracy per-image or per-region, and on what class balance?
5. Are their benign conditions applied before or after embedding?

Until these are answered, the only defensible sentence about the published bar
is: *we reproduce the protocol; our number on their corpus and their tamper
family will be reported beside theirs, with the ceiling.*

---

## 6. Layout and typography

### 6.1 Sizing the architecture figure — read this before placing it

The figure is a **paper figure**, drawn at natural size **594 × 406 mm** (A2
landscape). Its body type is 12 units on a 2400-unit canvas, which is **8.4 pt at
that size** — right for a printed A2 sheet held in the hand, far too small for a
wall.

Type actually printed, at various placements:

| placed at | 12-unit body text prints at | 23-unit heading prints at |
|---|---|---|
| 594 mm (A2, natural) | 8.4 pt | 16 pt |
| 794 mm | 11.2 pt | 21 pt |
| 1 100 mm | 15.5 pt | 30 pt |
| 1 189 mm (full A0 width) | 16.8 pt | 32 pt |

A poster's body convention is 24–32 pt at one metre. **No placement of the
existing figure reaches that**, and it cannot: the figure carries roughly forty
text items.

**Recommended resolution.** Regenerate the same composition at poster type scale
— same blocks, same order, same argument, but type multiplied ~2.5×, which means
each block keeps its heading and one clause instead of three lines. At that type
the detail lines move into the poster's own panels, where they belong. This is
not a second architecture diagram; it is the same drawing re-typeset for a
different reading distance, and the paper figure stays exactly as it is.

**Do not** scale the 8.4 pt figure up to A0 and hope. It prints as a grey smear
at every viewing distance, which is worse than not including it.

### 6.2 Recommended layout

**A0 landscape, 1189 × 841 mm.** Landscape because the figure is landscape and
because the argument runs left to right: problem → method → result.

```
┌──────────────────────────────────────────────────────────────────────┐
│  TITLE · takeaway line · author · affiliation                        │  90 mm
├───────────────────────────┬──────────────────────────────────────────┤
│ P1 Problem                │                                          │
│                           │      P3  THE FIGURE                      │
│ P2 Gap                    │      (poster-scale redraw)               │  470 mm
│   (table)                 │                                          │
│                           │                                          │
├───────────────────────────┼──────────────────────────────────────────┤
│ P7 Abstention             │  P5  measured row (six statistics)       │  150 mm
│                           ├──────────────────────────────────────────┤
│                           │  P6  the ceiling — number + crossing     │  120 mm
├───────────────────────────┼──────────────────────────────────────────┤
│ P8 claims / refusals      │  P4  C0–C11  ·  gates  ·  DESIGNED      │  80 mm
└───────────────────────────┴──────────────────────────────────────────┘
```

Column split 34 / 66. P3 and P6 take the width; the argument panels stack in the
narrow column where they are read as text.

For an **A1 portrait** variant (841 × 594 mm, two columns of 400 mm), drop P7 to
a single sentence and put the reason codes in the caption. P6 must survive any
reduction — it is the poster.

### 6.3 Type

| element | size | weight |
|---|---|---|
| title | 72–84 pt | semibold |
| takeaway line | 34 pt | regular |
| panel heading | 34 pt | semibold |
| body | 26 pt | regular |
| table content | 24 pt | regular |
| figure caption, footnote | 18–20 pt | regular |

Two type families at most. The project's own figure uses a humanist sans for
prose and a monospace for identifiers — keep that pairing, it is the honest one
for a technical poster: `verify()` and `capacity_refusal` are monospace because
they are names, not words.

### 6.4 Colour

The figure is monochrome with one accent, used only for parts that do not exist
yet. Keep that discipline on the poster:

- **black** — established, measured
- **one accent** — planned or not yet run
- everything else — white, and rules

**Do not** colour-code the eight panels. Eight colours is what makes a poster
read as an infographic, which is the exact critique the figure was rebuilt to
answer. If the poster needs colour to separate sections, the sections are wrong.

### 6.5 Density

Roughly 40 % of the sheet should be empty. The instinct at this stage is to fill
it; resist. The two panels that must never be crowded are P6 and P8, because
both are read once and must land in one pass.

---

## 7. Say this, not that

| do not write | write |
|---|---|
| "detects tampering with 99.99 % accuracy" | "returns a TAMPERED verdict on 12 969 of 12 970 tampered images" |
| "0.9936 IoU, beating 0.832" | "0.9936 block-level IoU on ISIC 2018; 0.832 is a pixel-level figure on LiTS, not run here" |
| "the model detects tampering" | "the keyed channel produces the evidence; the model reads it" |
| "state-of-the-art" | "on our frozen protocol, which we publish in full" |
| "99.9 % accurate" | never a percentage where a fraction is available |
| "we use deep learning" | "a learned reader over keyed evidence, priced against the classical control in C0 vs C8" |
| "robust to attacks" | "survives JPEG 90/75/50, noise and resize; fails 2 of 300 at Q100" |
| "abstains when uncertain" (as a result) | "returns CANNOT SAY with a causal reason code; refusals are scored against coverage" |
| "future work will improve accuracy" | the specific thing: "the semi-robust second carrier is the highest remaining design risk" |

---

## 8. Fact index by panel

| panel | facts |
|---|---|
| P1 Problem | — |
| P2 Gap | P-01, P-02, P-03, P-04 |
| P3 Method | C-01, M-02 |
| P4 Study | T-01, T-02, T-03 |
| P5 Measured | M-01, M-02, M-03, M-04, M-05, M-06, M-07, M-09 |
| P6 Ceiling | C-01, C-02, P-03 |
| P7 Abstention | — (design claim only) |
| P8 Claims | M-01, M-02, M-03, M-09, X-01…X-09 |

Nothing in `unverified` appears on any panel. That is the check to run before
sending to print.

---

## 9. If the panel asks

| question | answer in one breath |
|---|---|
| "Is this better than the published work?" | "We cannot say yet, and we designed the study that will say it. On their corpora we have not run." |
| "Then what have you shown?" | "A system that localises and abstains, measured on 12 970 images, plus an arithmetic proof that the published localisation bar is unreachable at small lesion sizes for any block-granular system — including a perfect one." |
| "Why is your IoU 0.9936 if theirs is 0.832?" | "Ours is block-level on ISIC 2018 with copy-move and inpainting. Theirs is pixel-level on LiTS with lesion insertion. Two different measurements." |
| "Is the deep learning doing anything?" | "Not yet — it is implemented and untrained. That is why C0 versus C8 is the headline of the next phase, and why this poster labels the matrix *designed, not run*." |
| "Can't someone just forge the image?" | "Not without the key. The tag depends on key, address and content. That is tested in C9 by removing the key." |
| "Your notebook publishes the key." | "Yes. It is required for reproducibility, and it voids the security claim for that artifact specifically. C9 and C10 measure the property independently of which key is used." |
| "Why only ISIC?" | "A scoped decision. It is one of the three corpora the reference work uses, so the ground is shared; what it does not buy is a row in their CheXpert or LiTS tables, and we do not claim one." |
| "Why should we believe the numbers?" | "Protocol frozen in code before the run, receipt with a clean tree and a commit hash, every ratio with its denominator, and one criterion printed as failing." |

Longer answers, and the thirty-second pitch: `docs/poster/SPEAKER_NOTES.md`.
