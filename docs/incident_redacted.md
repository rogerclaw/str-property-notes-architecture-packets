# Sample Property Failed Publish Incident

incident_state: INVALID_CLOSEOUT_DEVICE_VISIBLE_FAILURE
property_id: sample_property
created_at: 2026-07-02T13:51:40Z
bad_closeout: ops/progress/sample_property_publish_closeout_20260702.md
bad_live_title: "Sample Property Dossier"
bad_live_note_id: x-coredata://REDACTED_NOTE_ID
bad_live_body_private_backup: data/private/redacted/property_info_note_backups/sample_property_failed_publish_bad_live_backup_20260702_135125.json
archived_pre_failed_publish_note_id: x-coredata://REDACTED_NOTE_ID
archived_pre_failed_publish_folder: STR Property Information Review
active_sample_property_note_count_before_repair: 1
no_other_properties_authorized: true

## Reason

- Device-visible note is not manager useful.
- Dry-run/process text was published.
- Source/progress path noise was published.
- False no-publish language appeared in the published note.
- Visible link/HTML serialization was reported by Charles and related link-surface checks were insufficient.
- Generic placeholder evidence rows reached the polished note.
- Negative unknown rows reached the polished note.
- Live-source sweep was not proven at the time of the invalid closeout.

## Superseded Closeout

`ops/progress/sample_property_publish_closeout_20260702.md` is superseded by this incident. Its final state `PUBLISHED_VERIFIED_SAMPLE_PROPERTY` must not be reused for this phase.

## Rollback Safety

Before mutation, the active sample-property note body was backed up privately at the path above. The failed fresh-replace archived note was identified in `STR Property Information Review`; if the V2 repair cannot produce and verify a useful active note, restore or quarantine Sample Property under the fresh-replace rollback policy and stop at an allowed failure state.

## Safety

No email, email draft, iMessage, SMS, Telegram visible send, guest message, owner message, booking, refund, spend, dispatch, reminder, calendar, credential, billing, or other external action occurred while creating this incident artifact.

Raw access values, Wi-Fi passwords, private phone numbers, private emails, and raw private source bodies are not repeated in this artifact.
