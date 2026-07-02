---
property_id: sample_property
property_title: "Sample Property Dossier"
run_id: str-property-fact-system-architecture-repair-20260702
final_state: PUBLISHED_USEFUL_SAMPLE_PROPERTY_V2_DEVICE_VERIFIED
redaction_scope: no raw access codes, Wi-Fi passwords, private phones, private emails, or source bodies repeated
external_actions: none
---

# Sample Property Failed Publish Repair Closeout V2

## Result

Final state: `PUBLISHED_USEFUL_SAMPLE_PROPERTY_V2_DEVICE_VERIFIED`.

The invalid device-visible Sample Property note was repaired with a sample-property-only
fresh-replace publish. The current active Apple Note is:

- Folder: `STR Property Information`
- Title: `Sample Property Dossier`
- Active note id: `x-coredata://REDACTED_NOTE_ID`
- Active sample-property note count after repair: `1`

The failed-publish live note was preserved before mutation and then removed
from the active folder through the fresh-replace archive flow:

- Private bad-live-body backup:
  `data/private/redacted/property_info_note_backups/sample_property_failed_publish_bad_live_backup_20260702_135125.json`
- Pre-repair failed note id:
  `x-coredata://REDACTED_NOTE_ID`
- Failed note archived as:
  `STR Property Information Review / ARCHIVED 20260702_140335_100687 - Sample Property Dossier`
- Failed note archive id:
  `x-coredata://REDACTED_NOTE_ID`
- Intermediate parser-repair note archived as id:
  `x-coredata://REDACTED_NOTE_ID`

## Evidence

- Incident artifact:
  `ops/progress/sample_property_failed_publish_incident_20260702.md`
- Live source sweep receipt:
  `ops/progress/sample_property_live_source_sweep_receipts_20260702.md`
- Live source sweep receipt JSON:
  `ops/progress/sample_property_live_source_sweep_receipts_20260702.json`
- Execute report:
  `ops/progress/sample_property_fresh_replace_property_info_execute_20260702_140453_327861.json`
- Live readback report:
  `ops/progress/sample_property_live_readback_report_v2_20260702.json`
- Property-scoped validation report:
  `ops/progress/sample_property_property_scoped_validation_v2_20260702.json`
- Backend sync report:
  `ops/progress/sample_property_backend_sync_v2_20260702_1405.json`
- Post-publish gate report:
  `ops/progress/sample_property_property_info_gate_results_20260702_140547.json`
- sample-property-only usability validator:
  `ops/progress/sample_property_usability_validator_v2_20260702_1405.json`
- Typed backend validator:
  `ops/progress/sample_property_typed_backend_validator_v2_20260702_1405.json`
- Global contract validator, retained for transparency:
  `ops/progress/sample_property_contract_validator_v2_20260702_1405.json`

## Gate Summary

- Fresh-replace execute: `PASS`, exit `0`.
- Exact live readback material match against expected locked-note body: `PASS`.
- Device-visible semantic/usefulness gate on live Apple Notes body: `PASS`.
- Source receipt gate: `PASS`.
- Post-publish gate suite: `PASS`.
- Leak/redaction scans on public progress reports: `PASS`.
- Backend sync/rebuild: `PASS`.
- sample-property-only usability validator: `PASS`.
- Typed backend validator: `PASS` with unrelated warning-only Firmona rows.
- Global contract validator: `FAIL` from pre-existing unrelated STR Issue
  Archive and non-sample-property legacy dossier issues; sample property-scoped
  validation passed.

## Source Family Coverage

The sample-property-only source sweep covered all required families. Statuses:

- `apple_notes_current`: `hits_found`
- `apple_notes_historical`: `hits_found`
- `backend_private`: `hits_found`
- `cc_email`: `hits_found`
- `charles_work_email`: `auth_unavailable` with available-account inventory
  recorded; this did not block because other live source families supported the
  note.
- `strops_email`: `hits_found`
- `personal_message_bridge`: `hits_found`
- `hospitable_api`: `hits_found`
- `hospitable_webhooks`: `hits_found`
- `airbnb_listing_reviews`: `hits_found`
- `house_manual_docs_permits`: `hits_found`
- `maintenance_repair_artifacts`: `hits_found`

## Commands And Exit Codes

- `python3 scripts/build_sample_property_live_source_sweep.py` -> `0`
- `python3 scripts/ingest_property_fact_candidates.py --property-id sample_property --all-approved-source-families --write` -> `0`
- `python3 scripts/promote_property_fact_candidates.py --property-id sample_property --write` -> `0`
- `python3 scripts/validate_property_note_semantic_quality.py --property-id sample_property --mode source_receipt --receipt-json ops/progress/sample_property_live_source_sweep_receipts_20260702.json` -> `0`
- `python3 scripts/validate_property_info_publish_gates.py --property-id sample_property --pre-publish --autonomous-closure --review-packet ops/progress/sample_property_autonomous_source_closure_v3_20260702.md` -> `0`
- `python3 scripts/fresh_replace_property_information_note.py --property-id sample_property --execute --approved-by-charles` -> first repair mutation archived the bad note but exited `1` because the newly added live-readback parser was too strict for Apple Notes HTML; parser was repaired and sample-property-only semantic readback passed.
- `python3 scripts/fresh_replace_property_information_note.py --property-id sample_property --execute --approved-by-charles` -> `0`
- `python3 scripts/sync_str_property_notes_backend.py` -> `0`
- `python3 scripts/validate_property_info_publish_gates.py --property-id sample_property --post-publish --autonomous-closure --review-packet ops/progress/sample_property_autonomous_source_closure_v3_20260702.md` -> `0`
- `python3 scripts/validate_str_property_notes_contract.py` -> `1`, unrelated global failures; see property-scoped validation report.
- `python3 scripts/validate_str_property_notes_usability.py --dossiers data/private/redacted/property_info_note_backups/sample_property_property_dossier_subset_20260702.json` -> `0`
- `python3 scripts/validate_str_property_backend_typed_fields.py` -> `0`
- `python3 -m unittest tests.test_property_note_semantic_quality -v` -> `0`
- `python3 -m unittest tests.test_property_fact_registry_schemas tests.test_property_source_coverage_gate tests.test_property_required_fact_gate tests.test_property_contact_role_gate tests.test_property_access_private_value_gate tests.test_property_conflict_suppression_gate tests.test_property_renderer_canonical_strict_mode tests.test_property_publish_gate_refuses_without_charles tests.test_property_autonomous_closure_gate tests.test_property_no_charles_review_gate tests.test_property_conditional_required_activation tests.test_property_programming_admin_code_activation tests.test_property_owner_b_phone_candidate_does_not_block tests.test_property_emergency_ops_fallback tests.test_property_optional_contact_verified_negative tests.test_property_locked_note_private_resolver -v` -> `0`
- `python3 -m unittest tests.test_property_notes_review_validators -v` -> `0`
- `python3 -m py_compile scripts/strops_long_build.py scripts/fresh_replace_property_information_note.py scripts/lib/property_note_semantic_quality.py scripts/validate_property_note_semantic_quality.py scripts/build_sample_property_live_source_sweep.py scripts/lib/str_property_fact_registry.py scripts/ingest_property_fact_candidates.py scripts/promote_property_fact_candidates.py` -> `0`

## Files Changed

- `scripts/lib/property_note_semantic_quality.py`
- `scripts/validate_property_note_semantic_quality.py`
- `scripts/build_sample_property_live_source_sweep.py`
- `scripts/lib/str_property_fact_registry.py`
- `scripts/ingest_property_fact_candidates.py`
- `scripts/promote_property_fact_candidates.py`
- `scripts/fresh_replace_property_information_note.py`
- `scripts/strops_long_build.py`
- `tests/test_property_note_semantic_quality.py`
- `data/str_property_backend/fact_registry/property_source_coverage.jsonl`
- `data/str_property_backend/fact_registry/property_fact_candidates.jsonl`
- `data/str_property_backend/fact_registry/property_facts_canonical.json`
- `ops/progress/sample_property_failed_publish_incident_20260702.md`
- `ops/progress/sample_property_publish_closeout_20260702.md`
- `ops/progress/sample_property_live_source_sweep_receipts_20260702.md`
- `ops/progress/sample_property_live_source_sweep_receipts_20260702.json`
- `ops/progress/sample_property_property_scoped_validation_v2_20260702.json`
- `ops/progress/sample_property_publish_closeout_v2_20260702.md`
- `loops/str-ops-loop/RUN_LOG.md`
- `loops/str-ops-loop/RESULTS.md`
- `ops/progress/ACTIVE.md`
- `ops/progress/long_builds/str-property-fact-system-architecture-repair-20260702.json`

Private backup and expected/readback body files were also written under
`data/private/redacted/property_info_note_backups/`.

## Not Changed

- No property other than Sample Property was published or intentionally mutated.
- No email, email draft, iMessage, SMS, Telegram visible send, guest message,
  owner message, cleaner message, contractor message, booking, refund, spend,
  dispatch, reminder, calendar, credential, billing, or other external action
  occurred.
- Raw access codes, Wi-Fi passwords, private phones, private emails, and raw
  private source bodies are not repeated in this progress/closeout artifact.
