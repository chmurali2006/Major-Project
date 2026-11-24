#!/usr/bin/env python3
"""Build a privacy/licensing-bounded source and evidence context ZIP.

The package is not a raw-data/model-weight release and deliberately strips
notebook outputs. It preserves repository-relative paths and writes a SHA-256
manifest for every included payload file (the manifest excludes itself).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = "Major-Project-Context-2026-10-19"
ZIP_PATH = ROOT / "deliverables/PROJECT_CONTEXT_BUNDLE_2026-10-19.zip"
MANIFEST_PATH = ROOT / "deliverables/PACKAGE_MANIFEST.csv"
EXCLUSIONS_PATH = ROOT / "deliverables/PACKAGE_EXCLUSIONS.md"

TEXT_EXTS = {
    ".md", ".txt", ".json", ".jsonl", ".csv", ".log", ".py", ".ipynb",
    ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".bib", ".sha256",
}
ROOT_FILES = {
    ".gitignore", "README.md", "PROJECT_CONTEXT_MASTER.md", "RUNNING.md",
    "PROTOCOL_V2.md", "FREEZE_PROTOCOL.md", "FREEZE_PROTOCOL.md.sha256",
    "requirements.txt", "requirements-test.txt", "requirements-presentation.txt",
    "requirements-editguard.txt", "requirements-training.txt", "pytest.ini",
    "pyproject.toml", "setup.cfg", "tox.ini",
}
DELIVERABLE_BINARY = {".docx", ".pptx"}
SENSITIVE_DIRS = {".git", ".venv", "venv", "node_modules", "google_drive", "__pycache__", ".cache"}
SENSITIVE_SUFFIXES = {
    ".zip", ".7z", ".rar", ".tar", ".gz", ".pt", ".pth", ".ckpt", ".onnx",
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff",
    ".npz", ".npy", ".pem", ".key", ".p12", ".pfx", ".db", ".sqlite",
    ".html", ".pdf", ".svg",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_safe_path(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in SENSITIVE_DIRS for part in rel.parts):
        return False
    if path.is_symlink() or not path.is_file():
        return False
    if path.suffix.lower() in SENSITIVE_SUFFIXES:
        return False
    # Never bundle obvious credential/private-key files, even if text-based.
    lower = path.name.lower()
    if any(term in lower for term in ("credentials", "secret", "private_key", "id_rsa")):
        return False
    return True


def include_path(path: Path) -> bool:
    if not is_safe_path(path):
        return False
    rel = path.relative_to(ROOT)
    if rel.as_posix() in {"deliverables/PACKAGE_MANIFEST.csv", "deliverables/PROJECT_CONTEXT_BUNDLE_2026-10-19.zip"}:
        return False
    if rel.as_posix() in ROOT_FILES:
        return True
    if rel.parts[0] in {"src", "scripts", "tests", "docs", "project-context", "notebooks", "results", "runs"}:
        if rel.parts[0] == "project-context" and len(rel.parts) > 1 and rel.parts[1] == "papers":
            return False
        return path.suffix.lower() in TEXT_EXTS
    if rel.parts[0] == "deliverables":
        if len(rel.parts) == 1:
            return False
        # Include current narrative/status documents, derived tables/receipts,
        # source notebooks and editable generated overview/deck; never archives/media.
        return path.suffix.lower() in TEXT_EXTS or path.suffix.lower() in DELIVERABLE_BINARY
    return False


def notebook_source_only(data: bytes) -> bytes:
    nb = json.loads(data.decode("utf-8"))
    nb.pop("widgets", None)
    for cell in nb.get("cells", []):
        cell.pop("outputs", None)
        cell.pop("execution_count", None)
        # Strip attachments in markdown cells: they can contain embedded pixels.
        cell.pop("attachments", None)
    # Drop transient execution metadata but retain kernel/language specification.
    md = nb.get("metadata", {})
    md.pop("execution", None)
    md.pop("widgets", None)
    return (json.dumps(nb, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def payload_files() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in ROOT.rglob("*"):
        if not include_path(path):
            continue
        rel = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        if path.suffix.lower() == ".ipynb":
            data = notebook_source_only(data)
        files[rel] = data
    required = {
        "PROJECT_CONTEXT_MASTER.md",
        "deliverables/T1_VALIDATION_RESULTS.md",
        "deliverables/PROJECT_FULL_OVERVIEW_AND_GAPS.md",
        "deliverables/CLAIMS_EVIDENCE_LIMITS.md",
        "deliverables/TEST_SPLIT_RECOVERY_DECISION.md",
        "deliverables/GATE0_PROVENANCE_STATUS.md",
        "deliverables/PROJECT_CONTEXT_PACKAGE_README.md",
    }
    # Package README is added from this location; master + evidence sources are required.
    required.discard("deliverables/PROJECT_CONTEXT_PACKAGE_README.md")
    missing = required - files.keys()
    if missing:
        raise RuntimeError(f"Required context files missing from package: {sorted(missing)}")
    files["deliverables/PROJECT_CONTEXT_PACKAGE_README.md"] = (ROOT / "deliverables/PROJECT_CONTEXT_PACKAGE_README.md").read_bytes()
    return dict(sorted(files.items()))


def exclusions_doc(files: dict[str, bytes]) -> bytes:
    lines = [
        "# Package exclusions and inventory boundary",
        "",
        "Snapshot: 2026-10-19 UTC. This is a curated project-context/source package, not a byte-for-byte repository or data/model release.",
        "",
        "Included: source code, tests, protocols, markdown/text documentation, reference/plan files, sanitized notebook source (all cell outputs/execution counts/attachments stripped), CSV/JSON/log evidence and analysis tables, plus the refreshed overview DOCX and presentation draft PPTX.",
        "",
        "Excluded by design:",
        "- `.git` history, virtual environments, dependency caches, build outputs and temporary files.",
        "- `google_drive/` contents (including the 40 MB T1 result ZIP and source metadata files). The T1 report/tables are included; visual case panels and any raw/user-provided archive are not redistributed.",
        "- Raw medical-image pixels, image/media files, patient/source metadata spreadsheets, and notebooks' rendered outputs/attachments.",
        "- Original mid-review/poster PDFs are not redistributed: embedded visual content has not been screened for medical pixels or permissions; a text-only transition record preserves reported claims and source links.",
        "- Model weights/checkpoints and other binary inference artifacts; opaque NumPy/NPZ maps; all ZIP/TAR/RAR archives (contents not fully screened for source images or licensing).",
        "- Full-text papers/PDFs and vector/raster figures. Bibliographic references/textual review notes remain where licensed/appropriate.",
        "- Private keys, credentials, databases and obvious secret-named files.",
        "",
        "Included path count: " + str(len(files)),
        "The adjacent `PACKAGE_MANIFEST.csv` lists each included payload path, its post-sanitization byte count and SHA-256. The manifest does not hash itself or the final ZIP (which would be recursive); the final ZIP hash is recorded in the outer manifest file.",
        "",
        "All exclusions are content/scope safeguards, not statements that omitted material does not exist. Obtain source/dataset/upstream licenses and owner approval before any redistribution.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ZIP_PATH)
    ap.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = ap.parse_args()
    files = payload_files()
    exclusions = exclusions_doc(files)
    files["PACKAGE_EXCLUSIONS.md"] = exclusions

    # Manifest hashes all payload files except itself.
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["path", "bytes", "sha256", "transform"])
    for rel, data in sorted(files.items()):
        transform = "notebook outputs/execution counts/attachments stripped" if rel.endswith(".ipynb") else "included bytes"
        writer.writerow([rel, len(data), sha(data), transform])
    manifest = buffer.getvalue().encode("utf-8")
    files["PACKAGE_MANIFEST.csv"] = manifest

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_bytes(manifest)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for rel, data in sorted(files.items()):
            info = zipfile.ZipInfo(f"{PACKAGE_ROOT}/{rel}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            zf.writestr(info, data)
    # Integrity and privacy guardrails on the produced package.
    with zipfile.ZipFile(args.output) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"ZIP integrity test failed at {bad}")
        names = zf.namelist()
        forbidden = [n for n in names if Path(n).suffix.lower() in SENSITIVE_SUFFIXES]
        if forbidden:
            raise RuntimeError(f"Forbidden file type(s) entered package: {forbidden[:10]}")
        for n in names:
            if n.endswith(".ipynb"):
                nb = json.loads(zf.read(n).decode("utf-8"))
                if any("outputs" in c or "execution_count" in c or "attachments" in c for c in nb.get("cells", [])):
                    raise RuntimeError(f"Notebook output was not stripped: {n}")
    print(json.dumps({
        "archive": str(args.output),
        "size_bytes": args.output.stat().st_size,
        "sha256": sha(args.output.read_bytes()),
        "payload_files": len(files),
        "manifest": str(args.manifest),
        "zip_test": "passed",
        "notebooks_source_only": True,
    }, indent=2))


if __name__ == "__main__":
    main()
