> **Historical / pre-audit material.** This file is not evidence for the current audited recipe. See root `VERIFICATION.md` and use fresh measured receipts for submission. In particular, any-overlap block IoU is not a universal ceiling.

# Literature survey

**Purpose.** Not a list of summaries. A comparison on axes that expose the gap
this project occupies, so that chapter 2 of the report can be written from it and
chapter 1.4 can point at it.

**Comparison axes**, fixed before reading anything, so the survey cannot be
retrofitted to the conclusion:

| axis | why this axis |
|---|---|
| **embedder** | what actually carries the mark — a rule, or a network |
| **keyed?** | whether an attacker without the secret can construct a valid mark |
| **abstains?** | whether the system can decline to answer, and say why |
| **granularity** | image-level, block-level or pixel-level output |
| **corpus** | because a number without its corpus is not a number |
| **degradation** | whether routine processing is modelled or assumed away |

The first three are where this project differentiates. The last three are where
most reported numbers stop being comparable to each other.

---

## 1. The shape of the field

Three generations, and the transition between them is the story.

**First generation — fragile watermarking (1997–2005).** The mark is a function of
the image content and the key, embedded so that any modification destroys it.
Yeung and Mintzer [1] and Wong [2] established the form; Fridrich [3] formalised
what "secure" means for such a scheme; Celik et al. [4] and Lin and Chang [5] added
localisation and recovery. This generation has the property every later system
loses: **the mark cannot be forged without the key**, because it is a function of
the key and the content rather than of a trained model.

Its weakness was also structural: the mark is fragile in a way that does not
distinguish *an editor* from *a codec*. A JPEG round trip destroys it exactly as
a paste does, so these systems localise tampering but cannot tell routine handling
from an attack. That is the "benign vs malicious" problem, and it stayed open.

**Second generation — robust watermarking for medical images (2010s).** The
response was to make the mark survive processing. The cost is the property that
mattered: a mark designed to survive modification is a mark that survives
tampering. These systems are identification schemes, not integrity schemes.

**Third generation — learned watermarking (2023–2026).** Deep networks replace
the hand-built embedder, and accuracy jumps. This is the generation the comparison
set belongs to, and it inherits two problems from the first two:

1. **A learned embedder is invertible in principle.** An attacker with the model
   and enough image pairs trains the inverse. The security is computational and
   undocumented, not structural.
2. **Every one of them returns a binary verdict.** None reports "I cannot
   determine this", so a recompressed image, a wrong key, or a flat region is
   forced into an answer the system has no basis for.

Neither is a criticism of their accuracy. Both are statements about what they do
not report — and they are the two axes on which this project differs.

---

## 2. Comparative table

`—` means the work does not report the quantity. `n/s` means the corpus is not
stated in the source available to us.

| ref | method | year | embedder | keyed | abstains | granularity | detection | localisation | corpus |
|---|---|---|---|---|---|---|---|---|---|
| [1] | Yeung–Mintzer fragile mark | 1997 | rule (key-dependent LUT) | **yes** | no | pixel | — | reported qualitatively | standard test images |
| [2] | public-key watermark | 1998 | rule | **yes** | no | block | — | — | standard test images |
| [3] | security of fragile marks | 2002 | theory | **yes** | no | — | — | — | analysis |
| [4] | hierarchical watermarking | 2002 | rule (hierarchy) | **yes** | no | block | — | localisation + recovery | standard test images |
| [5] | hierarchical tamper detection & recovery | 2005 | rule | **yes** | no | block | — | localisation + recovery | standard test images |
| [6] | LSB baseline | — | rule (LSB) | no | no | pixel | fails benign | — | — |
| [7] | SECURENet | — | learned | no | no | — | 90.8 % / AUC .951 / 78 ms | — | CheXpert ᵇ |
| [8] | TFPDD | — | learned | no | no | — | 91.2 % / AUC .958 | — | CheXpert ᵇ |
| [9] | ConMark | — | learned | no | no | — | 93.5 % / AUC .965 | — | CheXpert ᵇ |
| [10] | DeepMark | — | end-to-end learned | no | no | — | 94.1 % / AUC .971 / 61 ms / 18.4 M | — | ᵇ |
| [11] | ASFW | — | learned, attention-guided | no | no | — | 95.2 % / AUC .978 | — | CheXpert ᵇ |
| [12] | **PFF-WM** | 2026 | learned: fragile wavelet + semi-robust DCT | no | no | pixel | **97.6 % / AUC .989 / 44 ms / 15.1 M** | **IoU .832 / acc 98.1 / F1 90.4** | CheXpert, **LiTS**, ISIC 2019 |
| [13] | WAM | 2025 | segmentation-as-watermark | no | no | pixel | — | >85 % mIoU (59 % after JPEG-80) | n/s |
| [14] | OmniGuard | 2025 | learned, degradation-aware | no | no | pixel | — | localises under AIGC/compression | n/s |
| [15] | SMARTMed | 2026 | hybrid | no | no | pixel | 94.9 % | 97.9 % | n/s |
| [16] | post-quantum DCT | 2026 | rule + classifier | partial | no | region | 98.1 % (three-class) | — | n/s |
| **this work** | keyed fragile + learned reader | — | **rule, keyed** | **yes** | **yes, with cause** | block + pixel | 0.99992 (ISIC 2018) | 0.9936 block-level | ISIC 2018 / 2019 |

ᵇ = numbers taken from the reference paper's table rather than from the work
itself. **These are secondary citations.** See §6.

**Two columns carry the argument.** Read down `keyed` and `abstains`: every
system from [7] to [16] is `no` and `no`. That is not an accident of this
selection — it is the state of the third generation.

---

## 3. What the reference system actually prices

The ablation in [12] is the most useful table in the field, because it is the only
one that prices its own components:

| configuration | AUC | IoU | Δ IoU |
|---|---|---|---|
| full system | 0.989 | **0.832** | — |
| minus RefineNet (raw AE error) | 0.989 | 0.770 | **−0.062** |
| minus dual watermark (fragile only) | 0.952 | 0.765 | −0.067 |
| minus stacked autoencoder | 0.963 | 0.744 | −0.088 |
| minus attention guidance | 0.971 | 0.801 | −0.031 |

Read that table and the field's problem becomes visible: **the localiser is worth
more than the attention module**, and the dual carrier is worth more than either.
Nobody would guess that ordering from the architecture diagrams, and no other
paper reports it.

It is also the direct justification for the design of this project. If components
can be priced, they can be compared — and a study that prices every component
against every other on one protocol is answering a question the field has left
open.

**A caveat to carry.** The `AUC 0.989` row for "minus RefineNet" is reported as
`0.989` in one table and inferred as unchanged from another; there is an internal
inconsistency in the source. It must be cited carefully or not at all.

---

## 4. Gap analysis

Five gaps. Each is a column or a cell in §2, not an opinion.

### G1 — No system is keyed any more

The first generation had structural security and lost it in the second, and the
third never had it. A learned embedder is a function of weights; an attacker with
the weights and enough pairs trains the inverse. None of [7]–[16] reports a
forgery test.

**Addressed by:** this work. The tag is a function of the key, the block address
and the block's own content, so a fabricated region requires computing a valid tag
under a secret. This is measured in configuration C9 — the full system with the
key removed — rather than asserted.

### G2 — No system can decline to answer

Every work in the table returns a binary verdict. But a recompressed image, a
flat lesion region that could never hold a mark, and a wrong key are three
entirely different situations, and a binary verdict conflates them with tampering.

**Addressed by:** this work. INTACT / TAMPERED / CANNOT SAY, with a causal reason
code (`capacity_refusal`, `routine_handling`, `geometry_change`,
`evidence_conflict`, `key_mismatch`) and refusals scored as selective risk against
coverage.

### G3 — Localisation numbers are not comparable across works

[12] reports 0.832 on LiTS with synthetic lesion insertion; [13] reports mIoU on
watermarks occupying ~10 % of the image; [15] reports 97.9 % with no stated area
distribution. These are not the same measurement, and no work states the lesion-size
distribution that would make them comparable.

**Addressed by:** this work, and this is the contribution that needs no external
corpus. A 64×64 decision grid bounds achievable pixel IoU as a function of target
radius — 0.809 at radius 32, 0.854 at 48, 0.937 at 128 — **independent of the
model**. Any localisation figure without its target size beside it is
underdetermined, and that is a property of the metric, not of any one paper.

### G4 — The benign/malicious distinction is unexamined

Fragile systems destroy under compression; robust systems survive tampering. The
middle ground — a mark that survives routine handling but not editing — is claimed
by the dual-carrier designs but tested only incidentally, usually as a false-positive
rate over a small set of transformations.

**Only partly addressed by this work.** Configuration C9 and the benign families
B1/B2 measure the distinction, and the envelope sweep found the boundary: 2 of 300
images produce a false claim at JPEG Q100, exceeding this project's 0.5 % bound.
That is a measured limit, not a solution.

### G5 — No work reports what it costs to be secure

There is no configuration in the comparison set that removes the security property
and measures the accuracy it was buying. It is the natural experiment and nobody
runs it.

**Addressed by:** C9 (key removed) and C10 (trained on one key, tested on another).
C10 in particular tests whether a learned reader has learned the *key* rather than
the *evidence* — a failure that no accuracy number would reveal.

---

## 5. Where this project sits, in one paragraph

The comparison set solves localisation well and does not address keyed evidence,
causal refusal, or the comparability of its own metrics. This project does not
attempt to beat the best localiser on its own corpus. It keeps the first
generation's structural security, adds the refusal none of the three generations
has, prices every component against every other on one frozen protocol, and
publishes a computed bound that explains why the localisation figures the field
reports are not comparable to one another. The one thing it does not do is
improve on 0.832 on LiTS, because LiTS was not run — and it says so.

---

## 6. Citation status — read before writing chapter 2

This survey was assembled under a constraint: the full texts of several compared
works were not available, and their reported numbers come from the reference
paper's comparison tables. That is normal practice and it is also how a survey
becomes wrong.

### Status of each entry

| ref | what we have | what must be done |
|---|---|---|
| [1]–[5] | canonical classical works, well established | verify volume, issue, pages against the PDFs |
| [6] | our own LSB baseline implementation | cite as own baseline, not as a paper |
| [7]–[9], [11] | **numbers only, via [12]** | either obtain the originals, or cite as *"as tabulated in [12]"* |
| [10] | abstract-level facts (94.1 %, AUC .971, 61 ms, 18.4 M) | verify author list and venue |
| [12] | full comparison tables read | verify author list, volume, pages |
| [13] | abstract and reported figures | verify venue and author list |
| [14] | abstract-level | verify author list |
| [15] | reported figures | verify author list and venue |
| [16] | reported figures only | verify author list and venue |
| [17] | dataset, public | cite dataset paper if one exists, else the repository |

### The rule

> A secondary citation is marked **"as tabulated in [12]"** in the text. It is
> never presented as though the original was read.

An examiner can open the reference paper and find the same row in thirty seconds.
The marking costs one clause and removes the only way this chapter can embarrass
the project.

### Reference list — to be completed

The list below fixes the *order* and the *identity* of each entry. Struck-through
fields must be filled from the PDFs before submission.

```
[1]  H. Y. S. Yeung and S. Mintzer, "An invisible watermarking technique for
     image verification," in Proc. IEEE ICIP, 1997. <verify pages>
[2]  P. W. Wong, "A public key watermark for image verification and
     authentication," in Proc. IEEE ICIP, 1998. <verify pages>
[3]  J. Fridrich, "Security of fragile authentication watermarks with
     localization," in Proc. SPIE Security and Watermarking of Multimedia
     Contents, 2002. <verify volume, pages>
[4]  M. U. Celik, G. Sharma, E. Saber and A. M. Tekalp, "Hierarchical
     watermarking for secure image authentication with localization,"
     IEEE Trans. Image Process., 2002. <verify vol/issue/pages>
[5]  P.-L. Lin and C.-C. Chang, "A hierarchical digital watermarking method for
     image tamper detection and recovery," Pattern Recognition, 2005.
     <verify vol/issue/pages>
[6]  (this work) least-significant-bit baseline. Reproduce in Ch. 5, do not cite.
[7]  SECURENet. <full citation required>
[8]  TFPDD. <full citation required>
[9]  ConMark. <full citation required>
[10] DeepMark. <full citation required>
[11] ASFW. <full citation required>
[12] PFF-WM, Khaldi et al., 2026. <full citation, volume, pages required>
[13] WAM, arXiv:2411.07231, ICLR 2025. <verify author list>
[14] OmniGuard, CVPR 2025. <verify author list and pages>
[15] SMARTMed, Scientific Reports, 2026. <verify author list>
[16] post-quantum DCT watermarking, 2026. <full citation required>
[17] ISIC 2019 dataset. <citation and licence terms required>
```

**Minimum for submission:** 25 entries, every one cited at least once, in order
of first appearance. The above carries 17; the remainder should come from the
background reading of fragile watermarking and the ISIC challenge reports.

---

## 7. How to read a reported number

A checklist for chapter 2, and for the viva.

| question | why it matters |
|---|---|
| What corpus? | CheXpert, LiTS and ISIC are not interchangeable, and lesion statistics differ by an order of magnitude |
| What granularity — image, block or pixel? | a block-level 0.99 and a pixel-level 0.83 are not the same measurement |
| Per-image mean or pooled ratio? | these differ substantially when target sizes vary, and papers rarely say which |
| What is the ground-truth mask? | a tumour mask and a paste rectangle have different ceilings |
| How many parameters, and what latency? | beating an IoU with a 15× larger model is not beating it |
| Was the test set opened once? | otherwise the number is the best of many tries |
| Are benign conditions applied before or after embedding? | changes what the false-positive rate means |

Six of these seven are unresolved for at least one work in §2. That is not a
criticism of the works; it is the reason this project froze its own protocol in
code first.
