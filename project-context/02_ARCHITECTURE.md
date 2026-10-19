# Architecture — modules, contracts, and data

Project: **A Fragile Watermarking for Medical Image Tamper Detection**
Companion to the project dossier. This file turns the dossier's design into
something buildable: twelve modules, each with its inputs, its outputs, its
invariants and its test.

---

## 1. The data model

Everything downstream is built on two records.

**BlockRecord** — one per 8 by 8 block, 4096 per image:

    address          integer 0..4095, row-major
    row, col         integers
    region_class     lesion | boundary | background
    texture_score    float, local standard deviation in 8-bit levels
    admitted         boolean
    refusal_reason   none | low_capacity | clipping
    digest           integer, coarse LL summary, used in the tag
    tag_bits         60 bits, what should be embedded
    extracted_bits   60 bits, what was read back
    fragile_error    float 0..1, fraction of tag bits that disagree
    robust_error     float, normalised correlation loss of Carrier B
    verdict          tampered | intact | cannot_say
    reason           none | routine_handling | capacity_refusal |
                     geometry_change | evidence_conflict | key_mismatch

**ImageRecord** — one per image:

    image_id         string, the dataset identifier
    luma             512x512 uint8, the working channel
    blocks           64x64 array of BlockRecord
    stats            quality, coverage, verdict counts
    receipt          dataset, seed, code version, environment id, parameters

---

## 2. Module map

    preprocess  ->  gate  ->  binder  ->  embedder A
                                      ->  embedder B  ->  container writer
                                                              |
                                                          (outside world)
                                                              |
    container reader -> verifier -> ladder -> reporter

### Module 1 — Preprocess

**In:** image file, mask file, dataset name.
**Out:** luma array 512x512 uint8, mask array 512x512 boolean, block map with
addresses, texture scores, region classes.
**Rules:** resize once, with a pinned interpolation rule; resize the *mask*
with nearest-neighbour only; convert colour with a pinned transform; record
every parameter in the receipt.
**Invariants:** output shape fixed; deterministic; no dependence on the mask
beyond producing region classes.
**Test:** two runs on the same file produce identical arrays; mask overlay
matches the lesion at the stated tolerance.

### Module 2 — Gate

**In:** texture scores, region classes, marked-value clipping check.
**Out:** `admitted` flag and `refusal_reason` per block.
**Rules:** lesion blocks are always admitted, overriding the threshold;
background blocks need a texture score of at least 3.0; any block that would
clip at 0 or 255 is refused with reason `clipping`.
**Invariants:** refusals are recorded, never silent; the admitted count is
reported.
**Test:** a synthetic flat block is refused; a synthetic lesion block with the
same flatness is admitted.

### Module 3 — Tag binder

**In:** image id, block address, LL summary, key.
**Out:** 60 bit `tag_bits` per admitted block.
**Rules:** digest is a coarse quantisation of the four level-two LL coefficients
(step Q, started at 32, validated); tag is HMAC-SHA256 over image id, address
and digest; the first 60 bits are used.
**Invariants:** the digest never reads a coefficient that the embedder writes.
**Test:** changing any single detail coefficient does not change the tag;
changing the address changes every bit of the tag.

### Module 4 — Embedder A, fragile tags

**In:** luma, admitted blocks, tag bits.
**Out:** marked luma.
**Rules:** Haar transform; write only LH, HL, HH; quantisation step 8 with
offset 2; one bit per coefficient across 60 slots per block.
**Invariants:** LL untouched; inverse transform reconstructs exactly when no
bits are written; write count equals admitted blocks times bits used.
**Test:** perturb a coefficient by one level and require a bit flip; assert LL
identical before and after.

### Module 5 — Embedder B, semi-robust reference

**In:** marked luma from Module 4, region classes.
**Out:** marked luma.
**Rules:** block DCT; a fixed mid-frequency index table; spread-spectrum
addition with a key-derived unit-energy sequence; strength
`0.1 * (1 + lambda * mask_value)` where mask_value is 1 inside the lesion and 0
outside, and lambda is validated.
**Invariants:** its index set is disjoint from the Haar detail coefficients
used by Carrier A.
**Test:** enabling Carrier B must not change the Carrier A error rate on
untouched images.

### Module 6 — Container writer and reader

**In:** marked luma plus original colour.
**Out:** PNG file; on read, luma plus colour.
**Rules:** lossless only; metadata in a sidecar, never in pixels; the read path
performs the same pinned luma conversion as the write path.
**Invariant:** write then read returns the identical luma array, bit for bit.
**Test:** array equality assertion after a real file round trip.

### Module 7 — Verifier

**In:** received image, key. **Nothing else.**
**Out:** per block extracted bits, fragile error, robust error.
**Rules:** recompute the tag from the key, the image id and the address, using
the digest recovered from the received LL; extract the embedded bits from the
detail coefficients; both errors per block.
**Invariants:** the function signature must not accept a mask, a caption, or
any side channel. A wrong key yields `key_mismatch` and CANNOT SAY, never
TAMPERED.
**Test:** the six pre-flight checks in the pitfalls document.

### Module 8 — Ladder

**In:** per block errors.
**Out:** verdict and reason per block.
**Rules:** the four-cell trip table, then four rungs — counts, two-phase
corroboration with the neighbouring block, texture context, abstention with a
reason.
**Invariants:** every verdict carries a reason code, including INTACT.
**Test:** synthetic error patterns produce the expected verdict for all four
cells.

### Module 9 — Reporter

**In:** an array of ImageRecords.
**Out:** addressed tamper mask, image roll-up sentence, metrics records, tables.
**Rules:** denominators defined once and printed; coverage always adjacent to
accuracy; every metric carries its n.
**Invariant:** no number leaves this module without its denominator.

### Module 10 — Battery runner

**In:** a frozen condition specification, an image record.
**Out:** a transformed image plus a receipt describing exactly what was done.
**Rules:** every random parameter seeded; every encoder pinned; the condition
identifier written into the output name.
**Invariant:** running the same condition twice produces byte-identical
output.

### Module 11 — Comparison protocol adapter

**In:** a baseline name, the frozen case list, the shared seeds.
**Out:** the baseline's verdicts on exactly those cases.
**Rules:** one interface, four implementations: our system, the classical
floor, the re-implemented classical baseline, and any released weights.
**Invariant:** a baseline cannot choose its own cases, its own seeds or its own
denominators.

### Module 12 — Metrics

**In:** verdicts plus ground truth.
**Out:** block-F1 at three stated denominators, IoU, false-positive rate per
condition, coverage, fragility ratio, confidence intervals.
**Rules:** implemented once, imported everywhere; bootstrap with a fixed seed.
**Invariant:** recomputing any published table from stored verdicts reproduces
it exactly.

---

## 3. Embed, in order

    read image and mask
    luma, mask = preprocess(image, mask)
    for each block:
        texture, region = describe(block)
        admitted, reason = gate(texture, region, clipping_check(block))
    for each admitted block:
        digest = coarse_ll_summary(block)
        tag    = hmac(key, image_id, address, digest)[:60]
    write detail coefficients by quantisation (Carrier A)
    write mid-frequency DCT spread spectrum (Carrier B)
    assert LL unchanged
    save as PNG
    write receipt

## 4. Verify, in order

    read PNG
    luma = pinned_conversion(file)
    for each block:
        extracted = read_detail_bits(block)
        digest    = coarse_ll_summary(block)        # from the received LL
        expected  = hmac(key, image_id, address, digest)[:60]
        fragile_error = hamming(extracted, expected) / 60
        robust_error  = correlation_loss(block)
    for each block:
        verdict, reason = trip_table(fragile_error, robust_error)
        verdict, reason = ladder(verdict, reason, neighbours, texture)
    assemble addressed mask
    report with denominators and coverage

**One thing to notice.** The expected tag is recomputed from the *received* LL
digest. That is deliberate: the LL is not marked, so on an untouched image the
received digest equals the embedded one. On an edited image the difference
either shows up in the detail bits (which the tag predicts) or in the digest
itself (which changes the expected tag and therefore breaks every slot). Both
routes lead to the same verdict, which is why the design is robust to not
knowing the original.

---

## 5. Suggested code layout

    src/
      config.py          frozen parameters, one place, no magic numbers elsewhere
      preprocess.py      Module 1
      gate.py            Module 2
      binder.py          Module 3
      embed_fragile.py   Module 4
      embed_robust.py    Module 5
      container.py       Module 6
      verify.py          Module 7
      ladder.py          Module 8
      report.py          Module 9
      battery/
        conditions.py    the 22, one function each, frozen parameters
        runner.py        Module 10
      baselines/
        protocol.py      Module 11
        trivial.py       always-tampered, always-intact
        wong_memon.py    classical floor
        smartmed.py      re-implementation
        external.py      released checkpoints, if available
      metrics.py         Module 12
      seeds.py           the single seeding function
      receipts.py        receipt writing and hashing
    tests/
      test_roundtrip.py      the six pre-flight checks
      test_transform.py      perfect reconstruction
      test_binder.py         digest independence, address sensitivity
      test_trip_table.py     all four cells
      test_determinism.py    same command, same bytes
    data/                download scripts only, never pixels
    runs/                one folder per experiment, containing receipts

**The rule that keeps this clean:** `config.py` is the only file allowed to
contain a number. Every other module imports from it. When an examiner asks
"where did 3.0 come from", there is exactly one place to look, and it carries a
comment saying whether the value is from the literature or was chosen here.

---

## 6. Invariants worth asserting in code, not in prose

1. LL coefficients identical before and after embedding.
2. Carrier A and Carrier B index sets disjoint.
3. Write-read round trip is bit identical.
4. One-level perturbation flips a bit.
5. Wrong key yields CANNOT SAY with key mismatch.
6. Verify never receives a mask.
7. Every block has a verdict and a reason.
8. Every metrics record has a denominator.
9. Same command, same bytes.
10. No module other than `config.py` contains a tunable constant.

An invariant that is only written in a document will be violated by the third
week. An invariant that is asserted by a test will not.
