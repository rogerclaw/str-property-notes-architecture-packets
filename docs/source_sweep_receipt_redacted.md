# Sample Property Live Source Sweep Receipts

Generated: 2026-07-02T13:59:17Z
Property: sample_property
External actions: none
Raw private values: not repeated

## apple_notes_current
- adapter: Notes JXA active-folder readback
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 1 of 1
- latest source timestamp: Wed Jul 01 2026 21:35:22 GMT-0700 (Pacific Daylight Time)
- candidate fact categories found: active_note, access, contacts, links
- promoted canonical facts: active_note.rollback_context
- unresolved gaps/backlog items: none
- notes: Active note was read directly before repair; raw body is private.

## apple_notes_historical
- adapter: Notes JXA review-folder inventory plus private backups
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 16 of 16
- latest source timestamp: Wed Jul 01 2026 21:35:22 GMT-0700 (Pacific Daylight Time)
- candidate fact categories found: historical_notes, rollback
- promoted canonical facts: archived_bad_note.rollback_path
- unresolved gaps/backlog items: none
- notes: Archived/replaced notes are available for rollback comparison.

## backend_private
- adapter: local backend/private JSON stores
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 7 of 7
- latest source timestamp: 2026-07-02T13:54:16.925153+00:00
- candidate fact categories found: access, contacts, wifi_systems, field_basics, links
- promoted canonical facts: access.guest_door_code, wifi.network, wifi.password, contacts.owner, contacts.cleaner, field.address, field.trash
- unresolved gaps/backlog items: programming_admin_code.backend_only_gap
- notes: Private values stay in private stores or locked note only.

## cc_email
- adapter: gog gmail messages search OWNER_MAILBOX_EXAMPLE_INVALID
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 50 of 50
- latest source timestamp: 2026-07-01 17:25
- candidate fact categories found: owner_email, permit, maintenance, vendor
- promoted canonical facts: contacts.owner, permit.ehs, maintenance.access_hardware
- unresolved gaps/backlog items: owner_b_phone.candidate_private_backlog
- notes: Read-only Gmail metadata/body search; no send/draft/write action.

## charles_work_email
- adapter: gog auth/account inventory
- status: auth_unavailable
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 0 of 0
- latest source timestamp: unknown
- candidate fact categories found: none
- promoted canonical facts: none
- unresolved gaps/backlog items: charles_work_email.auth_unavailable
- notes: No authenticated Charles work-email account is available to this worker.
- adapter error: available gog accounts: [REDACTED_EMAIL], [REDACTED_EMAIL]

## strops_email
- adapter: gog gmail messages search STROPS_MAILBOX_EXAMPLE_INVALID
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 50 of 50
- latest source timestamp: 2026-07-01 07:03
- candidate fact categories found: field_brief, hospitable_notification
- promoted canonical facts: message_activity.summary
- unresolved gaps/backlog items: none
- notes: Read-only Strops mailbox search; no send/draft/write action.

## personal_message_bridge
- adapter: SQLite message bridge metadata scan
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 5 of 5
- latest source timestamp: unknown
- candidate fact categories found: cleaner_messages, owner_messages, operations
- promoted canonical facts: contacts.cleaner, cleaner_activity.summary
- unresolved gaps/backlog items: non_property_specific_cleaner_thread_context
- notes: Searched bridge records by sample property tags; raw message bodies not copied.

## hospitable_api
- adapter: Hospitable API reservations/reviews with local cache fallback
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 120 of 120
- latest source timestamp: 2026-07-02T07:08:15.112Z
- candidate fact categories found: property, reservations, current_stay, upcoming_stays, occupancy_money, reviews, guest_threads
- promoted canonical facts: stays.current, stays.upcoming, metrics.ytd, metrics.trailing_year, reviews.signal
- unresolved gaps/backlog items: none
- notes: Live API returned reservations/reviews when available; local cache has 28 sample-property rows.

## hospitable_webhooks
- adapter: local webhook/log artifact search
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 19 of 19
- latest source timestamp: unknown
- candidate fact categories found: guest_messages, notifications
- promoted canonical facts: guest_message_activity.summary
- unresolved gaps/backlog items: none
- notes: Webhook/log artifacts checked by filename/source family; raw payload bodies not copied.

## airbnb_listing_reviews
- adapter: backend listing/cache/browser artifacts
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 177 of 177
- latest source timestamp: unknown
- candidate fact categories found: listing, reviews
- promoted canonical facts: links.airbnb, reviews.signal
- unresolved gaps/backlog items: none
- notes: Listing/review signal comes from authorized backend/Hospitable/local listing artifacts.

## house_manual_docs_permits
- adapter: house manual/private facts/Canva/permit artifacts
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 107 of 107
- latest source timestamp: unknown
- candidate fact categories found: house_manual, wifi_systems, trash, permit, links
- promoted canonical facts: wifi.network, wifi.password, field.trash, links.house_manual, permit.ehs
- unresolved gaps/backlog items: none
- notes: House manual, Canva, permit, and EHS/Home-Sharing artifacts checked; raw passwords stay private.

## maintenance_repair_artifacts
- adapter: local maintenance/order/invoice artifact search
- status: hits_found
- aliases searched: 123 Example, 123 Example St, Example St, Sample Property, sample_property, Owner A, Owner B, Cleaner A, Cleaner Co, ISP
- hits inspected: 200 of 239
- latest source timestamp: unknown
- candidate fact categories found: maintenance, access_hardware, vendor_candidate
- promoted canonical facts: maintenance.access_hardware
- unresolved gaps/backlog items: vendor_design.optional_backlog
- notes: Repair/order/invoice artifacts checked for durable manager facts.

No email, email draft, iMessage, SMS, guest message, owner message, booking, refund, spend, dispatch, reminder, calendar, credential, billing, or external action occurred.
