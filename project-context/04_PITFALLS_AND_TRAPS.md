# Pitfalls and traps — read this before writing any code

Project: **A Fragile Watermarking for Medical Image Tamper Detection**
Written 2026-10-19. Companion to the project dossier.

Thirty-five ways this project goes wrong. Each one is written as: what it looks
like, why it happens, the guard that prevents it, and the early warning sign.
The list is ordered by how much damage the trap does if it is not caught.

**The five that will actually kill the project if ignored:**
Trap 1 (JPEG container), Trap 4 (tag computed from marked pixels),
Trap 11 (abstention gaming), Trap 15 (thresholds tuned on test data),
Trap 18 (changing the system after seeing results). Everything else is
survivable. Those five are not.

---

## Family A — traps that silently destroy the watermark

These produce a system that runs, prints numbers, and is simply wrong. They are
the most expensive because nothing crashes and nothing looks odd.

### Trap 1 — Saving the protected container as JPEG

**Looks like:** everything works in memory; after a save-and-reload, the
verifier reports most of the image as tampered. Quality figures look excellent.
**Why:** a fragile mark lives in the fine detail coefficients. JPEG quantises
exactly those coefficients. Saving as JPEG is itself a tampering attack, so the
mark breaks at birth.
**Guard:** the container is PNG, always. JPEG exists only as a battery attack
condition. The round-trip test (embed, save, reload, verify, expect INTACT) runs
on every single image before it enters any experiment.
**Early warning:** clean-image false positives that appear only after the file
has been written and read back.

### Trap 2 — Using a half-step offset instead of a quarter-step

**Looks like:** detection works but is coarse; small edits pass as INTACT.
**Why:** the quantisation offset must be a quarter of the step (2 levels for a
step of 8). At a half step, a one-level change does not cross the decision
boundary, so the mark is not fragile in the sense the project claims.
**Guard:** step 8, offset 2, asserted in a unit test that perturbs a
coefficient by one level and requires a bit flip.
**Early warning:** a one-level change anywhere in the image leaves the verdict
INTACT.

### Trap 3 — Marking the LL band

**Looks like:** the watermark works and is robust — too robust. Fidelity drops
and the mark becomes visible as blockiness. Fragility is gone.
**Why:** LL carries the structure and the bulk of the energy. Changing it is a
visible change and also a change that survives almost any processing.
**Guard:** an assertion in the embedder that only LH, HL and HH coefficients
are written. The LL array is copied through untouched and hash-checked before
and after embedding.
**Early warning:** visible blocking in a difference image; quality below 40 dB.

### Trap 4 — Computing the tag from the coefficients you are about to mark

**Looks like:** every clean image reports as fully tampered. Nothing works at
all, and it is easy to misdiagnose as a threshold problem.
**Why:** the tag is a function of block content. If the content includes the
coefficients that carry the tag, the act of embedding changes the input to the
function, so the verifier recomputes a different tag from the one embedded.
**Guard:** the digest comes only from the LL summary, which is never written,
and it is quantised coarsely so benign handling does not shift it. Test: embed,
immediately verify in memory with no processing at all, require INTACT on
100% of admitted blocks.
**Early warning:** the in-memory no-processing round trip is not perfect. It
must be. That is the first test in the whole project.

### Trap 5 — Clipping at 0 and 255

**Looks like:** false tamper reports concentrated in very dark or very bright
regions — image corners, saturated highlights, air in CT.
**Why:** a quantisation step near the edge of the 8-bit range cannot be applied;
the value saturates, the embedded bit is lost, and the verifier sees a
mismatch.
**Guard:** before embedding, check whether the marked value would fall outside
0 to 255. If it would, record the block as a capacity refusal with its reason.
Never let a clip pass silently.
**Early warning:** false positives that cluster spatially, always at the
extremes of brightness.

### Trap 6 — Resizing after embedding

**Looks like:** the system works at one size only; any processing that changes
the grid destroys everything.
**Why:** every coefficient, and therefore every tag, depends on the addressing
grid. Resample after embedding and every address now holds different content.
**Guard:** resizing happens once, in preprocessing, before the gate. The
protected output is always 512 by 512. The resize rule and its interpolation
are recorded in the receipt and never change mid-experiment.
**Early warning:** you find yourself writing code to resize a protected image.

### Trap 7 — Colour-conversion drift

**Looks like:** clean-image false positives that vanish if you skip saving, or
that appear only on some images.
**Why:** RGB to luminance to RGB is lossy. Two libraries, or two versions of one
library, round differently. The mark is written in luminance; if the returned
RGB is re-converted to luminance by a different path, coefficients shift by a
level or two.
**Guard:** pin the conversion (library, version, coefficients, rounding rule).
Store and verify luminance-plane consistency with a round-trip test that
asserts a maximum absolute difference. Prefer working in float and quantising
once, at the end.
**Early warning:** a histogram of clean-image error rates with a long tail and
no obvious cause.

### Trap 8 — Integer versus float Haar mismatch

**Looks like:** embedding works; verification on the same array in float works;
verification after a round trip through uint8 fails.
**Why:** the Haar transform is linear, but the inverse in integer arithmetic
rounds. If embed uses one convention and verify uses another, every coefficient
is off by a fraction of a level.
**Guard:** one implementation of the transform pair, used by both embedder and
verifier, with a test that asserts perfect reconstruction on random arrays.
Never let two code paths own the transform.
**Early warning:** small but nonzero clean-image error everywhere, uniform
across the image.

### Trap 9 — The two carriers fighting each other

**Looks like:** clean-image false positives that appear only when the
semi-robust carrier is enabled.
**Why:** if the spread-spectrum mark lands on the same coefficients the fragile
tags occupy, each carrier's embedding is the other's tampering.
**Guard:** explicit frequency separation, enforced in code. Carrier A owns the
Haar detail coefficients. Carrier B owns specific mid-frequency DCT indices,
listed in a fixed table. A unit test asserts the two index sets are disjoint.
**Early warning:** enabling Carrier B raises the Carrier A error rate on
untouched images.

---

## Family B — traps that make the method fail by design

### Trap 10 — Comparing a tag against itself

**Looks like:** copy-move is never detected, and the system looks perfect on
clean images.
**Why:** a natural but wrong implementation recomputes the digest from the
received pixels and compares it to the tag extracted from those same received
pixels. If the block is internally consistent — which a moved block is — the
comparison agrees and the block passes.
**Guard:** the comparison is always between the extracted tag and the tag the
**key and the address** say should be there. The address must enter the hash.
Test: move a block, and require that the moved block fails while an untouched
control block passes.
**Early warning:** your copy-move test passes at the same rate as your clean
test, and both are near perfect.

### Trap 11 — Abstention gaming

**Looks like:** every metric improves. False positives go to zero, precision
goes to one, and the system "never makes a mistake".
**Why:** the system can always say CANNOT SAY. Abstention is the perfect escape
hatch, and every metric computed only over answered cases rewards it without
limit.
**Guard:** coverage is reported next to every accuracy figure, always, and the
refused share is a headline number. A result is only meaningful as a pair:
(coverage, accuracy on covered cases). Additionally, the abstention rate on
benign conditions must be low, or the system is simply refusing to work.
**Early warning:** a table with excellent accuracy and no coverage column.

### Trap 12 — Denominator drift

**Looks like:** two tables in the same report disagree about the same system.
**Why:** block-F1 can be computed over all blocks, over attacked blocks, over
answered blocks, or over eligible blocks. Each gives a different number, and if
the choice is made per table, the numbers become incomparable.
**Guard:** the denominators are defined once, in code, and every table prints
which one it used. The headline is fixed in advance.
**Early warning:** you cannot reproduce your own earlier number.

### Trap 13 — The mask leaking into verification

**Looks like:** excellent lesion localisation that collapses the moment the mask
is not available.
**Why:** if the verifier reads the diagnostic mask, it has been told where the
lesion is, which is precisely the thing a real system would not know.
**Guard:** the verifier's interface accepts the received image and the key,
nothing else. Enforce it at the function signature, so the mask is physically
unreachable. If you need region awareness at verification, it must be
reconstructed from the image, and that reconstruction is itself measured.
**Early warning:** a verification function with a mask parameter.

### Trap 14 — A copy-move test that is really a shift test

**Looks like:** copy-move scores look great, but the binding ablation changes
nothing.
**Why:** if the "copy" includes the surrounding context, or is placed adjacent
to its source, it looks like a translation of a region rather than a clone. It
also fails the spirit of the threat: the fraud is tissue from one location
covering a different location.
**Guard:** define source and target regions explicitly, non-overlapping, at a
stated minimum distance, recorded in the battery sheet. Verify that the source
and target blocks have different addresses by construction.
**Early warning:** the binding ablation does not hurt copy-move performance.

### Trap 15 — Thresholds tuned on test data

**Looks like:** results that are excellent and do not survive a rerun on new
images.
**Why:** grid-searching the decision thresholds to maximise performance on the
same images you report on is fitting the test set.
**Guard:** thresholds are searched on a validation split that is disjoint from
the reported set, using only authentic images to hit a target false-positive
rate. The held-out set is touched once, at the end, and never used for any
decision.
**Early warning:** you change a threshold after seeing a result on the same
images.

---

## Family C — traps that make the results dishonest

These do not break the code. They break the thesis.

### Trap 16 — Deciding what counts as a detection after seeing the results

**Looks like:** "our system detected the tampering" is true under a definition
invented after the fact.
**Why:** with a per-block mask, "detected" can mean one block flagged, the
majority flagged, the centroid inside the wound, or IoU above a cut-off. The
choice changes the number enormously.
**Guard:** the detection rule is fixed in the battery sheet before any run:
we define a case as detected when the flagged region overlaps the true wound
above a stated IoU threshold, and every other definition is reported as a
secondary figure.
**Early warning:** the definition is described in prose and not in code.

### Trap 17 — Reporting only the survivors

**Looks like:** "of the cases the system answered, 92% were correct", with no
mention that it answered a third of them.
**Why:** selective reporting is the natural consequence of an abstaining
system, and it flatters.
**Guard:** every accuracy appears as a pair with coverage. Every table has the
refused count.
**Early warning:** a percentage with no denominator.

### Trap 18 — Changing the system after seeing a bad cell

**Looks like:** twenty-two conditions quietly becoming twenty-one, or a
parameter changing "just for the CT set".
**Why:** the battery is the contract. Rewriting it after results is
p-hacking with extra steps.
**Guard:** the battery sheet is hashed and frozen. A change requires a dated
amendment, a written reason, and a full re-run of every affected condition.
**Early warning:** a result that exists for a condition the frozen sheet does
not contain.

### Trap 19 — Multiple comparisons without correction

**Looks like:** several "significant" improvements across twenty-two
conditions, most of which are noise.
**Why:** twenty-two conditions times several metrics is a large family of
tests; at the usual threshold, some will look significant by chance.
**Guard:** Holm–Bonferroni within each family, effect sizes with bootstrap
intervals, and the sample size printed in every cell.
**Early warning:** a claim of improvement with no interval and no correction.

### Trap 20 — Comparing on different cases

**Looks like:** "we beat the baseline by six points".
**Why:** the baseline was run on a different subset, at a different resolution,
with a different preprocessing, or with thresholds tuned for it rather than
taken from its authors.
**Guard:** one comparison protocol. Same images, same seeds, same
denominators, the baseline authors' own thresholds, and the deviations
declared in the table caption. If a method's home turf is different, say so
rather than silently adapting it.
**Early warning:** two rows in a table produced by two different scripts.

### Trap 21 — Presenting somebody else's number as ours

**Looks like:** a results table that mixes published values with measured ones.
**Why:** it is convenient, and it is fatal in a viva.
**Guard:** published values appear only in the literature comparison, in a
table that says so, with the citation in the row. Our tables contain only what
we measured.
**Early warning:** a number in a results table that no receipt points to.

---

## Family D — traps that destroy reproducibility

### Trap 22 — An unpinned JPEG library

**Looks like:** results shift between machines, or after a package update, by
a point or two.
**Why:** JPEG encoders differ in their chroma subsampling defaults, quantisation
tables and rounding. The entire benign family depends on exact encoder
behaviour.
**Guard:** pin the library and its version, record it in the environment
receipt, and refuse to run if the version differs from the frozen one.
**Early warning:** the JPEG ladder produces different files on a second machine.

### Trap 23 — Unseeded randomness

**Looks like:** slightly different numbers every run; a figure that cannot be
regenerated.
**Why:** paste placement, split assignment, bootstrap resampling and any
sampling step all use randomness.
**Guard:** one seed inventory, one seeding function called at process start,
and the seed written into every receipt.
**Early warning:** two runs of the same command disagree.

### Trap 24 — Numbers typed by hand into the report

**Looks like:** a table that is almost right.
**Why:** transcription. It is the single most common cause of an examiner
finding a number that does not match the code.
**Guard:** every table and figure is generated by a script from result files.
The report embeds generated output, never retyped digits. A check script
re-reads the results and regenerates every table before submission.
**Early warning:** a number in the report that you cannot trace to a file.

### Trap 25 — Environment drift between run and write-up

**Looks like:** the thesis describes a configuration that no longer exists.
**Why:** libraries get upgraded, and the code evolves while the analysis is
frozen.
**Guard:** the environment is frozen at Phase Zero and recorded: library
versions, Python version, hardware. Runs are tagged with that environment's
identifier.
**Early warning:** you cannot say which version produced a figure.

---

## Family E — traps in the data

### Trap 26 — ISIC 2018 and 2019 overlap

**Looks like:** the tertiary transfer result looks implausibly good.
**Why:** the 2019 set contains the 2017 and 2018 images. If any of them are in
your primary working set, the "transfer" set is partly your training
distribution.
**Guard:** the tertiary set is defined as the 2019 identifiers absent from the
primary working set, and the de-duplication receipt is produced before the
tertiary run and stored with it.
**Early warning:** a transfer gap that is suspiciously small.

### Trap 27 — Near-duplicate lesions split across validation and held-out

**Looks like:** validation-tuned thresholds work suspiciously well held-out.
**Why:** the same lesion is often photographed several times, sometimes years
apart. Random splitting puts the same patient on both sides without any
identifier collision.
**Guard:** perceptual-hash near-duplicate detection across the split, with a
stated distance threshold, recorded in the split receipt. Split by cluster, not
by image.
**Early warning:** visually identical images in two different splits.

### Trap 28 — Mask resampling with the wrong interpolation

**Looks like:** region classes that do not line up with the lesion; a halo of
half-lesion blocks; region statistics that drift.
**Why:** masks are binary. Resizing a mask with bilinear or bicubic
interpolation invents fractional values; thresholding them afterwards produces
a boundary that belongs to neither the lesion nor the background.
**Guard:** masks are resized with nearest-neighbour only, and the mask's own
resize rule is recorded separately from the image's. A mask overlay check is
part of the data receipt.
**Early warning:** region class counts that vary between two runs of
preprocessing.

### Trap 29 — Licence breach by convenience

**Looks like:** a repository or a shared folder containing dataset pixels.
**Why:** it is easier to copy a folder than to write a download script.
**Guard:** datasets are downloaded by script, never committed, never
redistributed. Only identifiers and numbers are published. The licence line for
each dataset appears in the data receipt and in the thesis appendix.
**Early warning:** a zip of images in the project folder.

### Trap 30 — Saturated or degenerate CT slices

**Looks like:** capacity refusals piling up on one dataset; quality figures
that look artificially good because much of the image was refused.
**Why:** the liver window clamps Hounsfield values at ±200. Regions beyond the
clamp become flat, carry no texture, and cannot hold a mark.
**Guard:** report the refusal rate per dataset as a headline number, inspect
the clamped fraction, and state it in the limitations. Never let a refusal
inflate a quality average by removing the hard cases.
**Early warning:** a refusal rate above a few percent without explanation.

### Trap 31 — Sampling only tumour-bearing slices

**Looks like:** a secondary result that cannot be compared with anything.
**Why:** if every CT slice contains a tumour, the negative class does not
exist and the false-positive rate is meaningless.
**Guard:** the sampling rule includes matched negatives at a fixed ratio, fixed
in advance and recorded per volume.
**Early warning:** a false-positive rate computed on images that all contain
tumours.

---

## Family F — traps in the claim

### Trap 32 — Overclaiming the scope

**Looks like:** "detects all forms of medical image tampering".
**Why:** enthusiasm, and a sentence that sounds strong in a slide.
**Guard:** every claim names its condition and its denominator: "on the
twenty-two-condition battery, at this coverage, on these datasets". Anything
outside that is future work, stated as such.
**Early warning:** a sentence with "all" in it.

### Trap 33 — Clinical language

**Looks like:** "diagnosis-safe", "clinically validated", "hospital-ready".
**Why:** the project protects integrity. It says nothing about whether an image
is diagnostically correct, and it is not a medical device.
**Guard:** the claim lock. The design property is "never distort the diagnostic
region beyond a declared budget, and say why when it cannot answer". Those
words only.
**Early warning:** the word clinical anywhere in a title or abstract.

### Trap 34 — Claiming novelty over the classical lineage

**Looks like:** presenting position-bound block authentication as new.
**Why:** it is not. Wong–Memon did address binding in 2001; Holliman–Memon
attacked it; Celik added hierarchy.
**Guard:** the contribution is the combination, the evaluation, and the honesty
machinery — copy-move-first design, deterministic region preference, designed
abstention, frozen battery. Cite the lineage explicitly and claim only the
delta.
**Early warning:** a novelty sentence that would be true of a 2001 paper.

### Trap 35 — The demonstration that runs different code

**Looks like:** the live demonstration looks better than the thesis table.
**Why:** the demonstration is written fresh, on hand-picked images, often with looser
thresholds or a friendlier case.
**Guard:** the demonstration calls the same evaluation code path as the
experiments, on images drawn from the frozen battery. The demonstration is a viewer, not
a second implementation.
**Early warning:** a demonstration script that reimplements anything.

---

## The two-minute pre-flight check

Before any experiment is believed, all six of these must pass:

1. Embed, verify in memory with no processing at all, on 100 images: 100%
   INTACT on admitted blocks, zero tampered blocks. If not, stop — Trap 4.
2. Embed, save as PNG, reload, verify: identical result to step 1. If not —
   Trap 1 or Trap 7.
3. Perturb one pixel by one level in one block: that block reports a changed
   verdict. If not — Trap 2.
4. Cut one block and paste it at a distant address: the pasted block reports
   tampered, the source block reports intact. If not — Trap 10 or Trap 14.
5. Verify with the wrong key: every block reports CANNOT SAY with key mismatch,
   never TAMPERED.
6. Run the same command twice: byte-identical result files. If not — Trap 23.

If all six pass, the implementation is sound enough to measure things with. If
any one fails, no result produced afterwards means anything.
