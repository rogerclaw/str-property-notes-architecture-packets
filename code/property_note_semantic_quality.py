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

PRIVATE_TOP_LEVEL_SECTIONS = [
    "Access & Codes",
    "Contacts",
    "Wi-Fi / Systems",
    "Field Basics",
    "Links",
    "Evidence / Refresh Notes",
]

EVIDENCE_REFRESH_SUBSECTIONS = [
    "Occupancy & Money",
    "Current / Upcoming Stays",
    "Owner & Message Activity",
    "Charles Visit Stats",
    "Difficulty Ranking",
    "Airbnb / Review Signal",
    "Recent Notable Events",
    "Active Ops Watchlist",
    "Management Notes",
    "Source / Refresh Notes",
]

PRIVATE_SECTIONS = PRIVATE_TOP_LEVEL_SECTIONS + EVIDENCE_REFRESH_SUBSECTIONS

NEEDS_CONFIRMATION_ALLOWED_SECTIONS = {
    "Management Notes",
    "Source / Refresh Notes",
}

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
    "canonical facts",
    "review packet",
    "validator",
    "validation",
    "gate result",
    "gate:",
    "execute report",
    "backend sync",
    "local cache",
    "dry-run",
    "dry run",
    "source path",
    "progress path",
    "ops/progress",
    "data/str_property_backend",
    "private backend",
    "private store",
    "backend row",
    "private row",
    "FAIL_BLOCKS_PUBLISH",
    "PASS_WITH_FALLBACK",
    "failed-publish repair",
    "process-heavy note",
    "no Apple Notes publish",
    "no Apple Notes publish occurred",
    "publish remains blocked",
    "public artifact",
]

AUDIT_SECTION_HEADINGS = [
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
    re.compile(r"\bsource-backed row pending canonical review\b", re.I),
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


def _detail_count(sections: dict[str, list[str]], section: str) -> int:
    return len([row for row in sections.get(section, []) if _has_detail(row)])


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

    for section, rows in sections.items():
        if section in NEEDS_CONFIRMATION_ALLOWED_SECTIONS:
            continue
        for row in rows:
            if _contains_needs_confirmation_term(row):
                findings.append({"check": "needs_confirmation_placement", "message": f"missing/candidate/conflict language outside management/source refresh notes: {section}"})

    access_text = _section_text(sections, "Access & Codes")
    if not re.search(r"(?i)\b(?:guest|front door|door/keypad)\b.*\bcode\b", access_text):
        findings.append({"check": "access_contract", "message": "guest/front-door access code row missing"})
    if not re.search(r"(?i)\b(?:admin|programming)\b.*\bcode\b", access_text):
        findings.append({"check": "access_contract", "message": "admin/programming code row or manager/source refresh decision missing"})
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

    links_text = _section_text(sections, "Links")
    if not re.search(r"(?i)\b(?:airbnb|house manual|manual|listing|map|permit)\b", links_text):
        findings.append({"check": "links_contract", "message": "links section lacks manager-useful listing/manual/map/permit link context"})
    if not _has_detail(links_text):
        findings.append({"check": "links_contract", "message": "links section lacks usable private-note detail"})

    occupancy_text = _section_text(sections, "Occupancy & Money")
    if not re.search(r"(?i)\b(?:YTD|year to date|trailing|revenue|bookings|nights|occupancy)\b", occupancy_text):
        findings.append({"check": "occupancy_money_contract", "message": "occupancy/money subsection lacks booking/revenue/nights context"})

    stay_text = _section_text(sections, "Current / Upcoming Stays")
    if not re.search(r"(?i)\bCurrent\b", stay_text) or not re.search(r"(?i)\bNext\b", stay_text):
        findings.append({"check": "stay_contract", "message": "current and next stay rows are required"})

    owner_message_text = _section_text(sections, "Owner & Message Activity")
    if not re.search(r"(?i)\b(?:owner|message|cleaner|guest)\b", owner_message_text):
        findings.append({"check": "owner_message_contract", "message": "owner/message activity subsection lacks message context"})

    visit_text = _section_text(sections, "Charles Visit Stats")
    if not re.search(r"(?i)\bCharles\b", visit_text) or not re.search(r"(?i)\bvisit\b", visit_text):
        findings.append({"check": "charles_visit_contract", "message": "Charles visit stats subsection lacks visit context"})

    difficulty_text = _section_text(sections, "Difficulty Ranking")
    if not re.search(r"(?i)\b(?:difficulty|ranking|rank|easy|medium|hard|complex)\b", difficulty_text):
        findings.append({"check": "difficulty_contract", "message": "difficulty ranking subsection lacks ranking context"})

    review_text = _section_text(sections, "Airbnb / Review Signal")
    if not re.search(r"(?i)\bAirbnb\b", review_text) or not re.search(r"(?i)\b(?:review|rating|guest signal)\b", review_text):
        findings.append({"check": "review_signal_contract", "message": "Airbnb/review subsection lacks review signal"})

    for subsection in ["Recent Notable Events", "Active Ops Watchlist", "Management Notes"]:
        if _detail_count(sections, subsection) < 1:
            findings.append({"check": "evidence_refresh_contract", "message": f"{subsection} needs at least one useful manager row"})

    source_rows = sections.get("Source / Refresh Notes") or []
    source_text = _section_text(sections, "Source / Refresh Notes")
    if not 1 <= len(source_rows) <= 4:
        findings.append({"check": "source_refresh_contract", "message": "Source / Refresh Notes must be short (1-4 rows)"})
    if re.search(r"(?i)\b(?:ops/progress|gate|audit|receipt|source body|command|exit code|backend sync|local cache|validator|validation)\b", source_text):
        findings.append({"check": "source_refresh_contract", "message": "source refresh section contains process/audit/debug prose"})

    for section in NEEDS_CONFIRMATION_ALLOWED_SECTIONS:
        for row in sections.get(section, []):
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
