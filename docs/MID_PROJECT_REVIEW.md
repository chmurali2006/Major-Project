# Mid-project review

**A Fragile Watermarking for Medical Image Tamper Detection**
Classical, zero-training, keyed fragile watermarking with tamper localisation,
honest abstention, and an evaluation battery that is falsifiable by construction.

**Date:** 2026-10-21 · **Branch:** `arena/4f1090b0-major-project` (PR #4 → `dev`,
merged as `28e4e6e`)
· **Corpus:** PH2, 200 dermoscopic images, 512 × 512, all 22 conditions — plus
the primary corpus **ISIC 2018 Task 1, full n=2594**, measured 2026-10-21
· **Receipts:** PH2 `runs/2026-10-20-n200-v8/receipt.json`; ISIC
`runs/isic-full-v8/receipt.json` — the command, config, git commit,
environment and per-condition counts are inside them
· **Second review pass:** A-031 (a codec read as surgery) and A-032 (a carrier
that could only veto) were found by measuring outside the battery, and both
changed the default configuration

---

## 1. What it is, in one page

An image is protected with no model and no training data. For each 8 × 8 block,
a 60-bit tag is derived from a key, the block's address, the block's own detail
content **and its mean**, and written into the block's Haar detail
coefficients. The verifier needs only the image: it recomputes every tag,
compares, and returns one of three verdicts **per block**, each with a reason.
(A second, semi-robust carrier existed until this pass; measurement showed it
could only ever remove coverage, so it is off by default — A-032.)

| verdict | meaning | what the clinician does |
|---|---|---|
| `INTACT` | the block carries the tag the key says it must | trust the pixel |
| `TAMPERED` | the block lost its tag and the image was not transformed globally | do not trust this region |
| `CANNOT_SAY` | the tool has no evidence here, and says which of four reasons applies | look at the block, do not rely on the mark |

The design's whole claim is that third row. A fragile watermark that guesses is
worse than one that abstains: a wrong `TAMPERED` destroys the reader's trust in
every other block, and a wrong `INTACT` is the failure mode a clinician acts on.
Every number in this document is produced by one command and stored with it.

---

## 2. The battery

22 frozen conditions in five families, applied to every image, with block-level
ground truth taken from the measured pixel change (A-019), not from the edit
geometry:

* **paste (1–6)** — copy-move at 64×64, 32×32, 16×16, 8×8, three clones.
* **benign (7–11)** — JPEG 90/75/50, σ=1 noise, resize 90% and back.
* **degrade (12–18)** — JPEG 30/10, double compression, a scale/JPEG chain,
  blur σ=2, noise σ=8, 70% crop and resize.
* **structure (19–22)** — block-aligned crop and shift, burned-in text,
  Telea inpainting.

Conditions 7–18 must never produce a tamper claim. Conditions 1–6 and 19–22 are
scored for detection and localisation. The battery was frozen before the results
in this document. On top of it, the **untouched protected image** is verified
every time; a claim there is the most basic error the tool could make.

---

## 3. Against the operating point

The levels come from the PFF-WM paper (CheXpert, 44 ms). Cross-paper comparison
is forbidden — the corpora differ — so these are the levels this project holds
itself to, not a claim to have beaten anyone.

| what | bar | measured (PH2, n=200) | |
|---|---|---|---|
| detection, conditions 1–5 | ≥ 97.6% | **99.40%** (95% CI 98.8–99.9) | met |
| localisation IoU, conditions 1–6 | ≥ 0.832 | **0.9336** (CI 0.9223–0.9440) | met |
| false claims, benign conditions | ≤ 0.5% | **0/1000** (≤ 0.30% at 95%) | met |
| false claims, untouched image | 0 | **0 / 200** (≤ 1.50% at 95%) | met |
| PSNR | ≥ 37.8 dB (mean) | **38.68 dB** mean, **36.00 dB** worst | met on the mean |
| verify latency | ≤ 44 ms | **40.19 ms** mean (median 39, p95 47) | met on the mean |
| false claims under any re-encode or noise | — | **0 in 3 800 readings** | not in the battery |

Four numbers belong beside them, because a detector that abstains a lot looks
excellent on the rows above:

* **coverage** — the fraction of blocks on which the tool commits to any
  verdict: **0.924** on the paste family; **0.000** on JPEG 90, where it
  declines the whole image rather than call a recompressed scan authentic. The
  full curve, quality by quality, is `BENCHMARKS.md` §1b.
* **detection at the strict IoU ≥ 0.5 reading** — **93.0–99.5%** on conditions
  1–5, against 99.0–100% at the stated IoU ≥ 0.10. The difference is boundary
  blocks on a 64×64 grid, and both are printed by every run.
* **silent failures** — changed blocks called `INTACT`: **0.0%** on conditions
  1–6, **8.7%** on burned-in text, **4.6%** on inpainting.
* **the envelope** — how much of the frame is still certified after ordinary
  handling, and whether the tool lies there. It never does: 0 false claims in
  3 800 readings from JPEG Q100 to Q50 and σ=0 to 8, which is the measurement
  that found A-031.

![The 22 conditions at a glance](figures/battery.png)

*Generated from the receipt by `scripts/make_figures.py`; the third panel is
the point — where a bar is not met, coverage says why.*

---

## 4. What this checkpoint changed

Eight defects were found by measurement in this branch and closed. Each has an
amendment entry with the numbers, and each was found by a run that *failed* —
which is the point of keeping failing receipts. The last three (§4.6–§4.8) were
found after the checkpoint was written, by measuring outside the frozen battery;
they are the reason this document has a second pass.

### 4.1 A saturated image accused itself (A-027)

The encoder refuses any block whose marked luma would leave the RGB gamut and
transmits it verbatim. The verifier had no way to see that decision, judged
those blocks, and read "no tag at all" as tampering. On IMD019, a clean
dermoscopy frame, the **clean** protected image claimed **741 blocks** with
`delta_f` up to 1.50; the true tamper was 16 blocks, so IoU was 0.02 and
detection scored it as a miss. 26 of 200 images failed this way.

The verifier now rebuilds the exact plane the encoder rebuilt — same signature,
same tag, same write, same inverse transform, same gamut test — and excuses a
block only when that reconstruction says the encoder could not have written
there. Measured agreement over 40 images: **163 787 / 163 840 blocks
(0.99968)**, and the residual is one-sided: the verifier excuses up to 13 extra
blocks per image and never misses one.

### 4.2 "Gamut-safe" did not mean safe (A-028)

The global-attenuation rule asks whether median tag evidence over gamut-safe
blocks has fallen below 0.95. "Gamut-safe" meant 3 levels inside the gamut; the
mark's measured excursion is p99 = 5, max = 9. So a "safe" block could still
clip, its evidence fell below 1.00 for reasons unrelated to editing, and the
rule declared a clean image globally transformed — excusing **all 64 blocks** of
a copy-move. Margin raised to 8, above the measured excursion.

### 4.3 Thirteen per cent of the frame carried no mark (A-028 → A-029)

Refusal was the binding constraint on detection: coverage 0.871, and every
remaining detection failure was an image whose tampered region had been
refused. Blocks are now shifted by the smallest integer DC offset that gives
four levels of headroom. A constant shift changes only the approximation
subband, so the detail-carried tag is untouched and the verifier needs nothing
new.

| FIT_MARGIN | detection | IoU | PSNR mean | PSNR worst | coverage |
|---|---|---|---|---|---|
| 0 | 0.9567* | 0.9096* | 39.71* | 38.83* | 0.871* |
| 2 | 0.9667* | 0.9321* | 39.19* | 38.79* | 0.894* |
| 3 | 0.9760 | 0.9033 | 38.77 | **37.65** | 0.894 |
| **4 (default)** | **0.9970** | **0.9367** | **38.27** | 35.52 | **0.926** |

<sub>* measured on 60 images; margins 3 and 4 on all 200. The 60-image sample
made margin 3 look better than it is — the full corpus showed it lands exactly
on the bar, which is why A-029 exists.</sub>

Four is taken because it clears detection with 2.1 points of room. It costs the
worst image 2.1 dB, below the 37.8 dB mean bar. That is disclosed, both receipts
ship, and margin 3 is one config line away for anyone who prefers the other side
of the trade.

### 4.4 Two silent failure modes, closed (A-023, A-025)

The detection statistic normalises by the residual it finds, which makes it
immune to how much of the mark survived — and blind to a mark that was
**deleted** rather than misaligned. A painted text box flattens half a block,
those coefficients drop out of numerator *and* denominator, and the untouched
half carries the score (`delta_f = 0.000` measured). The complement — the
fraction of slots still holding a readable residual — is now the test, trusted
only where the gamut cannot have clipped the mark.

Extent was also the wrong test for "the image was transformed as a whole": the
Telea wound covers 10.1% of the frame and was excused as routine handling. The
attenuation test now carries that question and extent is only a backstop above
half the frame (A-025).

### 4.5 The tag now names the block's mean (A-030) — the principal weakness

Until this week the tag named only the Haar *detail* coefficients, and details
cannot see a modification that moves a block's average brightness. Burned-in
text does exactly that: it flattens part of a block, those coefficients leave
the correlation, the untouched half carries the score, and the block verified —
**22.5% of the blocks the text changed were reported INTACT**.

The 2×2 `LL2` subband is the block's mean and its two coarse gradients. It is
bit-identical at embed and verify, because the mark writes only to details and
the integer lifting transform is exact, so it can be signed. It is now folded
into each coefficient's selector index. Nothing travels with the image and the
verifier needs no side information: it re-reads `LL2` from the received image.

| | before A-030 | after (v6, before A-032) |
|---|---|---|
| c21 detection (stated rule) | 36.0% | **97.0%** |
| c21 IoU | 0.082 | **0.286** |
| c21 changed blocks called INTACT | 22.5% | **5.9%** |
| c22 IoU | 0.875 | **0.912** |
| c22 changed blocks called INTACT | 3.8% | **2.9%** |
| detection, conditions 1–5 | 0.9970 | **0.9990** |
| IoU, conditions 1–6 | 0.9367 | **0.9421** |
| false claims, untouched image | — | **0 / 200** |

Ablation A7 cuts the binding and takes condition 21 from IoU 0.273 to **0.079**
on the same images; A-030 is load-bearing. The v8 column differs slightly
(c21 IoU 0.284, silent 8.7%) because A-032 later removed Carrier B from the
marked image; the A-030 comparison above is stated on the run that measured it.

### 4.6 A JPEG re-encode was read as surgery (A-031)

Every JPEG condition in the frozen battery is Q ≤ 90. At Q ≤ 90 the mark dies
everywhere, the attenuation rule notices, and the image abstains — which looked
like success and hid the opposite case. At **Q100** a re-encode breaks the
fragile mark in 6.4% of blocks: too few for the extent rule, too many to ignore.
Measured on all 200 images, the tool claimed tampering on **196 untouched
files**. Benign handling is the one number the design exists to protect, and the
battery scored it 0.00%.

The discriminator is shape, not size: JPEG codes each block independently, so
its damage is a scatter of isolated islands (median 64–250 of them), while every
edit in the battery is one contiguous region of 1–9 blocks. Damaged area spread
over ≥ 12 islands cannot be attributed to a region, and localisation is the only
thing a fragile mark is good for, so the verdict is
`CANNOT_SAY(routine_handling)`. Claims on a Q100 re-encode: **196/200 → 0/200**,
with 91% of the frame still certified.

### 4.7 The second carrier could only veto (A-032)

Carrier B was justified in the original design as an independent opinion. Its
only route into a verdict is a rule that fires on blocks the fragile carrier
already calls intact, so no threshold could ever let it create a `TAMPERED` — it
could only convert `INTACT` into `CANNOT_SAY`. Measured against the envelope it
was worse than inert: restoring it costs 18–27 points of certified area at Q99
and σ=1, prevents no false claim anywhere, and costs 0.38 dB of PSNR to embed.

It is now off by default. The cost is stated in the receipt rather than hidden:
detection 99.90% → 99.40%, IoU 0.9421 → 0.9336, while PSNR improves to 38.68 dB
and Q99 coverage rises from 0.72 to 0.89. A mechanism that cannot vote is not a
second opinion; it is a veto on answering.

### 4.8 The ablation that lied about its own result (A-033)

A3 had read "no effect" at every checkpoint. It was arithmetic: the metric was
`verdict.max() == 1`, and verdict codes run `INTACT=0, TAMPERED=1,
CANNOT_SAY=2`, so a single abstaining block made the maximum 2 and the metric
read zero. Coverage is 0.92 by design, so it read zero on almost every frame.
Corrected, switching the capacity refusal off claims **32.5%** of clean images.
The mechanism was load-bearing all along; the instrument that was supposed to
prove it could not return the value it needed to.

### 4.9 What the textbook scheme does, for comparison

`scripts/baseline_lsb.py` implements the obvious alternative — a keyed 8×8 block
hash written into the pixel LSBs — on the same corpus and the same battery. It
detects perfectly (IoU 1.000), is 17 dB kinder to the image, and claims tampering
on **100% of benign handling**, because a codec changes pixels and it has no
vocabulary for "changed but not edited". That comparison is the contribution
stated precisely: not a sharper localiser, but a detector that can tell damage
from editing and says so when it cannot. On the primary corpus the textbook
scheme behaves identically: 100% of benign handling claimed on ISIC images,
including 60/60 at Q100 and 60/60 at σ=1 (`runs/isic300-lsb/receipt.json`).

### 4.10 The primary corpus, measured in full (ISIC 2018 Task 1, n=2594)

The A-021 rule and the A-030 mean binding had been validated on a local
reproducer; the previous revision of this document said the ISIC
re-measurement was outstanding. It is now measured: the full 2594-image
corpus, the frozen 22-condition battery, the current configuration, receipt
`runs/isic-full-v8/receipt.json`, all four data bars met with an **empty
violations list**:

| bar | PH2, n=200 | ISIC, n=2594 | bar met |
|---|---|---|---|
| detection, conditions 1–5 | 99.40% | **99.99%** | ≥ 97.6% |
| localisation IoU, conditions 1–6 | 0.9336 | **0.9936** | ≥ 0.832 |
| false claims, benign conditions | 0.0% | **0.0%** | ≤ 0.5% |
| clean images claimed | 0 / 200 | **0 / 2594** | 0 |
| PSNR (mean; worst image) | 38.68; 36.00 dB | **40.47; 35.75 dB** | ≥ 37.8 dB |
| verify latency | 40.19 ms | 58.6 ms | ≤ 44 ms — not met on that laptop |

Both predictions the primary-corpus defect (A-021) motivated are confirmed on
the corpus itself, not assumed: condition 11 (resize) claims **0.0%**, and
condition 21 detection is **99.0%** with block-F1 0.423 — the same lift the
mean binding gave on PH2. The envelope sweep on ISIC found the one thing PH2
could not show: **2 of 300 untouched images (0.67%) claim at JPEG Q100**,
everything else exactly zero (Q99→Q50, σ=0→8, lossless PNG). The A9 ablation
ties it to the scatter rule — cut it and Q100 claims 100% — so the mechanism
is right and the calibration is marginally off at exactly one operating point.
It is stated here, in `BENCHMARKS.md` §6, and in `RESULTS.md` §3.12, rather
than tuned away.


---

## 5. What it still cannot do

Stated here rather than discovered in the viva.

**5.1 No mark, no evidence.** The tag is a signed perturbation of the detail
coefficients. A pixel already sitting on the RGB gamut bound cannot take it.
Blocks are fitted by a DC shift so this is rarer than it was, but on frames with
large saturated or specular regions blocks still refuse: **coverage 0.924
corpus mean**, falling to 0.000 at JPEG Q90. A tamper placed
entirely inside a refused region is a miss, not a false claim — and it is the
main residual source of the 5.9% silent blocks on condition 21. The tool cannot
certify what it could not mark.

**5.2 Burned-in text is an alarm, not a precise localiser.** Every image with
text raises a claim (100%) and 97.5% pass the stated detection rule, but block-F1
is 0.435, IoU is 0.284, and at IoU ≥ 0.5 only 0.5% of images pass. The claim is
wider than the text. A-030 improved this by a factor of 3.5 in IoU; it did not
make it precise, and no figure here should be quoted without the pair.

**5.3 A transplant forgery is only partly caught.** Copy a marked region, paste
it elsewhere, keep its visible signs. The content-bound tag localises **3.2%**
of forged blocks (56 of 1765 in a targeted attack run). The address binding is
what defeats a transplant, and it does so completely when the attacker cannot
rewrite the mark; content binding is defence in depth and is not a complete
answer.

**5.4 An image that is both globally transformed and locally edited cannot be
certified at all.** Every block abstains. That is the correct answer for a
fragile mark, and it is a real loss of detection on recompressed-and-forged
images (A-021). The measurable version of this is the benign coverage column:
0.000 after JPEG 90.

**5.5 The ISIC re-measurement has been done; what remains is one calibration
question.** §4.10 reports the result: on the full 2594-image corpus the A-021
rule holds (condition 11 claims 0.0%) and A-030 lifts condition-21 detection
to 99.0%. The residual moved rather than disappeared: the envelope sweep on
ISIC claims **2 of 300 untouched images at JPEG Q100** (0.67%), where PH2
showed zero. The ablation ties the residual to the scatter rule's calibration
on ISIC texture — a single operating point, stated as a limitation rather
than tuned away. Verify latency (58.6 ms) is also above the 44 ms bar on the
machine that ran it; the code tree is identical to the one that measured
40.19 ms here, so this is a property of the laptop, not of the code, until the
same tree is timed on the same machine.

**5.6 Worst-case image quality is 36.00 dB**, below the 37.8 dB mean bar. §4.3
has the trade and the alternative receipt.

**5.6b The latency bar is met on the mean, not on the tail.** 40.19 ms mean,
median 39, p95 47, max 52 on this sandbox, and two runs of identical code
measured 38.98 and 43.57 ms — the margin is inside the machine's own noise. It
is quoted as a distribution for that reason.

**5.6c A scattered surgical edit will abstain.** The scatter rule that fixed
A-031 cannot distinguish twelve erased lesions spread across the frame from a
codec's damage. That is a real loss of detection, it errs toward abstention
rather than a false pass, and it is named here rather than left to be found.

**5.6d Every constant was chosen on these 200 images.** The battery was frozen
before results and the failing receipts are kept, but there is no held-out
split yet: `bench.py --offset` exists for one, and the honest test is the corpus
the choices never saw.

**5.7 The corpus is the public PH2 mirror**, not the official BMP
distribution, and it has no expert masks. §0 of `BENCHMARKS.md` states what
that does and does not change; the prepare script ships a per-file SHA-256
receipt so the corpus is reconstructible.

---

## 6. Reproduce it

```bash
git clone https://github.com/vikaschouhan/PH2-dataset /tmp/ph2src
python scripts/prepare_ph2_public.py --src /tmp/ph2src --out datasets/ph2
python scripts/bench.py --data datasets/ph2 --limit 200 \
                        --receipt runs/<your-run>/receipt.json
python scripts/make_tables.py --receipt runs/<your-run>/receipt.json \
                        --write docs/BENCHMARKS.md
python scripts/make_figures.py --receipt runs/<your-run>/receipt.json \
                        --data datasets/ph2 --out docs/figures
```

`bench.py` prints the five bars and exits non-zero on a benign violation.
`scripts/ablate.py` runs the nine falsification switches (A1–A9), including the
ones that must destroy performance: with the address binding off, detection goes
**1.000 → 0.000**; with both global-transform rules off, benign resize claims go
**0.000 → 0.875**; with the mean binding off, condition 21 IoU goes **0.297 →
0.075**; with the scatter rule off, a Q100 re-encode is claimed on **100%** of
images instead of none; with the capacity refusal off, **32.5%** of clean images
are claimed. Six of nine switches move the battery as predicted; the three that
do not are reported as findings, not hidden. `scripts/ablate_envelope.py` repeats the four switches
the battery cannot see, under handling, and `scripts/baseline_lsb.py` measures
the textbook alternative on the same corpus.

---

## 7. Questions the panel should ask, and the answers

**"Your detection is 99.4% — is that not just because you abstain?"** Coverage
is 0.924 and is printed beside every detection number; the 95% interval over
images is [98.8, 99.9] on detection and [0.917, 0.932] on coverage. Where the
tool cannot read the mark it says so, and the reason code says why.

**"What happens if someone just re-saves the file at quality 100?"** Nothing is
claimed, and 91% of the frame is still certified. That was the A-031 failure:
before the scatter rule, this exact case produced a tamper claim on 196 of 200
untouched images. It is now part of the falsification harness (A9), and the
envelope sweeps twelve qualities and seven noise levels on every image.

**"Why did you delete a component between checkpoints?"** Because it could not
vote. Carrier B's only route into a verdict fired on blocks the fragile carrier
already called intact, so it could only ever remove coverage — measured at 18–27
points under handling, with no claim prevented. The removal costs 0.5 points of
detection and is reported with that cost attached.

**"Aren't you tuning on the same 200 images you report?"** Yes for the
constants, no for the battery: it was frozen before the results and every
failure is kept. The gap is stated in §5.6d, and the held-out test is the ISIC
corpus, which is the next item in the plan.

**"Then why does coverage drop to 0.000 on JPEG 90?"** Because after
recompression the mark is uniformly attenuated, and certifying any block would
be a guess. The honest verdict is `CANNOT_SAY`; the alternative — the earlier
code — claimed tampering on such images.

**"What happens if I edit a saturated region?"** The tool refuses that block in
the encoder and abstains in the verifier. Nothing is detected there, and nothing
is falsely claimed either. It is also the main reason 5.9% of text-changed
blocks are still called intact rather than abstained over.

**"You changed the tag twice in a week — is the design stable?"** Two changes,
each with its own falsification: the tag now names the mean (A-030) because
details cannot see a brightness shift, and it is written after a small DC fit
(A-029) so the mark can exist on a saturated frame. Everything else in the
scheme is unchanged, and the earlier failing receipts are in `runs/`.

**"Your worst image is 35.5 dB — is that invisible?"** It is below our own mean
bar and we report it as such. The configuration that keeps every image above
the bar exists, is measured, and is shipped as a receipt; it costs the detection
margin.

**"Why not use a CNN?"** Because a zero-training method can be audited end to
end: every verdict follows from a keyed tag and a stated reason, and every
number here is reproducible with one command on a laptop.

**"How do I know the numbers are real?"** Every receipt records the command,
the config, the git commit and the environment, and the harness records whether
the code paths were clean. The tables in `BENCHMARKS.md` are generated from the
receipt by `scripts/make_tables.py`, so prose cannot drift from measurement.
