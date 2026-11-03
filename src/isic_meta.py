"""ISIC 2019 metadata: lesion grouping and diagnostic strata.

Two jobs, both needed for an ISIC-2019-only evaluation to be worth anything:

1. **Grouping.** Images of the same lesion must never straddle train and test.
   ISIC 2019 ships a `lesion_id`; where it is missing we fall back to the image
   stem. This is an image-level split and cannot rule out lesion/patient leakage.

2. **Stratification by diagnosis.** The eight ISIC categories are not
   interchangeable for localisation. A flat naevus and a textured basal-cell
   carcinoma lose their mark in different places, and a single aggregate IoU
   hides that. Reporting per-diagnosis is what turns one corpus into a real
   study instead of a single headline number.

Nothing here assumes a column layout. ISIC 2019 ships in at least three shapes
depending on the mirror:

    image, lesion_id, MEL, NV, BCC, AK, BKL, DF, VASC, SCC, UNK   (one-hot)
    image, lesion_id, diagnosis                                    (single col)
    image                                                          (nothing)

The loader detects which one it has and says so. If it finds no diagnosis at
all, stratification is disabled loudly rather than silently producing a column
of "unknown".
"""

from __future__ import annotations

import csv
from pathlib import Path

DIAGNOSES = ("MEL", "NV", "BCC", "AK", "BKL", "DF", "VASC", "SCC")
UNKNOWN = "UNK"


class Metadata:
    """Parsed ISIC metadata, with the shape it was found in recorded."""

    def __init__(self, path: str | Path | None):
        self.path = Path(path) if path else None
        self.lesion: dict[str, str] = {}
        self.patient: dict[str, str] = {}
        self.diagnosis: dict[str, str] = {}
        self.schema = "none"
        self.note = ""
        if self.path is not None:
            self._load()

    def _load(self) -> None:
        with open(self.path, newline="") as fh:
            rows = list(csv.DictReader(fh))
        if not rows:
            self.note = "metadata file is empty"
            return
        cols = {c.strip() for c in rows[0].keys()}
        lower = {c.lower(): c for c in cols}

        img_key = lower.get("image") or lower.get("image_name") or lower.get("filename")
        if img_key is None:
            self.note = f"no image column in {sorted(cols)}"
            return

        one_hot = [d for d in DIAGNOSES if d in cols]
        single = lower.get("diagnosis") or lower.get("dx")

        if one_hot:
            self.schema = "one-hot"
        elif single:
            self.schema = "single"
        else:
            self.schema = "no-diagnosis"

        explicit_lesions = 0
        explicit_patients = 0
        for r in rows:
            stem = Path(str(r[img_key])).stem
            lid = r.get(lower.get("lesion_id", ""), "") or ""
            explicit_lesions += bool(str(lid).strip())
            self.lesion[stem] = str(lid).strip() or stem
            pid = r.get(lower.get('patient_id',''), '') or ''
            self.patient[stem] = str(pid).strip()
            explicit_patients += bool(str(pid).strip())
            if self.schema == "one-hot":
                hit = [d for d in one_hot if str(r.get(d, "0")).strip() not in ("", "0", "0.0")]
                self.diagnosis[stem] = hit[0] if hit else UNKNOWN
            elif self.schema == "single":
                self.diagnosis[stem] = str(r[single]).strip().upper() or UNKNOWN

        self.note = (f"schema={self.schema} rows={len(rows)} "
                     f"explicit_lesion={explicit_lesions} explicit_patient={explicit_patients} "
                     f"with_dx={len(self.diagnosis)}")

    # ------------------------------------------------------------------
    @property
    def has_diagnosis(self) -> bool:
        return bool(self.diagnosis)

    def group_of(self, stem: str) -> str:
        """The grouping key for splitting. Falls back to the stem."""
        return self.patient.get(stem) or self.lesion.get(stem, stem)

    def dx_of(self, stem: str) -> str:
        """Diagnosis, or 'UNKNOWN' when the corpus does not carry one."""
        return self.diagnosis.get(stem, UNKNOWN) if self.diagnosis else UNKNOWN


def stratify_by(items: list[dict], key: str) -> dict[str, list[int]]:
    """Indices grouped by `items[i][key]`. Every group is kept, including ones
    that turn out small -- an omitted bucket is a hidden result."""
    out: dict[str, list[int]] = {}
    for i, it in enumerate(items):
        out.setdefault(str(it.get(key, UNKNOWN)), []).append(i)
    return out


def report(strata: dict[str, list[int]], values: list[float],
           min_n_warn: int = 10) -> list[dict]:
    """One row per stratum with n, mean and a small-n flag.

    A bucket with n=3 is not evidence and must not be printed beside a bucket
    with n=3000 as though the two carried the same weight.
    """
    rows = []
    for name in sorted(strata):
        idx = strata[name]
        vals = [values[i] for i in idx]
        rows.append({
            "stratum": name,
            "n": len(idx),
            "mean": float(sum(vals) / len(vals)) if vals else float("nan"),
            "small_n": len(idx) < min_n_warn,
        })
    return rows
