# Redaction Notes

This packet intentionally replaces live property identifiers with sample values.

Examples:

- Real property id -> `sample_property`
- Real property title -> `Sample Property Dossier`
- Real address -> `123 Example St, Sample City, ST 00000`
- Real owner/cleaner/vendor names -> `Owner A`, `Owner B`, `Cleaner A`,
  `Cleaner Co`, `ISP`
- Real mailbox/account names -> `OWNER_MAILBOX_EXAMPLE_INVALID` and
  `STROPS_MAILBOX_EXAMPLE_INVALID`
- Apple Notes internal IDs -> `x-coredata://REDACTED_NOTE_ID`
- Private backend paths -> `data/private/redacted/...`

The packet should be treated as public-review safe. If any reviewer sees a raw
secret, raw private contact, or live customer/property value, that is a packet
sanitization bug.
