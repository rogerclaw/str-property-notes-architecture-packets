# Audit Brief

## Background

A Property Information Apple Note was previously reported as published and
verified, but the device-visible note was not useful to a property manager. It
contained dry-run/process language, source-path noise, visible markup, generic
placeholders, and unknown-negative rows.

The repair changed the acceptance standard: a publish is not complete unless
the live Apple Notes readback body itself passes semantic/usefulness checks.

A follow-up regression showed that this is still not enough if the note reads
like a validator, audit packet, evidence receipt, or process transcript. The
private live note must preserve source-backed operational facts and be useful as
an onsite field note. Redaction applies to public artifacts, not to the private
Apple Note.

## Final State

The repaired run reached:

`PUBLISHED_USEFUL_SAMPLE_PROPERTY_V2_DEVICE_VERIFIED`

The live readback materially matched the expected locked-note body, the
device-visible semantic/usefulness gate passed, source receipt checks passed,
backend sync passed, and focused regression tests passed.

## Architecture Claims To Review

- Private and public products are split explicitly:
  `build_private_operations_note(...)` is the private Apple Note product and
  `build_public_audit_artifact(...)` is the shareable audit/log product.
- The private-note contract has only operations sections: Access & Codes,
  Wi-Fi / Systems, Contacts, Other Property Contacts, Needs Confirmation, Field
  Basics, Current / Upcoming Stays, Operations Notes, Business Snapshot, and
  Refresh / Source Coverage.
- The private semantic gate rejects audit/process/source/gate wording, source
  paths, generic filler, public redaction placeholders in required private
  fields, and MISSING/not found/candidate language outside Needs Confirmation.
- Fact slots use explicit resolution states:
  `resolved_verified`, `private_value_present`, `unresolved_conflict`,
  `missing_after_full_sweep`, `candidate_unconfirmed`, and `not_applicable`.
- Fact-slot checks enforce owner conflict handling, missing phone placement,
  admin/programming code separation from guest code, candidate contact labels,
  and cleaner-vs-owner role separation.
- The fresh-replace packet model blocks duplicate active notes, requires exact
  title plus property marker/address/name matching, archive proof, old-id
  retirement, live readback, private readback semantic validation, and public
  redaction validation.
- Public closeout/progress/GitHub artifacts may contain source/gate/process
  language but must not contain raw private codes, passwords, phones, emails, or
  source bodies.

## Suggested ChatGPT Audit Questions

1. Are the two builder functions separated strongly enough, or can public audit
   rows still be passed into the private Apple Note path?
2. Are the private semantic forbidden-token checks too brittle, too broad, or
   easy to bypass?
3. Does the positive section contract prove onsite usefulness, or only token
   presence?
4. Are fact-slot states sufficient for owner email conflicts, missing phones,
   admin/programming access codes, candidate contacts, and cleaner/owner
   separation?
5. Does the fresh-replace model cover duplicate-note, archive-proof,
   old-id-active, partial-publish, and readback risks?
6. Are public redaction gates sufficient for progress artifacts and GitHub
   packets?
7. What tests should be added before rolling this to more properties?
8. What positive structure should prove the live note is actually useful to an
   onsite property manager?
