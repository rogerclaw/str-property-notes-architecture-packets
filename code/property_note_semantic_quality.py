"""Semantic/usefulness gates for STR Property Information note bodies."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROGRESS_DIR = ROOT / "ops" / "progress"

FORBIDDEN_PROCESS_TERMS = [
    "dry-run",
    "dry run",
    "review packet",
    "canonical review",
    "canonical facts",
    "staged as candidates",
    "source-backed",
    "source coverage",
    "source-exhausted",
    "verified-negative",
    "review-gated",
    "non-blocking",
    "fallback policy",
    "publish remains blocked",
    "Charles review",
    "inputs checked",
    "private store",
    "private backend",
    "ops/progress",
    "data/str_property_backend",
    "scripts/",
    "FAIL_BLOCKS_PUBLISH",
    "PASS_WITH_FALLBACK",
    "gate result",
    "gate:",
    "not a source for",
    "must be refreshed through",
    "context remains sourced",
    "intentionally separated",
    "retained as manager context",
    "does not substitute",
    "no Apple Notes publish",
]

FORBIDDEN_LINK_MARKUP = ["<a href=", "</a>", "utm_content=", "utm_campaign="]

NEGATIVE_UNKNOWN_PATTERNS = [
    re.compile(r"No verified .* found", re.I),
    re.compile(r"not found in checked sources", re.I),
    re.compile(r"missing_required", re.I),
    re.compile(r"MISSING_REQUIRED"),
    re.compile(r"needs confirmation", re.I),
    re.compile(r"unconfirmed", re.I),
]

GENERIC_FILLER = [
    "Occupancy and revenue context remains sourced from the existing reservation backend",
    "Upcoming-stay context must be refreshed through reservation tooling",
    "Owner-email evidence is staged as candidates",
    "Message-derived facts are staged only when they reveal durable facts",
    "Review and listing signal is contextual only",
    "Publish readiness is determined by objective source",
    "Source-backed row pending canonical review",
    "evidence supports context",
]

REQUIRED_SECTIONS = [
    "Access & Codes",
    "Contacts",
    "Wi-Fi / Systems",
    "Field Basics",
    "Links",
    "Evidence / Refresh Notes",
]

REQUIRED_EVIDENCE_SUBSECTIONS = [
    "Occupancy & Money",
    "Current / Upcoming Stays",
    "Owner Communication Snapshot",
    "Cleaner Message Activity",
    "Other Message Activity",
    "Charles Visit Stats",
    "Difficulty Ranking",
    "Airbnb / Review Signal",
    "Recent Notable Events",
    "Repairs / Maintenance To Do",
    "Management Notes",
    "Source / Refresh Notes",
]

REQUIRED_SOURCE_FAMILIES = [
    "apple_notes_current",
    "apple_notes_historical",
    "backend_private",
    "cc_email",
    "charles_work_email",
    "strops_email",
    "personal_message_bridge",
    "hospitable_api",
    "hospitable_webhooks",
    "airbnb_listing_reviews",
    "house_manual_docs_permits",
    "maintenance_repair_artifacts",
]

VALID_SOURCE_STATUSES = {
    "searched",
    "searched_no_hits",
    "source_adapter_unavailable_with_error",
    "auth_unavailable",
    "hits_found",
}


def visible_text(body: str) -> str:
    text = re.sub(r"(?i)<br\s*/?>", "\n", body or "")
    text = re.sub(r"(?i)</(?:div|p|li|h[1-6])\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def rendered_sections(body: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    token_re = re.compile(
        r"(?is)<h[1-6][^>]*>(.*?)</h[1-6]>"
        r"|<div><b><span style=\"font-size:\s*(?:18|24)px\">(.*?)</span></b>(?:<br>)?</div>"
        r"|<li[^>]*>(.*?)</li>"
    )
    for match in token_re.finditer(body or ""):
        heading = match.group(1) if match.group(1) is not None else match.group(2)
        item = match.group(3)
        if heading is not None:
            current = visible_text(heading)
            sections.setdefault(current, [])
        elif item is not None and current:
            sections.setdefault(current, []).append(visible_text(item))
    return sections


def _contains_any(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def evaluate_body(body: str, *, mode: str = "expected", property_id: str = "sample_property") -> dict[str, Any]:
    plain = visible_text(body)
    sections = rendered_sections(body)
    findings: list[dict[str, str]] = []

    for term in _contains_any(body, FORBIDDEN_LINK_MARKUP):
        findings.append({"check": "link_serialization", "message": f"visible link/html marker: {term}"})
    if re.search(r"https?://[^\s<]*&amp;", body or "", re.I):
        findings.append({"check": "link_serialization", "message": "escaped ampersand in visible URL"})
    for term in _contains_any(plain, FORBIDDEN_PROCESS_TERMS):
        findings.append({"check": "forbidden_process_text", "message": f"forbidden process text: {term}"})
    for pattern in NEGATIVE_UNKNOWN_PATTERNS:
        if pattern.search(plain):
            findings.append({"check": "negative_unknown_row", "message": f"negative/unknown polished row matched: {pattern.pattern}"})
    for term in _contains_any(plain, GENERIC_FILLER):
        findings.append({"check": "generic_filler", "message": f"generic filler: {term[:80]}"})

    missing_sections = [section for section in REQUIRED_SECTIONS if section not in sections]
    if missing_sections:
        findings.append({"check": "section_contract", "message": "missing sections: " + ", ".join(missing_sections)})

    minimum_rows = {
        "Access & Codes": 1,
        "Contacts": 3,
        "Wi-Fi / Systems": 2,
        "Field Basics": 3,
        "Links": 2,
        "Evidence / Refresh Notes": 20,
    }
    for section, minimum in minimum_rows.items():
        if section == "Evidence / Refresh Notes":
            count = sum(len(sections.get(subsection) or []) for subsection in REQUIRED_EVIDENCE_SUBSECTIONS)
            if count == 0:
                count = len(sections.get(section) or [])
        else:
            count = len(sections.get(section) or [])
        if count < minimum:
            findings.append({"check": "manager_usefulness_density", "message": f"{section} has {count} rows; expected at least {minimum}"})

    for subsection in REQUIRED_EVIDENCE_SUBSECTIONS:
        if subsection not in plain:
            findings.append({"check": "evidence_subsection", "message": f"missing evidence subsection: {subsection}"})

    required_markers = [
        "Door/keypad code:",
        "Owner -",
        "Cleaner",
        "Network:",
        "Password:",
        "123 Example St",
        "Trash pickup:",
        "Current:",
        "Next 1:",
        "Year to date",
        "Trailing year",
        "rating",
        "Recent event:",
        "Repair:",
        "Management guidance:",
    ]
    for marker in required_markers:
        if marker.lower() not in plain.lower():
            findings.append({"check": "manager_usefulness_content", "message": f"missing concrete marker: {marker}"})

    return {
        "ok": not findings,
        "property_id": property_id,
        "mode": mode,
        "plain_chars": len(plain),
        "section_row_counts": {section: len(rows) for section, rows in sections.items()},
        "findings": findings,
    }


def latest_receipt_json(property_id: str) -> Path:
    return PROGRESS_DIR / f"{property_id}_live_source_sweep_receipts_20260702.json"


def evaluate_source_receipts(property_id: str = "sample_property", receipt_path: Path | None = None) -> dict[str, Any]:
    path = receipt_path or latest_receipt_json(property_id)
    findings: list[dict[str, str]] = []
    if not path.exists():
        return {"ok": False, "property_id": property_id, "receipt_path": str(path), "findings": [{"check": "source_receipt_gate", "message": "receipt json missing"}]}
    payload = json.loads(path.read_text(encoding="utf-8"))
    families = {row.get("source_family"): row for row in payload.get("source_families") or []}
    for family in REQUIRED_SOURCE_FAMILIES:
        row = families.get(family)
        if not row:
            findings.append({"check": "source_receipt_gate", "message": f"missing source family: {family}"})
            continue
        status = str(row.get("status") or "")
        if status not in VALID_SOURCE_STATUSES:
            findings.append({"check": "source_receipt_gate", "message": f"{family} invalid status: {status}"})
        if status in {"source_adapter_unavailable_with_error", "auth_unavailable"} and not row.get("error"):
            findings.append({"check": "source_receipt_gate", "message": f"{family} unavailable without exact error"})
    return {"ok": not findings, "property_id": property_id, "receipt_path": str(path), "findings": findings}


def evaluate_closeout_truth(closeout_text: str, live_body: str, *, property_id: str = "sample_property") -> dict[str, Any]:
    body_result = evaluate_body(live_body, mode="closeout_truth_live_readback", property_id=property_id)
    findings = list(body_result.get("findings") or [])
    if "PUBLISHED_VERIFIED_SAMPLE_PROPERTY" in closeout_text:
        findings.append({"check": "closeout_truth_gate", "message": "deprecated success state used"})
    if "PUBLISHED_USEFUL_SAMPLE_PROPERTY_V2_DEVICE_VERIFIED" in closeout_text and not body_result["ok"]:
        findings.append({"check": "closeout_truth_gate", "message": "success closeout attempted while live body fails semantic gate"})
    return {"ok": not findings, "property_id": property_id, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate STR Property Information note semantic quality.")
    parser.add_argument("--property-id", default="sample_property")
    parser.add_argument("--body-file")
    parser.add_argument("--mode", choices=["expected", "live_readback", "source_receipt"], default="expected")
    parser.add_argument("--receipt-json")
    args = parser.parse_args(argv)
    if args.mode == "source_receipt":
        result = evaluate_source_receipts(args.property_id, Path(args.receipt_json) if args.receipt_json else None)
    else:
        if not args.body_file:
            parser.error("--body-file is required unless --mode source_receipt")
        result = evaluate_body(Path(args.body_file).read_text(encoding="utf-8"), mode=args.mode, property_id=args.property_id)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
