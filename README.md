# STR Property Notes Architecture Audit Packet

This repository is a sanitized audit packet for the STR Property Information
Apple Notes architecture repair completed on 2026-07-02.

The packet is intentionally redacted:

- The real property address and property id are replaced with a sample property.
- Private access codes, Wi-Fi passwords, phone numbers, emails, note body
  contents, source bodies, and backend private values are excluded.
- Local paths are retained only when useful for architecture review and are
  redacted where they point at private stores.

## What To Audit

Please audit whether this architecture is sufficient to prevent a useless
Apple Note from being published as "verified" again.

Focus areas:

1. Device-visible validation: the semantic gate must run against the live Apple
   Notes readback body, not only generated HTML or local metadata.
2. Manager usefulness: section headings alone should not pass if the body is
   dry-run/process prose, generic filler, source-policy commentary, or
   unknown-negative rows.
3. Source receipts: required source families should be explicitly searched or
   have an exact unavailable/auth error recorded.
4. Redaction boundaries: progress/closeout artifacts must not repeat raw
   access codes, Wi-Fi passwords, private phones, private emails, or source
   bodies.
5. Publish safety: fresh-replace should archive/rollback safely and verify a
   single active property note after publish.
6. Regression tests: tests should cover process-boilerplate, visible HTML,
   source paths, negative unknown rows, generic filler, and closeout truth.
7. Private-note boundary: the live Apple Note is a private operations note, so
   redaction must not strip access, Wi-Fi, contact, or operational facts from
   the live note. Redaction belongs only in public logs, GitHub packets, and
   closeouts.
8. Onsite usability: the live note must read like a property-manager field note
   for someone standing at the property, not like a validator, audit report,
   evidence receipt, or process transcript.

## Contents

- `docs/audit_brief.md` - narrative summary and audit prompts.
- `docs/chatgpt_audit_prompt.md` - copy-paste prompt for an external ChatGPT audit.
- `docs/private_operations_note_followup.md` - follow-up requirements from the
  live-note regression.
- `docs/incident_redacted.md` - redacted incident artifact.
- `docs/closeout_redacted.md` - redacted completion evidence.
- `docs/source_sweep_receipt_redacted.md` - redacted source receipt.
- `code/property_note_semantic_quality.py` - semantic/usefulness gate.
- `code/validate_property_note_semantic_quality.py` - CLI wrapper.
- `code/build_sample_property_live_source_sweep.py` - redacted source-sweep builder.
- `code/fresh_replace_property_information_note.py` - publish/readback safety path.
- `code/str_property_fact_registry.py` - redacted fact registry/render gates.
- `tests/test_property_note_semantic_quality.py` - focused semantic gate tests.

## Known Caveats

- This is a packet, not a runnable checkout of the full private workspace.
- Some imports reference private workspace modules that are not included.
- The full global validator still had unrelated non-sample-property failures;
  the property-scoped validation for this repair passed.
