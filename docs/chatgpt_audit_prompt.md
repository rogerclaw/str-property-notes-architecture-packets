# ChatGPT Audit Prompt

Please audit this public GitHub packet:

https://github.com/rogerclaw/str-property-notes-architecture-packets

Context: this is a sanitized architecture packet for an STR Property
Information Apple Notes publishing system. The real live Apple Note is private
and may contain access codes, Wi-Fi passwords, phone numbers, emails, and other
operational facts. The public GitHub packet is intentionally redacted.

The system has already failed in two ways:

1. It previously claimed a publish was verified even though the live
   device-visible note contained dry-run/process/source-path noise.
2. A later repair over-corrected toward validation and audit language, producing
   a note that still was not useful as an onsite property-manager operations
   note.

Audit goal: determine whether the architecture and tests are now sufficient to
ensure the private live Apple Note follows the useful 518 Vernon-style deluxe
dossier structure while public logs and GitHub artifacts remain redacted.

Please focus on these questions:

1. Is the split between `build_private_operations_note(...)` and
   `build_public_audit_artifact(...)` strong enough, or can public audit rows
   still leak into the private Apple Note path?
2. Does the private semantic gate prove onsite usefulness, or only absence of
   known bad phrases?
3. Does the required private-note section contract target the deluxe dossier
   shape: Access & Codes, Contacts, Wi-Fi / Systems, Field Basics, Links, and
   Evidence / Refresh Notes with Occupancy & Money, Current / Upcoming Stays,
   Owner & Message Activity, Charles Visit Stats, Difficulty Ranking,
   Airbnb / Review Signal, Recent Notable Events, Active Ops Watchlist,
   Management Notes, and Source / Refresh Notes?
4. Are the fact-slot resolution states strong enough for conflicting owner
   emails, missing phone numbers, admin/programming lock codes, candidate
   contacts, and cleaner-vs-owner separation?
5. What tests should be added so a note shaped like an audit report cannot pass,
   while a useful 518-style Evidence / Refresh Notes section does pass?
6. Does the fresh-replace/readback model adequately prove exactly one active
   note exists, prior bad notes are archived, the old id is gone, and readback
   was checked?
7. Are public redaction checks strong enough to reject raw private codes,
   Wi-Fi passwords, phones, emails, and source bodies?
8. What risks remain before rolling this pattern to other properties?

Please return findings in priority order with concrete references to files and
functions where possible. Recommend specific tests or code changes, but do not
ask for or include private access codes, passwords, phone numbers, emails, or
live property data.
