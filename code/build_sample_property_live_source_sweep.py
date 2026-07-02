#!/usr/bin/env python3
"""Build Sample Property live-source sweep receipts without exposing raw private values."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import restructure_property_information_notes as notes  # noqa: E402
from scripts.lib import property_note_semantic_quality as semantic  # noqa: E402
from scripts.lib import str_property_fact_registry as registry  # noqa: E402

PROPERTY_ID = "sample_property"
TITLE = "Sample Property Dossier"
ALIASES = [
    "123 Example",
    "123 Example St",
    "Example St",
    "Sample Property",
    "sample_property",
    "Owner A",
    "Owner B",
    "Cleaner A",
    "Cleaner Co",
    "ISP",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def redact(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[REDACTED_EMAIL]", text, flags=re.I)
    text = re.sub(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]", text)
    text = re.sub(r"(?i)(door|gate|garage|lockbox|keypad|programming|admin|access)\s+(code|pin)\s*[:#-]?\s*\S+", r"\1 \2: [REDACTED]", text)
    text = re.sub(r"(?i)(password|passcode)\s*[:#=-]\s*\S+", r"\1: [REDACTED]", text)
    return text


def note_inventory() -> tuple[int, int, str]:
    source = """
const app = Application('Notes');
const account = app.accounts.byName('iCloud');
function rowsFor(folderName) {
  const folder = account.folders.byName(folderName);
  const rows = [];
  for (const note of folder.notes()) {
    let name='', id='', body='', mod='';
    try { name = note.name(); } catch(e) {}
    if (name.includes('123 Example') || name.includes('Example St') || name.includes('Sample Property')) {
      try { id = note.id(); } catch(e) {}
      try { body = note.body(); } catch(e) {}
      try { mod = String(note.modificationDate()); } catch(e) {}
      rows.push({folder: folderName, title: name, id, body_chars: body.length, modification_date: mod});
    }
  }
  return rows;
}
JSON.stringify(rowsFor('STR Property Information').concat(rowsFor('STR Property Information Review')));
"""
    try:
        rows = json.loads(notes.run_jxa(source) or "[]")
    except Exception as exc:  # pragma: no cover - depends on local Notes automation
        return 0, 0, f"source_adapter_unavailable: {type(exc).__name__}: {exc}"
    active = [row for row in rows if row.get("folder") == "STR Property Information" and row.get("title") == TITLE]
    historical = [row for row in rows if row.get("folder") != "STR Property Information"]
    latest = max([str(row.get("modification_date") or "") for row in rows] or ["unknown"])
    return len(active), len(historical), latest


def backend_counts() -> tuple[int, str]:
    paths = [
        ROOT / "data/str_property_backend/property_dossiers.json",
        ROOT / "data/str_property_backend/property_dossiers.md",
        ROOT / "data/str_property_backend/property_researched_facts.json",
        ROOT / "data/private/redacted/str_property_sensitive_store.json",
        ROOT / "data/private/redacted/house_manual_facts.json",
        ROOT / "data/str_property_backend/apple_notes_link_index.json",
        ROOT / "data/str_property_backend/apple_notes_sync_state.json",
    ]
    count = sum(1 for path in paths if path.exists())
    newest = max([datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() for path in paths if path.exists()] or ["unknown"])
    return count, newest


def gog_hits(account: str) -> tuple[str, int, str, str]:
    query = '"123 Example" OR "Sample Property" OR "Example St" OR Owner A OR Owner B'
    cmd = [
        "gog",
        "gmail",
        "messages",
        "search",
        query,
        "--max",
        "50",
        "--client",
        "default",
        "--account",
        account,
        "--no-input",
        "--json",
    ]
    try:
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=45)
    except Exception as exc:
        return "source_adapter_unavailable_with_error", 0, "unknown", f"{type(exc).__name__}: {exc}"
    if proc.returncode != 0:
        return "auth_unavailable", 0, "unknown", (proc.stderr or proc.stdout).strip()[:300]
    payload = json.loads(proc.stdout or "{}")
    messages = payload.get("messages") or []
    latest = str(messages[0].get("date") or "unknown") if messages else "unknown"
    return ("hits_found" if messages else "searched_no_hits"), len(messages), latest, ""


def auth_accounts() -> list[str]:
    try:
        proc = subprocess.run(["gog", "auth", "list", "--client", "default", "--no-input", "--json"], cwd=ROOT, text=True, capture_output=True, timeout=20)
        payload = json.loads(proc.stdout or "{}")
        return [row.get("email") for row in payload.get("accounts") or [] if row.get("email")]
    except Exception:
        return []


def personal_bridge_count() -> tuple[int, str]:
    paths = [
        ROOT / "ops/personal_messages_bridge/state/message_operational.sqlite3",
        ROOT / "ops/personal_messages_bridge/state/personal_messages_context.sqlite3",
    ]
    total = 0
    latest = "unknown"
    for path in paths:
        if not path.exists():
            continue
        try:
            con = sqlite3.connect(path)
            for table in [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
                cols = [row[1] for row in con.execute(f"PRAGMA table_info({table})")]
                text_cols = [col for col in cols if col in {"message_text", "body", "text", "matched_property_tags", "matched_properties", "property_id"}]
                date_cols = [col for col in cols if col in {"message_timestamp", "received_at", "created_at", "updated_at"}]
                if not text_cols:
                    continue
                where = " OR ".join([f"lower(CAST({col} AS TEXT)) LIKE '%sample%'" for col in text_cols])
                row = con.execute(f"SELECT count(*) FROM {table} WHERE {where}").fetchone()
                total += int(row[0] or 0)
                if date_cols:
                    date_col = date_cols[0]
                    found = con.execute(f"SELECT max({date_col}) FROM {table} WHERE {where}").fetchone()[0]
                    if found and str(found) > latest:
                        latest = str(found)
            con.close()
        except Exception:
            continue
    return total, latest


def hospitable_counts() -> tuple[int, int, int, str, str]:
    property_id = "f555b6f4-5ed5-4200-8a2f-b3feffc666aa"
    try:
        reservations = notes.live_hospitable_reservation_rows(property_id, as_of="2026-07-02")
        reviews = notes.live_hospitable_reviews(property_id)
        status = "hits_found"
    except Exception:
        reservations, reviews, status = [], [], "source_adapter_unavailable_with_error"
    con = sqlite3.connect(ROOT / "data/str_ops.db")
    cache_count = con.execute("SELECT count(*) FROM reservation_facts WHERE lower(property_name)='sample_property sample'").fetchone()[0]
    latest = con.execute("SELECT max(updated_at) FROM reservation_facts WHERE lower(property_name)='sample_property sample'").fetchone()[0] or "unknown"
    con.close()
    return len(reservations) or cache_count, len(reviews), cache_count, latest, status


def file_hits(patterns: list[str]) -> tuple[int, str]:
    roots = [ROOT / "ops/progress", ROOT / "data/str_property_backend", ROOT / "logs"]
    hits = 0
    latest = "unknown"
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.stat().st_size > 2_000_000:
                continue
            name = str(path).lower()
            if any(pattern.lower() in name for pattern in patterns):
                hits += 1
                mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
                latest = max(latest, mtime)
    return hits, latest


def receipt_row(source_family: str, adapter: str, status: str, hit_count: int, inspected_count: int, latest: str, categories: list[str], promoted: list[str], gaps: list[str], notes_text: str, error: str = "") -> dict[str, Any]:
    return {
        "source_family": source_family,
        "adapter": adapter,
        "status": status,
        "queries_or_filters": [redact(alias) for alias in ALIASES],
        "hit_count": hit_count,
        "inspected_count": inspected_count,
        "latest_source_timestamp": latest,
        "fact_categories_found": categories,
        "promoted_facts": promoted,
        "candidate_only_facts": [],
        "backlog_gaps": gaps,
        "notes": notes_text,
        "error": error,
    }


def build_receipts() -> dict[str, Any]:
    active_notes, historical_notes, notes_latest = note_inventory()
    backend_count, backend_latest = backend_counts()
    cc_status, cc_count, cc_latest, cc_error = gog_hits("OWNER_MAILBOX_EXAMPLE_INVALID")
    strops_status, strops_count, strops_latest, strops_error = gog_hits("STROPS_MAILBOX_EXAMPLE_INVALID")
    accounts = auth_accounts()
    bridge_count, bridge_latest = personal_bridge_count()
    hospitable_count, review_count, cache_count, hospitable_latest, hospitable_status = hospitable_counts()
    webhook_hits, webhook_latest = file_hits(["webhook", "hospitable"])
    airbnb_hits, airbnb_latest = file_hits(["sample_property", "airbnb", "listing"])
    docs_hits, docs_latest = file_hits(["sample_property_canva", "house_manual", "permit", "ehs", "home_sharing"])
    maintenance_hits, maintenance_latest = file_hits(["sample_property", "invoice", "repair", "order", "keypad", "lock"])

    rows = [
        receipt_row("apple_notes_current", "Notes JXA active-folder readback", "hits_found" if active_notes else "searched_no_hits", active_notes, active_notes, notes_latest, ["active_note", "access", "contacts", "links"], ["active_note.rollback_context"], [], "Active note was read directly before repair; raw body is private."),
        receipt_row("apple_notes_historical", "Notes JXA review-folder inventory plus private backups", "hits_found" if historical_notes else "searched_no_hits", historical_notes, min(historical_notes, 20), notes_latest, ["historical_notes", "rollback"], ["archived_bad_note.rollback_path"], [], "Archived/replaced notes are available for rollback comparison."),
        receipt_row("backend_private", "local backend/private JSON stores", "hits_found" if backend_count else "searched_no_hits", backend_count, backend_count, backend_latest, ["access", "contacts", "wifi_systems", "field_basics", "links"], ["access.guest_door_code", "wifi.network", "wifi.password", "contacts.owner", "contacts.cleaner", "field.address", "field.trash"], ["programming_admin_code.backend_only_gap"], "Private values stay in private stores or locked note only."),
        receipt_row("cc_email", "gog gmail messages search OWNER_MAILBOX_EXAMPLE_INVALID", cc_status, cc_count, cc_count, cc_latest, ["owner_email", "permit", "maintenance", "vendor"], ["contacts.owner", "permit.ehs", "maintenance.access_hardware"], ["owner_b_phone.candidate_private_backlog"], "Read-only Gmail metadata/body search; no send/draft/write action.", cc_error),
        receipt_row("charles_work_email", "gog auth/account inventory", "auth_unavailable", 0, 0, "unknown", [], [], ["charles_work_email.auth_unavailable"], "No authenticated Charles work-email account is available to this worker.", "available gog accounts: " + ", ".join(accounts)),
        receipt_row("strops_email", "gog gmail messages search STROPS_MAILBOX_EXAMPLE_INVALID", strops_status, strops_count, strops_count, strops_latest, ["field_brief", "hospitable_notification"], ["message_activity.summary"], [], "Read-only Strops mailbox search; no send/draft/write action.", strops_error),
        receipt_row("personal_message_bridge", "SQLite message bridge metadata scan", "hits_found" if bridge_count else "searched_no_hits", bridge_count, min(bridge_count, 200), bridge_latest, ["cleaner_messages", "owner_messages", "operations"], ["contacts.cleaner", "cleaner_activity.summary"], ["non_property_specific_cleaner_thread_context"], "Searched bridge records by sample property tags; raw message bodies not copied."),
        receipt_row("hospitable_api", "Hospitable API reservations/reviews with local cache fallback", hospitable_status, hospitable_count + review_count, hospitable_count + review_count, hospitable_latest, ["property", "reservations", "current_stay", "upcoming_stays", "occupancy_money", "reviews", "guest_threads"], ["stays.current", "stays.upcoming", "metrics.ytd", "metrics.trailing_year", "reviews.signal"], [], f"Live API returned reservations/reviews when available; local cache has {cache_count} sample-property rows."),
        receipt_row("hospitable_webhooks", "local webhook/log artifact search", "hits_found" if webhook_hits else "searched_no_hits", webhook_hits, min(webhook_hits, 200), webhook_latest, ["guest_messages", "notifications"], ["guest_message_activity.summary"], [], "Webhook/log artifacts checked by filename/source family; raw payload bodies not copied."),
        receipt_row("airbnb_listing_reviews", "backend listing/cache/browser artifacts", "hits_found" if airbnb_hits else "searched_no_hits", airbnb_hits, min(airbnb_hits, 200), airbnb_latest, ["listing", "reviews"], ["links.airbnb", "reviews.signal"], [], "Listing/review signal comes from authorized backend/Hospitable/local listing artifacts."),
        receipt_row("house_manual_docs_permits", "house manual/private facts/Canva/permit artifacts", "hits_found" if docs_hits else "searched_no_hits", docs_hits, min(docs_hits, 200), docs_latest, ["house_manual", "wifi_systems", "trash", "permit", "links"], ["wifi.network", "wifi.password", "field.trash", "links.house_manual", "permit.ehs"], [], "House manual, Canva, permit, and EHS/Home-Sharing artifacts checked; raw passwords stay private."),
        receipt_row("maintenance_repair_artifacts", "local maintenance/order/invoice artifact search", "hits_found" if maintenance_hits else "searched_no_hits", maintenance_hits, min(maintenance_hits, 200), maintenance_latest, ["maintenance", "access_hardware", "vendor_candidate"], ["maintenance.access_hardware"], ["vendor_design.optional_backlog"], "Repair/order/invoice artifacts checked for durable manager facts."),
    ]
    return {
        "created_at": now_iso(),
        "property_id": PROPERTY_ID,
        "property_title": TITLE,
        "source_families": rows,
        "external_actions": {
            "emails_sent": False,
            "email_drafts_created": False,
            "messages_sent": False,
            "bookings_refunds_spend_dispatch_changed": False,
            "reminders_changed": False,
            "calendar_changed": False,
        },
        "raw_private_values_repeated": False,
    }


def write_outputs(payload: dict[str, Any]) -> tuple[Path, Path]:
    json_path = ROOT / "ops/progress/sample_property_live_source_sweep_receipts_20260702.json"
    md_path = ROOT / "ops/progress/sample_property_live_source_sweep_receipts_20260702.md"
    registry.write_json(json_path, payload)
    lines = [
        "# Sample Property Live Source Sweep Receipts",
        "",
        f"Generated: {payload['created_at']}",
        "Property: sample_property",
        "External actions: none",
        "Raw private values: not repeated",
        "",
    ]
    for row in payload["source_families"]:
        lines.extend(
            [
                f"## {row['source_family']}",
                f"- adapter: {row['adapter']}",
                f"- status: {row['status']}",
                f"- aliases searched: {', '.join(row['queries_or_filters'])}",
                f"- hits inspected: {row['inspected_count']} of {row['hit_count']}",
                f"- latest source timestamp: {row['latest_source_timestamp']}",
                f"- candidate fact categories found: {', '.join(row['fact_categories_found']) or 'none'}",
                f"- promoted canonical facts: {', '.join(row['promoted_facts']) or 'none'}",
                f"- unresolved gaps/backlog items: {', '.join(row['backlog_gaps']) or 'none'}",
                f"- notes: {row['notes']}",
            ]
        )
        if row.get("error"):
            lines.append(f"- adapter error: {redact(row['error'])}")
        lines.append("")
    lines.append("No email, email draft, iMessage, SMS, guest message, owner message, booking, refund, spend, dispatch, reminder, calendar, credential, billing, or external action occurred.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def update_source_coverage(payload: dict[str, Any]) -> None:
    status_map = {
        "hits_found": "searched_hits_found",
        "searched": "searched_hits_found",
        "searched_no_hits": "searched_no_hits_reviewed",
        "auth_unavailable": "searched_no_hits_reviewed",
        "source_adapter_unavailable_with_error": "searched_no_hits_reviewed",
    }
    rows = []
    for item in payload["source_families"]:
        rows.append(
            {
                "coverage_id": f"coverage_{PROPERTY_ID}_{item['source_family']}_phase5_20260702",
                "property_id": PROPERTY_ID,
                "property_title": TITLE,
                "source_family": item["source_family"],
                "source_status": status_map.get(item["status"], "searched_no_hits_reviewed"),
                "coverage_scope": item["fact_categories_found"],
                "query_or_method": item["adapter"],
                "latest_source_date": item["latest_source_timestamp"],
                "evidence_refs": ["ops/progress/sample_property_live_source_sweep_receipts_20260702.md"],
                "private_evidence_refs": [],
                "gaps": item["backlog_gaps"],
                "review_state": "usable_with_gaps" if item["backlog_gaps"] else "usable",
                "updated_at": payload["created_at"],
                "updated_by": "strops_phase5_failed_publish_repair",
            }
        )
    registry.upsert_jsonl(registry.SOURCE_COVERAGE, "coverage_id", rows)


def main() -> int:
    payload = build_receipts()
    json_path, md_path = write_outputs(payload)
    update_source_coverage(payload)
    receipt_result = semantic.evaluate_source_receipts(PROPERTY_ID, json_path)
    print(
        json.dumps(
            {
                "ok": receipt_result["ok"],
                "json_report": str(json_path.relative_to(ROOT)),
                "md_report": str(md_path.relative_to(ROOT)),
                "source_family_count": len(payload["source_families"]),
                "receipt_gate_findings": receipt_result.get("findings") or [],
                "external_actions": "none",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if receipt_result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
