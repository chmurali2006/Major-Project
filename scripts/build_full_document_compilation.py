"""Combine the project overview and related narrative/status documents verbatim."""
from hashlib import sha256
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MD_OUT = ROOT / "deliverables/PROJECT_COMPLETE_DOCUMENT_COMPILATION.md"
TXT_OUT = ROOT / "deliverables/PROJECT_COMPLETE_DOCUMENT_COMPILATION.txt"

# Current controlling documents come first. Older protocol/planning snapshots are
# included in full for completeness and are explicitly labeled as historical where
# they conflict with the current split disposition.
SOURCES = [
    ("PROJECT_CONTEXT_MASTER.md", "Authoritative cross-strand project status and document index", "Start here; status date 2026-10-19 UTC."),
    ("deliverables/PROJECT_CONTEXT_PACKAGE_README.md", "Context bundle scope and exclusions", "Read before redistribution; raw images, weights and archives are excluded."),
    ("deliverables/T1_VALIDATION_RESULTS.md", "T1 three-model validation results", "Validation-only; no TEST access; no independent source-pixel/model replay."),
    ("deliverables/MIDREVIEW_POSTER_TRANSITION_RECORD.md", "Historical mid-review/poster transition record", "Legacy ISIC 2018 watermark claims; date/provenance unresolved; not current T1 evidence."),
    ("deliverables/PROJECT_FULL_OVERVIEW_AND_GAPS.md", "Consolidated current project inventory and research plan", "Detailed inventory; includes T1 and evidence boundaries."),
    ("deliverables/TEST_SPLIT_RECOVERY_DECISION.md", "Controlling historical test-membership decision", "Recovery is closed unless authentic original membership evidence appears."),
    ("deliverables/GATE0_PROVENANCE_STATUS.md", "Provenance and evaluation-state record", "Receipt checks are distinguished from source/data replay."),
    ("deliverables/CLAIMS_EVIDENCE_LIMITS.md", "Claim/evidence/boundary handout", "Use these boundaries in academic reporting."),
    ("deliverables/MATCHED_EDITGUARD_VALIDATION_RETURN_REVIEW.md", "Matched EditGuard returned-record audit", "Receipt/signature audit; not pixel/model replay."),
    ("deliverables/PRESENTATION_DEFENSE_PACK.md", "Faculty presentation cues and claim guardrails", "Aligned to the revised faculty deck."),
    ("deliverables/INDEPENDENT_REVIEW_REPORT.md", "Independent-review findings and updates", "Historical findings are retained; current disposition is cross-referenced."),
    ("deliverables/KAGGLE_EXECUTION_GUIDE.md", "External validation handoff and current holdout status", "Current 500-image holdout is not authorized for further outcome analysis."),
    ("README.md", "Repository landing page", "Root project entry point."),
    ("PROTOCOL_V2.md", "RGB-HMAC protocol specification", "Separate study line; not the detached Ed25519 system."),
    ("RUNNING.md", "Execution and environment guide", "Safe current instructions; TEST execution remains blocked."),
    ("docs/LITERATURE.md", "Research references and novelty boundaries", "Bibliographic details/licences still require verification."),
    ("docs/DESIGN_REVIEW.md", "Technical design review and historical experiment log", "Long-form historical record; some older status entries are superseded."),
    ("docs/REVIEW_READINESS_PLAN.md", "Research readiness and evaluation plan", "Use current split decision over any older test workflow references."),
    ("docs/ADAPTED_FINALISATION_ROADMAP.md", "Adapted-cohort roadmap", "Contains historical planning sections; current status is stated near the top."),
    ("docs/ACADEMIC_UPGRADE_IMPLEMENTATION_PLAN.md", "Academic upgrade plan", "Candidate ideas are not results; current cohort cannot be confirmatory."),
    ("docs/STUDY_TO_CONTRIBUTION.md", "Study-to-contribution and QIM review", "Contains historical snapshot passages; status correction appears near the top."),
    ("docs/FACULTY_REVIEW_AND_CLASSIFIER_RETURN.md", "Classifier-return review", "Receipt-level classifier review and its limitations."),
    ("project-context/README.md", "Project-context index", "Links to the consolidated inventory."),
    ("FREEZE_PROTOCOL.md", "TEST-protocol revocation notice", "Old executable switches and commands were removed; not an active protocol."),
    ("deliverables/DIAGNOSTIC_EMBEDDING_PILOT_REVIEW_ADDENDUM.txt", "QIM pilot review addendum", "Historical small TRAIN pilot; not a main efficacy claim."),
    ("deliverables/PROJECT_INDEPENDENT_REVIEW_SNAPSHOT.txt", "Long-form independent-review dossier", "Historical snapshot; its current-status override is at the beginning."),
]


def load_sources():
    loaded = []
    for rel, role, warning in SOURCES:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(f"Required source document is missing: {rel}")
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        loaded.append({
            "path": rel,
            "role": role,
            "warning": warning,
            "text": text,
            "size": len(raw),
            "sha256": sha256(raw).hexdigest(),
        })
    return loaded


def cover(docs):
    lines = [
        "PROJECT COMPLETE DOCUMENT COMPILATION",
        "Full narrative, protocol, evidence, review, and planning texts",
        "",
        "Purpose: provide one portable text bundle containing the full contents of the project's relevant narrative and status documents. The individual source texts below are included in full; they are not summarized or silently edited in this compilation.",
        "",
        "Scope boundary: this compilation contains documentation only. It does not embed source code, notebooks, raw medical images, model weights, credentials, or binary result archives. Those remain in their original repository paths and are referenced by the documents.",
        "",
        "Reading order / authority:",
        "1. Start with PROJECT_CONTEXT_MASTER.md for the authoritative cross-strand status; then use T1_VALIDATION_RESULTS.md and PROJECT_FULL_OVERVIEW_AND_GAPS.md for detailed evidence.",
        "2. The test-split decision, Gate 0 status, claims table, and matched-return review are the controlling current records for their topics.",
        "3. Protocols, design reviews, and older planning/snapshot documents are included for completeness. They may preserve historical statements; their current-status corrections and the revocation notice take precedence. The later 500-image cohort is non-confirmatory and closed to further outcome analysis.",
        "4. Reopen the historical membership decision only if authentic original membership evidence appears.",
        "",
        f"Included source documents: {len(docs)}",
        "",
        "SOURCE MANIFEST (byte counts and SHA-256 identify the exact source files included):",
    ]
    for i, d in enumerate(docs, 1):
        lines.append(f"{i:02d}. {d['path']} | {d['size']} bytes | SHA-256 {d['sha256']}")
    return "\n".join(lines)


def build():
    docs = load_sources()
    intro = cover(docs)
    md = [
        "# Project complete document compilation",
        "",
        "> This bundle includes the full text of all listed project narrative/status documents. It is a documentation compilation, not an archive of source code, notebooks, data pixels, model weights, or binary results.",
        "",
        "## How to read this bundle",
        "",
        "The consolidated overview, historical mid-review/poster transition record, and current decision records appear first. The transition record explicitly separates stage claims from current results. Older protocol/planning/review files are included verbatim afterward for completeness; some preserve superseded instructions. The controlling split decision takes precedence: the current later holdout is non-confirmatory and must not be opened for further outcome analysis.",
        "",
        "## Source manifest",
        "",
        "| # | Source path | Role / status | Bytes | SHA-256 |",
        "|---:|---|---|---:|---|",
    ]
    for i, d in enumerate(docs, 1):
        md.append(f"| {i} | `{d['path']}` | {d['role']} {d['warning']} | {d['size']} | `{d['sha256']}` |")
    md.extend(["", "## Full source texts", ""])
    txt = ["\n" + "=" * 88, "FULL SOURCE DOCUMENTS", "=" * 88]
    for i, d in enumerate(docs, 1):
        heading = f"{i:02d}. {d['path']}"
        md.extend([
            f"### {heading}",
            "",
            f"**Role:** {d['role']}  ",
            f"**Status note:** {d['warning']}  ",
            f"**Source SHA-256:** `{d['sha256']}` ({d['size']} bytes)",
            "",
        ])
        max_run = max((len(m.group(0)) for m in re.finditer(r"`+", d["text"])), default=0)
        fence = "`" * max(3, max_run + 1)
        md.extend([fence + "text", d["text"].rstrip("\n"), fence, ""])
        txt.extend([
            "\n" + "=" * 88,
            heading,
            f"ROLE: {d['role']}",
            f"STATUS NOTE: {d['warning']}",
            f"SOURCE: {d['size']} bytes; SHA-256 {d['sha256']}",
            "=" * 88,
            d["text"].rstrip("\n"),
        ])
    MD_OUT.write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    TXT_OUT.write_text(intro + "\n" + "\n".join(txt) + "\n", encoding="utf-8")
    return MD_OUT, TXT_OUT, len(docs)


if __name__ == "__main__":
    md_path, txt_path, count = build()
    print(f"Wrote {count} full source documents:\n{md_path}\n{txt_path}")
