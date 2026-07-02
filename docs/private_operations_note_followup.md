# Private Operations Note Follow-Up

## Regression

The repaired live Apple Note still failed the real user need: it looked like a
validator/process/audit artifact instead of the useful deluxe dossier structure
Charles expected from the successful 518 Vernon note.

This follow-up resets the architecture target. A successful publish must
produce a private live note that is useful to Charles, a cleaner, or a helper
standing at the property, using the 518-style deluxe dossier shape rather than
a narrow validator-safe shape.

## Boundary

The live Apple Note is private. It may include source-backed operational facts
such as:

- access codes and lock details
- Wi-Fi network and password
- owner, cleaner, helper, vendor, and emergency contact details
- current and upcoming stay context
- field basics and onsite checks

Public artifacts are different. GitHub packets, closeouts, run logs, and audit
docs must remain redacted and must not expose raw private values.

## Live Note Must Not Contain

- failed-publish language
- validation or validator language
- source receipt language
- execute report language
- backend sync language
- local cache language
- private row/backend row commentary
- source-path or progress-path noise
- invoice/evidence-supports-context filler
- generic owner snapshot filler
- unknown-negative rows dressed up as content
- dry-run, gate, execute report, backend sync, local cache, ops/progress, or
  private/backend row commentary

## Target Private Note Structure

The private Apple Note target is:

- `[Property Address / Property Name] - Deluxe Dossier`
- Access & Codes
- Contacts
- Wi-Fi / Systems
- Field Basics
- Links
- Evidence / Refresh Notes

Evidence / Refresh Notes should contain:

- Occupancy & Money
- Current / Upcoming Stays
- Owner & Message Activity
- Charles Visit Stats
- Difficulty Ranking
- Airbnb / Review Signal
- Recent Notable Events
- Active Ops Watchlist
- Management Notes
- Source / Refresh Notes

The Evidence / Refresh Notes section is allowed in the private note when it is
field-useful manager context. It is not allowed to become a process log,
validator report, or public audit artifact.

## Required Pre-Publish Source Tasks

The source sweep must resolve or explicitly mark these Venice-only facts:

- exact source-backed owner email when candidate emails conflict
- Silvia phone number, or a short missing-fact line if not found
- lock admin/programming code, distinct from the guest/front-door code
- verified Venice-specific neighbor, local-helper, contractor, vendor, design,
  building, or emergency contacts
- candidate contacts with clear `CANDIDATE` labels and source context
- Johanna / Sunrise as cleaner/turnover, not owner
- separate guest door code, admin/programming code, and Wi-Fi facts

## Acceptance Test Shape

The final live readback should be checked against a small forbidden-phrase list
and a positive field-note contract:

- top sections are Access & Codes, Contacts, Wi-Fi / Systems, Field Basics,
  Links, and Evidence / Refresh Notes
- evidence subsections match the 518-style list above
- access, Wi-Fi, owner, cleaner, and stay facts appear as usable facts, not as
  evidence commentary
- missing or candidate facts appear only in manager/source refresh notes until
  confirmed
- exactly one active property note exists after publish
- prior bad notes are archived
- no other property is changed
