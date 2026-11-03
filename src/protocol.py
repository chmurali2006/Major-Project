"""The frozen protocol. Single source of truth.

Nothing in this file may change after the first training run. Any change is an
amendment: appended to docs/AMENDMENTS.md, the superseded number retired, the
new number reported separately. This is the same discipline that produced 34
amendments on the classical system, applied to a larger one.

Why this file exists as code and not as prose: in the classical phase, one
document claimed 0.999 detection while another claimed 0.987 coverage, and a
third claimed a latency from a branch that no longer existed. Three files, three
stories, one repository. A protocol that is imported cannot drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------- corpora

@dataclass(frozen=True)
class Corpus:
    name: str
    role: str            # seen | benchmark | substitute
    n_images: int | None
    note: str


CORPORA = (
    Corpus("isic2019", "primary", 25331,
           "Kaggle, free. THE corpus for this phase: train, validate and test."),
    Corpus("lits", "deferred", 131,
           "DEFERRED 2026-10-24. PFF-WM measured 0.832 IoU here. This is the only "
           "corpus on which a localisation number can sit beside theirs."),
    Corpus("chexpert", "deferred", None,
           "DEFERRED 2026-10-24 by decision. Requires a Stanford research-use form. "
           "PFF-WM's 97.6% detection is reported here, so without it no detection "
           "number of ours can be tabulated against theirs."),
    Corpus("nih_chestxray14", "deferred", 112120,
           "DEFERRED. Free substitute for CheXpert. If ever used, must be labelled "
           "as a substitute and never called CheXpert."),
)

# What the deferral costs, stated once so it cannot be discovered later as a
# surprise. This is a scope decision, not a defect: ISIC 2019 is one of the
# three corpora PFF-WM evaluates on, so running on it is legitimate. What it
# does not buy is a row in their headline tables.
DEFERRAL_NOTE = (
    "ISIC 2019 is one of the three corpora PFF-WM evaluates on, so a run here is "
    "on their ground. But their Table 2 (detection) is CheXpert and their "
    "Table 4 (localisation IoU) is LiTS. Numbers from an ISIC-only phase cannot "
    "be placed in either table; they can only be reported as this work's own "
    "protocol on a corpus both systems can run on."
)

# ---------------------------------------------------------------- splits

@dataclass(frozen=True)
class Split:
    train: float
    val: float
    test: float
    grouped_by_patient: bool
    note: str


SPLIT = Split(
    train=0.70, val=0.15, test=0.15,
    grouped_by_patient=True,
    note=("Group by patient where the corpus carries patient ids. LiTS volumes "
          "are one patient each: a slice never appears in two splits. Test is "
          "opened once, after model selection on val."),
)

# ---------------------------------------------------------------- tamper families

@dataclass(frozen=True)
class Family:
    fid: str
    name: str
    kind: str            # tamper | benign
    params: tuple
    expected: str        # what a correct system does
    note: str = ""


TAMPER_FAMILIES = (
    Family("T1", "copy-move", "tamper", (8, 16, 32, 64),
           "flag the pasted blocks", "carried over from the classical battery"),
    Family("T2", "lesion insertion", "tamper", ("synthetic",),
           "flag the inserted mass",
           "the PFF-WM LiTS protocol: synthetic tumour pasted into liver parenchyma"),
    Family("T3", "lesion removal", "tamper", ("telea",),
           "flag the inpainted region", "classical condition 22"),
    Family("T4", "burned-in text", "tamper", ("64x24",),
           "flag the text box", "classical condition 21; our weakest family"),
    Family("T5", "splicing (cross-image)", "tamper", ("foreign",),
           "flag the spliced region",
           "the gap the classical phase never measured; see docs, limitation 5.3"),
    Family("T6", "generative substitution", "tamper", ("declared-out-of-scope",),
           "flag the substituted region",
           "NOT faked. Reported as unmeasured unless a generator is available."),
    Family("B1", "benign single op", "benign", ("jpeg90", "jpeg75", "jpeg50", "sigma1", "resize90"),
           "no tamper claim"),
    Family("B2", "benign chain", "benign", ("scale->jpeg->scale->jpeg",),
           "abstain, never accuse"),
)

# ---------------------------------------------------------------- metrics

@dataclass(frozen=True)
class MetricSpec:
    name: str
    direction: str       # higher | lower
    definition: str


# ---------------------------------------------------------------- strata

@dataclass(frozen=True)
class Stratum:
    name: str
    source: str
    note: str


STRATA = (
    Stratum("diagnosis", "isic2019 metadata",
            "ISIC 2019's eight diagnostic categories. Localisation can fail "
            "differently on flat lesions (NV, BKL) than on textured ones (BCC, "
            "SCC). Report every bucket with its n; an empty bucket is reported "
            "as empty, never omitted."),
    Stratum("tamper_area", "measured from the pixel mask",
            "IoU is strongly area-dependent, and a perfect block detector tops "
            "out at 0.809 on a radius-32 lesion. Every IoU is reported with the "
            "ceiling for its bucket."),
    Stratum("family", "the protocol",
            "Eight families. A mean over them is dominated by whichever is most "
            "numerous, so the family table is always printed in full."),
    Stratum("coverage", "the abstention rule",
            "Selective risk against coverage. A system that answers less must be "
            "shown to answer better, or the abstention is hiding a failure."),
)


METRICS = (
    MetricSpec("iou", "higher", "per-image IoU between predicted and measured tamper mask"),
    MetricSpec("dice", "higher", "harmonic mean of precision and recall on pixels"),
    MetricSpec("pixel_acc", "higher", "fraction of blocks classified correctly"),
    MetricSpec("pixel_f1", "higher", "F1 over tampered blocks"),
    MetricSpec("detection_acc", "higher", "fraction of images where the tamper verdict matches ground truth"),
    MetricSpec("benefit_at_0.5", "higher", "detection rate at IoU threshold 0.5"),
    MetricSpec("block_f1", "higher", "F1 at the 8x8 verdict grid"),
    MetricSpec("selective_risk", "lower", "error rate among answered blocks as coverage falls"),
    MetricSpec("latency_ms", "lower", "wall clock per 512x512 image, isolated"),
    MetricSpec("params_m", "lower", "trainable parameters, millions"),
)

# ---------------------------------------------------------------- bars

@dataclass(frozen=True)
class Bar:
    name: str
    value: float
    unit: str
    source: str
    corpus: str


BARS = (
    Bar("detection", 97.6, "%", "PFF-WM Table 2", "chexpert"),
    Bar("iou", 0.832, "IoU", "PFF-WM Table 4 (RefineNet)", "lits"),
    Bar("false_positive", 0.5, "%", "PFF-WM, benign transformations", "any"),
    Bar("latency", 44.0, "ms", "PFF-WM Table 6", "512x512"),
    Bar("params", 15.1, "M", "PFF-WM Table 6", "full model"),
)

# ---------------------------------------------------------------- configurations

@dataclass(frozen=True)
class Config:
    cid: str
    name: str
    components: tuple
    isolates: str
    required: bool = True


MATRIX = (
    Config("C0", "classical only", (), "the control — our existing system", True),
    Config("C1", "+ one-class AE", ("ae",), "PFF-WM row 3", True),
    Config("C2", "+ RefineNet", ("refine",), "PFF-WM row 4", True),
    Config("C3", "+ AE + RefineNet", ("ae", "refine"), "PFF-WM rows 3+4, no attention", True),
    Config("C4", "+ attention (full PFF-WM)", ("ae", "refine", "attn"), "PFF-WM row 1, full reproduction", True),
    Config("C5", "+ degradation conditioning", ("ae", "refine", "attn", "degrad"), "OmniGuard row 6", True),
    Config("C6", "+ segmentation formulation", ("ae", "refine", "attn", "degrad", "seg"), "WAM row 5", True),
    Config("C7", "+ three-way head", ("ae", "refine", "attn", "degrad", "seg", "three"), "row 7", True),
    Config("C8", "full synthesis", ("ae", "refine", "attn", "degrad", "seg", "three", "keyed"),
           "all eight rows", True),
    Config("C9", "C8 minus the key", ("ae", "refine", "attn", "degrad", "seg", "three"),
           "what security costs — row 2", True),
    Config("C10", "C8 trained K1, tested K2", ("rekey",),
           "key-leakage test — the one nobody runs", True),
    Config("C12", "C8 plus stage attention",
           ("ae", "refine", "attn", "degrad", "seg", "three", "keyed", "stage_attn"),
           "channel/spatial gates at three encoder stages; new unmeasured ablation", False),
    Config("C11", "C8 on held-out tamper family", ("heldout_family",),
           "negative transfer", True),
)

# ---------------------------------------------------------------- gates

GATES = {
    "coverage_floor": 0.90,
    "_note": ("A configuration whose classical layer refuses more than 10% of "
              "blocks is disqualified, whatever its IoU. It has not localised; "
              "it has abstained its way to a small denominator."),
    "rekey_max_drop_iou": 0.05,
    "_note_rekey": ("Training on K1 and testing on K2 must cost less than 0.05 "
                    "IoU. A larger drop means the network learned the key, which "
                    "is a security failure, not an accuracy failure."),
    "test_opened_once": True,
}


# ---------------------------------------------------------------- sanity

def audit() -> list[str]:
    """Structural checks that must pass before the matrix is run."""
    problems: list[str] = []
    ids = [c.cid for c in MATRIX]
    if len(ids) != len(set(ids)):
        problems.append("duplicate configuration ids")
    for c in MATRIX:
        unknown = set(c.components) - {"ae", "refine", "attn", "degrad", "seg",
                                       "three", "keyed", "rekey", "heldout_family", "stage_attn"}
        if unknown:
            problems.append(f"{c.cid}: unknown components {sorted(unknown)}")
    fam = [f.fid for f in TAMPER_FAMILIES]
    if len(fam) != len(set(fam)):
        problems.append("duplicate family ids")
    if abs(SPLIT.train + SPLIT.val + SPLIT.test - 1.0) > 1e-9:
        problems.append("splits do not sum to 1")
    return problems


if __name__ == "__main__":
    issues = audit()
    print(f"configurations: {len(MATRIX)}")
    print(f"families:       {len(TAMPER_FAMILIES)}")
    print(f"metrics:        {len(METRICS)}")
    print(f"audit:          {'PASS' if not issues else 'FAIL'}")
    for p in issues:
        print("  -", p)
