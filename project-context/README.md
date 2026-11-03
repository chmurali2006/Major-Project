> **Historical / pre-audit material.** This file is not evidence for the current audited recipe. See root `VERIFICATION.md` and use fresh measured receipts for submission. In particular, any-overlap block IoU is not a universal ceiling.

# project-context

Everything needed to talk about this project — on a poster, in a deck, in an
abstract, in a viva — without re-deriving it and without inventing a number.

| file | what it is | read it when |
|---|---|---|
| `ARCHITECTURE.md` | **the definitive technical description**: the design principle, the three-stage lifecycle, the PROTECT / VERIFY / LEARN flows with their constants, the interfaces, layer status, and the honest ledger of what `dev` contributes | you need to know how the thing actually works |
| `POSTER_CONTEXT.md` | **the presentation layer**: thesis, the eight poster panels written out, the extended plan in full, layout arithmetic, and the phrasebook for what may and may not be said | you are making a poster, deck or abstract |
| `facts.json` | every number with an id, a provenance string, a corpus tag and a status (`verified` / `computed` / `published` / `planned` / `unverified` / `forbidden`) | before printing anything |

`ARCHITECTURE.md` is what the system *is*. `POSTER_CONTEXT.md` is how to *say*
it. They share the fact base and neither may contradict it.

## Why two files

A prose document and a number base, deliberately separated.

The prose is for a reader — it argues, it orders, it explains why panel 6 exists.
The fact base is for checking — it is the list of what is true, and nothing that
is not in it may be printed.

This project's entire claim to credibility is that no figure was ever rounded,
borrowed or remembered. A single document cannot enforce that; a document plus a
fact base can. Same logic as `src/protocol.py`: **a protocol that is imported
cannot drift.**

## The workflow

```
1.  Write the poster from POSTER_CONTEXT.md §4, panel by panel.
2.  For every number that appears, look it up in facts.json and copy the
    `display` string exactly.
3.  Check the status. planned -> the panel must say DESIGNED, NOT YET RUN.
    unverified or forbidden -> the number comes out.
4.  Check the corpus tag is attached to every number.
5.  Check every ratio has its denominator.
6.  Check the ceiling is printed beside every IoU.
```

Step 6 is not a formality. `0.9936` without `block-level` invites a comparison
with `0.832` that cannot be defended, and that comparison is the single most
likely way this work gets challenged.

## What was found while writing this

Two numbers that had been circulating in the project's own documents do not have
a locatable receipt, and both were on the figure:

| number | status | resolution |
|---|---|---|
| block coverage `0.987` | unverified — the only `0.987` in the repository is T5 evidence separation in `KAGGLE_RUNBOOK.md`, a different quantity entirely | removed from the figure (U-01) |
| worst-image PSNR `35.75 dB` | unverified — no receipt in the tree | removed from the figure (U-02) |

They are recorded rather than deleted, because how a number drifted is worth
knowing. This is exactly the failure mode `src/protocol.py` was written to
prevent, and it happened anyway, in the poster.

## The six rules, short form

1. Only `verified`, `computed`, `published`. `planned` only under a label.
2. Every number carries its corpus.
3. Every ratio carries its denominator.
4. Every IoU carries its granularity and its ceiling.
5. Losing results are printed.
6. Nothing is called achieved that has not run.

## Related

| file | what it adds |
|---|---|
| `docs/poster/architecture.{pdf,svg,png,html}` | the figure itself — PDF is vector, print that |
| `docs/poster/SPEAKER_NOTES.md` | the thirty-second pitch, the walk-through, the long-form answers |
| `docs/SYNTHESIS_STUDY.md` | the study design in its original, longer form |
| `project-context/ARCHITECTURE.md` | the final architecture and its working, stage by stage |
| `docs/DESIGN_REVIEW.md` | the ten flaws found by measurement, and §5 open questions |
| `docs/KAGGLE_RUNBOOK.md` | compute plan and the notebook's cell-by-cell behaviour |
| `src/protocol.py` | the frozen protocol, as code |
