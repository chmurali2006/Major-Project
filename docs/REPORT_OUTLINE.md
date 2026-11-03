# Project report — structure and acceptance criteria

**Target.** 60–80 pages of body text, excluding front matter, references and
appendices. Standard B.Tech format: A4, 12 pt body, 1.5 line spacing, 25 mm
margins, numbered chapters, figures and tables captioned and cross-referenced.

**How to use this document.** Write from the artefact, never from memory. Every
section below names the file its content comes from and the test it must pass.
A section that fails its acceptance test is not finished, however good the prose
is.

> **The one rule.** No number enters the report that is not in
> `project-context/facts.json` with a status of `verified`, `computed` or
> `published`. `planned` may appear only under a heading that says so.

---

## Front matter

| item | pages | notes |
|---|---|---|
| title page | 1 | format per your university's template |
| certificate | 1 | signed by the supervisor |
| declaration | 1 | originality statement |
| acknowledgement | 1 | |
| abstract | 1 | **250 words maximum**, see below |
| table of contents | 1–2 | |
| list of figures | 1 | |
| list of tables | 1 | |
| list of abbreviations | 1 | see the list below |

### The abstract

The most-read page of the report. 250 words, five moves, no throat-clearing.

```
[1] The problem, in one sentence.      ~35 words
[2] What published systems do, and     ~45 words
    the specific gap.
[3] What this work does.               ~55 words
[4] The computed result.               ~45 words
[5] What was measured, and what        ~70 words
    is explicitly not claimed.
```

Draft:

> Medical images are routinely edited, and conventional metadata proves nothing
> about image content. Published tamper-detection systems each optimise one
> component and report a single aggregate, so the field cannot attribute a result
> to a component. This work presents a keyed, training-free fragile watermark in
> which the tag written into each 8×8 block is bound to the secret key, the block
> address and the block's own content, so that pasted or altered regions carry an
> inconsistent tag. Verification requires only the container and the key, returns
> INTACT, TAMPERED or CANNOT SAY, and attaches a causal reason code to every
> refusal. A learned refinement stage consumes this keyed evidence without being
> able to generate it. It is preceded by an analysis showing that a block-granular
> decision grid cannot exceed 0.809 pixel IoU on a radius-32 lesion even with
> perfect classification, which is below the published 0.832 bar and establishes
> that the gap is architectural rather than a learning deficit. On 12 970 images
> the keyed system attains 0.99992 image-level detection and 0.9936 block-level
> IoU with zero benign false claims; 2 of 300 images yield a false claim at JPEG
> Q100, above this project's 0.5 % bound, and this is reported. No comparison with
> published accuracy is claimed.

**Acceptance:** contains no adjective that is not backed by a number in the same
sentence; contains the disclosed failure; contains an explicit non-claim.

### Abbreviations

`AE` autoencoder · `AUC` area under the ROC curve · `AURC` area under the risk-coverage curve · `DCT` discrete cosine transform · `Haar/QIM` Haar wavelet / quantisation index modulation · `IoU` intersection over union · `ISIC` International Skin Imaging Collaboration · `LiTS` Liver Tumor Segmentation benchmark · `PSNR` peak signal-to-noise ratio · `RCT` reversible colour transform · `ROC` receiver operating characteristic

---

## Chapter 1 — Introduction *(8 pages)*

| § | content | source | acceptance |
|---|---|---|---|
| 1.1 | Background: images as evidence, and as files | plan §0 | opens with a concrete scenario, not a definition |
| 1.2 | Motivation: why integrity matters, why "where" matters more than "whether" | `POSTER_CONTEXT.md` §3 | states the two questions and says that published work answers one |
| 1.3 | Problem statement | plan §1 | one paragraph, no bullet list |
| 1.4 | **Objectives** — six, numbered, testable | plan §1 | each maps to a chapter or a table later |
| 1.5 | Scope and limitations | plan §2 | names LiTS and CheXpert as *deferred by decision*, with the cost |
| 1.6 | Organisation of the report | — | one paragraph |

**1.4 is where novelty is stated, and it must be stated plainly rather than
implied.** Three bullets: the keyed evidence channel, the causal refusal, and the
computed localisation ceiling. Then one sentence on what is *not* claimed.

**Avoid in this chapter:** prevalence statistics for medical-image fraud, and any
sentence beginning "In today's world". Neither has a citation in the fact base.

---

## Chapter 2 — Literature survey *(12 pages)*

Content: `docs/LITERATURE.md`, expanded.

| § | content | acceptance |
|---|---|---|
| 2.1 | Survey method — how works were selected and compared | states the comparison axes up front: keyed?, abstains?, corpus, granularity |
| 2.2 | Classical fragile watermarking | explains *why* fragile marking works before explaining who did what |
| 2.3 | Deep-learning approaches | grouped by which sub-problem they solve, not chronologically |
| 2.4 | **Comparative analysis** | a single table, ≥ 12 works, with the gap column |
| 2.5 | Gap analysis | five gaps, each naming the works that fail to address it |
| 2.6 | Summary | one paragraph: what the literature establishes, what it leaves open |

**Acceptance for 2.4:** the table has a `keyed?` and an `abstains?` column, and
every accuracy figure carries its corpus. If a figure's corpus is unknown, the
cell reads `not stated` — it does not get filled in.

**Acceptance for 2.5:** every gap is derived from a column of the table in 2.4.
A gap that cannot be pointed at in the table is an opinion, not an analysis.

**Do not** write the survey as a list of summaries. A reader should be able to
read 2.4 and 2.5 alone and see the gap.

---

## Chapter 3 — System design *(14 pages)*

Content: `project-context/ARCHITECTURE.md`, expanded, with the figure.

| § | content | acceptance |
|---|---|---|
| 3.1 | Design principle | §1 of ARCHITECTURE: *the network never generates evidence, only reads it*, and the three consequences |
| 3.2 | System overview | the Figure 1 architecture, with the full caption |
| 3.3 | **Protect** — six stages in order | the three load-bearing decisions, each with an attack it blocks |
| 3.4 | **Verify** — gate, carriers, ladder | why a ladder and not a threshold; the four invariants |
| 3.5 | **Learned refinement** | the tensor flow, and the two things it adds that the classical layer structurally cannot |
| 3.6 | Design rationale and rejected alternatives | each rejection has a measurement or a stated reason |
| 3.7 | Constants and their provenance | the appendix-A table; `LIT`/`CHOSEN`/`DERIVED`/`MEASURED` |

**3.3 must contain the attack table.** Paste-from-elsewhere, content-edit,
fabricate-from-scratch, re-key-with-another-key — each with the mechanism that
defeats it. That table is the security argument, and it is four rows long.

**3.4 must contain the invariants** as enforced properties, not intentions:
verify cannot receive the original image because its signature has no such
parameter; a key mismatch cannot produce a TAMPERED verdict.

**3.6 is the section that distinguishes a design from a description.** Every
rejected alternative should be rejected *for a reason that was measured*: region
weighting bought nothing (A-018); gating cost more than it bought (A-007); a
floating-point carrier was replaced by integer Haar because the quantisation index
must be exactly recoverable.

---

## Chapter 4 — Implementation *(12 pages)*

| § | content | source | acceptance |
|---|---|---|---|
| 4.1 | Tools and environment | Python 3.11, NumPy, OpenCV, PyWavelets, PyTorch, pytest; Kaggle T4 | versions stated |
| 4.2 | Module structure | `src/` map | every module named has one job, stated in one line |
| 4.3 | The evidence channel | `src/evidence.py` | explains why 10 channels rather than 2, with the AUC gain quoted as *small* |
| 4.4 | Tamper synthesis | `src/tamper.py` | masks are measured by differencing, never declared |
| 4.5 | The learned architecture | `src/models.py` | forward shapes given; the single loss function and why it exists |
| 4.6 | Data pipeline | `src/isic_meta.py`, split by lesion | the split is by lesion, and this is stated |
| 4.7 | Testing | 86 tests (78 without torch; 8 model tests need it) | three bugs found by tests, described honestly |
| 4.8 | Reproducibility | protocol, receipts, `code_dirty` | a third party could rerun it |

**4.7 is worth more space than a student normally gives it.** Three real bugs
were caught by tests and are documented:

1. **Block-locality inversion** — `reshape(ny,k,nx,k) → (ny,nx,k*k)` collapses the
   axes in the wrong order and scatters one block's coefficients across several.
   It round-trips perfectly, so an inverse-only test passes while locality is
   destroyed.
2. **The vacuous locality test** — the first version perturbed a block by a
   constant offset, which lands entirely in `LL2` and never touches a detail
   coefficient. Correct behaviour, meaningless test.
3. **Heads with no gradient** — v1 trained the pixel branch alone, so the block
   head and classifier received `grad=None` and would have looked trained while
   being random.

Presenting these is not a confession; it is evidence that the test suite does
work. A report that claims no bugs were found is claiming the tests found
nothing.

---

## Chapter 5 — Results and discussion *(16 pages)*

**The chapter the panel reads first. Structure it so the honest parts are
visible, not buried.**

| § | content | acceptance |
|---|---|---|
| 5.1 | Experimental setup | corpus, n, split, hardware, receipt provenance — one table |
| 5.2 | Classical baseline on ISIC 2018 | the six measured statistics, and the disclosed failure **in the same table** |
| 5.3 | Classical baseline on ISIC 2019 | the C0 reproduction, reported whether it rises or falls |
| 5.4 | **The localisation ceiling** | the radius/IoU table, the crossing point, and the square-paste row at 1.000 |
| 5.5 | The configuration matrix | C0–C11, with `not run` where not run |
| 5.6 | Controls: key removal, re-key, held-out family | the three rows that make this a contribution |
| 5.7 | Comparison with published work | **stated as a comparison of protocols, not of numbers** |
| 5.8 | Stratified analysis | per diagnosis, per area bucket, each with the ceiling |
| 5.9 | Abstention analysis | selective risk against coverage |
| 5.10 | Discussion | what survived assembly, what did not, and why |

### 5.2 — the layout that matters

Print the failure at the same size as the successes, in the same table:

| metric | value | n | note |
|---|---|---|---|
| image-level detection | 0.99992 | 12 969 / 12 970 | any block flagged |
| localisation IoU | 0.9936 | — | **block level**, 8×8 grid |
| benign false claims | 0.000 | 0 / 12 970 | benign battery |
| PSNR | 40.47 dB | — | mean |
| verification latency | 58.6 ms | — | per 512², isolated |
| **envelope false claims** | **0.0067** | **2 / 300** | **JPEG Q100 — exceeds the 0.5 % bound** |

**Acceptance:** the sixth row is present, at the same size, in the same table.

### 5.4 — the argument, in four sentences

1. A decision grid of `IMAGE_SIZE / BLOCK = 64` blocks cannot express a boundary
   finer than 8 pixels.
2. Therefore the best possible pixel IoU for a tampered region of radius *r* is a
   pure function of *r* and the grid — tabulated for eight radii.
3. At *r* = 32 that bound is 0.809, below the published 0.832, **at zero errors**.
4. A block-aligned square paste scores 1.000, which is why the bound is a
   property of *shape and size*, not a limitation of our implementation.

Then: this is why the learned layer operates at 512², and why localisation
numbers reported at different lesion sizes are not comparable.

**Do not** phrase point 3 as a criticism of the published authors. They refine at
pixel resolution, which is exactly why their number clears the bound. The claim
is narrower and stronger: *the floor exists, and comparisons that ignore lesion
size are not comparisons.*

### 5.7 — the section most likely to go wrong

The published detection figure is measured on CheXpert; the published localisation
figure on LiTS with synthetic lesion insertion. **Neither corpus was run here.**
So:

| what may be said | what may not |
|---|---|
| "on a protocol frozen before training, we report both systems' settings and corpora" | "we outperform 0.832" |
| "our 0.9936 is a block-level figure on ISIC 2018" | placing it in a column beside a pixel-level LiTS number |
| "a direct comparison requires a LiTS run, which is out of scope" | omitting that sentence |

**Acceptance:** the section contains the words *not comparable* at least once,
attached to a specific pair of numbers.

### 5.9 — the honest position on abstention

The mechanism is real; the calibration is still owed. On the smoke check the
AURC (0.0036) was better than raw block error (0.0052) but not by enough to call
it calibrated. So 5.9 states the *mechanism* and reports the curve, without
claiming calibration. If the full run shows the curve separating, claim it then.

---

## Chapter 6 — Conclusion and future work *(5 pages)*

| § | content | acceptance |
|---|---|---|
| 6.1 | What was established | restates the six objectives with their outcomes, including unmet ones |
| 6.2 | Contributions | three, each in one sentence |
| 6.3 | Limitations | the disclosed failure, the corpus scope, the artefact that publishes its key, the untrained learned layer |
| 6.4 | Future work | specific, not "improve accuracy" |

**Acceptance for 6.1:** unmet objectives are listed as unmet. An objectives table
that shows six ticks after a project that did not train its model is the single
most damaging thing a report can contain.

**Acceptance for 6.4:** every item is a named next step with a reason:

- run LiTS with the reference protocol, to place a localisation number beside the
  published one at matched capacity and matched lesion-size distribution
- replace the four hand-built degradation scalars with a semi-robust carrier
  designed to survive JPEG — the reference ablation prices this at −0.067 IoU
  when removed, more than its attention module
- characterise the C11 negative-transfer result if it appears
- calibrate the abstention path properly, and report risk–coverage curves for
  each diagnosis stratum

---

## References

≥ 25 entries, IEEE style. Every entry cited in the text at least once, in order of
first citation.

**A warning that applies to this project specifically.** Six of the compared works
are currently known by corpus and reported result, with the numbers taken from
the reference paper's tables rather than from the works themselves. Those are
**secondary citations** and must either be upgraded to primary before submission
or marked as such, in the form: *"as tabulated in [ref]"*. Presenting a secondary
citation as a primary one is the kind of error an examiner can find in a minute
with the original PDF open.

`docs/LITERATURE.md` flags which entries need this treatment.

---

## Appendices

| appendix | content | pages |
|---|---|---|
| A | The frozen protocol, printed from `src/protocol.py` | 3 |
| B | A complete receipt, printed as JSON | 2 |
| C | The amendment log — a selection with rationale | 3 |
| D | Additional results: per-family, per-diagnosis, per-area | 4 |
| E | Reproduction instructions | 1 |

Appendix A is not padding: printing the protocol *is* the reproducibility claim.
A reader can see the twelve configurations and the gates without reading the
source.

---

## Figures and tables to produce

| # | figure/table | status |
|---|---|---|
| Fig 1 | system architecture | **done** — `docs/poster/architecture.pdf` |
| Fig 2 | evidence channel: tensor flow from pixels to `E`, `S` | to draw |
| Fig 3 | the decision ladder as a flow with reason codes | to draw |
| Fig 4 | `PixelRefineNet` block diagram with shapes | to draw |
| Fig 5 | ceiling curve: pixel IoU against lesion radius, with the 0.832 bar | to draw — **the key figure of the results chapter** |
| Fig 6 | selective risk against coverage | after the run |
| Fig 7 | per-diagnosis IoU with n | after the run |
| Tab 1 | literature comparison, ≥ 12 works | from `LITERATURE.md` |
| Tab 2 | the eight tamper families | from `protocol.py` |
| Tab 3 | constants and provenance | from `ARCHITECTURE.md` App. A |
| Tab 4 | classical baseline with the disclosed failure | receipts |
| Tab 5 | the C0–C11 matrix | after the run |
| Tab 6 | comparison with published work — protocols, not numbers | from the bars |

---

## Writing order

Do not write the chapters in order. Write them in this order, for these reasons:

1. **Ch. 3 design** — it is already written in `ARCHITECTURE.md`; expand it,
   change nothing factual.
2. **Ch. 4 implementation** — mechanical, sourced from the code, mostly done.
3. **Ch. 2 literature** — expand `LITERATURE.md`; do it early because it needs
   the PDFs, and PDF access is the long lead item.
4. **Ch. 5 results** — the parts that do not depend on the run (5.1, 5.2, 5.4)
   can be written now. 5.4 is the strongest section and needs no training.
5. **Ch. 1 introduction** — write it last among the body chapters; you cannot
   introduce a project you have not finished describing.
6. **Abstract and Ch. 6** — last, in that order.

Writing 5.4 early has a second benefit: if the runs overrun, the strongest
content in the report is already finished.

---

## Before submission — the check

```
[ ] every number in the report appears in facts.json with a permitted status
[ ] every ratio has its denominator
[ ] every IoU states its granularity; every IoU is beside its ceiling
[ ] every accuracy figure names its corpus
[ ] the JPEG Q100 failure appears at full size in Ch. 5, not in a footnote
[ ] the objectives table shows unmet objectives as unmet
[ ] secondary citations are marked "as tabulated in [ref]"
[ ] the learned-layer status is described as implemented and untrained
[ ] no claim of SOTA, robustness, or clinical utility anywhere
[ ] the repository state described in Ch. 4 matches the committed tree
```

The last line is the one that gets forgotten. A report describing a repository
that has since changed by three commits is a report that no longer describes the
artefact — and the receipt hash is right there to prove it.
