"""Semantic gates for private STR Property Information note bodies.

This packet models the architecture without live Apple Notes access.  The
private-note validator is intentionally different from public redaction checks:
private notes must contain usable operational facts, while public artifacts must
not expose those facts.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

PRIVATE_SECTIONS = [
    "Access & Codes",
    "Wi-Fi / Systems",
    "Contacts",
    "Other Property Contacts",
    "Needs Confirmation",
    "Field Basics",
    "Current / Upcoming Stays",
    "Operations Notes",
    "Business Snapshot",
    "Refresh / Source Coverage",
]

NEEDS_CONFIRMATION_TERMS = [
    "MISSING",
    "not found",
    "candidate",
    "CANDIDATE",
    "needs confirmation",
    "unconfirmed",
    "conflict",
]

FORBIDDEN_PRIVATE_PROCESS_TERMS = [
    "audit report",
    "audit packet",
    "canonical review",
    "review packet",
    "validator",
    "validation",
    "gate result",
    "gate:",
    "source receipt",
    "execute report",
    "backend sync",
    "local cache",
    "dry-run",
    "dry run",
    "source-backed",
    "source path",
    "progress path",
    "ops/progress",
    "data/str_property_backend",
    "private backend",
    "private store",
    "FAIL_BLOCKS_PUBLISH",
    "PASS_WITH_FALLBACK",
    "no Apple Notes publish",
    "publish remains blocked",
    "public artifact",
]

AUDIT_SECTION_HEADINGS = [
    "Evidence / Refresh Notes",
    "Source / Refresh Notes",
    "Gate Summary",
    "Commands And Exit Codes",
    "Files Changed",
    "Source Family Coverage",
    "Architecture Claims",
]

GENERIC_FILLER_PATTERNS = [
    re.compile(r"\bowner (?:was|is) responsive\b", re.I),
    re.compile(r"\bcleaner (?:confirmed|activity) (?:normal|routine)\b", re.I),
    re.compile(r"\bno known issues\b", re.I),
    re.compile(r"\broutine maintenance (?:normal|ok)\b", re.I),
    re.compile(r"\bevidence supports context\b", re.I),
    re.compile(r"\bcontext remains sourced\b", re.I),
    re.compile(r"\bmessage-derived facts are staged\b", re.I),
    re.compile(r"\bsource-backed row pending\b", re.I),
    re.compile(r"\bpublish readiness is determined\b", re.I),
]

PRIVATE_REQUIRED_VALUE_PLACEHOLDERS = [
    "[REDACTED",
    "REDACTED_",
    "private value present",
    "private_value_present",
    "exists in private",
    "private ref",
    "private_ref",
    "locked_note_private_value_required",
]

PUBLIC_PRIVATE_VALUE_PATTERNS = [
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"(?i)\b(?:door|gate|garage|lockbox|keypad|admin|programming)\s+(?:code|pin)\s*[:#=-]\s*(?!\[REDACTED)[A-Z0-9-]{4,}\b"),
    re.compile(r"(?i)\b(?:wi[\s-]?fi|wifi|router).{0,24}(?:password|passcode)\s*[:#=-]\s*(?!\[REDACTED)[A-Z0-9-]{4,}\b"),
    re.compile(r"\bSAMPLE_(?:GUEST|ADMIN|WIFI)_[A-Z_]*\b"),
]


def visible_text(body: str) -> str:
    text = re.sub(r"(?i)<br\s*/?>", "\n", body or "")
    text = re.sub(r"(?i)</(?:div|p|li|h[1-6])\s*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def rendered_sections(body: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = ""
    token_re = re.compile(
        r"(?is)<h[1-6][^>]*>(.*?)</h[1-6]>"
        r"|<li[^>]*>(.*?)</li>"
        r"|(?:^|\n)##\s+([^\n]+)"
        r"|(?:^|\n)-\s+([^\n]+)"
    )
    for match in token_re.finditer(body or ""):
        heading = match.group(1) if match.group(1) is not None else match.group(3)
        item = match.group(2) if match.group(2) is not None else match.group(4)
        if heading is not None:
            current = visible_text(heading).strip()
            sections.setdefault(current, [])
        elif item is not None and current:
            sections.setdefault(current, []).append(visible_text(item))
    return sections


def _section_text(sections: dict[str, list[str]], name: str) -> str:
    return "\n".join(sections.get(name) or [])


def _section_index(text: str, section: str) -> int:
    match = re.search(rf"(?im)^\s*(?:#+\s*)?{re.escape(section)}\s*$|<h[1-6][^>]*>\s*{re.escape(section)}\s*</h[1-6]>", text)
    return match.start() if match else -1


def _has_detail(text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 16:
        return False
    return not any(token.lower() in cleaned.lower() for token in PRIVATE_REQUIRED_VALUE_PLACEHOLDERS)


def _contains_needs_confirmation_term(text: str) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in NEEDS_CONFIRMATION_TERMS)


def evaluate_public_redaction_gate(text: str, *, property_id: str = "sample_property") -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for pattern in PUBLIC_PRIVATE_VALUE_PATTERNS:
        for match in pattern.finditer(text or ""):
            findings.append({"check": "public_redaction_gate", "message": f"private-looking value: {match.group(0)[:80]}"})
    if re.search(r"(?is)source body\s*:\s*['\"].{40,}", text or ""):
        findings.append({"check": "public_redaction_gate", "message": "raw source body appears in public artifact"})
    return {"ok": not findings, "property_id": property_id, "findings": findings}


def evaluate_private_operations_note(body: str, *, property_id: str = "sample_property", mode: str = "live_readback") -> dict[str, Any]:
    plain = visible_text(body)
    sections = rendered_sections(body)
    findings: list[dict[str, str]] = []

    missing_sections = [section for section in PRIVATE_SECTIONS if section not in sections]
    if missing_sections:
        findings.append({"check": "private_section_contract", "message": "missing sections: " + ", ".join(missing_sections)})

    for prior, later in zip(PRIVATE_SECTIONS, PRIVATE_SECTIONS[1:]):
        if _section_index(body, prior) > _section_index(body, later) >= 0:
            findings.append({"check": "private_section_order", "message": f"{prior} appears after {later}"})

    for heading in AUDIT_SECTION_HEADINGS:
        if heading in sections:
            findings.append({"check": "private_audit_shape", "message": f"audit-shaped section is not allowed in private note: {heading}"})

    lowered = plain.lower()
    for term in FORBIDDEN_PRIVATE_PROCESS_TERMS:
        if term.lower() in lowered:
            findings.append({"check": "forbidden_process_text", "message": f"forbidden private-note process/audit term: {term}"})

    for pattern in GENERIC_FILLER_PATTERNS:
        if pattern.search(plain):
            findings.append({"check": "generic_filler", "message": f"generic filler matched: {pattern.pattern}"})

    needs_confirmation_text = _section_text(sections, "Needs Confirmation")
    for section, rows in sections.items():
        if section == "Needs Confirmation":
            continue
        for row in rows:
            if _contains_needs_confirmation_term(row):
                findings.append({"check": "needs_confirmation_placement", "message": f"missing/candidate/conflict language outside Needs Confirmation: {section}"})

    access_text = _section_text(sections, "Access & Codes")
    if not re.search(r"(?i)\b(?:guest|front door|door/keypad)\b.*\bcode\b", access_text):
        findings.append({"check": "access_contract", "message": "guest/front-door access code row missing"})
    if not re.search(r"(?i)\b(?:admin|programming)\b.*\bcode\b", access_text):
        findings.append({"check": "access_contract", "message": "admin/programming code row or Needs Confirmation decision missing"})
    access_values = re.findall(r"(?i)\b(?:code|pin)\s*(?:[:#=-]|uses)\s*([A-Z0-9_-]{4,})", access_text)
    if len(set(access_values)) < len(access_values):
        findings.append({"check": "access_contract", "message": "guest and admin/programming code values are not distinct"})
    if not _has_detail(access_text):
        findings.append({"check": "access_contract", "message": "access section lacks usable private-note detail"})

    wifi_text = _section_text(sections, "Wi-Fi / Systems")
    if not re.search(r"(?i)\bnetwork\b", wifi_text) or not re.search(r"(?i)\bpassword\b", wifi_text):
        findings.append({"check": "wifi_contract", "message": "Wi-Fi network and password must both be present"})
    if not _has_detail(wifi_text):
        findings.append({"check": "wifi_contract", "message": "Wi-Fi section lacks usable private-note detail"})

    contacts_text = _section_text(sections, "Contacts")
    if not re.search(r"(?i)\bowner\b", contacts_text):
        findings.append({"check": "contacts_contract", "message": "owner contact missing"})
    if not re.search(r"(?i)\bcleaner|turnover\b", contacts_text):
        findings.append({"check": "contacts_contract", "message": "cleaner/turnover contact missing"})
    if re.search(r"(?i)\bowner\b.*\bcleaner\b|\bcleaner\b.*\bowner\b", contacts_text):
        findings.append({"check": "contacts_contract", "message": "owner and cleaner roles appear collapsed in one row"})

    field_text = _section_text(sections, "Field Basics")
    for marker in ["Address", "Parking", "Trash"]:
        if marker.lower() not in field_text.lower():
            findings.append({"check": "field_basics_contract", "message": f"missing field basic: {marker}"})

    stay_text = _section_text(sections, "Current / Upcoming Stays")
    if not re.search(r"(?i)\bCurrent\b", stay_text) or not re.search(r"(?i)\bNext\b", stay_text):
        findings.append({"check": "stay_contract", "message": "current and next stay rows are required"})

    operations_text = _section_text(sections, "Operations Notes")
    if len([row for row in sections.get("Operations Notes", []) if _has_detail(row)]) < 2:
        findings.append({"check": "operations_contract", "message": "operations notes need at least two actionable rows"})

    business_text = _section_text(sections, "Business Snapshot")
    if not re.search(r"(?i)\b(?:YTD|year to date|trailing|revenue|bookings|nights)\b", business_text):
        findings.append({"check": "business_contract", "message": "business snapshot lacks booking/revenue/nights context"})

    refresh_rows = sections.get("Refresh / Source Coverage") or []
    refresh_text = _section_text(sections, "Refresh / Source Coverage")
    if not 1 <= len(refresh_rows) <= 3:
        findings.append({"check": "refresh_contract", "message": "Refresh / Source Coverage must be short (1-3 rows)"})
    if re.search(r"(?i)\b(?:ops/progress|gate|audit|receipt|source body|command|exit code)\b", refresh_text):
        findings.append({"check": "refresh_contract", "message": "refresh section contains process/source/audit prose"})

    if needs_confirmation_text:
        for row in sections.get("Needs Confirmation", []):
            if re.search(r"(?i)\bcandidate\b", row) and not re.search(r"\bCANDIDATE\b", row):
                findings.append({"check": "candidate_labeling", "message": "candidate facts must be labeled CANDIDATE"})

    return {
        "ok": not findings,
        "property_id": property_id,
        "mode": mode,
        "plain_chars": len(plain),
        "section_row_counts": {section: len(rows) for section, rows in sections.items()},
        "findings": findings,
    }


def evaluate_body(body: str, *, mode: str = "live_readback", property_id: str = "sample_property") -> dict[str, Any]:
    return evaluate_private_operations_note(body, property_id=property_id, mode=mode)


def evaluate_source_receipts(property_id: str = "sample_property", receipt_path: Path | None = None) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    if not receipt_path or not receipt_path.exists():
        return {"ok": False, "property_id": property_id, "findings": [{"check": "source_receipt_gate", "message": "receipt json missing"}]}
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    for row in payload.get("source_families") or []:
        if not row.get("source_family") or not row.get("status"):
            findings.append({"check": "source_receipt_gate", "message": "source family row missing family/status"})
        if row.get("status") in {"source_adapter_unavailable_with_error", "auth_unavailable"} and not row.get("error"):
            findings.append({"check": "source_receipt_gate", "message": f"{row.get('source_family')} unavailable without exact error"})
    return {"ok": not findings, "property_id": property_id, "findings": findings}


def evaluate_closeout_truth(closeout_text: str, live_body: str, *, property_id: str = "sample_property") -> dict[str, Any]:
    readback = evaluate_private_operations_note(live_body, property_id=property_id, mode="closeout_truth_live_readback")
    redaction = evaluate_public_redaction_gate(closeout_text, property_id=property_id)
    findings = list(readback.get("findings") or []) + list(redaction.get("findings") or [])
    if "PUBLISHED_VERIFIED_SAMPLE_PROPERTY" in closeout_text:
        findings.append({"check": "closeout_truth_gate", "message": "deprecated success state used"})
    return {"ok": not findings, "property_id": property_id, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate sanitized STR Property Information note gates.")
    parser.add_argument("--property-id", default="sample_property")
    parser.add_argument("--body-file")
    parser.add_argument("--mode", choices=["expected", "live_readback", "source_receipt", "public_redaction"], default="live_readback")
    parser.add_argument("--receipt-json")
    args = parser.parse_args(argv)
    if args.mode == "source_receipt":
        result = evaluate_source_receipts(args.property_id, Path(args.receipt_json) if args.receipt_json else None)
    else:
        if not args.body_file:
            parser.error("--body-file is required unless --mode source_receipt")
        text = Path(args.body_file).read_text(encoding="utf-8")
        result = evaluate_public_redaction_gate(text, property_id=args.property_id) if args.mode == "public_redaction" else evaluate_body(text, mode=args.mode, property_id=args.property_id)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
