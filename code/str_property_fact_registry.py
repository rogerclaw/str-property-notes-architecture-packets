"""Sanitized fact-slot and render model for STR Property Information notes."""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

try:  # Allow both direct packet imports and package-style imports.
    from property_note_semantic_quality import (
        PRIVATE_SECTIONS,
        evaluate_private_operations_note,
        evaluate_public_redaction_gate,
    )
except ImportError:  # pragma: no cover
    from .property_note_semantic_quality import (
        PRIVATE_SECTIONS,
        evaluate_private_operations_note,
        evaluate_public_redaction_gate,
    )

FACT_SLOT_STATES = {
    "resolved_verified",
    "private_value_present",
    "unresolved_conflict",
    "missing_after_full_sweep",
    "candidate_unconfirmed",
    "not_applicable",
}

PRIVATE_RENDERABLE_STATES = {"resolved_verified", "private_value_present", "not_applicable"}
NEEDS_CONFIRMATION_STATES = {"unresolved_conflict", "missing_after_full_sweep", "candidate_unconfirmed"}

PUBLIC_AUDIT_ALLOWED_TERMS = [
    "source coverage",
    "gate",
    "evidence",
    "review",
    "redacted",
    "candidate",
]


@dataclass
class FactSlot:
    slot_id: str
    section: str
    label: str
    state: str
    value_for_private_note: str = ""
    public_summary: str = ""
    role: str = ""
    subtype: str = ""
    private_ref: str = ""
    value_hash: str = ""
    required: bool = False
    target_section: str | None = None
    source_refs: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "FactSlot":
        return cls(
            slot_id=str(row.get("slot_id") or row.get("fact_key") or row.get("label") or ""),
            section=str(row.get("section") or row.get("target_section") or ""),
            label=str(row.get("label") or row.get("fact_label") or ""),
            state=str(row.get("state") or row.get("value_state") or ""),
            value_for_private_note=str(row.get("value_for_private_note") or row.get("private_render") or ""),
            public_summary=str(row.get("public_summary") or row.get("fact_value_redacted") or ""),
            role=str(row.get("role") or row.get("contact_role") or ""),
            subtype=str(row.get("subtype") or row.get("access_subtype") or row.get("fact_subtype") or ""),
            private_ref=str(row.get("private_ref") or ""),
            value_hash=str(row.get("value_hash") or ""),
            required=bool(row.get("required")),
            target_section=row.get("target_section"),
            source_refs=list(row.get("source_refs") or []),
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_slots(fact_slots: list[dict[str, Any] | FactSlot]) -> list[FactSlot]:
    return [slot if isinstance(slot, FactSlot) else FactSlot.from_mapping(slot) for slot in fact_slots]


def _html_section(name: str, rows: list[str]) -> str:
    safe_name = html.escape(name, quote=False)
    if not rows:
        rows = ["No property-specific rows for this section."]
    return f"<h2>{safe_name}</h2>\n<ul>\n" + "\n".join(rows) + "\n</ul>\n"


def _private_row(slot: FactSlot) -> str:
    return f"<li><b>{html.escape(slot.label, quote=False)}:</b> {html.escape(slot.value_for_private_note, quote=False)}</li>"


def _needs_confirmation_row(slot: FactSlot) -> str:
    label = slot.label
    if slot.state == "candidate_unconfirmed" and "CANDIDATE" not in label:
        label = "CANDIDATE - " + label
    if slot.state == "missing_after_full_sweep" and "MISSING" not in label:
        label = "MISSING - " + label
    if slot.state == "unresolved_conflict" and "CONFLICT" not in label:
        label = "CONFLICT - " + label
    summary = slot.public_summary or slot.value_for_private_note or "Needs confirmation before rendering as an operational fact."
    return f"<li><b>{html.escape(label, quote=False)}:</b> {html.escape(summary, quote=False)}</li>"


def sample_fact_slots() -> list[dict[str, Any]]:
    """Return sample-only fact slots; values are synthetic and not live data."""
    return [
        {
            "slot_id": "access.guest_door_code",
            "section": "Access & Codes",
            "label": "Front door guest code",
            "state": "private_value_present",
            "value_for_private_note": "Door/keypad code uses SAMPLE_GUEST_ACCESS_VALUE.",
            "public_summary": "Guest entry code present in private note only.",
            "subtype": "guest_door_code",
            "private_ref": "private://sample/access/guest_door_code",
            "value_hash": "hash_guest_code",
            "required": True,
        },
        {
            "slot_id": "access.programming_admin_code",
            "section": "Access & Codes",
            "label": "Lock admin/programming code",
            "state": "private_value_present",
            "value_for_private_note": "Admin/programming code uses SAMPLE_ADMIN_ACCESS_VALUE.",
            "public_summary": "Admin/programming code present and distinct from guest code.",
            "subtype": "programming_admin_code",
            "private_ref": "private://sample/access/programming_admin_code",
            "value_hash": "hash_admin_code",
            "required": True,
        },
        {
            "slot_id": "wifi.network",
            "section": "Wi-Fi / Systems",
            "label": "Wi-Fi network",
            "state": "resolved_verified",
            "value_for_private_note": "Network: SAMPLE-NETWORK.",
            "public_summary": "Wi-Fi network label verified.",
            "subtype": "wifi_network",
            "required": True,
        },
        {
            "slot_id": "wifi.password",
            "section": "Wi-Fi / Systems",
            "label": "Wi-Fi password",
            "state": "private_value_present",
            "value_for_private_note": "Password uses SAMPLE_WIFI_SECRET.",
            "public_summary": "Wi-Fi password present in private note only.",
            "subtype": "wifi_password",
            "private_ref": "private://sample/wifi/password",
            "value_hash": "hash_wifi_password",
            "required": True,
        },
        {
            "slot_id": "contact.owner.primary",
            "section": "Contacts",
            "label": "Owner - Owner A",
            "state": "resolved_verified",
            "value_for_private_note": "SAMPLE_OWNER_CONTACT.",
            "public_summary": "Owner A contact verified.",
            "role": "owner",
            "subtype": "primary",
            "value_hash": "hash_owner_a",
            "required": True,
        },
        {
            "slot_id": "contact.cleaner.primary",
            "section": "Contacts",
            "label": "Cleaner / turnover - Cleaner A",
            "state": "resolved_verified",
            "value_for_private_note": "SAMPLE_CLEANER_CONTACT.",
            "public_summary": "Cleaner A is the cleaner/turnover contact, not an owner.",
            "role": "cleaner",
            "subtype": "primary",
            "value_hash": "hash_cleaner_a",
            "required": True,
        },
        {
            "slot_id": "contact.vendor.design_candidate",
            "section": "Other Property Contacts",
            "target_section": "Needs Confirmation",
            "label": "CANDIDATE - design/vendor contact",
            "state": "candidate_unconfirmed",
            "value_for_private_note": "",
            "public_summary": "CANDIDATE contact has property-specific source context but is not promoted.",
            "role": "vendor",
            "subtype": "design_vendor_contact",
        },
        {
            "slot_id": "field.address",
            "section": "Field Basics",
            "label": "Address",
            "state": "resolved_verified",
            "value_for_private_note": "123 Example St, Sample City.",
            "public_summary": "Sample address used for public packet.",
            "subtype": "address",
            "required": True,
        },
        {
            "slot_id": "field.parking",
            "section": "Field Basics",
            "label": "Parking",
            "state": "resolved_verified",
            "value_for_private_note": "Driveway/curb plan is in the field note.",
            "public_summary": "Parking instructions verified.",
            "subtype": "parking",
            "required": True,
        },
        {
            "slot_id": "field.trash",
            "section": "Field Basics",
            "label": "Trash",
            "state": "resolved_verified",
            "value_for_private_note": "Trash cans are on the right side facing the house; normal pickup Tuesday.",
            "public_summary": "Trash location/pickup verified.",
            "subtype": "trash",
            "required": True,
        },
    ]


def evaluate_fact_slot_resolution(fact_slots: list[dict[str, Any] | FactSlot]) -> dict[str, Any]:
    slots = normalize_slots(fact_slots)
    findings: list[dict[str, str]] = []

    for slot in slots:
        if slot.state not in FACT_SLOT_STATES:
            findings.append({"check": "fact_slot_state", "message": f"{slot.slot_id} has invalid state {slot.state}"})
        if slot.state == "private_value_present" and not slot.private_ref:
            findings.append({"check": "private_ref", "message": f"{slot.slot_id} private value lacks private_ref"})
        if slot.state in NEEDS_CONFIRMATION_STATES and (slot.target_section or slot.section) != "Needs Confirmation":
            findings.append({"check": "needs_confirmation_placement", "message": f"{slot.slot_id} must render only in Needs Confirmation"})
        if slot.state == "candidate_unconfirmed" and "CANDIDATE" not in slot.label:
            findings.append({"check": "candidate_contact_label", "message": f"{slot.slot_id} candidate lacks CANDIDATE label"})

    owner_email_slots = [
        slot for slot in slots
        if slot.role == "owner" and slot.subtype in {"email", "primary"} and slot.state in {"resolved_verified", "private_value_present"}
    ]
    owner_hashes = {slot.value_hash or slot.value_for_private_note for slot in owner_email_slots if slot.value_hash or slot.value_for_private_note}
    if len(owner_email_slots) > 1 and len(owner_hashes) > 1 and not any(slot.state == "unresolved_conflict" for slot in slots):
        findings.append({"check": "owner_conflict", "message": "conflicting owner contact values must be unresolved_conflict until reviewed"})

    for slot in slots:
        if slot.required and slot.subtype == "phone" and slot.state == "missing_after_full_sweep":
            if (slot.target_section or slot.section) != "Needs Confirmation":
                findings.append({"check": "missing_phone", "message": f"{slot.slot_id} missing phone must stay in Needs Confirmation"})

    guest_codes = [slot for slot in slots if slot.subtype == "guest_door_code" and slot.state == "private_value_present"]
    admin_codes = [slot for slot in slots if slot.subtype == "programming_admin_code" and slot.state == "private_value_present"]
    for guest in guest_codes:
        for admin in admin_codes:
            if (guest.value_hash and guest.value_hash == admin.value_hash) or (guest.private_ref and guest.private_ref == admin.private_ref):
                findings.append({"check": "access_code_separation", "message": "admin/programming code must be distinct from guest/front-door code"})

    owners = {slot.value_hash or slot.value_for_private_note for slot in slots if slot.role == "owner" and slot.state in PRIVATE_RENDERABLE_STATES}
    cleaners = {slot.value_hash or slot.value_for_private_note for slot in slots if slot.role in {"cleaner", "turnover_manager"} and slot.state in PRIVATE_RENDERABLE_STATES}
    if owners & cleaners:
        findings.append({"check": "cleaner_owner_separation", "message": "cleaner/turnover contact is also rendered as owner"})

    return {"ok": not findings, "fact_slot_states": sorted(FACT_SLOT_STATES), "findings": findings}


def build_private_operations_note(property_id: str, fact_slots: list[dict[str, Any] | FactSlot] | None = None, *, title: str = "Sample Property Dossier") -> str:
    slots = normalize_slots(fact_slots or sample_fact_slots())
    rows_by_section: dict[str, list[str]] = {section: [] for section in PRIVATE_SECTIONS}
    for slot in slots:
        if slot.state in PRIVATE_RENDERABLE_STATES:
            if slot.section in rows_by_section:
                rows_by_section[slot.section].append(_private_row(slot))
        elif slot.state in NEEDS_CONFIRMATION_STATES:
            rows_by_section["Needs Confirmation"].append(_needs_confirmation_row(slot))

    rows_by_section["Current / Upcoming Stays"].extend(
        [
            "<li><b>Current:</b> No current in-house accepted stay in the sample packet.</li>",
            "<li><b>Next 1:</b> Next accepted stay is held in the reservation system; refresh before guest-specific action.</li>",
        ]
    )
    rows_by_section["Operations Notes"].extend(
        [
            "<li><b>Access:</b> Confirm the guest code works before a same-day arrival or dispatch.</li>",
            "<li><b>Turnover:</b> Cleaner role is separate from owner escalation; confirm property name on multi-property threads.</li>",
        ]
    )
    rows_by_section["Business Snapshot"].extend(
        [
            "<li><b>YTD bookings:</b> Sample packet keeps booking/night/revenue context here without raw guest data.</li>",
            "<li><b>Trailing context:</b> Review rating and revenue should be refreshed from reservation tooling before owner reporting.</li>",
        ]
    )
    rows_by_section["Refresh / Source Coverage"].append(
        "<li><b>Refresh:</b> Refreshed from current note, locked property records, owner/message sources, reservations, manual/docs, and maintenance artifacts.</li>"
    )

    body = f"<h1>{html.escape(title, quote=False)}</h1>\n"
    for section in PRIVATE_SECTIONS:
        body += _html_section(section, rows_by_section.get(section) or [])
    gate = evaluate_private_operations_note(body, property_id=property_id)
    if not gate["ok"]:
        raise ValueError("private operations note failed semantic gate: " + json.dumps(gate["findings"], ensure_ascii=False))
    return body


def build_public_audit_artifact(property_id: str, fact_slots: list[dict[str, Any] | FactSlot] | None = None, *, title: str = "Sample Property Dossier") -> str:
    slots = normalize_slots(fact_slots or sample_fact_slots())
    gate = evaluate_fact_slot_resolution(slots)
    lines = [
        f"# Public Audit Artifact - {title}",
        "",
        "This public artifact may discuss source coverage, gates, conflicts, and review state, but it must not include raw private values.",
        "",
        "## Gate Summary",
        f"- Fact-slot state gate: {'PASS' if gate['ok'] else 'FAIL_BLOCKS_PUBLISH'}",
        "- Public redaction gate: evaluated before closeout or GitHub publication",
        "",
        "## Source Coverage",
        "- current_apple_note: searched",
        "- private_backend: searched, raw values withheld",
        "- owner_cleaner_guest_contractor_messages: searched, source bodies withheld",
        "",
        "## Fact Slots",
    ]
    for slot in slots:
        summary = slot.public_summary or "No public summary."
        public_slot_id = slot.slot_id.replace("password", "credential").replace("code", "access_value")
        lines.append(f"- {public_slot_id}: state={slot.state}; {summary}")
    artifact = "\n".join(lines) + "\n"
    redaction = evaluate_public_redaction_gate(artifact, property_id=property_id)
    if not redaction["ok"]:
        raise ValueError("public audit artifact failed redaction gate: " + json.dumps(redaction["findings"], ensure_ascii=False))
    return artifact


def render_canonical_note(property_id: str, *, body_mode: str = "locked_apple_note_body") -> str:
    if body_mode == "locked_apple_note_body":
        return build_private_operations_note(property_id)
    if body_mode == "redacted_review_body":
        return build_public_audit_artifact(property_id)
    raise ValueError(f"unsupported body_mode: {body_mode}")


def evaluate_gates(property_id: str, *, mode: str = "dry_run", proposed_body: str | None = None, review_packet: Any | None = None) -> dict[str, Any]:
    slots = sample_fact_slots()
    fact_result = evaluate_fact_slot_resolution(slots)
    private_body = proposed_body or build_private_operations_note(property_id, slots)
    private_gate = evaluate_private_operations_note(private_body, property_id=property_id, mode=mode)
    public_artifact = build_public_audit_artifact(property_id, slots)
    public_gate = evaluate_public_redaction_gate(public_artifact, property_id=property_id)
    gates = [
        {"gate_name": "required_fact_gate", "result": "PASS" if fact_result["ok"] else "FAIL_BLOCKS_PUBLISH", "blocking": not fact_result["ok"], "messages": [f["message"] for f in fact_result["findings"]]},
        {"gate_name": "private_operations_note_gate", "result": "PASS" if private_gate["ok"] else "FAIL_BLOCKS_PUBLISH", "blocking": not private_gate["ok"], "messages": [f["message"] for f in private_gate["findings"]]},
        {"gate_name": "public_redaction_gate", "result": "PASS" if public_gate["ok"] else "FAIL_BLOCKS_PUBLISH", "blocking": not public_gate["ok"], "messages": [f["message"] for f in public_gate["findings"]]},
    ]
    ok = all(not gate["blocking"] for gate in gates)
    return {
        "gate_run_id": f"gate_{property_id}_{now_iso()}",
        "property_id": property_id,
        "mode": mode,
        "overall_result": "PASS" if ok else "FAIL_BLOCKS_PUBLISH",
        "gates": gates,
        "created_at": now_iso(),
        "review_packet": str(review_packet) if review_packet else None,
    }
