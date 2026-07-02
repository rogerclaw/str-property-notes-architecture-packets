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

1. Product separation: `build_private_operations_note(...)` /
   `build_private_deluxe_dossier_note(...)` builds the private live Apple Note
   shape, while `build_public_audit_artifact(...)` builds a shareable audit/log
   artifact.
2. Device-visible validation: the private semantic gate must run against the
   live Apple Notes readback body, not only generated HTML or local metadata.
3. Manager usefulness: section headings alone should not pass if the private
   body is dry-run/process prose, generic filler, source-policy commentary, or
   unknown-negative rows.
4. Private-note contract: the private Apple Note target is the 518 Vernon-style
   deluxe dossier, not a stripped validator-safe shape. The required top
   sections are `Access & Codes`, `Contacts`, `Wi-Fi / Systems`,
   `Field Basics`, `Links`, and `Evidence / Refresh Notes`; the evidence
   section must include `Occupancy & Money`, `Current / Upcoming Stays`,
   `Owner & Message Activity`, `Charles Visit Stats`, `Difficulty Ranking`,
   `Airbnb / Review Signal`, `Recent Notable Events`,
   `Active Ops Watchlist`, `Management Notes`, and `Source / Refresh Notes`.
5. Fact-slot resolution: source outcomes are explicit states
   `resolved_verified`, `private_value_present`, `unresolved_conflict`,
   `missing_after_full_sweep`, `candidate_unconfirmed`, and `not_applicable`.
6. Redaction boundaries: public progress/closeout/GitHub artifacts may discuss
   process, gates, source coverage, and conflicts, but must not repeat raw
   access codes, Wi-Fi passwords, private phones, private emails, or source
   bodies.
7. Publish safety: fresh-replace must precheck duplicate active notes by exact
   title plus property marker/address/name, prove archive creation, prove the
   old id is no longer active, require live readback, run the private semantic
   gate on readback, and run the public redaction gate on closeout.
8. Regression tests: tests cover a positive sanitized 518-style deluxe dossier
   fixture, audit-shape rejection, source/process rows, generic filler,
   confirmation placement, candidate labeling, owner conflict, access-code
   separation, redaction placeholders, public redaction, duplicate blocking,
   archive proof, and live readback.

## Contents

- `docs/audit_brief.md` - narrative summary and audit prompts.
- `docs/chatgpt_audit_prompt.md` - copy-paste prompt for an external ChatGPT audit.
- `docs/private_operations_note_followup.md` - follow-up requirements from the
  live-note regression.
- `docs/incident_redacted.md` - redacted incident artifact.
- `docs/closeout_redacted.md` - redacted completion evidence.
- `docs/source_sweep_receipt_redacted.md` - redacted source receipt.
- `code/property_note_semantic_quality.py` - private semantic/usefulness gate
  and public redaction gate.
- `code/validate_property_note_semantic_quality.py` - CLI wrapper.
- `code/build_sample_property_live_source_sweep.py` - redacted source-sweep builder.
- `code/fresh_replace_property_information_note.py` - sanitized
  fresh-replace/readback safety model; no live mutation.
- `code/str_property_fact_registry.py` - redacted fact-slot registry plus
  separate private/public builders.
- `tests/test_property_note_semantic_quality.py` - focused semantic gate tests.

## Known Caveats

- This is a packet, not a runnable checkout of the full private workspace.
- Some imports reference private workspace modules that are not included.
- The full global validator still had unrelated non-sample-property failures;
  the property-scoped validation for this repair passed.
