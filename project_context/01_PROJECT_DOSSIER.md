# A Fragile Watermarking for Medical Image Tamper Detection
## Project dossier — the single authority for design and execution

Written 2026-10-19. This document is the only design authority for the
project. It states what we want to do, how we will do it, and what we need to
do, in that order. An implementing chat should need nothing else.

**Companion documents in this package:** 04_PITFALLS_AND_TRAPS.md (read
before writing code), 02_ARCHITECTURE.md (module contracts), 03_PROJECT_FLOW.md
(phases and gates), 00_START_HERE.md (reading order and the first session).

**Three rules for whoever uses this document**
1. Nothing here is invented. Published numbers are attributed; parameters we
   chose ourselves are marked as chosen, not measured.
2. Nothing here is carried over from an earlier attempt. The project starts
   from zero: no prior result, no prior pilot figure, no prior code appears
   anywhere in this document.
3. If any other file disagrees with this one, this one wins.

---

# Part I — What we want to do

## 1. The problem

A medical image is a diagnosis. It travels: second opinions, referrals,
research datasets, insurance, telemedicine, messaging apps. Once it leaves the
clinic, nothing in the file says whether it still shows what the scanner saw.

Three edits matter, in ascending order of danger:

- **A finding added.** A lesion painted into a clear region. Something foreign
  entered the picture.
- **A finding removed or altered.** Pixels changed to flip an AI verdict.
- **A finding cloned over.** The quietest edit of all: tissue is copied from
  elsewhere in the same image and pasted over the lesion, so the lesion
  disappears and healthy-looking skin remains.

The third one is the reason this project exists. Every pixel in the tampered
image is still a real pixel from that same patient, at the same scale, under
the same lighting. There are no foreign traces for a passive detector to
catch. To an eye, and to most forensic networks, the image looks natural,
because in a literal sense it is natural — it is just no longer true.

## 2. Why existing work leaves this open

We reviewed fourteen bodies of work closely enough to say what each one proves
and where each one stops (the full comparison is in Section 15).

- **Learned proactive watermarks** (EditGuard, OmniGuard) protect an image
  before sharing and localise edits well on general photographs. Their marks
  are learned end-to-end; our own pilot observation, and the structure of the
  method, suggest that a block whose content was moved wholesale can still
  decode self-consistently, because the payload travels with the pixels.
- **The closest medical rival** (PFF-WM) is strong and recent: it protects
  diagnostic regions with a learned attention map and reaches 97.6% detection
  with IoU 0.83 across three datasets. But its region preference needs an A100
  to train, its decision rule is a learned pair of thresholds, and its
  copy-move test is a random patch move rather than the clinically meaningful
  case of tissue cloned over the lesion.
- **Classical self-embedding schemes** (the Slant family, reversible ROI
  schemes) are implementable and honest, and some recover data. Their
  evaluated attack sets, by and large, do not include the copy-move that
  worries us most.
- **Nobody reviewed** treats abstention as a first-class, separately justified
  output, and nobody packages the evaluation so that an independent reader
  can reproduce it without the authors.

So the opening is narrow and real: keep the classical, trainable-on-a-laptop
construction; make the region preference deterministic instead of learned;
make position binding the defence against copy-move; and make abstention a
measured output rather than a hidden failure.

## 3. What this project will deliver

Three promises, kept in strict order. The order is a safety requirement, not
a stylistic one.

**Protect.** Before an image is shared, write an invisible, keyed watermark
into it. The mark is fragile by design: it is *supposed* to break when the
image is tampered with. Extra protection mass is placed inside the diagnostic
region, because that is the part a fraud would attack.

**Indicate.** After the image comes back, extract the marks, compare them with
what the key says should be there, and report per region: TAMPERED (with
addresses), INTACT, or CANNOT SAY with a stated reason. Never a guess.

**Recover.** Where recovery data survives, reconstruct a visibly marked
approximation of the lost region. This runs only after localisation is final,
is never presented as evidence, and is held out until commissioned.

The trap that makes recovery dangerous is named and designed against: recovery
data stored inside the region it describes dies together with that region.
Our payload is placed outside the region it protects.

## 4. Research questions

1. Can a classical, zero-training, keyed dual mark localise same-image
   copy-move over the diagnostic region, where a learned proactive watermark
   of the EditGuard class does not?
2. Can the diagnostic-region preference that PFF-WM buys with A100 training be
   obtained deterministically from the ground-truth mask at no training cost,
   and what does that cost in image distortion inside the lesion?
3. Does a two-carrier decision rule with a fully specified trip table and a
   stated abstention reason produce honest behaviour under benign handling and
   under destructive handling?
4. Does the mechanism transfer across modality (dermoscopy to CT) and across
   year (2018 to 2019 dermoscopy) without retuning, and how large is the
   measured gap when it does not?

## 5. Scope: what is in, what is out

**In scope**
- Dermoscopy as the primary modality, with a full evaluation.
- Liver CT as a secondary modality, full battery, core metrics.
- A cross-year dermoscopy transfer report with zero tuning.
- Copy-move as a first-class attack target, including tissue cloned over the
  lesion.
- Benign handling: JPEG, mild noise, a resize round trip.
- Destructive handling: heavy compression, chaining, blur, noise, cropping.
- Block-aligned crops and shifts, burned-in text, classical inpainting
  removal.
- Honest abstention with four named reasons.

**Out of scope, with the reason stated**
- Arbitrary rotation, arbitrary rescaling, and print-scan: they break the
  eight-pixel addressing grid. Reported as geometry-change abstentions;
  resynchronisation is future work.
- Adversarial machine-learning perturbations: a different threat model that
  needs its own study.
- Splicing: joins the battery in the final phase.
- Generation-side watermarking: a different problem, kept in its own lane.
- Chest X-ray and mammography datasets: no masks in the first, size and DICOM
  friction in the second. Named as future modalities.
- Any clinical claim: this is an integrity prototype, never a diagnostic
  device.

## 6. The claim we will defend, and its price

Each contribution is stated together with what it costs us, because a claim
without a stated price is a claim an examiner will attack.

1. **Copy-move-first fragile watermarking.** Position-bound keyed tags make a
   moved block carry the wrong tag. *Price:* an abstention rate on
   low-capacity regions, and a localisation floor of one eight-pixel block.
2. **Deterministic region preference, zero training.** The ground-truth mask
   drives mark strength. *Price:* extra distortion inside the lesion, always
   reported as a separate quality figure.
3. **Mechanism isolation by falsification.** Removing the binding must make
   the system blind to copy-move; if it does not, the claim is false and we
   say so. *Price:* small pastes sit at the edge of detection and are
   disclosed as such.
4. **Designed abstention with separated reasons.** Capacity refusal, routine
   handling, geometry change and evidence conflict are distinguished.
   *Price:* the refused share becomes a headline number, not a footnote.
5. **A reproducibility package** — frozen battery, seed inventory, per-number
   receipts, a sealed held-out run. *Price:* slower iteration.
6. **Cross-modality honesty.** Per-modality batteries and reporting, no pooled
   score, a raw transfer gap published un-tuned. *Price:* the gap is visible.

## 7. Success criteria — the eight acceptance bars

The bars are fixed before any result is seen. The sealed expectations document
states how high each must be; this project states how each is computed. A bar
never moves after results exist; moving one is a written amendment plus a full
re-run.

| Bar | What it asks | How it is computed |
|-----|--------------|--------------------|
| Localisation | Do we find the wound and say where? | Block-F1 over eligible, attacked, answered cases, plus IoU where masks exist |
| Benign silence | Do we stay quiet under ordinary handling? | False-positive rate per benign condition against the stated line |
| Fidelity | Is the protected image still usable? | PSNR and SSIM, global and split lesion/background |
| Region preference | Does the lesion actually get more protection? | Lesion-versus-background distortion ratio, with the absolute cost reported |
| Binding | Is position binding what defeats copy-move? | The binding ablation must collapse copy-move performance |
| Head-to-head | Do we hold up against a learned proactive method? | Same cases, same thresholds for them, copy-move family |
| Honesty | Can every number be traced? | Receipt per number, sealed held-out run once |
| Reproducibility | Can someone else repeat it? | Headline table reproduced on a second machine within tolerance |

## 8. Threat model

- The attacker acts **after** protection: they edit a shared image.
- The attacker does **not** hold the key and cannot re-run the embedder.
- The attacker cannot touch the image **before** protection: pre-capture fraud
  is out of scope, because nothing can authenticate what it never saw.
- Success for the attacker is an edit our verdicts call INTACT.
- Success for us is every tested edit either localised or met with an honest
  abstention carrying a reason.
- Key custody in a real hospital is an operational problem, named as future
  work, not solved here.

---

# Part II — How we will do it

## 9. Design overview

The protected unit is a 512 by 512 image plus its diagnostic mask. The mark is
written in the luminance channel only; chroma is untouched and that is a
declared blind spot. The addressing grid is 64 by 64 blocks of 8 by 8 pixels,
giving 4096 addressed blocks.

Protection writes two marks:

- **Carrier A — fragile, position-bound tags.** Quantisation with a fixed
  step, one bit per detail coefficient. Any one-level change crosses a
  decision boundary, so the mark breaks on the smallest edit.
- **Carrier B — semi-robust texture reference.** A spread-spectrum mark in
  mid-frequency cosine coefficients. It survives ordinary handling, so it can
  tell "this image was recompressed" apart from "this image was edited".

Verification reads both and compares them. The pair of errors lands in one of
four cells of a trip table, and the ladder converts that into a verdict.

## 10. Preprocessing

- Decode, convert to luminance, resize to 512 by 512 with one fixed
  interpolation rule recorded in the receipt.
- Build the block map: 4096 blocks, each with an address.
- Compute a texture score per block: the local standard deviation in
  8-bit levels.
- Compute the mask-aligned region class per block: inside lesion, on the
  boundary, or background.
- The protected container is stored as **PNG**. JPEG enters only as an attack
  condition. This is not a stylistic choice: saving the container as JPEG
  would break the fragile mark at birth and confound recompression with
  tampering.
- Nothing below one 8 by 8 block, that is 64 pixels, is ever claimed. The
  measured granularity ceiling is reported as a percent of what is reachable.

## 11. Texture gate

A block with no texture cannot carry a mark without visible damage.

- Texture score below 3.0 (8-bit levels) in the **background** means the block
  is refused: recorded as a capacity refusal, never silently skipped.
- Blocks **inside the lesion** override the threshold and are always admitted,
  because the diagnostic region is exactly what must be protected. Their
  distortion cost is reported separately.
- The threshold 3.0 is a chosen starting value; it is validated on the primary
  validation split and frozen before results are collected.

## 12. Tag binder

For each admitted block, the tag is

    digest = coarse-summary(LL coefficients of the block)   <- never modified
    tag    = HMAC-SHA256(key, image-id ‖ block-address ‖ digest)

The key is secret and never travels with the image. The address is the block's
position in the grid.

**The digest must never be taken from the coefficients that carry the mark.**
If it were, embedding would change the content the tag depends on, so every
clean block would recompute a different tag and the system would report the
whole image as tampered. The digest therefore comes only from the LL
low-frequency summary, which the embedder never touches, and it is quantised
coarsely so that small changes from benign handling do not cross a
quantisation boundary.

The digest is a handful of bits: the four level-two LL coefficients per block,
each quantised by a coarse step Q, concatenated. Q is a design parameter,
started at 32 levels and then validated: the stability test is that under
JPEG 90 and JPEG 75, the great majority of blocks must keep an identical
digest. If they do not, Q is too fine and the design is wrong, not the test.

**Slot fitting.** HMAC-SHA256 yields 256 bits; the block has 60 slots. The
first 60 bits of the expanded MAC are used. This costs security margin
honestly — 60 bits of forgery resistance, ample for tamper detection and
recorded as such.

**Why this answers copy-move.** A block copied from position A and pasted at
position B carries A's tag. The verifier computes the tag that B should have
and compares. A moved block therefore fails at every slot, not at a few, which
is what makes the response to a clone qualitatively different from the
response to a recompression.

## 13. The two carriers

**Carrier A — fragile quantisation.**

    embed:  q = round(c / Δf) * Δf ;  q' = q + (bit == 1 ? +Δf/4 : -Δf/4)
    read:   bit = (round((c' - round(c'/Δf)*Δf) / (Δf/2)) + 1) mod 2

with Δf = 8 levels and an offset of Δf/4 = 2 levels. The offset must be a
quarter step, not a half step: at a quarter step any one-level change crosses
the boundary, which is what "fragile" means here.

Coefficients are taken from the Haar detail sub-bands only — LH, HL, HH —
never from LL. LL carries the image's structure; marking it is what makes
watermarks visible.

**Slot budget.** Per 8 by 8 block, two Haar levels give 16 coefficients per
sub-band at level one and 4 at level two. Across three detail sub-bands that
is (16 + 4) × 3 = 60 bits per block, or 245,760 bits per image. The HMAC is
expanded across those slots; no block depends on a single bit.

**Carrier B — semi-robust spread spectrum.**

    c' = c + β · w · p

where p is a key-derived pseudo-random sequence of unit energy over the
mid-frequency band, w is the mark bit, and β is the strength. Strength is
modulated by the mask in the same functional form PFF-WM uses for attention,
with the mask replacing attention:

    β(block) = 0.1 · (1 + λ · mask(block))

with λ chosen at validation and recorded. This gives region preference without
a single trained parameter.

**Clipping guard.** A quantisation step can push a coefficient past the 8-bit
range. Any block whose marked coefficients would clip at 0 or 255 is recorded
as a capacity refusal rather than allowed to clip silently; clipped pixels
destroy the tag and manufacture false tampering.

**Determinism.** The colour transform, the resize interpolation, the Haar
transform and the PNG encoder are all pinned by library and version, because
two implementations that differ by a rounding rule produce two different
tamper masks. The round-trip test is part of Phase One: embed, save, reload,
verify, expect INTACT.

**Declared distortion budget.** Per region, the maximum allowed change is
declared before experiments and checked afterwards, separately for lesion and
background.

## 14. Verifier and ladder

**The verifier never sees the diagnostic mask.** The mask shapes the embedder
only. At verification the system has the received image and the key, nothing
else, because in the real world the mask does not travel with the image. Any
design that reads the mask during verification is measuring an advantage it
would not have in use; this is a standing validity rule.

Two errors are computed per block: the fragile error rate δf and the
semi-robust error rate δsr. The trip table has four cells, and all four are
defined:

| Fragile | Semi-robust | Reading | Verdict |
|---------|-------------|---------|---------|
| low | low | nothing happened | INTACT |
| high | low | mark broke, reference survived | CANNOT SAY — routine handling |
| high | high | both marks broken | TAMPERED |
| low | high | contradiction | CANNOT SAY — evidence conflict |

The ladder then refines a TAMPERED reading in four rungs:

1. Counts per block.
2. Two-phase corroboration: does the neighbouring block agree that this one
   is a wound edge?
3. Texture context: is this a flat region where the mark never sat well?
4. Otherwise abstain, with one of the four reasons: capacity refusal,
   routine handling, geometry change, evidence conflict.

**Thresholds.** τf and τsr are grid-searched on authentic validation images to
a target joint false-positive rate of 0.01%, then frozen per modality. The
values live in the battery sheet, not in anyone's memory.

**Key control.** A wrong key must return CANNOT SAY — key mismatch. It must
never return TAMPERED. This is tested once per dataset and reported.

## 15. What each paper gave us

Fourteen works, each with what we take and what we refuse. Nothing here is
decoration: every "take" lands somewhere in Sections 9 to 14.

| Work | What it establishes | We take | We refuse |
|------|--------------------|---------|-----------|
| EditGuard (CVPR 2024) | Learned dual watermark; 37.77 dB / 0.949; F1 0.966; thresholds 0.2 clean, 0.4 degraded | The head-to-head protocol and its published operating point | Retraining it; putting learned weights in our evidence path |
| PFF-WM (2025) | Fragile QIM step 8 in detail bands; semi-robust DCT reference; decision pair; ρ above 5; 97.6% detection, IoU 0.83; rotation weakness 11.3% at 10° | Decision-pair logic, fragility ratio, the never-touch-LL rule, the benign suite and the 32×32 copy-move as cross-validation | Learned attention, autoencoder detector, A100 training, classifier explanations, any numeric cross-paper comparison |
| SMARTMed (2026) | Slant 2×2 blocks, 8-bit payload, chaotic embedding, 44.91 dB / 0.9624, 94.9% detection, 97.9% localisation | The block recipe as our classical baseline on our own battery; the attack taxonomy | Its headline numbers as our targets; DNN fingerprinting |
| Slant self-embedding family | Recovery payload mapping, robustness to removal and collage | Mapping and payload patterns for the recovery extension | Blind adoption: its attack set lacks copy-move |
| ROI-reversible (2026) | ROI / non-ROI payload split, difference expansion, +28.14 dB recovery | The payload-outside-the-region architecture | The "reversible" contract, which is a different promise |
| Amrullah two-level detection | Two-phase refinement, cross-checks | The refinement pattern as the ladder's middle rung | — |
| OmniGuard (CVPR 2025) | Stronger learned comparator; repository public but released step by step, pipeline pending | A conditional phase-two comparison only if an inference-capable checkpoint appears | Cross-table number fusion |
| GenPTW | In-generation watermarking, a different problem | The scope fence it draws | The method |
| FractalForensics (ACM MM 2025) | Entry-to-patch binding; manipulations omitted from training; proof that cross-paper numbers are not comparable | Convergent precedent for position binding; black-box discipline | Face-domain training and headline targets |
| AdvMark (IJCAI 2024) | Watermarks can overlap forgery signals | The law that learned parts stay out of the evidence path | — |
| LaMa (WACV 2022) | Fourier-convolution inpainting, Apache-2.0 | The final-phase removal attacker | Using it mid-project |
| Wong–Memon (2001) | The address idea | Honest classical floor baseline | Any novelty claim over it |
| Holliman–Memon | The collage attack | Threat framing | — |
| Celik (2002) | Hierarchy lineage | Vocabulary | — |

Where a number is quoted above it is the published figure, reproduced here as
a baseline for context — never as something this project has measured.

## 16. Datasets

Three tiers, deliberately different in depth. Per-modality batteries and
per-modality reporting always; a pooled cross-modality score is forbidden,
because a single number across two modalities hides exactly the difference we
are trying to measure.

### Primary — ISIC 2018 Task 1 (dermoscopy)

- 2594 dermoscopic JPEGs with released lesion-segmentation masks, one PNG per
  image, curated by practising dermatologists, EXIF stripped.
- Licence: the official page lists the collection as CC-0, while the
  challenge's own citation note asks users to honour the CC BY-NC 4.0
  attribution terms of the aggregate training set. **We treat it as
  attribution-required and non-commercial.** We publish image identifiers and
  computed numbers; we never redistribute pixels.
- Source images vary in size, roughly 540×720 up to 4439×6708. The fixed
  resize to 512×512 is part of preprocessing and is recorded in the receipt.
- Role: mechanism proof, every ablation, every figure.
- Split: training-free method, so the split is validation for threshold
  selection and a sealed held-out set for the reported result.

### Secondary — LiTS (liver CT)

- 131 training volumes and 70 test volumes of contrast-enhanced abdominal CT
  from seven institutions. Pixel-wise liver and tumour masks are released for
  the training volumes only; the test labels stay with the organisers, so we
  use the training volumes and split them ourselves.
- Licence: CC BY-NC-SA, non-commercial research. Numbers and identifiers
  published, pixels never redistributed.
- Region definition: the diagnostic region is the **tumour mask**. The liver
  mask is used only to give the slice a meaningful boundary for context; a
  slice that contains liver but no tumour is a matched negative, used for
  benign and capacity measurements. This mirrors the dermoscopy case, where
  the region is the lesion mask.
- Preparation: NIfTI to axial 512×512 PNG slices, liver window fixed at width
  160 HU and level 60 HU, Hounsfield values clamped to ±200 and mapped
  linearly to 8 bits. Tumour-bearing slices sampled at a fixed stride plus
  matched negatives, capped per volume. Every parameter in the receipt.
- Role: cross-modality generality with exact region splits.

### Tertiary — ISIC 2019 (cross-year dermoscopy)

- 25,331 images across the eight diagnostic classes, CC BY-NC, no
  segmentation masks.
- It contains the 2017 and 2018 predecessors, so overlap with our primary set
  is certain. **The tertiary set is defined as the 2019 images whose
  identifiers are absent from our 2018 working set**, and a de-duplication
  receipt is mandatory.
- No masks means no region split. The supported measurements are: quality
  envelope, benign silence, paste detection where we place the paste and
  therefore own the ground truth, and abstention rates.
- Role: same-modality, new-distribution transfer with the primary operating
  point applied as it is. The raw gap is published.

### Excluded, with reasons

- **CheXpert** (224,316 radiographs, Stanford Research Use Agreement,
  registration-gated): no segmentation masks, and the agreement conflicts with
  open packaging. Named as a future modality, conditional on a segmentation
  module.
- **CBIS-DDSM** (mammography, 163 GB DICOM, CC BY 3.0): size and DICOM
  friction on a student machine. Named as future.
- **MIMIC-CXR and similar credentialed sets**: excluded by doctrine, because
  credentialed access is incompatible with a package anyone can re-run.

## 17. The battery — 22 frozen conditions

Four families: 6 pastes, 5 benign, 7 degrades, 4 structure. Every condition
carries its parameter, the verdict class we expect, and the failure that
counts against us.

| # | Family | Condition and parameter | Expected | Failure that counts |
|---|--------|------------------------|----------|---------------------|
| 1 | Paste | copy-move 32×32, background to background | addressed tamper blocks | silent INTACT |
| 2 | Paste | copy-move 32×32, healthy tissue over the lesion | addressed tamper blocks | silent INTACT, above all inside the lesion |
| 3 | Paste | copy-move 64×64, healthy tissue over the lesion | addressed tamper blocks | silent INTACT |
| 4 | Paste | three 32×32 clones in one image | all three wounds addressed | any wound left unaddressed |
| 5 | Paste | copy-move 16×16 | tamper blocks or abstention; never INTACT | silent INTACT or a fabricated address |
| 6 | Paste | copy-move 8×8, exactly one block | tamper signal or abstention | silent INTACT or a fabricated address |
| 7 | Benign | JPEG quality 90 | no tamper claim | any tamper claim |
| 8 | Benign | JPEG quality 75 | no tamper claim | any tamper claim |
| 9 | Benign | JPEG quality 50 | no tamper claim | any tamper claim |
| 10 | Benign | Gaussian noise, σ = 1 level | no tamper claim | any tamper claim |
| 11 | Benign | resize 90% and back to 512 | no tamper claim | any tamper claim |
| 12 | Degrade | JPEG quality 30 | abstention or tamper signal | silent INTACT |
| 13 | Degrade | JPEG quality 10 | abstention with reason | silent INTACT |
| 14 | Degrade | double compression 75 then 50 | abstention or tamper signal | silent INTACT |
| 15 | Degrade | chain: scale 0.8 → JPEG 60 → scale 1.25 → JPEG 60 | abstention, handling or geometry | silent INTACT |
| 16 | Degrade | Gaussian blur σ = 2.0 | abstention with reason | silent INTACT |
| 17 | Degrade | Gaussian noise σ = 8 levels | abstention with reason | silent INTACT |
| 18 | Degrade | 70% centre crop then resize to 512 | abstention, geometry | silent INTACT |
| 19 | Structure | block-aligned crop, 24 pixels per side | addressed blocks along the cut | INTACT at the cut |
| 20 | Structure | block-aligned shift, 8 pixels | addressed border strips | INTACT at the borders |
| 21 | Structure | burned-in text, 64×24 box | addressed blocks over the text | INTACT over the text |
| 22 | Structure | classical inpainting removal, lesion-sized mask, Telea and Navier–Stokes | addressed blocks at the wound | INTACT at the wound |

**The rule underneath the table.** Degrade and structure conditions may
legitimately return CANNOT SAY. None of them may ever return INTACT, because
that is the silent failure. Benign conditions may name benign handling; none
of them may ever claim tampering.

**Geometry doctrine.** Only block-aligned crops and shifts are inside the
addressed envelope, because the grid must stay aligned. Arbitrary rotation,
rescaling and print-scan break alignment and are reported as geometry-change
abstentions.

**Lineage.** The families and the quantities measured follow the StirMark
benchmark's test taxonomy — false alarm, robustness, quality, capacity, speed.
StirMark's geometric-desynchronisation attacks, built for robust ownership
marks, are replaced here by the block-aligned structure family.

After freeze, any change to this table requires a dated amendment and a full
re-run.

## 18. Evaluation protocol

- **Quality.** PSNR and SSIM, global, worst case, and split lesion versus
  background. LPIPS as a secondary perceptual measure, computed once on the
  trial subset rather than the whole sweep.
- **Localisation.** Block-F1 at stated denominators — the headline uses
  eligible, attacked, answered cases; all-block and decided-only variants are
  fenced and reported. IoU where masks exist. The granularity ceiling is
  reported as a percent of reachable.
- **Benign.** False-positive rate per condition against the stated line, plus
  the fragility ratio ρ per region: semantic-tamper response divided by
  routine-handling response.
- **Abstention honesty.** Coverage-versus-risk curves, following the
  selective-prediction literature, and the refused share reported as a
  headline rate.
- **Comparisons.** Paired tests on identical cases, bootstrap intervals,
  passive baselines treated leniently, trivial bounds always shown.
- **Multiplicity.** Holm–Bonferroni correction within each condition family;
  effect sizes with 95% bootstrap intervals; the cell size printed in every
  row of every table.
- **Minimum evidence.** No rate reported on fewer than 300 images without a
  small-sample flag.
- **Runtime.** Wall-clock per 100-image batch on named CPUs, GPU job clocks,
  and Big-O per module. The verification path must run on a laptop CPU, and
  that is measured, not assumed.
- **Failure gallery.** A curated figure of misses, each with its reason.
- **Seed inventory.** Paste sampler, split generator, JPEG library pin,
  classifier initialisation, bootstrap seed — all recorded.

## 19. Falsification checks

Seven ablations, each designed to break one claim. Same battery, same
denominators, one removal at a time.

1. **Binding cut** — remove the address from the tag. Must go blind on
   copy-move. If it does not, contribution one is false.
2. **Corroboration cut** — remove the semi-robust carrier. The trip table
   collapses to one bit.
3. **Gate opened** — admit every block. Measures the quality price of refusing
   nothing.
4. **Tilt flattened** — uniform strength. Measures what region preference buys.
5. **Gate flattened** — uniform threshold. Measures the price of mask
   awareness.
6. **Ladder collapsed** — one threshold, no abstention. Measures what
   abstention saves.
7. **Calibration removed** — the primary operating point applied to the
   secondary set without recalibration. Measures the calibration cost.

No mechanism ships without its falsification check.

## 20. Recovery extension — designed, gated, held out

Coarse thumbnails or region-prioritised payloads placed in non-region blocks,
authenticated first, applied only after localisation is final.

Gates, all of which must pass: a capacity proof; a coincidence guard, meaning
the reference must survive the attack that destroys its region, analysed by gap
analysis first; and a liability framing, meaning every reconstructed region
carries a visible corner marker, a metadata flag, and the word approximation in
every export.

Default: not built. It is commissioned or it is not.

---

# Part III — What we need to do

## 21. Prerequisites

**Accounts and access**
- A Kaggle account, for the free GPU tier: T4 dual or P100, roughly 30 GPU
  hours per week with a weekly reset, 12-hour sessions. Budget against the
  floor, never the ceiling.
- No paid compute. No multi-GPU. No large-network training without approval.

**Software, all free**
- Python 3.10 or later; NumPy, SciPy, OpenCV; PyWavelets for the Haar
  transform; scikit-image for SSIM; PyTorch for LPIPS and for running released
  checkpoints; Pillow; pandas and matplotlib for tables and figures.
- A JPEG library pinned by version, because the battery depends on its exact
  behaviour.

**Hardware**
- One ordinary laptop for the whole CPU path. The mid-review must complete
  without the GPU.

## 22. Data acquisition checklist

| Dataset | What to fetch | Size | Licence handling |
|---------|---------------|------|------------------|
| ISIC 2018 Task 1 | Training images and Task 1 ground-truth masks | About 10.4 GB images, 26 MB masks | Attribution and non-commercial; identifiers published, pixels never |
| LiTS | Training volumes only (131), with masks | Large; fetch once, keep archives off the machine | CC BY-NC-SA; numbers published only |
| ISIC 2019 | Images for the tertiary set | About 9 GB | CC BY-NC; de-duplicate against 2018 before use |

For each: record the download date, the file hash, and the licence line in the
data receipt. A dataset that is not receipted does not exist.

## 23. Work phases with acceptance checks

Each phase ends in something checkable. A phase that cannot be checked did not
finish.

**Phase Zero — ground.**
Load all three datasets with identifiers; sign the licence table; freeze the
environment; build the seed inventory.
*Done when:* three receipts exist and the environment reproduces.

**Phase One — core.**
Preprocess, gate, binder, both carriers, verifier, ladder, end to end on the
primary trial slice.
*Done when:* addressed verdicts on 50 trial images, and the runtime table
exists.

**Phase Two — battery and baselines.**
Implement all 22 conditions, the comparison protocol, the trivial bounds, the
Wong–Memon floor and the SMARTMed re-implementation.
*Done when:* the battery sheet is frozen and every baseline runs through one
identical procedure.

**Phase Three — evaluation.**
Full primary run, all seven ablations, secondary run, tertiary transfer,
failure gallery, survey table.
*Done when:* every figure and table in the thesis exists and carries receipts.

**Phase Four — GPU slice.**
EditGuard head-to-head, FractalForensics zero-shot domain-gap pilot, optional
advisory classifier.
*Done when:* each job has a receipt, or a blocked-with-receipt note.

**Phase Five — writeup.**
Thesis, ninety-second demonstration with the dermoscopy and CT cases
switchable, poster.
*Done when:* delivered to faculty.

**Phase Six — final.**
Splicing joins the battery, LaMa as the removal attacker, the recovery
commission decision, the sealed held-out run exactly once, external check,
polish.
*Done when:* the held-out run is recorded and cannot be repeated.

## 24. Deliverables

1. **The report.** Problem, literature, method, experiments, results,
   limitations — following this document's structure.
2. **The demonstration.** Protect, attack, indicate — on a dermoscopy image
   and a CT slice, switchable live, on a laptop processor. Recovery only if
   commissioned.
3. **The tables and figures.** Quality, localisation, robustness, ablations,
   trivial bounds, failure gallery, runtime.
4. **The reproducibility package.** Frozen battery sheet, seed inventory,
   per-number receipts, code, environment record.
5. **The review materials.** Slides and poster, matching the report's numbers
   exactly.

Nothing counts as done until its numbers carry receipts.

## 25. Risks and how each is handled

| Risk | Handling |
|------|----------|
| Copy-move turns out harder than expected | Position binding is the designed answer, and the binding ablation will tell us honestly if it fails |
| No GPU time | The entire CPU path is complete without it; GPU only strengthens |
| EditGuard environment fights back | Fixes are documented, and a blocked job is recorded as blocked rather than hidden |
| Scope creep | Frozen battery, fixed claim list, tiered dataset depth |
| Licence trouble | Three cards, a receipt per dataset, and a never-redistribute rule |
| 2018 and 2019 overlap | De-duplication receipt is mandatory before the tertiary run |
| The student is asked to defend unfamiliar parameters | Every parameter in this document has a one-line justification |
| Recovery payload too dense | Gap analysis first; the extension is off by default |

## 26. Decisions still open

These are genuine choices, not omissions. Each is to be settled before the
phase that needs it.

1. **Battery size.** This document fixes 22 conditions. If the sealed
   expectations document names a different set, that difference must be
   reconciled in writing before Phase Two, not after results.
2. **Bar thresholds.** The bars are named and their computation fixed here;
   the numeric heights live in the sealed document. Publishing them would end
   their protection as a held-out check.
3. **Recovery.** Commissioned or not. Default is not.
4. **OmniGuard.** Only if an inference-capable checkpoint is released before
   the GPU window closes.
5. **Modality four.** CheXpert needs a segmentation module first; it is not a
   this-project item.

---

# Appendices

## A. Glossary

- **Abstention** — a deliberate verdict: cannot decide, and here is why. A
  designed output, not a failure.
- **Bar** — a pre-registered acceptance criterion with a fixed computation
  rule.
- **Battery** — the frozen set of 22 attack and handling conditions.
- **Binding** — a mark authenticates its own position; a copied mark never
  validates somewhere else.
- **Capacity refusal** — a block too flat to carry a mark, recorded as a
  reason, never silently skipped.
- **Carrier** — one of the two marks: the fragile tags or the semi-robust
  reference.
- **Comparison protocol** — the single frozen procedure every baseline runs
  through, so no method gets its home turf.
- **Coverage** — the fraction of cases the system answers rather than abstains
  on.
- **Evidence conflict** — the carriers disagree in a way that matches neither
  tampering nor handling; the ladder stops rather than guesses.
- **Fragility ratio (ρ)** — semantic-tamper response divided by
  routine-handling response; the design target is above five.
- **Frozen transfer** — evaluation on a new dataset with no tuning at all.
- **Geometry-change abstention** — the grid no longer aligns; the honest answer
  is CANNOT SAY.
- **Receipt** — the dated record behind one number: command, seed, image
  count, code version.
- **Recovery approximation** — reconstructed content, visibly marked, never
  evidence.
- **Tamper coincidence** — the trap where recovery data dies with the block it
  describes; guarded by placing payloads outside the region.
- **Trivial bound** — the score of a no-skill baseline; every method must
  clear it.

## B. References

**Comparators and prior art.** EditGuard, CVPR 2024, arXiv 2312.08883. PFF-WM,
Khaldi et al., Intelligent Systems with Applications 31 (2026) 200684.
SMARTMed, Scientific Reports 16:26353. OmniGuard, CVPR 2025, arXiv 2412.01615.
GenPTW, arXiv 2504.19567. FractalForensics, ACM Multimedia 2025, arXiv
2504.09451. AdvMark, IJCAI 2024. LaMa, WACV 2022, arXiv 2109.07161.

**Classical lineage.** Wong and Memon, 2001. Holliman and Memon, 2000. Celik
et al., 2002. Chen and Wornell, QIM, 2001. Fridrich, fragile authentication
and its limits, 2002.

**Methods.** SSIM, Wang et al., 2004. LPIPS, Zhang et al., 2018. Telea
inpainting, 2004. Navier–Stokes inpainting, Bertalmío et al., 2000. StirMark
benchmark, Petitcolas, Anderson and Kuhn, 1998; Petitcolas, 2001. Selective
classification and risk–coverage, El-Yaniv and Wiener, 2010; Geifman and
El-Yaniv, 2017.

**Datasets.** ISIC 2018 Task 1, challenge.isic-archive.com. LiTS, arXiv
1901.04056, competitions.codalab.org/competitions/17094. ISIC 2019, same
archive. CheXpert and CBIS-DDSM are named only as excluded.

## C. Working rules for the implementing chat

1. **Verify before claiming.** Every external fact — a paper number, a link, a
   dataset size, a licence — is checked against its source before it is used.
   Anything unverified is labelled unverified.
2. **Never invent a number.** Behaviour that has not been measured is
   described qualitatively.
3. **A receipt or it did not happen.** Every figure in the report traces to a
   command, a seed, an image count and a code version.
4. **Do not open the sealed expectations** until results exist and are frozen.
   It exists to check us afterwards, not to steer us during.
5. **No silent scope change.** If reality forces a change, it is written down
   with the date and the reason, and the affected runs are repeated.
6. **State the failure plainly.** A miss is reported as a miss, in the same
   table as the hit.
7. **The title is fixed** and is never reworded.

---

End of dossier. This is the whole project: what it is for, how it is built,
and what has to happen, in the order it has to happen.
