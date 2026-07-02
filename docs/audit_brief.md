# Audit Brief

## Background

A Property Information Apple Note was previously reported as published and
verified, but the device-visible note was not useful to a property manager. It
contained dry-run/process language, source-path noise, visible markup, generic
placeholders, and unknown-negative rows.

The repair changed the acceptance standard: a publish is not complete unless
the live Apple Notes readback body itself passes semantic/usefulness checks.

## Final State

The repaired run reached:

`PUBLISHED_USEFUL_SAMPLE_PROPERTY_V2_DEVICE_VERIFIED`

The live readback materially matched the expected locked-note body, the
device-visible semantic/usefulness gate passed, source receipt checks passed,
backend sync passed, and focused regression tests passed.

## Architecture Claims To Review

- The semantic gate fails on process/dry-run text, visible HTML link markup,
  internal paths, unknown-negative polished rows, and generic filler.
- The source receipt gate requires each source family to be searched or to
  record an exact unavailable/auth error.
- The publisher performs a live readback and runs semantic checks on that
  readback before success can be claimed.
- Redacted closeout/progress artifacts avoid raw private operational values.
- Unknown optional contacts belong in backend/workbench gaps, not polished
  Apple Note rows.

## Suggested ChatGPT Audit Questions

1. Where could generated review/dry-run text still reach the locked Apple Note?
2. Are the semantic forbidden-token checks too brittle, too broad, or easy to
   bypass?
3. Does the usefulness density check prove useful content or only token
   presence?
4. Is source-family coverage meaningfully verified, or can stale/local evidence
   masquerade as a fresh source sweep?
5. Does the fresh-replace path leave any duplicate-note, rollback, or partial
   publish risks?
6. Are redaction gates sufficient for public progress artifacts?
7. What tests should be added before rolling this to more properties?
