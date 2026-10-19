# Re-running the battery on your machine

Everything here runs from a clean checkout of this branch. The ISIC 2018 run
matters most: it is the primary corpus, and the last trial found a defect there
that PH2 could not reveal.

---

## 0. What changed since the run you already did

Your trial ran `e3290ca`. Three things have landed since, and one of them is a
direct answer to the ISIC result you reported.

| finding in your report | what changed |
|---|---|
| **c11 resize: 27.3% false claims on ISIC**, 0% on PH2 | **Fixed.** A-021: the tool now measures the tag's amplitude where the gamut cannot have clipped it, and abstains when the whole image was transformed. On a local reproducer, resize claims went 79.2% → 0.0% with no loss of detection. |
| c10 σ=1: 28.0% claims (ISIC) / 28.5% (PH2) | **Fixed.** Same rule: 25.0% → 0.0%. Condition 10 is therefore back in the `benign` family — A-017 withdrawn, battery unchanged from the dossier. |
| `opencv-python-headless==5.0.0` does not exist on PyPI | **Fixed**, pinned to `5.0.0.93`. |
| detection 0.95 with the tamper clearly found | **Fixed.** A-027/A-028/A-029: the verifier now reproduces the embedder's refusals exactly, the "gamut-safe" margin was raised above the mark's measured excursion, and blocks are fitted by a small DC shift before marking. |
| burned-in text reported as authentic | **Fixed, mostly.** A-030: the tag now names the block's mean, which the detail coefficients cannot see. Changed blocks reported INTACT on that condition fell from 22.5% to **5.9%**, and detection rose from 36.0% to **97.0%**. The residual is blocks the embedder refused, which carry no mark. |
| verify 53.7–57.7 ms on the i5-1235U | **Improved**: one PNG decode instead of two, one gamut map instead of two, and keyed BLAKE2b instead of HMAC-SHA256 for the 4096 per-block tags (2.2×). Was 40.8 → now 42.9 ms on the Linux reference sandbox; your machine should land near 45–50 ms. That is the one bar that may still miss on your CPU, and it is hardware-relative — please report the number you get. |

---

## 1. Environment

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
. .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # expect 39 passed
```

Python 3.11–3.13. Python 3.14 has no PyWavelets 1.8.0 wheel and will try a
source build.

---

## 2. The ISIC 2018 run (the one that matters)

```bash
python scripts/prepare_isic.py --src <ISIC2018_Task1-2_Training_Input> \
                               --masks <ISIC2018_Task1_Training_GroundTruth> \
                               --out datasets/isic2018

python scripts/bench.py --data datasets/isic2018 --limit 300 \
                        --receipt runs/isic300-after-a021/receipt.json
```

**What to look for.** Condition 11 must read `claim 0.0%`. The benign bar must
read `met`. Everything else should be at least as good as your previous
`arena` run (detection 0.9967, IoU 0.8933, PSNR 39.06). Also check condition 21:
it should now localise at IoU ≥ 0.10 on more images than the 0.3% it used to,
but it will still leave changed blocks reported `INTACT` — that is A-020, the
known open weakness, not a regression.

If condition 11 is still non-zero, do not adjust anything — capture the receipt
and send it. The rule keys on `TAU_EVIDENCE = 0.95`, measured over blocks whose
every pixel sits more than 3 levels inside its own gamut interval; a corpus
whose images are flatter or more saturated than PH2 could shift that
population, and the fix would be a measurement, not a guess.

Then the full corpus, which nobody has run yet:

```bash
python scripts/bench.py --data datasets/isic2018 --limit 0 \
                        --receipt runs/isic-all/receipt.json
```

`--limit 0` means all 2594. Expect roughly 35–45 minutes on your machine.

---

## 3. PH2, for the record — and the fastest way to check this branch

The corpus is the **public mirror**, so no registration is needed:

```bash
git clone https://github.com/vikaschouhan/PH2-dataset /tmp/ph2src
python scripts/prepare_ph2_public.py --src /tmp/ph2src --out datasets/ph2
python scripts/bench.py --data datasets/ph2 --limit 200 \
                        --receipt runs/ph2-200/receipt.json
```

`prepare_ph2_public.py` writes a receipt with a SHA-256 for every source and
derived file. It also states, in the receipt itself, that the mirror ships no
expert masks and that the placeholders it writes are unused at `lam = 0` with
the texture gate off. If you have the official distribution with `_lesion.bmp`
masks, `prepare_ph2.py` takes that instead and checks the masks properly.

Expected, from the Linux reference run (`runs/2026-10-20-n200-v6/`, commit
`dd06beb`, code paths clean, 665 s):

```
detection 0.9990 | IoU 0.9421 | benign 0.0000 | clean-image claims 0/200
PSNR 38.27 dB (worst 35.52) | verify 38.98 ms | coverage 0.927
```

Exact reproduction is not expected on different hardware: verify latency is the
one number that moves with the CPU (~1.4× slower on the i5-1235U), and the rest
should match to the digit because the battery is deterministic.

Two more commands turn a receipt into the documents:

```bash
python scripts/make_tables.py --receipt runs/ph2-200/receipt.json \
                              --write docs/BENCHMARKS.md
python scripts/make_figures.py --receipt runs/ph2-200/receipt.json \
                               --data datasets/ph2 --out docs/figures
python scripts/probe_coverage.py --data datasets/ph2 --limit 200 \
                                 --out runs/ph2-200/coverage.json
```

---

## 4. The falsification checks

```bash
python scripts/ablate.py --data datasets/ph2 --limit 12 --receipt runs/ablate/
python scripts/ablate.py --data datasets/ph2 --limit 12 --smooth 0.9 \
                         --receipt runs/ablate-smooth/
```

Eight switches, each with the claim it would falsify printed next to it. The
ones that matter most: **A1** takes copy-move detection from 1.000 to 0.000;
**A7** takes condition 21 from IoU 0.285 to 0.065; **A8** removes both
global-transform rules and takes the resize false-claim rate from 0.000 to
1.000. Switches that no longer move the battery are printed as
"NO EFFECT - finding", with the reason, rather than quietly dropped.

---

## 5. Reading a receipt

Each `receipt.json` carries the command, the full configuration, the git
commit, the environment and the per-condition counts. Two fields to check
before trusting a number:

- `code_dirty` must be `false`. A receipt that cites code it did not run is
  worthless, and the harness prints a warning when the tree is dirty.
- `git_commit` must match `git rev-parse HEAD` at the time of the run.

---

## 6. What is still open

**A-020, the pin-hole.** A modification that changes only a block's mean —
burned-in text over a flat region, inpainting over smooth skin — used to be
invisible to a tag made only of detail coefficients. A-023 (erasure rung) cut
it, and A-030 closed most of the rest by binding the block mean into the tag
(PH2 condition 21: 22.5% → **5.9%** of changed blocks called `INTACT`;
condition 22: 3.8% → 2.9%). What is left is concentrated in blocks the embedder
refused, which carry no mark at all. Do not describe condition 21 as a precise
localiser: its block-F1 is 0.437 and its IoU 0.286.

**A5's relevance.** With A-021 in place, collapsing the extent rule no longer
changes the battery. A-021 subsumes it for these conditions. Worth a decision
later, not worth changing now.
