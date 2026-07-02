#!/usr/bin/env python3
"""Sanitized fresh-replace publish model for STR Property Information notes.

This packet does not mutate Apple Notes.  It models the precheck and proof
conditions that the live publisher must satisfy before claiming success.
"""
from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from property_note_semantic_quality import evaluate_private_operations_note, evaluate_public_redaction_gate
except ImportError:  # pragma: no cover
    from .property_note_semantic_quality import evaluate_private_operations_note, evaluate_public_redaction_gate


@dataclass(frozen=True)
class PropertyIdentity:
    property_id: str
    title: str
    marker: str
    address: str
    name: str


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _text(note: dict[str, Any]) -> str:
    return " ".join(str(note.get(key) or "") for key in ("title", "body", "property_marker", "address", "name"))


def note_matches_identity(note: dict[str, Any], identity: PropertyIdentity) -> bool:
    if note.get("folder") != "STR Property Information":
        return False
    if str(note.get("title") or "") != identity.title:
        return False
    haystack = _text(note).lower()
    markers = [identity.marker, identity.address, identity.name]
    return any(marker and marker.lower() in haystack for marker in markers)


def active_matching_notes(notes: list[dict[str, Any]], identity: PropertyIdentity) -> list[dict[str, Any]]:
    return [note for note in notes if note_matches_identity(note, identity)]


def precheck_duplicate_matching(notes: list[dict[str, Any]], identity: PropertyIdentity) -> dict[str, Any]:
    matches = active_matching_notes(notes, identity)
    findings: list[dict[str, str]] = []
    if not matches:
        findings.append({"check": "duplicate_precheck", "message": "no active note matches exact title plus property marker/address/name"})
    if len(matches) > 1:
        findings.append({"check": "duplicate_precheck", "message": "duplicate active notes match exact title plus property marker/address/name"})
    return {
        "ok": not findings,
        "match_count": len(matches),
        "matched_ids": [str(note.get("id") or "") for note in matches],
        "findings": findings,
    }


def archive_note_model(note: dict[str, Any], identity: PropertyIdentity) -> dict[str, Any]:
    archive_id = f"archive::{note.get('id') or 'unknown'}::{now_iso()}"
    return {
        "id": archive_id,
        "title": "ARCHIVED - " + identity.title,
        "folder": "STR Property Information Review",
        "body": note.get("body") or "",
        "archived_from_id": note.get("id"),
        "archived_at": now_iso(),
    }


def validate_archive_proof(archive_note: dict[str, Any] | None, old_note: dict[str, Any], active_after: list[dict[str, Any]]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    if not archive_note:
        findings.append({"check": "archive_proof", "message": "archive note proof missing"})
    else:
        if archive_note.get("folder") != "STR Property Information Review":
            findings.append({"check": "archive_proof", "message": "archive proof is not in review/archive folder"})
        if archive_note.get("archived_from_id") != old_note.get("id"):
            findings.append({"check": "archive_proof", "message": "archive proof does not reference old note id"})
    if any(note.get("id") == old_note.get("id") for note in active_after):
        findings.append({"check": "old_id_no_longer_active", "message": "old note id is still active after replace"})
    return {"ok": not findings, "findings": findings}


def simulate_fresh_replace_property_information_note(
    *,
    identity: PropertyIdentity,
    notes_before: list[dict[str, Any]],
    replacement_body: str,
    live_readback_body: str | None,
    public_closeout_text: str,
    execute: bool = False,
) -> dict[str, Any]:
    """Model fresh-replace proofs without touching live Apple Notes."""
    findings: list[dict[str, str]] = []
    precheck = precheck_duplicate_matching(notes_before, identity)
    findings.extend(precheck["findings"])
    if not precheck["ok"]:
        return {
            "ok": False,
            "execute": execute,
            "mutated_live_apple_notes": False,
            "precheck": precheck,
            "findings": findings,
        }

    old_note = active_matching_notes(notes_before, identity)[0]
    archive_note = archive_note_model(old_note, identity)
    new_note = {
        "id": "new::" + str(old_note.get("id") or identity.property_id),
        "title": identity.title,
        "folder": "STR Property Information",
        "body": live_readback_body if live_readback_body is not None else replacement_body,
        "property_marker": identity.marker,
        "address": identity.address,
        "name": identity.name,
    }
    active_after = [
        deepcopy(note)
        for note in notes_before
        if note.get("folder") == "STR Property Information" and note.get("id") != old_note.get("id")
    ]
    active_after.append(new_note)

    archive_proof = validate_archive_proof(archive_note, old_note, active_after)
    findings.extend(archive_proof["findings"])

    postcheck = precheck_duplicate_matching(active_after, identity)
    if not postcheck["ok"] or postcheck["matched_ids"] != [new_note["id"]]:
        findings.append({"check": "post_replace_single_active", "message": "post-replace state is not exactly one active matching note"})

    if live_readback_body is None:
        findings.append({"check": "live_readback_required", "message": "live Apple Notes readback body is required"})
        readback_gate = {"ok": False, "findings": [{"check": "live_readback_required", "message": "missing readback"}]}
    else:
        readback_gate = evaluate_private_operations_note(live_readback_body, property_id=identity.property_id, mode="live_readback")
        findings.extend(readback_gate["findings"])

    replacement_gate = evaluate_private_operations_note(replacement_body, property_id=identity.property_id, mode="expected")
    findings.extend(replacement_gate["findings"])

    redaction_gate = evaluate_public_redaction_gate(public_closeout_text, property_id=identity.property_id)
    findings.extend(redaction_gate["findings"])

    material_readback_match = live_readback_body is not None and _compact(live_readback_body) == _compact(replacement_body)
    if not material_readback_match:
        findings.append({"check": "live_readback_material_match", "message": "live readback body does not materially match replacement body"})

    return {
        "ok": not findings,
        "execute": execute,
        "mutated_live_apple_notes": False,
        "model_only": True,
        "property_id": identity.property_id,
        "precheck": precheck,
        "postcheck": postcheck,
        "archive_proof": archive_proof,
        "old_id_no_longer_active": not any(note.get("id") == old_note.get("id") for note in active_after),
        "live_readback_required": live_readback_body is not None,
        "readback_semantic_gate": readback_gate,
        "replacement_semantic_gate": replacement_gate,
        "public_redaction_gate": redaction_gate,
        "material_readback_match": material_readback_match,
        "active_after_ids": [note.get("id") for note in active_after],
        "archive_id": archive_note.get("id"),
        "findings": findings,
    }


def _compact(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _load_model(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-json", type=Path, required=True, help="Sanitized JSON model with identity, notes_before, replacement_body, live_readback_body, and public_closeout_text.")
    args = parser.parse_args(argv)
    payload = _load_model(args.model_json)
    identity = PropertyIdentity(**payload["identity"])
    result = simulate_fresh_replace_property_information_note(
        identity=identity,
        notes_before=payload.get("notes_before") or [],
        replacement_body=payload.get("replacement_body") or "",
        live_readback_body=payload.get("live_readback_body"),
        public_closeout_text=payload.get("public_closeout_text") or "",
        execute=bool(payload.get("execute")),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
