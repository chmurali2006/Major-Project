# Project flow — from an idea to a defended thesis

Project: **A Fragile Watermarking for Medical Image Tamper Detection**
Companion to the project dossier. This file is the narrative of how the work
actually moves: what happens in what order, what must be true before the next
thing starts, and where the decisions are.

---

## 1. The idea in one paragraph

A medical image is evidence of what the scanner saw, and after it leaves the
clinic nothing in it says whether it still is. The quietest fraud is not a
foreign object pasted in — it is the patient's own tissue cloned over the
lesion, leaving every pixel genuine and the picture false. This project
protects an image before it is shared, with an invisible keyed mark that is
designed to break on tampering, concentrates its protection on the diagnostic
region, and binds every block to its own address so a moved block carries the
wrong name. When the image comes back, the system says where it was changed, or
says honestly that it cannot tell and why. It never guesses.

---

## 2. The journey of one image

This is the whole system in nine steps. Everything else in the project is a
measurement of these nine steps.

1. **Capture.** A 512 pixel dermoscopy image arrives with its lesion mask. In the
   CT case, a windowed slice arrives with a tumour mask.
2. **Describe.** The image is split into 4096 blocks of 8 by 8 pixels. Each
   block gets an address, a texture score, and a region class.
3. **Refuse.** Blocks too flat to hold a mark are refused and recorded. Lesion
   blocks are never refused.
4. **Name.** Each admitted block gets a tag: a keyed hash of the image
   identity, the block's own address, and a coarse summary of the block's
   low-frequency content. The coarse summary is deliberately taken from the part
   of the block the mark never touches.
5. **Protect.** The tag is written into the fine detail coefficients with a
   quantisation step small enough that a one-level change breaks it. A second,
   sturdier mark is written into mid-frequency coefficients to act as a
   reference for what ordinary handling does.
6. **Share.** The PNG leaves the clinic. The key does not.
7. **Attack.** In the evaluation, the battery applies one of twenty-two
   conditions: a clone, a recompression, a crop, a burn-in.
8. **Judge.** The verifier reads both marks and produces two errors per block.
   The pair lands in one of four cells, and the ladder turns that into
   TAMPERED with addresses, INTACT, or CANNOT SAY with a reason.
9. **Account.** Every verdict becomes a table row with a denominator, and every
   table row keeps a receipt.

---

## 3. The shape of the build

Six phases. Each has an entry condition, an exit check, and a gate that must be
passable before the next one starts. The gate exists so that a mistake is
caught in the phase that made it rather than in the results chapter.

### Phase Zero — Ground

**Build:** dataset download scripts, licence table, environment freeze, seed
inventory, the empty repository with `config.py`.
**Entry:** nothing. This is the start.
**Exit check:** three datasets load and produce identifiers; the environment
manifest exists with pinned versions; the same script run twice produces
identical output.
**Gate:** if a dataset cannot be loaded, or a version cannot be pinned, the
project does not proceed. Two days here saves two months later.

### Phase One — Core mechanism

**Build:** preprocess, gate, binder, both embedders, container, verifier,
ladder. One image in, one verdict out.
**Entry:** Phase Zero closed.
**Exit check:** the six pre-flight checks in the pitfalls document all pass,
plus the digest stability measurement — under JPEG 90 and JPEG 75, the
proportion of blocks that keep an identical digest is recorded. If it is low,
the quantisation step Q is too fine and the design is corrected here.
**Gate:** the in-memory round trip must be perfect. Not 99 percent. Perfect. A
system that reports clean images as tampered cannot be measured afterwards.

### Phase Two — Battery and baselines

**Build:** all twenty-two conditions, the receipt writer, the trivial bounds,
the classical floor, the re-implemented classical baseline, the comparison
protocol.
**Entry:** Phase One closed.
**Exit check:** the battery sheet is written, hashed and frozen; every baseline
runs through the same interface on the same cases; the sheet contains, for each
condition, its exact parameters and the failure that counts against us.
**Gate:** no baseline may be tuned after this point, and no condition may be
added without a dated amendment.

### Phase Three — Measurement

**Build:** the full primary run, the seven falsification checks, the secondary
run, the tertiary transfer, the failure gallery, every table and figure.
**Entry:** Phases One and Two closed.
**Exit check:** every table in the thesis exists and carries receipts; the
ablation results are in; the gallery is curated with a reason per miss.
**Gate:** this is where the honest result appears, whatever it is. If binding
does not defeat copy-move, the ablation says so and the claim is rewritten. The
gate is not "the result is good", it is "the result is measured and reported".

### Phase Four — GPU slice

**Build:** the EditGuard head-to-head, the zero-shot domain-gap pilot, the
optional advisory classifier.
**Entry:** Phase Three done, because the GPU work is supplementary and must not
gate the main result.
**Exit check:** each job has a receipt, or a blocked-with-receipt note
explaining what was attempted and what failed.
**Gate:** the mid-review is already complete without this. GPU time adds a
comparison, never a dependency.

### Phase Five — Write-up and demonstration

**Build:** the thesis, the ninety-second demonstration, the poster.
**Entry:** Phase Three closed; Phase Four either done or recorded as blocked.
**Exit check:** the demonstration runs the same code path as the experiments,
on images from the frozen battery, live, on a laptop processor.
**Gate:** every number on a slide is generated from the same result files as
the thesis.

### Phase Six — Final hardening

**Build:** splicing joins the battery, the inpainting attacker, the recovery
commission decision, the sealed held-out run — executed exactly once — and an
external check.
**Entry:** the thesis is otherwise complete.
**Exit check:** the held-out run is recorded and cannot be re-run; the
limitations chapter matches what was actually found.
**Gate:** the held-out number is the one in the abstract, or the abstract
changes.

---

## 4. Dependency order, drawn

    data ──► preprocess ──► gate ──► binder ──► embed A ──► embed B
                                                    │
                                                    ▼
                                                 container
                                                    │
                                                    ▼
                                                verifier ──► ladder
                                                    │            │
                                                    ▼            ▼
                                                 battery ──► metrics
                                                    │
                    baselines ──────────────────────┤
                                                    ▼
                                             comparison protocol
                                                    │
                                                    ▼
                                    ablations ──► thesis tables
                                                    │
                                                    ▼
                                        demonstration ──► held-out run

Two facts this diagram makes visible. **Nothing can be measured before the
verifier is trusted**, which is why Phase One's gate is absolute. And **the
battery and the baselines must both exist before any comparison number is
produced**, because a comparison produced before the protocol exists is a
comparison on unequal cases.

---

## 5. The decisions and when they must be made

| Decision | Needed by | Default if undecided |
|----------|-----------|----------------------|
| Battery composition reconciled with the sealed expectations | Start of Phase Two | The twenty-two conditions in the dossier |
| Texture threshold, validated rather than assumed | End of Phase One | 3.0 background, lesion override |
| Digest quantisation step Q | End of Phase One | 32 levels, adjusted by the stability test |
| Region-strength coefficient lambda | End of Phase One | Validated on primary validation |
| Threshold grid target | Phase Two | Joint false-positive rate of 0.01% |
| Secondary calibration rule | Phase Three | Declared validation calibration |
| Recovery commissioned or not | Phase Six | Not commissioned |
| OmniGuard included or not | Phase Four | Only if an inference-capable checkpoint exists |

Each of these has a default, so the project never stalls waiting for a
decision. The default is used and recorded; a later change is an amendment with
a re-run.

---

## 6. What "mid-review ready" means

A defensible mid-review needs exactly four things, and none of them is a
result:

1. The mechanism working end to end on a handful of images, demonstrated live.
2. The battery frozen and printed, so the examiner can see the contract.
3. The first honest measurement — even if it is small, even if it is
   unflattering — with a receipt.
4. A clear statement of what is not yet done and why.

An examiner at mid-review is testing whether the plan is real. A working
mechanism plus a frozen battery answers that. A slide full of predictions does
not.

---

## 7. How the work fails if the order is ignored

- **Building the battery before the verifier is trusted** produces a battery
  tuned to a broken verifier, and every later number is meaningless.
- **Running the primary experiment before the baselines exist** produces a
  result that has to be redone once the comparison protocol reveals the
  denominators were wrong.
- **Doing the GPU comparison early** makes supplementary work gate the main
  result, which is exactly backwards for a project that must survive without a
  GPU.
- **Writing the report before the gallery exists** produces a claims-first
  document that the gallery then contradicts.
- **Touching the held-out set early** destroys the only number in the thesis
  that nobody, including you, could have tuned.

The order in Section 3 is not a preference. Each phase exists to make the next
phase's result trustworthy.
