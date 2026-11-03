# Project plan — B.Tech Major Project

**Project.** A Fragile Watermarking for Medical Image Tamper Detection
**Subtitle.** Keyed, training-free evidence with learned refinement and calibrated abstention
**Status at this document.** Phase-I review complete (2026-10-24); the design has
been restructured in response. This plan covers the remainder of the project.

> **Assumption to correct.** The dates below assume a conventional Indian
> B.Tech calendar: Phase-I review October, Phase-II review February–March,
> final viva April–May. If your actual review dates differ, move the milestones
> and keep the *order* and the *exit criteria* — those are the parts that matter.

---

## 0. The project in one page

Medical images are evidence, and they are also files. A lesion can be removed
with an inpainting tool in seconds; a region can be pasted from another study; a
pigmented area can be retouched. The image remains visually plausible and
metadata proves nothing about content.

Published systems in this area each optimise one component and report one
aggregate, so the field cannot say **which component is carrying the result**.
This project does the opposite:

> It decomposes tamper detection into eight sub-problems, takes the measured best
> answer to each, assembles them, and then measures the assembly against every
> one of its constituents on a protocol frozen in code before any training run.

Two components in that assembly are not reproductions:

1. **A key.** The evidence channel is keyed and training-free. A tag is bound to
   the key, the block address and the block's own content, so a region pasted
   from elsewhere carries the tag of its old address and an edited block carries
   the tag of its old content. Every learned embedder in the comparison set is
   invertible in principle. This is measured by a control that removes the key,
   not asserted.
2. **A refusal.** Verification returns INTACT, TAMPERED or **CANNOT SAY**, and
   every refusal carries a causal reason code. No system in the comparison set
   outputs "I cannot determine this, and here is why".

Underneath both sits a result that reframes the published comparison: a decision
grid of 8×8 blocks cannot express a boundary finer than 8 pixels, so a **flawless**
block classifier scores 0.809 pixel IoU on a radius-32 lesion — below the
published bar of 0.832, at zero errors. The gap is architectural, not a learning
deficit. That computation is why the learned layer is designed at pixel
resolution, and it is why localisation numbers reported at different lesion sizes
are not, in fact, comparable.

**The deliverable is not a better number. It is an attribution study with a
frozen protocol, in which every number — including the one criterion that fails —
is traceable to a receipt.**

---

## 1. Objectives

Six, numbered so they can be marked. Each has a test.

| # | objective | how it is proved | status |
|---|---|---|---|
| **O1** | Establish a keyed, training-free fragile watermark that localises tampering without the original image | receipt `isic-full-v8`, 12 970 images, clean tree | **done** |
| **O2** | Return a three-way verdict with a causal reason code for every refusal | ladder implemented; reason-code taxonomy frozen | **done** (design) |
| **O3** | Freeze the evaluation protocol in code before any training run | `src/protocol.py` committed; 12 configurations, gates, splits | **done** |
| **O4** | Reproduce the classical baseline on ISIC 2019 and show whether it travels | C0 on ISIC 2019, reported whatever it shows | open |
| **O5** | Measure the contribution of the learned half against its own control | C0 vs C8 on one split; full C0–C11 matrix | open |
| **O6** | Disclose every failing criterion and refuse every unsupportable claim | `facts.json` statuses; the Q100 envelope failure on the figure | **done, ongoing** |

O1–O3 and O6 are complete. O4 and O5 are the remaining work and they are the
substance of Phase-II.

---

## 2. Scope

### In scope

- **ISIC 2019** (25 331 images) as the single corpus for the learned phase.
  Free on Kaggle, no approval required, and one of the three corpora the
  reference system evaluates on — so the ground is shared.
- Eight tamper families (five tampering, two benign, one declared out of scope).
- The twelve-configuration matrix, including the key-removal, re-key and
  held-out-family controls.
- Per-diagnosis and per-area stratification, with the block ceiling printed
  beside every IoU.

### Out of scope — decided, not forgotten

| excluded | why | what it costs |
|---|---|---|
| **LiTS** | deferred by decision | the published 0.832 localisation bar is measured here, so no localisation number of ours can be tabulated against it |
| **CheXpert** | deferred by decision; needs a Stanford form | the published 97.6 % detection is measured here, so no detection number of ours can be tabulated against it |
| **T6 generative substitution** | no generator available | declared unmeasured; it is not faked, and it is not silently dropped |
| **Clinical validation** | no clinician involvement | no diagnostic claim is made anywhere; saliency is a localisation aid, never a pathology annotation |
| **Deployment** | not a product | latency is reported; no device or PACS integration is claimed |

**The scope decision is defensible and must be stated in exactly this form:**
ISIC 2019 is shared ground, so the comparison is legitimate; what it does not buy
is a row in the reference work's headline tables, and no such row is claimed.
The result that needs no external corpus is **C0 versus C8 on the same split**,
and that is therefore the headline of the learned phase.

---

## 3. Work breakdown

Five phases, each with a single exit criterion. A phase is not "mostly done" —
it is closed or it is not.

### Phase A — Classical system *(complete)*

| task | state |
|---|---|
| keyed protect / verify, three-way ladder, reason codes | done |
| 34 recorded amendments, provenance-annotated constants | done |
| ISIC 2018 measurement, 12 970 images, clean receipt | done |
| falsification battery, envelope sweep, disclosed failure | done |

**Exit criterion:** a receipt from a clean tree, and one failing criterion
disclosed rather than hidden. **Met.**

### Phase B — Protocol freeze and ISIC 2019 port *(3–4 weeks)*

| # | task | effort | depends on |
|---|---|---|---|
| B1 | freeze `src/protocol.py`; record the freeze date in `AMENDMENTS.md` | 1 d | — |
| B2 | port `isic_meta.py` to the 2019 layout (8 single-label categories, `lesion_id`) | 2 d | — |
| B3 | build the ISIC 2019 split, grouped by lesion, and freeze it | 2 d | B2 |
| B4 | **reproduce C0 on ISIC 2019** | 3 d | B3 |
| B5 | write the C0 result up as a finding, whatever it shows | 1 d | B4 |
| B6 | confirm the evidence channel behaves on the new corpus (separation by family) | 2 d | B4 |

**Exit criterion:** C0 measured on ISIC 2019 from a clean tree, with the
per-diagnosis strata reported. **B4 is the gate** — nothing trains until it is
done, because if the classical number does not travel, every downstream
comparison is measured against a different baseline and the whole study shifts.

**Why this phase is not trivial.** It is the step everyone skips, and it is the
step that decides whether the study is honest.

### Phase C — Headline runs *(4 weeks)*

| # | configuration | purpose | GPU-h |
|---|---|---|---|
| C1 | **C8** full synthesis | the assembly | 6.3 |
| C2 | **C3** AE + RefineNet, no attention | isolate the attention module | 6.3 |
| C3 | **C9** C8 minus the key | price the security property | 6.3 |
| C4 | **C10** re-key | key-leakage test | 6.3 |
| C5 | analysis and figures | — | CPU |

**Exit criterion:** the C0-vs-C8 comparison with gates applied, plus the two
controls. This is the result the project turns on.

Budget note: 30 GPU-h/week on the Kaggle free tier covers four configurations per
week with margin. Measured cost is 6.3 GPU-h per 30-epoch configuration.

### Phase D — Full matrix and analysis *(4 weeks)*

| # | task | purpose |
|---|---|---|
| D1 | C1, C2 | isolate the autoencoder and the refiner |
| D2 | C4 | full reproduction of the reference architecture |
| D3 | C5, C6, C7 | degradation, segmentation, three-way head |
| D4 | C11 | held-out tamper family |
| D5 | stratified analysis | per diagnosis, per area bucket, with the ceiling |
| D6 | selective risk vs coverage | whether the abstention is calibrated |
| D7 | ablation narrative | which components survive assembly, and which do not |

**Exit criterion:** every row of the matrix has a number or an explicit
`not run — reason`. An empty cell is never coloured in.

### Phase E — Dissemination *(4 weeks)*

| # | deliverable |
|---|---|
| E1 | project report, 60–80 pages |
| E2 | A0 poster, generated from `project-context/` |
| E3 | review presentation, 16–20 slides |
| E4 | demonstration: live verify, then a tampered image detected and localised |
| E5 | conference paper draft |
| E6 | repository prepared for inspection: tests, receipts, protocol |

**Exit criterion:** a viva can be conducted entirely from artefacts in the
repository, with no claim resting on memory.

---

## 4. Timeline

| week | dates | phase | milestone |
|---|---|---|---|
| W1–W4 | 03 Nov – 30 Nov | **B** | C0 reproduced on ISIC 2019 |
| W5–W8 | 01 Dec – 28 Dec | **C** | C8 headline + C9 + C10 |
| W9–W12 | 29 Dec – 25 Jan | **D** | full matrix closed |
| W13–W16 | 26 Jan – 22 Feb | **E** | report + poster + slides |
| — | ~Feb–Mar | — | **Phase-II review** |
| — | ~Apr–May | — | **final viva** |

Slack: two weeks are deliberately unallocated. Every run in this project has
cost more than estimated once; the two configurations most likely to overrun are
C8 (capacity tuning at matched width) and C11 (a held-out family may show
negative transfer, which needs a second run to characterise).

---

## 5. Deliverables

| # | deliverable | format | audience | due |
|---|---|---|---|---|
| 1 | working system, tested | repository | panel, examiner | continuous |
| 2 | frozen protocol | `src/protocol.py` | demonstrator of rigour | **already** |
| 3 | receipts | JSON, one per run | verification | per run |
| 4 | project report | PDF, 60–80 pp | examiner | Phase-II |
| 5 | poster | A0 PDF, vector | review panel | Phase-II |
| 6 | presentation | 16–20 slides | review panel | Phase-II |
| 7 | live demonstration | 5 min | viva panel | final viva |
| 8 | conference paper draft | 6–8 pp | supervisor | final viva |
| 9 | progress log | this repo | supervisor | fortnightly |

---

## 6. Why this is a strong B.Tech project

Five differentiators, each of which is a property of the work rather than a
claim about it.

**1. It is an attribution study, not a reproduction.**
The obvious response to "your system isn't deep enough" is to rebuild as a deep
network. That produces a reproduction, which invites the question *what did you
contribute?* The response taken here instead prices every component against the
others on one split — which is what the field itself has not done.

**2. It contains a computed result, not only a measured one.**
The block-ceiling analysis (§0) is arithmetic. It cannot be argued with, it does
not depend on a training run, and it changes how published localisation numbers
should be read. Very few undergraduate projects contain a result of that kind.

**3. Two components are genuinely novel in the comparison set.**
A keyed, training-free evidence channel; and a verifier that refuses with a
cause. Both are measured — the key by a control that removes it, the refusal by
selective risk against coverage.

**4. The procedure cannot produce an inflated number.**
Protocol frozen in code before training; every constituent in the table; the test
split opened once; the losing configurations printed; one failing criterion
published at full size on the poster. This is the strongest available answer to
*"how do we know you didn't tune to the test set?"* — and it is an answer most
projects cannot give.

**5. The engineering discipline is visible.**
86 tests, 34 recorded amendments, constants annotated with provenance
(`LIT` / `CHOSEN` / `DERIVED` / `MEASURED`), receipts carrying a commit hash and a
`code_dirty` flag. Three real bugs were caught by tests and are documented rather
than quietly fixed. That record is inspectable, which is what makes it worth
something.

---

## 7. B.Tech evaluation mapping

How each standard criterion is answered, and by which artefact.

| criterion | what the panel looks for | where it is answered |
|---|---|---|
| problem definition | a specific problem, not a topic | plan §0; report Ch. 1 |
| literature survey | ≥ 15 works, a gap table, not a list | `docs/LITERATURE.md`; report Ch. 2 |
| objectives | numbered and testable | plan §1 |
| methodology | a design with stated rationale | `ARCHITECTURE.md`; report Ch. 3 |
| implementation | working, tested software | `src/`, 86 tests (78 runnable without torch); report Ch. 4 |
| results | measured, not estimated | receipts; report Ch. 5 |
| comparison with published work | same protocol, corpora stated | matrix; report Ch. 5.7 |
| analysis | explains the numbers, including the bad ones | `DESIGN_REVIEW.md`; report Ch. 5 |
| conclusion | what was shown, and what was not | report Ch. 6 |
| novelty | what is new, stated plainly | plan §0; report Ch. 1.4 |
| presentation | poster, slides, demo | deliverables 5–7 |
| documentation | reproducible by a third party | `project-context/`, protocol, receipts |

---

## 8. Risk register

| # | risk | P | impact | mitigation | trigger to act |
|---|---|---|---|---|---|
| R1 | C0 does not travel to ISIC 2019 | M | high | treat it as the first finding; report both; the study becomes a transfer study | Phase B exit |
| R2 | C8 does not beat C0 | M | medium | **report it.** The study is an attribution study; a negative result is a result | Phase C exit |
| R3 | re-key drop exceeds 0.05 IoU | L | high | it is a security failure, not an accuracy one — reported as such, and it becomes the headline limitation | C10 receipt |
| R4 | Kaggle quota insufficient | M | medium | 6.3 GPU-h per configuration; two-stage 256²→512² training halves it if needed | any week at > 28 GPU-h |
| R5 | negative transfer on the held-out family | M | medium | C11 exists precisely to measure it; a drop is reported, not hidden | C11 receipt |
| R6 | semi-robust carrier is approximated by four scalars | **M** | **medium** | highest remaining design risk. Port `dev`'s Carrier B as a feature before the headline run if time allows | Phase C start |
| R7 | report written under time pressure | M | high | Phase E starts before the matrix finishes; Ch. 1–4 are writable now | end of Phase C |
| R8 | a number reaches a slide without a receipt | L | **severe** | `facts.json` is the gate; every number carries a status | every slide review |

R8 is the one that matters most. It has already happened once — two figures
(`0.987` coverage, `35.75 dB` worst-image PSNR) were found on the poster with no
locatable receipt and were removed. That is why the fact base exists.

---

## 9. Ethics and data governance

A medical imaging project must state this explicitly, and most undergraduate
projects do not.

| question | answer |
|---|---|
| Does this use patient data? | No identifiable data. ISIC 2019 is a public research dataset under its own terms; images are dermoscopic and carry no patient identifiers. |
| Does this make clinical claims? | **No.** The system reports whether an image has been altered. It does not diagnose, and no output is a clinical finding. |
| Is tampering performed on real clinical records? | No. Tamper families are synthesised on public research images only. |
| Is the saliency map a pathology annotation? | **No.** It is trained from a localisation loss and is never validated against a dermatologist's annotation. It must not be described as clinical saliency. |
| Is the released artefact secure? | **No, and this is disclosed.** The published notebook contains its key, which is required for reproducibility and which voids the security claim *for that artefact*. The property itself is measured independently in C9/C10. |
| What happens to generated images? | They are derived from public data and stay out of the repository. No dataset pixels are committed. |
| Reproducibility vs security | Favouring reproducibility and disclosing the cost is the honest choice, and it is stated before anyone asks. |

**One sentence for the report:** *this is a technical study of image integrity on
a public research corpus; it makes no diagnostic claim, uses no identifiable
patient data, and discloses the one respect in which its released artefact is not
secure.*

---

## 10. Publication plan

**Target:** a national conference paper, or an IEEE student track, in the
6–8 page range. The claim determines the venue, so the claim is fixed first.

| if the matrix shows | the paper is |
|---|---|
| C8 > C0, gates pass, re-key holds | *"A keyed evidence channel with learned refinement for medical image tamper localisation"* — the full study |
| C8 ≈ C0 | *"What a learned localiser adds to keyed fragile watermarking, and when it adds nothing"* — an attribution paper, still publishable, and honest |
| a gate fails | *"Diagnosing key leakage in learned tamper localisation"* — narrower, and arguably more interesting |

**The paper never claims SOTA.** The strongest admissible sentence is: *on a
protocol frozen before training, the assembly is compared against every
constituent, and the components that do not survive are reported.*

What must be complete before submission: author affiliations, the exact citation
details of every compared work (currently known by corpus and result, and flagged
in `docs/LITERATURE.md` as needing completion from the PDFs), and a replication
statement pointing at `src/protocol.py`.

---

## 11. Repository standards

The repository is a deliverable. These are the rules it holds itself to.

| rule | why |
|---|---|
| `src/protocol.py` is the single source of truth for the evaluation | a protocol that is imported cannot drift |
| every printable number lives in `facts.json` with a status | three documents told three different stories once; this is the fix |
| a receipt carries a commit hash and `code_dirty` | a receipt from a dirty tree is worthless |
| constants carry provenance (`LIT`/`CHOSEN`/`DERIVED`/`MEASURED`) | so a change is a recorded decision, not a diff |
| amendments are appended, never edited | the record of what changed and why is the asset |
| tests before claims | three real bugs were caught by tests and are documented |
| no dataset pixels in the repository | data governance, and keeps the clone inspectable |

### Progress log template

```markdown
## Week NN — <date range>
**Planned:** ...
**Done:** ...
**Numbers produced:** <fact ids, or "none">
**Blocked by:** ...
**Decision taken:** <one line, or "none">
**Next week:** ...
```

One entry per week, committed. It is the cheapest possible evidence of
supervision structure, and supervisors notice when it is missing.

---

## 12. The questions a supervisor will ask

| question | answer |
|---|---|
| What is new here? | A keyed, training-free evidence channel that a learned reader consumes without being able to forge it; a verifier that refuses with a cause; and a computed ceiling that shows why the published localisation bar is unreachable at small lesion sizes for any block-granular system. |
| What have you actually done? | A working keyed system measured on 12 970 images from a clean tree; a frozen protocol of twelve configurations; a learned architecture implemented and unit-tested. Not trained — and the matrix is labelled accordingly. |
| Did you beat the published work? | No claim is made. The comparison is not yet run, the corpora differ, and the paper says so. |
| Is this deep learning? | It has a learned component, and the project measures what that component is worth against a classical control instead of asserting that it helps. |
| Why only one dataset? | A scoped decision. It is shared ground with the reference work — one of its three corpora — and the limitation it creates is stated rather than hidden. |
| How do we know the numbers are real? | Frozen protocol, receipts with commit hashes, every ratio with its denominator, and one failing criterion printed at the same size as the successes. |
| What if the deep model doesn't help? | That is a reported outcome, and a publishable one. The study is designed so that a negative result is a result. |
