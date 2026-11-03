"""Metadata parsing must never guess. Three real ISIC 2019 layouts are tested,
plus the case where the diagnosis is absent entirely."""
import csv
import pytest
from src.isic_meta import DIAGNOSES, Metadata, report, stratify_by


def _write(tmp_path, header, rows, name="meta.csv"):
    p = tmp_path / name
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return p


def test_one_hot_schema(tmp_path):
    p = _write(tmp_path,
               ["image", "lesion_id", "MEL", "NV", "BCC", "AK", "BKL", "DF", "VASC", "SCC", "UNK"],
               [["ISIC_0000001.jpg", "L1", "1", "0", "0", "0", "0", "0", "0", "0", "0"],
                ["ISIC_0000002.jpg", "L2", "0", "1", "0", "0", "0", "0", "0", "0", "0"],
                ["ISIC_0000003.jpg", "L1", "0", "0", "0", "0", "0", "0", "0", "0", "1"]])
    m = Metadata(p)
    assert m.schema == "one-hot"
    assert m.has_diagnosis
    assert m.dx_of("ISIC_0000001") == "MEL"
    assert m.dx_of("ISIC_0000002") == "NV"
    assert m.dx_of("ISIC_0000003") == "UNK"


def test_single_column_schema(tmp_path):
    p = _write(tmp_path, ["image", "lesion_id", "diagnosis"],
               [["a.jpg", "L9", "bcc"], ["b.jpg", "L8", "mel"]])
    m = Metadata(p)
    assert m.schema == "single"
    assert m.dx_of("a") == "BCC"
    assert m.dx_of("b") == "MEL"


def test_no_diagnosis_column_disables_stratification(tmp_path):
    p = _write(tmp_path, ["image", "lesion_id"], [["a.jpg", "L1"]])
    m = Metadata(p)
    assert m.schema == "no-diagnosis"
    assert not m.has_diagnosis
    assert m.dx_of("a") == "UNK"


def test_lesion_grouping_falls_back_to_stem(tmp_path):
    p = _write(tmp_path, ["image", "lesion_id"], [["a.jpg", ""], ["b.jpg", "L7"]])
    m = Metadata(p)
    assert m.group_of("a") == "a"      # no lesion id -> its own group
    assert m.group_of("b") == "L7"
    assert m.group_of("never_seen") == "never_seen"


def test_no_metadata_is_safe():
    m = Metadata(None)
    assert m.schema == "none"
    assert m.group_of("x") == "x"
    assert m.dx_of("x") == "UNK"


def test_same_lesion_shares_a_group(tmp_path):
    """The whole point of the grouping key: leakage prevention."""
    p = _write(tmp_path, ["image", "lesion_id"], [["x1.jpg", "L1"], ["x2.jpg", "L1"]])
    m = Metadata(p)
    assert m.group_of("x1") == m.group_of("x2")


def test_stratify_keeps_every_bucket():
    items = [{"dx": "MEL"}, {"dx": "MEL"}, {"dx": "RARE"}]
    s = stratify_by(items, "dx")
    assert set(s) == {"MEL", "RARE"}
    assert s["RARE"] == [2]


def test_report_flags_small_buckets():
    s = {"MEL": list(range(50)), "RARE": [50, 51]}
    vals = [1.0] * 50 + [0.0, 0.0]
    rows = {r["stratum"]: r for r in report(s, vals)}
    assert rows["MEL"]["n"] == 50 and not rows["MEL"]["small_n"]
    assert rows["RARE"]["small_n"] is True
    assert rows["RARE"]["mean"] == 0.0


def test_diagnoses_tuple_is_the_isic_set():
    assert DIAGNOSES == ("MEL", "NV", "BCC", "AK", "BKL", "DF", "VASC", "SCC")
