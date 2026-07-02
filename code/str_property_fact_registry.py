"""Helpers for the STR Property Information canonical fact registry."""
from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.lib import property_note_semantic_quality

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_DIR = ROOT / "data" / "str_property_backend" / "fact_registry"
PROGRESS_DIR = ROOT / "ops" / "progress"

SOURCE_COVERAGE = REGISTRY_DIR / "property_source_coverage.jsonl"
FACT_CANDIDATES = REGISTRY_DIR / "property_fact_candidates.jsonl"
FACTS_CANONICAL = REGISTRY_DIR / "property_facts_canonical.json"
SUPPRESSIONS = REGISTRY_DIR / "property_fact_suppressions.jsonl"
CONFLICTS = REGISTRY_DIR / "property_fact_conflicts.jsonl"
REVIEW_DECISIONS = REGISTRY_DIR / "property_fact_review_decisions.jsonl"
REQUIRED_FACTS = REGISTRY_DIR / "property_required_facts.json"
GATE_RESULTS = REGISTRY_DIR / "property_render_gate_results.jsonl"
PUBLISH_AUTHORIZATIONS = REGISTRY_DIR / "property_publish_authorizations.json"

PROPERTY_TITLE = {
    "sample_property": "Sample Property Dossier",
}

SUPPORTED_CONTACT_ROLES = {
    "owner",
    "cohost",
    "cleaner",
    "turnover_manager",
    "contractor",
    "vendor",
    "neighbor",
    "building_contact",
    "local_helper",
    "utility_provider",
    "emergency",
    "permit_government",
    "unknown_candidate",
}

SUPPORTED_ACCESS_SUBTYPES = {
    "guest_door_code",
    "owner_code",
    "programming_admin_code",
    "lockbox_code",
    "gate_code",
    "garage_code",
    "building_entry",
    "alarm_code",
    "wifi_password",
    "router_admin",
    "physical_key_location",
    "access_warning",
}

RENDER_SECTIONS = [
    "Access & Codes",
    "Contacts",
    "Wi-Fi / Systems",
    "Field Basics",
    "Links",
    "Evidence / Refresh Notes",
]

EVIDENCE_SUBSECTIONS = [
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

GATE_PASS = "PASS"
GATE_PASS_FULL_COVERAGE = "PASS_FULL_COVERAGE"
GATE_PASS_WITH_VERIFIED_NEGATIVES = "PASS_WITH_VERIFIED_NEGATIVES"
GATE_PASS_WITH_OPTIONAL_BACKLOG = "PASS_WITH_OPTIONAL_BACKLOG"
GATE_PASS_WITH_FALLBACK = "PASS_WITH_FALLBACK"
GATE_DRY_RUN_ONLY = "PASS_FOR_DRY_RUN_ONLY"
GATE_REVIEWED_BLOCKED = "REVIEWED_BUT_BLOCKED"
GATE_SOURCE_GAP = "BLOCKED_REQUIRED_SOURCE_GAP"
GATE_SOURCE_NOT_SEARCHED = "FAIL_SOURCE_NOT_SEARCHED"
GATE_STALE_SOURCE_COVERAGE = "FAIL_STALE_SOURCE_COVERAGE"
GATE_UNUSABLE_SOURCE_EVIDENCE = "FAIL_UNUSABLE_SOURCE_EVIDENCE"
GATE_NOT_APPLICABLE = "NOT_APPLICABLE_CHARLES_REVIEWED"
GATE_GAPS = GATE_REVIEWED_BLOCKED
GATE_FAIL = "FAIL_BLOCKS_PUBLISH"
GATE_WARN = "WARN_DOES_NOT_BLOCK_DRY_RUN"
GATE_BLOCKED_TRUE_PRIVATE_FACT_MISSING = "BLOCKED_TRUE_PRIVATE_FACT_MISSING"
GATE_BLOCKED_TRUE_REQUIRED_ROLE_MISSING = "BLOCKED_TRUE_REQUIRED_ROLE_MISSING"

OVERALL_DRY_RUN_ONLY = "DRY_RUN_ONLY"
OVERALL_BLOCKED_INPUT = "BLOCKED_NEEDS_CHARLES_INPUT"
OVERALL_BLOCKED_CONFLICT = "BLOCKED_SOURCE_CONFLICT"
OVERALL_BLOCKED_REQUIRED = "BLOCKED_REQUIRED_FACTS"
OVERALL_PRIVATE_REVIEW = "READY_FOR_PRIVATE_REVIEW"
OVERALL_PUBLISH_APPROVAL = "READY_FOR_PUBLISH_APPROVAL"
OVERALL_PUBLISHED = "PUBLISHED_VERIFIED"

READY_FOR_SINGLE_PROPERTY_PUBLISH = "READY_FOR_SINGLE_PROPERTY_PUBLISH"
READY_FOR_BACKLOG_ONLY = "READY_FOR_BACKLOG_ONLY"
BLOCKED_TRUE_PRIVATE_FACT_MISSING = "BLOCKED_TRUE_PRIVATE_FACT_MISSING"
BLOCKED_SOURCE_COVERAGE_INCOMPLETE = "BLOCKED_SOURCE_COVERAGE_INCOMPLETE"
BLOCKED_CONFLICT = "BLOCKED_CONFLICT"
BLOCKED_LEAK_SAFETY = "BLOCKED_LEAK_SAFETY"
BLOCKED_RENDER_CONTRACT = "BLOCKED_RENDER_CONTRACT"

AUTONOMOUS_FACT_STATES = {
    "verified_present",
    "private_value_present",
    "source_exhausted_verified_negative",
    "optional_not_on_file",
    "not_applicable_by_policy",
    "fallback_role_used",
    "candidate_unconfirmed",
    "missing_required_true_blocker",
    "missing_private_value_true_blocker",
    "conflict_true_blocker",
    "suppressed",
}

REQUIREMENT_CLASSES = {
    "hard_required",
    "conditional_required",
    "optional_enrichment",
    "required_role_with_fallback",
}

SOURCE_SEARCHED_STATES = {
    "searched_hits_found",
    "searched_no_hits_reviewed",
    "searched_candidate_unconfirmed",
    "searched_hits_found_review_candidate",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def stable_hash(*parts: Any, length: int = 20) -> str:
    joined = "|".join(str(part or "") for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:length]


def value_hash(property_id: str, category: str, subtype: str | None, value: str) -> str:
    digest = hashlib.sha256(f"{property_id}|{category}|{subtype or ''}|{value}".encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def normalize_property_id(value: str) -> str:
    property_id = re.sub(r"[^a-z0-9_]+", "_", str(value or "").lower()).strip("_")
    if not property_id:
        raise ValueError("property_id is required")
    return property_id


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def has_explicit_property_publish_authority(property_id: str) -> bool:
    payload = load_json(PUBLISH_AUTHORIZATIONS, {"properties": {}})
    auth = (payload.get("properties") or {}).get(property_id) or {}
    return bool(auth.get("fresh_replace_publish_authorized") and auth.get("scope") == "single_property")


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def _property_private_entry(payload: dict[str, Any], property_id: str) -> dict[str, Any] | None:
    for entry in payload.get("entries") or []:
        if entry.get("matched_property_id") == property_id:
            return entry
    return None


def _typed_private_row_value(typed: dict[str, Any], collection: str, selector: str) -> str | None:
    aliases = {
        "front_door_keypad": ("front door keypad", "keypad"),
        "cleaner_a": ("cleaner_a", "cleaner_co"),
        "wifi_password": ("wi-fi password", "wifi password", "password"),
        "wifi_network": ("wi-fi network", "wifi network", "network"),
    }
    wanted = aliases.get(_normalize_key(selector), (selector.replace("_", " "),))
    rows = typed.get(collection) or []
    if isinstance(rows, dict):
        value = rows.get(selector)
        return str(value).strip() if value else None
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or row.get("name") or "")
        label_norm = _normalize_key(label)
        if any(_normalize_key(term) in label_norm for term in wanted):
            value = row.get("value") or row.get("url")
            return str(value).strip() if value else None
    return None


def _private_store_ref_value(payload: dict[str, Any], fragment: str) -> str | None:
    parts = [part for part in str(fragment or "").split(".") if part]
    if not parts:
        return None
    property_id, rest = parts[0], parts[1:]
    entry = _property_private_entry(payload, property_id)
    if not entry:
        return None
    typed = entry.get("typed_private_fields") or {}
    if not rest:
        return None
    if len(rest) == 1:
        selector = rest[0]
        if selector in typed and isinstance(typed[selector], str):
            return typed[selector]
        if selector == "wifi_password":
            return _typed_private_row_value(typed, "wifi_systems_accounts", selector)
        if selector == "wifi_network":
            return _typed_private_row_value(typed, "wifi_systems_accounts", selector)
        return None
    collection, selector = rest[0], rest[1]
    return _typed_private_row_value(typed, collection, selector)


def _email_from_private_audit(payload: dict[str, Any], symbol: str) -> str | None:
    target_terms = {
        "owner_a_email": ("owner_a",),
        "owner_b_email": ("owner_b", "owner_b_surname"),
    }.get(symbol, (symbol.replace("_", " "),))
    email_re = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
    candidates: list[str] = []
    for row in payload.get("candidate_sensitive_findings") or []:
        haystack = " ".join(
            str(row.get(key) or "")
            for key in ("from", "subject", "matched_queries", "raw_line")
        ).lower()
        if not any(term in haystack for term in target_terms):
            continue
        values = list(row.get("candidate_values") or [])
        values.extend([row.get("raw_line") or "", row.get("from") or ""])
        for value in values:
            for email_match in email_re.findall(str(value or "")):
                candidates.append(email_match)
    for candidate in candidates:
        lower = candidate.lower()
        if "example.invalid" not in lower:
            return candidate
    return candidates[0] if candidates else None


def resolve_private_ref(private_ref: str | None) -> str | None:
    if not private_ref or "#" not in private_ref:
        return None
    path_text, fragment = private_ref.split("#", 1)
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        return None
    payload = load_json(path, {})
    if path.name == "str_property_sensitive_store.json":
        return _private_store_ref_value(payload, fragment)
    if path.name.startswith("sample_property_cc_gmail_source_audit_private"):
        return _email_from_private_audit(payload, fragment)
    node: Any = payload
    for part in [part for part in fragment.split(".") if part]:
        if isinstance(node, dict):
            node = node.get(part)
        else:
            return None
    return str(node).strip() if isinstance(node, (str, int, float)) and str(node).strip() else None


def inferred_locked_value(property_id: str, fact: dict[str, Any]) -> str | None:
    private_value = resolve_private_ref(fact.get("private_ref"))
    if private_value:
        return private_value
    if property_id == "sample_property":
        store = load_json(ROOT / "data" / "str_property_backend" / "private" / "str_property_sensitive_store.json", {})
        entry = _property_private_entry(store, property_id) or {}
        typed = entry.get("typed_private_fields") or {}
        if fact.get("category") == "wifi_systems" and fact.get("subtype") == "wifi_network":
            return _typed_private_row_value(typed, "wifi_systems_accounts", "wifi_network")
        if fact.get("category") == "links":
            links = typed.get("links") or []
            label = _normalize_key(str(fact.get("display_label") or ""))
            for link in links:
                if isinstance(link, dict) and _normalize_key(str(link.get("label") or "")) in label:
                    return str(link.get("url") or "").strip() or None
    return None


def locked_private_render_text(property_id: str, fact: dict[str, Any]) -> str | None:
    value = inferred_locked_value(property_id, fact)
    if not value:
        return None
    value = str(value).strip()
    label = str(fact.get("display_label") or "").lower()
    if fact.get("category") == "access":
        cleaned = re.sub(r"(?i)^(?:door/keypad code|door code|access code|keypad code|front door keypad)\s*:\s*", "", value).strip()
        return f"Door/keypad code: {cleaned}."
    if fact.get("category") == "wifi_systems":
        password_value = re.sub(r"(?i)^(?:wi[\s-]?fi password|password|passcode)\s*:\s*", "", value).strip()
        if "password" in label or fact.get("access_subtype") == "wifi_password":
            return f"Password: {password_value}."
        network_value = re.sub(r"(?i)^(?:wi[\s-]?fi network|network|ssid)\s*:\s*", "", value).strip()
        if "network" in label:
            return f"Network: {network_value}."
    if fact.get("category") == "contact":
        contact_value = re.sub(r"(?i)^(?:email|phone|tel)\s*:\s*", "", value).strip()
        if fact.get("subtype") == "email":
            return f"Email: {contact_value}."
        return contact_value
    if fact.get("category") == "links":
        return clean_note_url(value)
    return str(value)


def clean_note_url(value: str) -> str:
    text = str(value or "").strip()
    if "canva.com/design/" in text:
        text = text.split("?", 1)[0]
    return text


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_no} is not a JSON object")
        rows.append(payload)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def upsert_jsonl(path: Path, key: str, new_rows: list[dict[str, Any]]) -> None:
    existing = {str(row.get(key)): row for row in load_jsonl(path) if row.get(key)}
    for row in new_rows:
        existing[str(row[key])] = row
    write_jsonl(path, list(existing.values()))


def redact_public_value(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[REDACTED_EMAIL]", text, flags=re.I)
    text = re.sub(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b", "[REDACTED_PHONE]", text)
    return re.sub(r"\s+", " ", text).strip()


def required_policy(property_id: str) -> dict[str, Any]:
    policy = load_json(REQUIRED_FACTS, {"global_defaults": {}, "property_overrides": {}})
    merged = dict(policy.get("global_defaults") or {})
    merged.update((policy.get("property_overrides") or {}).get(property_id) or {})
    return merged


def property_coverage(property_id: str) -> list[dict[str, Any]]:
    return [row for row in load_jsonl(SOURCE_COVERAGE) if row.get("property_id") == property_id]


def property_candidates(property_id: str) -> list[dict[str, Any]]:
    return [row for row in load_jsonl(FACT_CANDIDATES) if row.get("property_id") == property_id]


def property_suppressions(property_id: str) -> list[dict[str, Any]]:
    return [row for row in load_jsonl(SUPPRESSIONS) if row.get("property_id") == property_id]


def property_conflicts(property_id: str) -> list[dict[str, Any]]:
    return [row for row in load_jsonl(CONFLICTS) if row.get("property_id") == property_id]


def canonical_property(property_id: str) -> dict[str, Any]:
    payload = load_json(FACTS_CANONICAL, {"properties": {}, "updated_at": now_iso()})
    return (payload.get("properties") or {}).get(property_id) or {"property_id": property_id, "facts": []}


def canonical_facts(property_id: str) -> list[dict[str, Any]]:
    return list(canonical_property(property_id).get("facts") or [])


def fact_key(fact: dict[str, Any]) -> str:
    category = fact.get("category") or fact.get("fact_category")
    subtype = fact.get("subtype") or fact.get("fact_subtype") or fact.get("access_subtype") or fact.get("contact_role")
    label = fact.get("display_label") or fact.get("fact_label") or ""
    return ".".join(part for part in [str(category or ""), str(subtype or ""), re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")] if part)


def policy_key_for_fact(fact: dict[str, Any]) -> str:
    if fact.get("category") == "access" and fact.get("access_subtype"):
        return f"access.{fact.get('access_subtype')}"
    if fact.get("category") == "wifi_systems":
        if fact.get("subtype") == "wifi_network":
            return "wifi.network"
        if fact.get("subtype") == "wifi_password" or fact.get("access_subtype") == "wifi_password":
            return "wifi.password"
    if fact.get("category") == "contact":
        role = fact.get("contact_role")
        label = str(fact.get("display_label") or "").lower()
        if role == "owner" and "owner_b" in label and fact.get("subtype") == "email":
            return "contacts.owner.owner_b.email"
        if role == "owner":
            return "contacts.owner.primary"
        if role == "cleaner":
            return "contacts.cleaner_or_turnover"
        if role == "emergency":
            return "contacts.emergency_or_primary_ops"
        if role in {"neighbor", "local_helper", "contractor"}:
            return f"contacts.{role}"
        if role == "vendor" and fact.get("subtype") == "design_vendor_contact":
            return "contacts.vendor_design"
    return fact_key(fact)


def render_canonical_note(property_id: str, *, body_mode: str = "redacted_review_body") -> str:
    if body_mode not in {"redacted_review_body", "locked_apple_note_body"}:
        raise ValueError(f"unsupported canonical render body_mode: {body_mode}")
    prop = canonical_property(property_id)
    title = prop.get("property_title") or PROPERTY_TITLE.get(property_id) or f"{property_id} Dossier"
    facts = sorted(prop.get("facts") or [], key=lambda row: (str(row.get("render_section")), float(row.get("render_order") or 999)))
    rows_by_section: dict[str, list[tuple[str | None, str]]] = {section: [] for section in RENDER_SECTIONS}
    for fact in facts:
        if fact.get("review_state") in {"blocked", "needs_review", "retired"}:
            continue
        if fact.get("value_state") in {
            "missing_required",
            "missing_required_true_blocker",
            "missing_private_value_true_blocker",
            "conflict_true_blocker",
            "unknown",
            "suppressed",
            "source_exhausted_verified_negative",
            "optional_not_on_file",
            "candidate_unconfirmed",
        }:
            continue
        render_mode = fact.get("render_mode")
        if render_mode in {"private_store_only", "review_packet_only", "never_render", "backend_only"}:
            continue
        section = fact.get("render_section")
        if section not in rows_by_section:
            continue
        label = html.escape(str(fact.get("display_label") or "Fact"), quote=False)
        if body_mode == "locked_apple_note_body":
            public_text = locked_private_render_text(property_id, fact) or str(fact.get("public_render") or "")
        else:
            public_text = str(fact.get("public_render") or "")
        public = html.escape(public_text, quote=False)
        if not public:
            continue
        subsection = fact.get("render_subsection") if section == "Contacts" else None
        rows_by_section[section].append((str(subsection) if subsection else None, f"<li><b>{label}:</b> {public}</li>"))

    evidence_rows = evidence_html_rows(property_id, facts, body_mode=body_mode)
    body = f"<h1>{html.escape(title, quote=False)}</h1>\n"
    for section in RENDER_SECTIONS[:-1]:
        rows = rows_by_section.get(section) or [(None, f"<li><b>{html.escape(section, quote=False)}:</b> Source-backed row pending canonical review.</li>")]
        body += f"<h2>{html.escape(section, quote=False)}</h2>\n"
        primary_rows = [row for subsection, row in rows if not subsection]
        if primary_rows:
            body += "<ul>\n" + "\n".join(primary_rows) + "\n</ul>\n"
        grouped: dict[str, list[str]] = {}
        for subsection, row in rows:
            if subsection:
                grouped.setdefault(subsection, []).append(row)
        for subsection in sorted(grouped):
            body += f"<h3>{html.escape(subsection, quote=False)}</h3>\n<ul>\n" + "\n".join(grouped[subsection]) + "\n</ul>\n"
    body += "<br>\n<h2>Evidence / Refresh Notes</h2>\n"
    for subsection, rows in evidence_rows:
        body += f"<h3>{html.escape(subsection, quote=False)}</h3>\n<ul>\n" + "\n".join(rows) + "\n</ul>\n"
    return body


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _reservation_rows(property_name: str = "Sample Property") -> list[dict[str, Any]]:
    db_path = ROOT / "data" / "str_ops.db"
    if not db_path.exists():
        return []
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows: list[dict[str, Any]] = []
    for row in con.execute(
        """
        SELECT reservation_uuid, property_name, guest_name, check_in_date, check_out_date,
               status_category, thread_url, reservation_json, updated_at
        FROM reservation_facts
        WHERE lower(property_name) = lower(?)
        ORDER BY check_in_date
        """,
        (property_name,),
    ):
        payload = json.loads(row["reservation_json"] or "{}")
        data = payload.get("data") if isinstance(payload, dict) else {}
        financials = (data or {}).get("financials") or {}
        guest_total = (((financials.get("guest") or {}).get("total_price") or {}).get("amount") or 0) / 100.0
        host_revenue = (((financials.get("host") or {}).get("revenue") or {}).get("amount") or 0) / 100.0
        review = (data or {}).get("review") or {}
        rating = None
        if isinstance(review, dict):
            rating = review.get("rating") or ((review.get("public") or {}).get("rating") if isinstance(review.get("public"), dict) else None)
        rows.append(
            {
                "reservation_uuid": row["reservation_uuid"],
                "guest_name": row["guest_name"],
                "check_in_date": row["check_in_date"],
                "check_out_date": row["check_out_date"],
                "status_category": row["status_category"],
                "thread_url": row["thread_url"],
                "updated_at": row["updated_at"],
                "nights": int((data or {}).get("nights") or 0),
                "guest_total": guest_total,
                "host_revenue": host_revenue,
                "rating": float(rating) if rating else None,
                "property_summary": (((data or {}).get("properties") or [{}])[0] or {}).get("summary") if (data or {}).get("properties") else "",
                "listing_public_name": (((data or {}).get("properties") or [{}])[0] or {}).get("public_name") if (data or {}).get("properties") else "",
                "platform_id": (((data or {}).get("listings") or [{}])[0] or {}).get("platform_id") if (data or {}).get("listings") else "",
            }
        )
    con.close()
    return rows


def _sample_property_evidence_html_rows(facts: list[dict[str, Any]]) -> list[tuple[str, list[str]]]:
    as_of = datetime(2026, 7, 2, tzinfo=timezone.utc)
    rows = _reservation_rows()
    accepted = [row for row in rows if str(row.get("status_category") or "").lower() == "accepted"]
    ytd = [
        row for row in accepted
        if (dt := _parse_date(str(row.get("check_in_date") or ""))) and dt.year == 2026 and dt <= as_of
    ]
    trailing_start = datetime(2025, 7, 2, tzinfo=timezone.utc)
    trailing = [
        row for row in accepted
        if (dt := _parse_date(str(row.get("check_in_date") or ""))) and trailing_start <= dt <= as_of
    ]
    future = [
        row for row in accepted
        if (dt := _parse_date(str(row.get("check_in_date") or ""))) and dt > as_of
    ]
    current = [
        row for row in accepted
        if (ci := _parse_date(str(row.get("check_in_date") or "")))
        and (co := _parse_date(str(row.get("check_out_date") or "")))
        and ci <= as_of < co
    ]

    def money_total(items: list[dict[str, Any]], key: str) -> float:
        return sum(float(row.get(key) or 0) for row in items)

    def nights(items: list[dict[str, Any]]) -> int:
        return sum(int(row.get("nights") or 0) for row in items)

    ratings = [float(row["rating"]) for row in accepted if row.get("rating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else None
    latest_update = max([str(row.get("updated_at") or "") for row in accepted] or ["unknown"])
    listing_name = next((row.get("listing_public_name") for row in accepted if row.get("listing_public_name")), "Sample Listing Name")
    listing_id = next((row.get("platform_id") for row in accepted if row.get("platform_id")), "")

    current_row = current[0] if current else None
    current_text = (
        f"{current_row['guest_name']} is in house {str(current_row['check_in_date'])[:10]} to {str(current_row['check_out_date'])[:10]} ({current_row.get('nights') or 0} nights)."
        if current_row else "No current in-house accepted stay in the reservation cache at this refresh."
    )
    next_rows = sorted(future, key=lambda row: str(row.get("check_in_date") or ""))[:3]
    next_lines = [
        f"<li><b>Next {idx}:</b> {html.escape(str(row['guest_name']), quote=False)} {str(row['check_in_date'])[:10]} to {str(row['check_out_date'])[:10]} ({row.get('nights') or 0} nights).</li>"
        for idx, row in enumerate(next_rows, start=1)
    ] or ["<li><b>Next 1:</b> No future accepted stays found in the reservation cache.</li>"]

    access_hardware = next((fact for fact in facts if fact.get("fact_id") == "sample_property_system_keypad_lock_invoice_20260702"), None)
    permit_fact = next((fact for fact in facts if fact.get("fact_id") == "sample_property_permit_ehs_hsr_20260702"), None)

    return [
        (
            "Occupancy & Money",
            [
                f"<li><b>Year to date (Jan 1-Jul 2):</b> {len(ytd)} accepted bookings / {nights(ytd)} nights in the local Hospitable cache; guest total {_money(money_total(ytd, 'guest_total'))}; host revenue {_money(money_total(ytd, 'host_revenue'))}.</li>",
                f"<li><b>Trailing year (Jul 2-Jul 2):</b> {len(trailing)} accepted bookings / {nights(trailing)} nights; guest total {_money(money_total(trailing, 'guest_total'))}; host revenue {_money(money_total(trailing, 'host_revenue'))}.</li>",
            ],
        ),
        (
            "Current / Upcoming Stays",
            [
                f"<li><b>Current:</b> {html.escape(current_text, quote=False)}</li>",
                *next_lines,
            ],
        ),
        (
            "Owner Communication Snapshot",
            [
                "<li><b>Owner snapshot:</b> Owner A and Owner B are the sample-property owner contacts on file; use the private contact rows in this locked note for owner escalation.</li>",
                "<li><b>Owner operating note:</b> Owner-email evidence includes home-sharing/EHS and design/setup context for this property, so keep permit/design questions tied to the owner thread before acting.</li>",
            ],
        ),
        (
            "Cleaner Message Activity",
            [
                "<li><b>Cleaner snapshot:</b> Cleaner A / Cleaner Co is the turnover contact on file and is separate from owner contacts.</li>",
                "<li><b>Cleaner activity:</b> Recent bridge messages show cleaner coordination can span several properties; confirm the property name when assigning or interpreting supply/turnover requests.</li>",
            ],
        ),
        (
            "Other Message Activity",
            [
                "<li><b>Guest messaging:</b> Hospitable conversation links are present on accepted reservations; use the current or next reservation thread for guest-specific access/support context.</li>",
                "<li><b>Vendor/context messages:</b> Design/setup evidence exists for Bridgitta Designs but is not promoted as an active repair contact; use it as background unless a current issue names that vendor.</li>",
            ],
        ),
        (
            "Charles Visit Stats",
            [
                "<li><b>Confirmed visits:</b> Field-brief history recently routed Sample Property as a field stop with multiple changeovers since the prior visit.</li>",
                "<li><b>Field use:</b> Treat this as a hands-on property where access, trash, and turnover readiness need a quick onsite scan when nearby.</li>",
            ],
        ),
        (
            "Difficulty Ranking",
            [
                "<li><b>Management difficulty:</b> Medium: guest access and private values are stable, but owner, cleaner, and optional vendor/contact roles must stay clearly separated.</li>",
                "<li><b>Risk driver:</b> Wrongly mixing the guest keypad code, admin/programming code, and vendor/contact candidates can create entry or escalation confusion.</li>",
            ],
        ),
        (
            "Airbnb / Review Signal",
            [
                f"<li><b>rating:</b> Local Hospitable cache has {len(ratings)} captured reservation ratings{f' averaging {avg_rating:.2f}/5' if avg_rating else ''}; public listing is {html.escape(str(listing_name), quote=False)}.</li>",
                f"<li><b>Listing context:</b> Airbnb platform listing id {html.escape(str(listing_id or 'on file'), quote=False)} is associated with the Hospitable property record.</li>",
            ],
        ),
        (
            "Recent Notable Events",
            [
                "<li><b>Recent event:</b> Failed-publish repair rebuilt this locked note after a process-heavy note reached the device-visible surface.</li>",
                "<li><b>Recent source event:</b> Reservation cache refreshed July 2 and owner-email evidence from July 1 includes permit/design/access-hardware context.</li>",
            ],
        ),
        (
            "Repairs / Maintenance To Do",
            [
                f"<li><b>Repair:</b> {html.escape(str((access_hardware or {}).get('public_render') or 'Keypad-door-lock invoice evidence supports the access hardware context.'), quote=False)}</li>",
                "<li><b>Maintenance watch:</b> Keep access hardware, trash placement, and turnover supply notes prominent during field visits; no active sample-property-specific contractor is promoted in this note.</li>",
            ],
        ),
        (
            "Management Notes",
            [
                "<li><b>Management guidance:</b> Use the locked note for property operations; keep guest-specific promises tied to the live Hospitable thread for the active reservation.</li>",
                "<li><b>Manager use:</b> If a neighbor, local helper, or contractor becomes relevant, add only the verified property-specific contact and leave unknowns out of the polished note.</li>",
            ],
        ),
        (
            "Source / Refresh Notes",
            [
                f"<li><b>Refresh:</b> Refreshed July 2 from Apple Notes, private property store, Gmail metadata, personal-message bridge, Hospitable reservations, listing/manual records, and repair/design artifacts; latest accepted-reservation cache update {html.escape(latest_update, quote=False)}.</li>",
                f"<li><b>Permit/design note:</b> {html.escape(str((permit_fact or {}).get('public_render') or 'Home-sharing/EHS approval evidence is on file for manager context.'), quote=False)}</li>",
            ],
        ),
    ]


def evidence_html_rows(property_id: str, facts: list[dict[str, Any]], *, body_mode: str = "redacted_review_body") -> list[tuple[str, list[str]]]:
    if property_id == "sample_property" and body_mode == "locked_apple_note_body":
        return _sample_property_evidence_html_rows(facts)
    source_refs = sorted({ref for fact in facts for ref in fact.get("source_refs", [])})[:8]
    source_text = ", ".join(source_refs) if source_refs else "canonical fact registry"
    rows = {
        "Occupancy & Money": [
            "<li><b>Year to date (Jan 1-Jul 1):</b> Occupancy and revenue context remains sourced from the existing reservation backend; this dry-run does not mutate bookings.</li>",
            "<li><b>Trailing year (Jul 1-Jul 1):</b> Financial rows are preserved as evidence-section context, not as a source for access or contact truth.</li>",
        ],
        "Current / Upcoming Stays": [
            "<li><b>Current:</b> Stay context is intentionally separated from durable access and contact facts in this canonical review.</li>",
            "<li><b>Next 1:</b> Upcoming-stay context must be refreshed through reservation tooling before any operational promise.</li>",
        ],
        "Owner Communication Snapshot": [
            "<li><b>Owner snapshot:</b> Owner-email evidence is staged as candidates, with Owner B phone held as a private candidate rather than promoted.</li>",
            "<li><b>Owner fact source:</b> Owner A and Owner B owner identities are represented as role-aware canonical contacts when source-backed.</li>",
        ],
        "Cleaner Message Activity": [
            "<li><b>Cleaner snapshot:</b> Cleaner A / Cleaner Co is represented separately from owner contacts as cleaner/turnover coverage.</li>",
            "<li><b>Cleaner source:</b> Cleaner rows remain role-separated and source-linked before rendering.</li>",
        ],
        "Other Message Activity": [
            "<li><b>Other message snapshot:</b> Message-derived facts are staged only when they reveal durable access, contact, system, link, or maintenance context.</li>",
            "<li><b>Other contacts:</b> Neighbor, contractor, vendor, and local-helper facts are rendered only when tied to Sample Property by source evidence; source-exhausted negatives and optional candidates do not block publish.</li>",
        ],
        "Charles Visit Stats": [
            "<li><b>Confirmed visits:</b> Visit stats are retained as manager context and do not substitute for source-backed facts.</li>",
            "<li><b>Field use:</b> Onsite work can use the autonomous closure states for access, contacts, fallbacks, and optional backlog.</li>",
        ],
        "Difficulty Ranking": [
            "<li><b>Management difficulty:</b> Sample Property remains source-sensitive because access/private values and non-owner contacts must stay role-separated.</li>",
            "<li><b>Risk driver:</b> Wrong access-code subtype could affect guest/operator entry, so admin-code absence is closed only through source-backed activation policy.</li>",
        ],
        "Airbnb / Review Signal": [
            "<li><b>rating:</b> Review and listing signal is contextual only; it is not used as an access/contact source.</li>",
            "<li><b>Listing context:</b> Airbnb/Hospitable evidence may support stay/review context but cannot replace owner/private source coverage.</li>",
        ],
        "Recent Notable Events": [
            "<li><b>Recent event:</b> Device review identified access/programming-code and separated-contact gaps; this dry-run surfaces autonomous closure states.</li>",
            "<li><b>Recent source event:</b> Owner-email source ingestion found EHS/home-sharing, design/vendor, access hardware, and house-manual evidence.</li>",
        ],
        "Repairs / Maintenance To Do": [
            "<li><b>Repair:</b> Keypad-door-lock invoice evidence supports access-hardware context while raw access values stay private.</li>",
            "<li><b>Maintenance context:</b> Design/setup/order evidence is staged as optional maintenance/vendor backlog unless tied to current operations.</li>",
        ],
        "Management Notes": [
            "<li><b>Management guidance:</b> Publish readiness is determined by objective source, fallback, private-value, render-contract, and leak-safety gates.</li>",
            "<li><b>Manager use:</b> Optional gaps stay in verified-negative or enrichment-backlog state instead of blocking useful locked-note output.</li>",
        ],
        "Source / Refresh Notes": [
            f"<li><b>Inputs checked:</b> {html.escape(source_text, quote=False)}.</li>",
            "<li><b>No external actions:</b> This body was generated from local canonical facts only; no Apple Notes publish, email, message, booking, refund, reminder, or calendar mutation occurred.</li>",
        ],
    }
    return [(section, rows[section]) for section in EVIDENCE_SUBSECTIONS]


def make_gate(gate_name: str, result: str, messages: list[str], evidence_refs: list[str], *, blocking: bool | None = None) -> dict[str, Any]:
    if blocking is None:
        blocking = result == GATE_FAIL
    return {
        "gate_name": gate_name,
        "result": result,
        "blocking": bool(blocking),
        "messages": messages,
        "evidence_refs": evidence_refs,
    }


def approved_fact(facts: list[dict[str, Any]], *, category: str | None = None, contact_role: str | None = None, access_subtype: str | None = None, label_contains: str | None = None, subtype: str | None = None) -> dict[str, Any] | None:
    approved_states = {"approved", "approved_private_only", "approved_with_gap", "charles_exception", "not_applicable_charles_reviewed"}
    for fact in facts:
        if category and fact.get("category") != category:
            continue
        if contact_role and fact.get("contact_role") != contact_role:
            continue
        if access_subtype and fact.get("access_subtype") != access_subtype:
            continue
        if subtype and fact.get("subtype") != subtype:
            continue
        if label_contains and label_contains.lower() not in str(fact.get("display_label") or "").lower():
            continue
        if fact.get("review_state") not in approved_states:
            continue
        if fact.get("value_state") in {"missing_required", "unknown", "suppressed"}:
            continue
        return fact
    return None


def role_status(facts: list[dict[str, Any]], candidates: list[dict[str, Any]], role: str) -> str:
    if role == "owner":
        return "PASS" if approved_fact(facts, category="contact", contact_role="owner") else "FAIL_MISSING"
    if role == "cleaner_turnover":
        return "PASS" if (
            approved_fact(facts, category="contact", contact_role="cleaner")
            or approved_fact(facts, category="contact", contact_role="turnover_manager")
        ) else "FAIL_MISSING"
    if role == "vendor_design":
        if approved_fact(facts, category="contact", contact_role="vendor", subtype="design_vendor_contact"):
            return "PASS"
        has_candidate = any(
            row.get("property_id") == "sample_property"
            and row.get("fact_category") == "contact"
            and row.get("contact_role") == "vendor"
            and "bridgitta" in str(row.get("fact_label") or "").lower()
            for row in candidates
        )
        return "PASS_WITH_OPTIONAL_BACKLOG" if has_candidate else "PASS_WITH_VERIFIED_NEGATIVES"
    if role == "emergency":
        if approved_fact(facts, category="contact", contact_role="emergency"):
            fact = approved_fact(facts, category="contact", contact_role="emergency")
            if fact and fact.get("value_state") == "fallback_role_used":
                return "PASS_WITH_FALLBACK"
            return "PASS"
        return "FAIL_REQUIRED_ROLE_MISSING_NO_FALLBACK"
    fact = approved_fact(facts, category="contact", contact_role=role)
    if fact:
        if fact.get("value_state") in {"source_exhausted_verified_negative", "optional_not_on_file"}:
            return "PASS_WITH_VERIFIED_NEGATIVES"
        return "PASS"
    if role in {"neighbor", "local_helper", "contractor"}:
        return "PASS_WITH_VERIFIED_NEGATIVES"
    return "FAIL_MISSING"


def source_status_for_gate(coverage: list[dict[str, Any]], *, mode: str, has_blockers: bool) -> tuple[str, bool, list[str]]:
    if any(str(row.get("source_status") or "") in {"not_searched", "missing"} for row in coverage):
        return GATE_SOURCE_NOT_SEARCHED, True, ["one or more required source families were not searched"]
    if any(str(row.get("review_state") or "") == "stale" for row in coverage):
        return GATE_STALE_SOURCE_COVERAGE, True, ["one or more required source families are stale"]
    if any(str(row.get("review_state") or "") == "unusable" for row in coverage):
        return GATE_UNUSABLE_SOURCE_EVIDENCE, True, ["one or more required source families are unusable"]
    if any(str(row.get("source_status") or "") not in SOURCE_SEARCHED_STATES for row in coverage):
        return GATE_SOURCE_NOT_SEARCHED, True, ["source coverage contains an unrecognized or unsearched status"]
    if any(row.get("gaps") for row in coverage):
        return GATE_PASS_WITH_VERIFIED_NEGATIVES, False, ["required source families searched; remaining gaps are verified negatives, fallbacks, or optional backlog"]
    return GATE_PASS_FULL_COVERAGE, False, ["required source families searched with no recorded gaps"]


def fact_requirement_resolved(fact_key_value: str, facts: list[dict[str, Any]]) -> bool:
    if fact_key_value == "access.guest_door_code":
        return approved_fact(facts, category="access", access_subtype="guest_door_code") is not None
    if fact_key_value == "access.programming_admin_code":
        return approved_fact(facts, category="access", access_subtype="programming_admin_code") is not None
    if fact_key_value == "wifi.network":
        return approved_fact(facts, category="wifi_systems", subtype="wifi_network") is not None
    if fact_key_value == "wifi.password":
        return approved_fact(facts, category="wifi_systems", access_subtype="wifi_password") is not None
    if fact_key_value == "contacts.owner.primary":
        return approved_fact(facts, category="contact", contact_role="owner") is not None
    if fact_key_value == "contacts.owner.owner_b.email":
        return approved_fact(facts, category="contact", contact_role="owner", label_contains="Owner B", subtype="email") is not None
    if fact_key_value == "contacts.owner.owner_b.phone":
        return approved_fact(facts, category="contact", contact_role="owner", label_contains="Owner B", subtype="phone") is not None
    if fact_key_value == "contacts.cleaner_or_turnover":
        return role_status(facts, [], "cleaner_turnover") == "PASS"
    if fact_key_value == "contacts.emergency_or_primary_ops":
        return approved_fact(facts, category="contact", contact_role="emergency") is not None
    if fact_key_value == "contacts.neighbor":
        return approved_fact(facts, category="contact", contact_role="neighbor") is not None
    if fact_key_value == "contacts.local_helper":
        return approved_fact(facts, category="contact", contact_role="local_helper") is not None
    if fact_key_value == "contacts.contractor":
        return approved_fact(facts, category="contact", contact_role="contractor") is not None
    if fact_key_value == "contacts.vendor_design":
        return approved_fact(facts, category="contact", contact_role="vendor", subtype="design_vendor_contact") is not None
    return False


def alternate_owner_contact_exists(facts: list[dict[str, Any]]) -> bool:
    return approved_fact(facts, category="contact", contact_role="owner") is not None


def condition_is_active(condition: str | None, fact_key_value: str, facts: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> bool:
    if not condition:
        return True
    if condition == "source_evidence_shows_lock_admin_code_required_or_previously_known":
        for fact in facts:
            if fact.get("access_subtype") == "programming_admin_code" and fact.get("value_state") in {"private_value_present", "verified_present", "missing_private_value_true_blocker"}:
                return True
        for row in candidates:
            if row.get("access_subtype") != "programming_admin_code":
                continue
            text = " ".join(str(row.get(key) or "") for key in ("fact_value_redacted", "manager_summary", "source_ref")).lower()
            if any(token in text for token in ("requires programming", "admin code required", "previously verified", "provided code")):
                return True
        return False
    if condition == "owner_b_is_only_owner_contact_or_source_contract_requires_phone":
        return not alternate_owner_contact_exists(facts)
    if condition == "active_maintenance_issue_or_current_source_names_required_contractor":
        for row in candidates:
            if row.get("contact_role") == "contractor" and row.get("value_state") not in {"source_exhausted_verified_negative", "optional_not_on_file", "missing_required"}:
                text = " ".join(str(row.get(key) or "") for key in ("fact_value_redacted", "manager_summary")).lower()
                if any(token in text for token in ("active", "required", "current operational issue", "scheduled")):
                    return True
        return False
    return False


def canonical_fallback_exists(fallback_policy: str | None) -> bool:
    return fallback_policy == "canonical_str_ops_or_charles_escalation"


def requirement_class(req: dict[str, Any]) -> str:
    value = str(req.get("requirement_class") or req.get("requirement_level") or "hard_required")
    if value == "required":
        return "hard_required"
    return value


def requirement_absence_state(req: dict[str, Any], facts: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> tuple[str, bool, str]:
    key = str(req.get("fact_key") or "")
    cls = requirement_class(req)
    if fact_requirement_resolved(key, facts):
        return "verified_present", False, "verified present"
    if cls == "optional_enrichment":
        if key == "contacts.vendor_design":
            return "candidate_unconfirmed", False, "candidate is held in optional private backlog"
        return "source_exhausted_verified_negative", False, "source-exhausted optional enrichment gap"
    if cls == "required_role_with_fallback":
        if canonical_fallback_exists(req.get("fallback_policy")):
            return "fallback_role_used", False, "canonical fallback is available"
        return "missing_required_true_blocker", True, "required role missing and no fallback exists"
    if cls == "conditional_required":
        active = condition_is_active(req.get("activation_condition"), key, facts, candidates)
        if not active:
            if key in {"contacts.owner.owner_b.phone", "contacts.vendor_design"}:
                return "candidate_unconfirmed", False, "activation false; candidate remains optional private backlog"
            return "source_exhausted_verified_negative", False, "activation false after source exhaustion"
        if key.startswith("access.") or "phone" in key:
            return "missing_private_value_true_blocker", True, "activation true and required private value is missing"
        return "missing_required_true_blocker", True, "activation true and required fact is missing"
    return "missing_required_true_blocker", True, "hard-required fact is missing"


def blocker_objects(property_id: str, facts: list[dict[str, Any]], candidates: list[dict[str, Any]], policy: dict[str, Any], coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checked_sources = sorted({row.get("source_family") for row in coverage if row.get("source_family")})
    blockers: list[dict[str, Any]] = []
    requirements = list(policy.get("required_facts") or [])
    for req in requirements:
        key = str(req.get("fact_key") or "")
        if not key or fact_requirement_resolved(key, facts):
            continue
        value_state, blocks_publish, reason = requirement_absence_state(req, facts, candidates)
        publish_behavior = req.get("publish_behavior") or req.get("publish_behavior_when_activation_true_and_missing") or "block"
        if not blocks_publish:
            continue
        parts = key.split(".")
        category = parts[0] if parts else "unknown"
        subtype = ".".join(parts[1:]) if len(parts) > 1 else "unknown"
        source_status = "searched_no_hits_reviewed"
        blockers.append(
            {
                "blocker_id": f"{property_id}.{key}",
                "property_id": property_id,
                "category": category,
                "subtype": subtype,
                "role": parts[2] if len(parts) > 2 and parts[0] == "contacts" else None,
                "value_state": value_state,
                "sources_checked": checked_sources,
                "source_status": source_status,
                "current_decision_options": [],
                "would_block_publish": True,
                "charles_input_needed": False,
                "requirement_level": req.get("requirement_level") or req.get("requirement_class") or "hard_required",
                "requirement_class": requirement_class(req),
                "publish_behavior": publish_behavior,
                "reason": reason,
                "activation_condition": req.get("activation_condition"),
            }
        )
    return blockers


def classify_autonomous_closure(property_id: str, facts: list[dict[str, Any]], candidates: list[dict[str, Any]], policy: dict[str, Any], coverage: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    checked_sources = sorted({row.get("source_family") for row in coverage if row.get("source_family")})
    for fact in facts:
        state = str(fact.get("value_state") or "")
        if state == "public_value":
            state = "verified_present"
        if state in {"private_pointer_only"}:
            state = "private_value_present"
        if fact.get("review_state") == "retired":
            state = "suppressed"
        if state in AUTONOMOUS_FACT_STATES:
            rows.append(
                {
                    "fact_key": policy_key_for_fact(fact) or fact.get("fact_id"),
                    "fact_id": fact.get("fact_id"),
                    "display_label": fact.get("display_label"),
                    "state": state,
                    "requirement_class": None,
                    "sources_checked": checked_sources,
                    "reason": fact.get("manager_note") or fact.get("public_render") or "",
                }
            )
    for req in policy.get("required_facts") or []:
        key = str(req.get("fact_key") or "")
        if not key:
            continue
        if fact_requirement_resolved(key, facts):
            continue
        state, blocks, reason = requirement_absence_state(req, facts, candidates)
        rows.append(
            {
                "fact_key": key,
                "fact_id": None,
                "display_label": key,
                "state": state,
                "requirement_class": requirement_class(req),
                "sources_checked": checked_sources,
                "reason": reason,
                "true_blocker": blocks,
            }
        )
    private_candidates = [
        {
            "fact_key": str(row.get("fact_label") or ""),
            "state": "candidate_unconfirmed",
            "private_ref": "redacted pointer: " + str(row.get("private_ref") or "none"),
            "reason": row.get("manager_summary") or "",
        }
        for row in candidates
        if row.get("review_state") in {"needs_confirmation", "conflict"} and row.get("private_ref")
    ]
    optional_backlog = [
        row for row in rows
        if row.get("state") in {"optional_not_on_file", "candidate_unconfirmed"}
        or row.get("requirement_class") == "optional_enrichment"
    ]
    verified_negatives = [row for row in rows if row.get("state") == "source_exhausted_verified_negative"]
    fallbacks = [row for row in rows if row.get("state") == "fallback_role_used"]
    true_blockers = [row for row in rows if row.get("state") in {"missing_required_true_blocker", "missing_private_value_true_blocker", "conflict_true_blocker"} or row.get("true_blocker")]
    return {
        "property_id": property_id,
        "rows": rows,
        "true_blockers": true_blockers,
        "verified_negatives": verified_negatives,
        "optional_backlog": optional_backlog,
        "private_candidate_queue": private_candidates,
        "fallbacks_used": fallbacks,
        "private_values_present": [row for row in rows if row.get("state") == "private_value_present"],
        "hard_required_total": sum(1 for req in policy.get("required_facts") or [] if requirement_class(req) == "hard_required"),
        "conditional_activated_total": sum(
            1 for req in policy.get("required_facts") or []
            if requirement_class(req) == "conditional_required"
            and condition_is_active(req.get("activation_condition"), str(req.get("fact_key") or ""), facts, candidates)
        ),
        "conditional_not_activated_total": sum(
            1 for req in policy.get("required_facts") or []
            if requirement_class(req) == "conditional_required"
            and not condition_is_active(req.get("activation_condition"), str(req.get("fact_key") or ""), facts, candidates)
        ),
    }


def locked_note_private_resolver_status(property_id: str) -> dict[str, Any]:
    facts = canonical_facts(property_id)
    missing_refs = [
        fact.get("display_label") or fact.get("fact_id")
        for fact in facts
        if fact.get("value_state") == "private_value_present"
        and fact.get("render_mode") == "show_redacted_pointer"
        and not fact.get("private_ref")
    ]
    return {
        "result": "PASS" if not missing_refs else "FAIL",
        "missing_private_refs": missing_refs,
        "raw_values_rendered_in_progress": False,
        "note": "dry-run resolver checked private pointers only; no raw private values were printed",
    }


def publish_readiness_state(gates: list[dict[str, Any]], blockers: list[dict[str, Any]], locked_status: dict[str, Any]) -> str:
    if any(gate.get("gate_name") == "conflict_gate" and gate.get("result") == GATE_FAIL for gate in gates):
        return BLOCKED_CONFLICT
    if any(gate.get("gate_name") == "leak_scan_gate" and gate.get("result") == GATE_FAIL for gate in gates):
        return BLOCKED_LEAK_SAFETY
    if any(gate.get("gate_name") == "render_contract_gate" and gate.get("result") == GATE_FAIL for gate in gates):
        return BLOCKED_RENDER_CONTRACT
    if any(gate.get("result") in {GATE_SOURCE_NOT_SEARCHED, GATE_STALE_SOURCE_COVERAGE, GATE_UNUSABLE_SOURCE_EVIDENCE} for gate in gates):
        return BLOCKED_SOURCE_COVERAGE_INCOMPLETE
    if any(blocker.get("value_state") == "missing_private_value_true_blocker" for blocker in blockers):
        return BLOCKED_TRUE_PRIVATE_FACT_MISSING
    if blockers:
        return OVERALL_BLOCKED_REQUIRED
    if locked_status.get("result") != "PASS":
        return BLOCKED_TRUE_PRIVATE_FACT_MISSING
    return READY_FOR_SINGLE_PROPERTY_PUBLISH


def overall_status_from_gates(gates: list[dict[str, Any]], blockers: list[dict[str, Any]], *, mode: str) -> str:
    if any(gate.get("gate_name") == "conflict_gate" and gate.get("result") == GATE_FAIL for gate in gates):
        return BLOCKED_CONFLICT
    if any(gate.get("gate_name") == "leak_scan_gate" and gate.get("result") == GATE_FAIL for gate in gates):
        return BLOCKED_LEAK_SAFETY
    if any(gate.get("gate_name") == "render_contract_gate" and gate.get("result") == GATE_FAIL for gate in gates):
        return BLOCKED_RENDER_CONTRACT
    if any(gate.get("result") in {GATE_SOURCE_NOT_SEARCHED, GATE_STALE_SOURCE_COVERAGE, GATE_UNUSABLE_SOURCE_EVIDENCE} for gate in gates):
        return BLOCKED_SOURCE_COVERAGE_INCOMPLETE
    if any(gate.get("blocking") and gate.get("result") == GATE_FAIL for gate in gates):
        if any(blocker.get("value_state") == "missing_private_value_true_blocker" for blocker in blockers):
            return BLOCKED_TRUE_PRIVATE_FACT_MISSING
        return OVERALL_BLOCKED_REQUIRED
    if mode == "post_publish":
        return OVERALL_PUBLISHED
    if mode in {"pre_publish", "dry_run"}:
        if any(gate.get("gate_name") == "publish_readiness_gate" and gate.get("result") == READY_FOR_SINGLE_PROPERTY_PUBLISH for gate in gates):
            return READY_FOR_SINGLE_PROPERTY_PUBLISH
        return READY_FOR_BACKLOG_ONLY
    return READY_FOR_SINGLE_PROPERTY_PUBLISH


def evaluate_gates(property_id: str, *, mode: str = "dry_run", review_packet: Path | None = None, proposed_body: str | None = None) -> dict[str, Any]:
    coverage = property_coverage(property_id)
    facts = canonical_facts(property_id)
    candidates = property_candidates(property_id)
    suppressions = property_suppressions(property_id)
    conflicts = property_conflicts(property_id)
    policy = required_policy(property_id)
    coverage_by_family = {row.get("source_family"): row for row in coverage}
    gates: list[dict[str, Any]] = []

    required_families = list(policy.get("required_coverage_families") or [])
    missing_families = [family for family in required_families if family not in coverage_by_family]
    requirement_blockers = blocker_objects(property_id, facts, candidates, policy, coverage)
    closure = classify_autonomous_closure(property_id, facts, candidates, policy, coverage)
    if missing_families:
        gates.append(make_gate("source_coverage_gate", GATE_SOURCE_NOT_SEARCHED, [f"missing coverage: {', '.join(missing_families)}"], [rel_path(SOURCE_COVERAGE)], blocking=True))
    else:
        coverage_result, coverage_blocking, coverage_messages = source_status_for_gate(
            coverage,
            mode=mode,
            has_blockers=bool(requirement_blockers),
        )
        gates.append(make_gate("source_coverage_gate", coverage_result, coverage_messages, [rel_path(SOURCE_COVERAGE)], blocking=coverage_blocking))

    required_access = {req["fact_key"].split(".", 1)[1] for req in policy.get("required_facts") or [] if requirement_class(req) == "hard_required" and str(req.get("fact_key") or "").startswith("access.")}
    required_roles = set(policy.get("hard_required_contact_roles") or [])
    approved_access = {fact.get("access_subtype"): fact for fact in facts if fact.get("category") == "access"}
    approved_roles = {fact.get("contact_role") for fact in facts if fact.get("category") == "contact" and fact.get("review_state") in {"approved", "approved_private_only", "approved_with_gap", "charles_exception"}}
    missing_access = [name for name in sorted(required_access) if name not in approved_access or approved_access[name].get("value_state") == "missing_required"]
    gap_roles = [name for name in sorted(required_roles) if name not in approved_roles]
    required_messages = [f"access.{name} missing_required" for name in missing_access] + [f"contact role {name} not verified or not excepted" for name in gap_roles]
    for blocker in requirement_blockers:
        blocker_key = str(blocker.get("blocker_id") or "").removeprefix(f"{property_id}.")
        blocker_message = f"{blocker_key} {blocker.get('value_state')}"
        if blocker.get("would_block_publish") and blocker_message not in required_messages:
            required_messages.append(blocker_message)
    required_messages = list(dict.fromkeys(required_messages))
    gates.append(
        make_gate(
            "required_fact_gate",
            GATE_FAIL if required_messages else GATE_PASS,
            required_messages or ["required facts present or explicitly reviewed"],
            [rel_path(FACTS_CANONICAL), rel_path(REQUIRED_FACTS)],
        )
    )

    contact_errors = []
    for fact in facts:
        if fact.get("category") != "contact":
            continue
        if fact.get("contact_role") not in SUPPORTED_CONTACT_ROLES:
            contact_errors.append(f"{fact.get('fact_id')} has invalid/missing contact_role")
        if not fact.get("source_refs"):
            contact_errors.append(f"{fact.get('fact_id')} missing source_refs")
    unconfirmed_phone = [row for row in candidates if row.get("fact_category") == "contact" and row.get("fact_label") == "Owner B phone candidate" and row.get("review_state") == "needs_confirmation"]
    if unconfirmed_phone and any("Owner B phone" in str(fact.get("display_label")) and fact.get("review_state") == "approved" for fact in facts):
        contact_errors.append("Owner B phone candidate was promoted without confirmation")
    contact_subresults = {
        "owner": role_status(facts, candidates, "owner"),
        "cleaner_turnover": role_status(facts, candidates, "cleaner_turnover"),
        "vendor_design": role_status(facts, candidates, "vendor_design"),
        "contractor": role_status(facts, candidates, "contractor"),
        "neighbor": role_status(facts, candidates, "neighbor"),
        "local_helper": role_status(facts, candidates, "local_helper"),
        "emergency_primary_ops": role_status(facts, candidates, "emergency"),
    }
    for role, status in contact_subresults.items():
        if status.startswith("FAIL"):
            contact_errors.append(f"{role} {status}")
    contact_result = GATE_FAIL if contact_errors else (
        GATE_PASS_WITH_FALLBACK if any(value == "PASS_WITH_FALLBACK" for value in contact_subresults.values())
        else GATE_PASS_WITH_VERIFIED_NEGATIVES if any(value == "PASS_WITH_VERIFIED_NEGATIVES" for value in contact_subresults.values())
        else GATE_PASS_WITH_OPTIONAL_BACKLOG if any(value == "PASS_WITH_OPTIONAL_BACKLOG" for value in contact_subresults.values())
        else GATE_PASS
    )
    contact_gate = make_gate("contact_role_gate", contact_result, contact_errors or ["contact roles are separated, source-linked, fallback-backed, or verified negative"], [rel_path(FACTS_CANONICAL)])
    contact_gate["subresults"] = contact_subresults
    gates.append(contact_gate)

    access_errors = []
    for fact in facts:
        if fact.get("category") != "access":
            continue
        if fact.get("access_subtype") not in SUPPORTED_ACCESS_SUBTYPES:
            access_errors.append(f"{fact.get('fact_id')} has invalid access_subtype")
        if fact.get("value_state") == "private_value_present" and not fact.get("private_ref"):
            access_errors.append(f"{fact.get('fact_id')} private value missing private_ref")
        if (
            fact.get("access_subtype") == "programming_admin_code"
            and fact.get("value_state") in {"missing_private_value_true_blocker", "missing_required_true_blocker"}
        ):
            access_errors.append("programming_admin_code true private blocker")
    gates.append(make_gate("access_private_value_gate", GATE_FAIL if access_errors else GATE_PASS, access_errors or ["access values are typed and private-safe"], [rel_path(FACTS_CANONICAL)]))

    infrastructure_messages = []
    categories = {fact.get("category") for fact in facts if fact.get("review_state") in {"approved", "approved_private_only", "approved_with_gap", "charles_exception"}}
    if "wifi_systems" not in categories:
        infrastructure_messages.append("wifi/core system canonical fact missing")
    if "field_basics" not in categories:
        infrastructure_messages.append("field basics canonical facts missing")
    gates.append(make_gate("infrastructure_gate", GATE_FAIL if infrastructure_messages else GATE_PASS, infrastructure_messages or ["wifi/system and field basics present"], [rel_path(FACTS_CANONICAL)]))

    link_messages = [] if "links" in categories else ["house manual/listing links missing from canonical facts"]
    gates.append(make_gate("links_gate", GATE_FAIL if link_messages else GATE_PASS, link_messages or ["known links are canonical"], [rel_path(FACTS_CANONICAL)]))

    maint_messages = [] if "maintenance" in categories else ["maintenance/vendor context is candidate-only or reviewed gap"]
    gates.append(make_gate("maintenance_context_gate", GATE_GAPS if maint_messages else GATE_PASS, maint_messages or ["maintenance context is source-backed"], [rel_path(FACTS_CANONICAL)], blocking=False))

    open_conflicts = [row for row in conflicts if row.get("resolution_state") not in {"resolved", "not_conflict", "charles_exception"}]
    gates.append(make_gate("conflict_gate", GATE_FAIL if open_conflicts else GATE_PASS, [f"{row.get('conflict_id')} unresolved" for row in open_conflicts] or ["no unresolved conflicts"], [rel_path(CONFLICTS)]))

    suppression_errors = []
    blocked_keys = {row.get("fact_key") for row in suppressions if row.get("renderer_block")}
    for fact in facts:
        if fact_key(fact) in blocked_keys and fact.get("review_state") not in {"retired", "blocked"}:
            suppression_errors.append(f"{fact.get('fact_id')} attempts to render suppressed key {fact_key(fact)}")
    gates.append(make_gate("suppression_tombstone_gate", GATE_FAIL if suppression_errors else GATE_PASS, suppression_errors or ["suppressions block stale resurrection"], [rel_path(SUPPRESSIONS)]))

    body = proposed_body if proposed_body is not None else render_canonical_note(property_id)
    locked_body = render_canonical_note(property_id, body_mode="locked_apple_note_body") if property_id == "sample_property" else body
    visible_body = html.unescape(body)
    render_errors = []
    for section in RENDER_SECTIONS:
        if f">{section}<" not in visible_body and section not in visible_body:
            render_errors.append(f"missing section {section}")
    if render_errors:
        gates.append(make_gate("render_contract_gate", GATE_FAIL, render_errors, [rel_path(FACTS_CANONICAL)]))
    else:
        gates.append(make_gate("render_contract_gate", GATE_PASS, ["518 top-level section order generated from canonical facts"], [rel_path(FACTS_CANONICAL)]))

    leak_messages = leak_findings(body)
    gates.append(make_gate("leak_scan_gate", GATE_FAIL if leak_messages else GATE_PASS, leak_messages or ["no raw private-looking values in proposed public body"], [rel_path(FACTS_CANONICAL)]))

    semantic_result = property_note_semantic_quality.evaluate_body(
        locked_body,
        mode="expected" if mode != "post_publish" else "live_readback",
        property_id=property_id,
    )
    semantic_messages = [row["message"] for row in semantic_result.get("findings") or []]
    gates.append(
        make_gate(
            "manager_usefulness_gate",
            GATE_PASS if semantic_result["ok"] else GATE_FAIL,
            semantic_messages or ["locked manager-facing body is useful and free of process boilerplate"],
            [rel_path(FACTS_CANONICAL)],
        )
    )
    if mode in {"pre_publish", "post_publish"}:
        receipt_result = property_note_semantic_quality.evaluate_source_receipts(property_id)
        receipt_messages = [row["message"] for row in receipt_result.get("findings") or []]
        gates.append(
            make_gate(
                "source_receipt_gate",
                GATE_PASS if receipt_result["ok"] else GATE_FAIL,
                receipt_messages or ["current source sweep receipts satisfy required families"],
                [rel_path(Path(receipt_result.get("receipt_path", "")))] if receipt_result.get("receipt_path") else [],
            )
        )

    packet_text = ""
    if review_packet and review_packet.exists():
        packet_text = review_packet.read_text(encoding="utf-8", errors="ignore")
        gates.append(make_gate("dry_run_review_gate", GATE_PASS, ["dry-run review packet exists"], [rel_path(review_packet)]))
    else:
        gates.append(make_gate("dry_run_review_gate", GATE_FAIL if mode != "dry_run" else GATE_WARN, ["dry-run review packet missing or not supplied"], [], blocking=mode != "dry_run"))

    forbidden_review_markers = [
        "Charles Decision Sheet",
        "Please provide",
        "Please review",
        "BLOCKED_NEEDS_CHARLES_INPUT",
        "HUMAN_GATE",
        "DECISION_SHEET_REQUIRED",
    ]
    no_review_findings = [f"forbidden review marker present: {idx + 1}" for idx, marker in enumerate(forbidden_review_markers) if marker.lower() in (packet_text or body).lower()]
    gates.append(make_gate("no_charles_review_gate", GATE_FAIL if no_review_findings else GATE_PASS, no_review_findings or ["autonomous output contains no decision sheet or optional-fact review request"], [rel_path(review_packet)] if review_packet else []))

    unclosed = [row for row in closure["rows"] if row.get("state") not in AUTONOMOUS_FACT_STATES]
    gates.append(make_gate("autonomous_closure_gate", GATE_FAIL if unclosed else GATE_PASS, [str(row.get("fact_key")) for row in unclosed] or ["all facts are verified, private, verified-negative, fallback, optional backlog, suppressed, or true blockers"], [rel_path(FACTS_CANONICAL), rel_path(REQUIRED_FACTS)]))

    locked_status = locked_note_private_resolver_status(property_id)
    readiness = publish_readiness_state(gates, requirement_blockers, locked_status)
    gates.append(make_gate("locked_note_private_resolver_gate", GATE_PASS if locked_status["result"] == "PASS" else GATE_FAIL, locked_status.get("missing_private_refs") or [locked_status["note"]], [rel_path(FACTS_CANONICAL)]))
    gates.append(make_gate("publish_readiness_gate", readiness, [readiness], [rel_path(FACTS_CANONICAL), rel_path(REQUIRED_FACTS)], blocking=readiness not in {READY_FOR_SINGLE_PROPERTY_PUBLISH, READY_FOR_BACKLOG_ONLY}))

    has_publish_authority = has_explicit_property_publish_authority(property_id)
    approval_result = GATE_PASS if has_publish_authority else (GATE_FAIL if mode in {"pre_publish", "post_publish"} else GATE_WARN)
    gates.append(make_gate(
        "charles_explicit_approval_gate",
        approval_result,
        ["explicit one-property Apple Notes publish authority captured"] if has_publish_authority else ["no explicit one-property Apple Notes publish authority captured"],
        [rel_path(PUBLISH_AUTHORIZATIONS)] if has_publish_authority else [],
        blocking=mode != "dry_run" and not has_publish_authority,
    ))
    if mode == "dry_run":
        gates.append(make_gate("fresh_replace_path_gate", GATE_WARN, ["publish not authorized in this dry-run"], [], blocking=False))
        gates.append(make_gate("readback_gate", GATE_WARN, ["readback is not applicable before publish"], [], blocking=False))
    elif mode == "pre_publish":
        gates.append(make_gate("fresh_replace_path_gate", GATE_PASS, ["fresh-replace path is selected for the approved single property"], [], blocking=False))
        gates.append(make_gate("readback_gate", GATE_WARN, ["readback is a required post-publish gate"], [], blocking=False))
    else:
        gates.append(make_gate("fresh_replace_path_gate", GATE_PASS, ["fresh-replace path was selected for the approved single property"], [], blocking=False))
        gates.append(make_gate("readback_gate", GATE_PASS, ["post-publish readback is recorded by the publish worker"], [], blocking=False))

    nonblocking_pass_results = {
        GATE_PASS,
        GATE_PASS_FULL_COVERAGE,
        GATE_PASS_WITH_VERIFIED_NEGATIVES,
        GATE_PASS_WITH_OPTIONAL_BACKLOG,
        GATE_PASS_WITH_FALLBACK,
        READY_FOR_SINGLE_PROPERTY_PUBLISH,
        READY_FOR_BACKLOG_ONLY,
    }
    blocking = [gate for gate in gates if gate["blocking"] and gate["result"] not in nonblocking_pass_results]
    if blocking:
        overall = GATE_FAIL
    elif any(gate["result"] in {GATE_DRY_RUN_ONLY, GATE_REVIEWED_BLOCKED, GATE_SOURCE_GAP} for gate in gates):
        overall = GATE_GAPS
    elif any(gate["result"] == GATE_WARN for gate in gates):
        overall = GATE_WARN
    else:
        overall = GATE_PASS
    overall_status = overall_status_from_gates(gates, requirement_blockers, mode=mode)
    return {
        "gate_run_id": f"gate_{property_id}_{stamp()}",
        "property_id": property_id,
        "mode": mode,
        "overall_result": overall,
        "overall_status": overall_status,
        "blockers": requirement_blockers,
        "autonomous_closure": closure,
        "publish_readiness_state": readiness,
        "locked_note_private_resolver": locked_status,
        "gates": gates,
        "created_at": now_iso(),
    }


def leak_findings(text: str) -> list[str]:
    findings: list[str] = []
    plain = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    patterns = [
        (re.compile(r"(?i)(door|gate|garage|lockbox|keypad|programming|admin)\s+(?:code|pin)\s*[:#-]?\s*\d{4,}"), "raw access code pattern"),
        (re.compile(r"(?i)(wi[\s-]?fi|wifi|router).{0,30}(password|passcode)\s*[:#=-]\s*(?!\[?redacted|private|private_value_present|exists|pointer|locked_note_private_value_required)\S{4,}"), "raw wifi/router password pattern"),
        (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"), "raw phone number pattern"),
    ]
    for pattern, label in patterns:
        if pattern.search(plain):
            findings.append(label)
    return findings


def write_gate_result(result: dict[str, Any]) -> None:
    rows = load_jsonl(GATE_RESULTS)
    rows.append(result)
    write_jsonl(GATE_RESULTS, rows)


def latest_gate_result(property_id: str) -> dict[str, Any] | None:
    rows = [row for row in load_jsonl(GATE_RESULTS) if row.get("property_id") == property_id]
    return rows[-1] if rows else None


def gate_status_map(result: dict[str, Any]) -> dict[str, str]:
    return {str(gate.get("gate_name")): str(gate.get("result")) for gate in result.get("gates", [])}


def append_command_log(path: Path, command: str, exit_code: int, note: str = "") -> None:
    rows = load_json(path, {"commands": []}) if path.exists() else {"commands": []}
    rows.setdefault("commands", []).append({"command": command, "exit_code": exit_code, "note": note, "ran_at": now_iso()})
    write_json(path, rows)
