#!/usr/bin/env python3
"""Fresh-replace one STR Property Information note to avoid Notes append drift."""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import restructure_property_information_notes as notes  # noqa: E402
from scripts.lib import property_note_semantic_quality as semantic_quality  # noqa: E402
from scripts.lib import str_property_fact_registry as fact_registry  # noqa: E402

ARCHIVE_FOLDER = "STR Property Information Review"
PRIVATE_BACKUP_DIR = ROOT / "data" / "str_property_backend" / "private" / "property_info_note_backups"
REPORT_DIR = ROOT / "ops" / "progress"
PUBLISH_AUTHORIZATIONS = ROOT / "data" / "str_property_backend" / "fact_registry" / "property_publish_authorizations.json"
AUTONOMOUS_CLOSURE_PACKETS = {
    "sample_property": ROOT / "ops" / "progress" / "sample_property_autonomous_source_closure_v3_20260702.md",
}
FORBIDDEN_VISIBLE_MARKERS = (
    "Title / listing / tags",
    "Quick access / contacts / codes",
    "At a glance",
    "Action alerts",
    "Current / next stay",
    "Access and security",
    "Guest-facing basics",
    "Systems and how-tos",
    "Maintenance and issue summary",
    "Property Issues summary",
    "Cleaning and turnover",
    "Supplies and inventory",
    "Financial snapshot",
    "Accounts and utilities",
    "Open questions",
    "Change log",
    "Backyard and front gates still locked",
    "Failed last week",
    "Saturday finishing list",
    "Raoul has last repairs",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def stamp_from_iso(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.now(timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def compact_visible(body: str) -> str:
    plain = notes.visible_text(body)
    plain = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[REDACTED_EMAIL]", plain, flags=re.I)
    plain = re.sub(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]", plain)
    plain = re.sub(r"(?i)(Wi[\s-]?Fi password:\s*)(?:password:\s*)?[^.]+", r"\1[REDACTED_WIFI_PASSWORD]", plain)
    plain = re.sub(r"(?i)(password:\s*)[^.;\s]+", r"\1[REDACTED_PASSWORD]", plain)
    plain = re.sub(
        r"(?i)(front door keypad:\s*)(door/keypad code|door code|access code|keypad code):\s*[^.]+",
        r"\1\2: [REDACTED_ACCESS_CODE]",
        plain,
    )
    plain = re.sub(
        r"(?i)(front door keypad:)(?!\s*(?:door/keypad code|door code|access code|keypad code):)\s*[^.]+",
        r"\1 [REDACTED_ACCESS_CODE]",
        plain,
    )
    plain = re.sub(r"(?i)(door/keypad code:\s*)[^.;\s]+", r"\1[REDACTED_ACCESS_CODE]", plain)
    plain = re.sub(r"(?i)(door code:\s*)[^.;\s]+", r"\1[REDACTED_ACCESS_CODE]", plain)
    plain = re.sub(r"(?i)(access code:\s*)[^.;\s]+", r"\1[REDACTED_ACCESS_CODE]", plain)
    plain = re.sub(r"(?i)(keypad code:\s*)[^.;\s]+", r"\1[REDACTED_ACCESS_CODE]", plain)
    return plain


def forbidden_marker_findings(body: str) -> list[str]:
    plain = compact_visible(body)
    return [marker for marker in FORBIDDEN_VISIBLE_MARKERS if re.search(re.escape(marker), plain, re.I)]


def jxa_json(source: str, timeout: int = 180) -> Any:
    raw = notes.run_jxa(source, timeout=timeout)
    return json.loads(raw or "{}")


def active_property_notes(property_title: str, property_marker: str) -> list[dict[str, Any]]:
    source = f"""
const app = Application('Notes');
const folder = app.accounts.byName('iCloud').folders.byName({json.dumps(notes.PROPERTY_FOLDER)});
const rows = [];
for (const note of folder.notes()) {{
  let title = '', id = '', body = '';
  try {{ title = note.name(); }} catch (e) {{}}
  if (title === {json.dumps(property_title)} || title.includes({json.dumps(property_marker)})) {{
    try {{ id = note.id(); }} catch (e) {{}}
    try {{ body = note.body(); }} catch (e) {{}}
    rows.push({{title, id, body, body_chars: body.length}});
  }}
}}
JSON.stringify(rows);
"""
    return jxa_json(source)


def backup_note(property_id: str, old_note: dict[str, Any], new_body: str) -> Path:
    PRIVATE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = PRIVATE_BACKUP_DIR / f"{property_id}_fresh_replace_{stamp()}.json"
    path.write_text(
        json.dumps(
            {
                "created_at": now_iso(),
                "property_id": property_id,
                "old_note": old_note,
                "replacement_body": new_body,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    os.chmod(path, 0o600)
    return path


def fresh_replace(title: str, old_note_id: str, old_body: str, new_body: str) -> dict[str, Any]:
    archive_title = f"ARCHIVED {stamp()} - {title}"
    source = f"""
const app = Application('Notes');
const account = app.accounts.byName('iCloud');
const activeFolder = account.folders.byName({json.dumps(notes.PROPERTY_FOLDER)});
const archiveFolder = account.folders.byName({json.dumps(ARCHIVE_FOLDER)});
let oldNote = null;
for (const note of activeFolder.notes()) {{
  let id = '';
  try {{ id = note.id(); }} catch (e) {{}}
  if (id === {json.dumps(old_note_id)}) {{
    oldNote = note;
    break;
  }}
}}
if (!oldNote) throw new Error('old active note not found');
const archiveBody = '<h1>' + {json.dumps(archive_title)} + '</h1>\\n' + {json.dumps(old_body)};
const archiveNote = app.Note({{name: {json.dumps(archive_title)}, body: archiveBody}});
archiveFolder.notes.push(archiveNote);
delay(1);
const newNote = app.Note({{body: {json.dumps(new_body)}}});
activeFolder.notes.push(newNote);
delay(2);
let newId = '', archiveId = '';
try {{ newId = newNote.id(); }} catch (e) {{}}
try {{ archiveId = archiveNote.id(); }} catch (e) {{}}
if (!newId) throw new Error('replacement note was not created; old active note was left in place');
oldNote.delete();
delay(1);
JSON.stringify({{archive_title: {json.dumps(archive_title)}, archive_id: archiveId, new_id: newId}});
"""
    return jxa_json(source, timeout=240)


def replace_links_section(body: str, links: list[dict[str, Any]]) -> str:
    link_section = notes.section("Links", notes.link_rows(links))
    patterns = [
        re.compile(r"(?is)(<h2[^>]*>\s*Links\s*</h2>\s*)<ul>.*?</ul>"),
        re.compile(
            r"(?is)(<div><b><span style=\"font-size:\s*18px\">\s*Links\s*</span></b>(?:<br>)?</div>\s*)<ul>.*?</ul>"
        ),
    ]
    for pattern in patterns:
        if pattern.search(body):
            return pattern.sub(link_section.strip(), body, count=1)
    return body + "\n" + link_section


def normalize_title_and_evidence_spacing(body: str, expected_title: str) -> str:
    escaped_title = html.escape(expected_title, quote=False)
    patterns = [
        re.compile(r"(?is)<h1[^>]*>.*?</h1>"),
        re.compile(r"(?is)<div><b><span style=\"font-size:\s*24px\">.*?</span></b>(?:<br>)?</div>"),
    ]
    normalized = body
    for pattern in patterns:
        if pattern.search(normalized):
            normalized = pattern.sub(f"<h1>{escaped_title}</h1>", normalized, count=1)
            break
    else:
        normalized = f"<h1>{escaped_title}</h1>\n" + normalized

    evidence_heading = re.compile(
        r"(?is)(?:<br>\s*)?(<h2[^>]*>\s*Evidence\s*/\s*Refresh\s*Notes\s*</h2>|"
        r"<div><b><span style=\"font-size:\s*18px\">\s*Evidence\s*/\s*Refresh\s*Notes\s*</span></b>(?:<br>)?</div>)"
    )
    return evidence_heading.sub(r"<br>\n\1", normalized, count=1)


def write_report(property_id: str, payload: dict[str, Any]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    mode = "execute" if payload.get("execute") else "dry_run"
    safe_property_id = notes.safe_report_property_id(property_id)
    run_stamp = stamp_from_iso(str(payload.get("created_at") or now_iso()))
    path = REPORT_DIR / f"{safe_property_id}_fresh_replace_property_info_{mode}_{run_stamp}.json"
    if REPORT_DIR.resolve() not in (path.resolve(), *path.resolve().parents):
        raise ValueError(f"report path escaped report directory: {path}")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(path, 0o600)
    return path


def has_explicit_property_publish_authority(property_id: str) -> bool:
    if not PUBLISH_AUTHORIZATIONS.exists():
        return False
    try:
        payload = json.loads(PUBLISH_AUTHORIZATIONS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    auth = (payload.get("properties") or {}).get(property_id) or {}
    return bool(auth.get("fresh_replace_publish_authorized") and auth.get("scope") == "single_property")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--property-id", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approved-by-charles", action="store_true")
    parser.add_argument(
        "--preserve-body-fix-links",
        action="store_true",
        help="Preserve the current body and replace only the Links block with functional visible URLs.",
    )
    args = parser.parse_args(argv)

    if args.execute and not args.approved_by_charles:
        print(json.dumps({"ok": False, "error": "missing_human_publish_approval"}, indent=2))
        return 2
    if args.execute:
        if not has_explicit_property_publish_authority(args.property_id):
            payload = {
                "ok": False,
                "created_at": now_iso(),
                "property_id": args.property_id,
                "execute": True,
                "error": "missing_explicit_single_property_publish_authority",
                "gate_overall_result": "REFUSED_BEFORE_APPLE_NOTES_MUTATION",
                "external_actions": {
                    "apple_notes_mutated_or_published": False,
                    "emails_sent": False,
                    "messages_sent": False,
                    "booking_refund_spend_dispatch_changed": False,
                    "reminders_changed": False,
                    "calendar_changed": False,
                },
            }
            report_path = write_report(args.property_id, payload)
            print(json.dumps({"report_path": str(report_path.relative_to(ROOT)), **payload}, indent=2, ensure_ascii=False))
            return 2
        gate_result = fact_registry.evaluate_gates(
            args.property_id,
            mode="pre_publish",
            review_packet=AUTONOMOUS_CLOSURE_PACKETS.get(args.property_id),
        )
        hard_failures = [
            gate
            for gate in gate_result.get("gates", [])
            if gate.get("blocking") and gate.get("result") == fact_registry.GATE_FAIL
        ]
        if hard_failures:
            payload = {
                "ok": False,
                "created_at": now_iso(),
                "property_id": args.property_id,
                "execute": True,
                "error": "canonical_fact_publish_gates_failed",
                "gate_overall_result": gate_result.get("overall_result"),
                "blocking_gates": [
                    {
                        "gate_name": gate.get("gate_name"),
                        "messages": gate.get("messages") or [],
                    }
                    for gate in hard_failures
                ],
                "external_actions": {
                    "apple_notes_mutated_or_published": False,
                    "emails_sent": False,
                    "messages_sent": False,
                    "booking_refund_spend_dispatch_changed": False,
                    "reminders_changed": False,
                    "calendar_changed": False,
                },
            }
            report_path = write_report(args.property_id, payload)
            print(json.dumps({"report_path": str(report_path.relative_to(ROOT)), **payload}, indent=2, ensure_ascii=False))
            return 2

    entry = notes.load_entry(args.property_id)
    title = notes.property_display_title(entry)
    display_name = ((entry.get("typed_private_fields") or {}).get("identity") or {}).get("display_name") or title.split(" - ")[0]
    live_notes = notes.list_notes()
    old_note = notes.find_live_note(entry, live_notes)
    if args.preserve_body_fix_links:
        new_body = replace_links_section(old_note.get("body") or "", (entry.get("typed_private_fields") or {}).get("links") or [])
        new_body = normalize_title_and_evidence_spacing(new_body, title)
        build_meta = {"mode": "preserve_body_fix_links", "link_count": len((entry.get("typed_private_fields") or {}).get("links") or [])}
    elif args.property_id == "sample_property":
        new_body, build_meta = notes.build_body_from_canonical(args.property_id, body_mode="locked_apple_note_body")
    else:
        new_body, build_meta = notes.build_body(entry, old_note.get("body") or "")
    proposed_review = notes.review_body(args.property_id, title, new_body)
    if not proposed_review.get("ok"):
        payload = {
            "ok": False,
            "created_at": now_iso(),
            "property_id": args.property_id,
            "execute": args.execute,
            "error": "proposed_body_failed_review",
            "proposed_review": proposed_review,
            "build_meta": build_meta,
        }
        report_path = write_report(args.property_id, payload)
        print(json.dumps({"report_path": str(report_path.relative_to(ROOT)), **payload}, indent=2, ensure_ascii=False))
        return 1

    backup_path = backup_note(args.property_id, old_note, new_body) if args.execute else None
    replacement = fresh_replace(title, old_note["id"], old_note.get("body") or "", new_body) if args.execute else None
    after_notes = active_property_notes(title, str(display_name)) if args.execute else [{"title": title, "id": old_note.get("id"), "body": new_body, "body_chars": len(new_body)}]
    active_matches = [note for note in after_notes if note.get("title") == title]
    after_body = active_matches[0].get("body") if len(active_matches) == 1 else ""
    after_review = notes.review_body(args.property_id, title, after_body or "")
    expected_semantic = semantic_quality.evaluate_body(new_body, mode="expected", property_id=args.property_id)
    readback_semantic = semantic_quality.evaluate_body(after_body or "", mode="live_readback", property_id=args.property_id)
    expected_visible = notes.visible_text(new_body)
    readback_visible = notes.visible_text(after_body or "")
    material_readback_match = expected_visible == readback_visible
    forbidden = forbidden_marker_findings(after_body or "")
    old_id_still_active = any(note.get("id") == old_note.get("id") for note in after_notes)
    ok = (
        proposed_review.get("ok")
        and after_review.get("ok")
        and len(active_matches) == 1
        and not forbidden
        and expected_semantic.get("ok")
        and readback_semantic.get("ok")
        and (not args.execute or material_readback_match)
        and (not args.execute or not old_id_still_active)
        and (not args.execute or bool(replacement and replacement.get("new_id")))
    )
    payload = {
        "ok": ok,
        "created_at": now_iso(),
        "property_id": args.property_id,
        "execute": args.execute,
        "folder": notes.PROPERTY_FOLDER,
        "archive_folder": ARCHIVE_FOLDER,
        "title": title,
        "old_note_id": old_note.get("id"),
        "backup_path": str(backup_path.relative_to(ROOT)) if backup_path else None,
        "replacement": replacement,
        "active_property_notes": [
            {k: note.get(k) for k in ("title", "id", "body_chars")} for note in after_notes
        ],
        "old_id_still_active": old_id_still_active,
        "build_meta": build_meta,
        "proposed_review": proposed_review,
        "after_review": after_review,
        "expected_semantic_gate": {
            "ok": expected_semantic.get("ok"),
            "plain_chars": expected_semantic.get("plain_chars"),
            "findings": expected_semantic.get("findings") or [],
        },
        "device_visible_semantic_gate": {
            "ok": readback_semantic.get("ok"),
            "plain_chars": readback_semantic.get("plain_chars"),
            "findings": readback_semantic.get("findings") or [],
        },
        "readback_material_match": material_readback_match,
        "forbidden_visible_markers": forbidden,
        "after_plain_preview": compact_visible(after_body or "")[:1200],
        "human_gate": {
            "approved_by_charles": bool(args.approved_by_charles),
            "scope": "one_property_only",
            "next_property_requires_new_approval": True,
        },
        "external_actions": {
            "messages_sent": False,
            "reminders_changed": False,
            "calendar_changed": False,
            "bookings_refunds_spend_dispatch_changed": False,
        },
    }
    report_path = write_report(args.property_id, payload)
    print(json.dumps({"report_path": str(report_path.relative_to(ROOT)), **payload}, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
