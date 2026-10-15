# Scoped release-package privacy review, October 14, 2026

This review covers the local V12 candidate and its matching ZIP, including text in runtime files named `.bin`, JSON/JSONL, scripts, documentation, filenames and the two bundled JPEG screenshots. It does not certify an accessible GitHub repository or Git history: both the public URL and authenticated repository lookup returned 404 during review, and this source directory has no Git history to inspect.

## Changes

An internal unsent partner message is excluded from V12. Three planning documents now refer to the partner generically instead of naming recipients or linking the private message. Public author identity, project links and license attribution remain deliberately included. V11 and private originals are preserved separately.

## Checks

Local Gitleaks 8.30.1, with its default rules, decoding and archive inspection enabled, was paired with a separate pattern scan for credentials, private keys, account/home paths, email, telephone, government/financial identifiers, network addresses, MAC addresses, Wi-Fi names, tailnet hostnames and location fields. Synthetic positive controls checked that the detectors report planted examples. No private source files were uploaded to a scanning service.

Two Gitleaks matches were reviewed as false positives: a SHA256 executable checksum and ordinary wording about tokenizers. Credential-pattern matches were an authorization note in saved launch scripts and a deliberately invalid URL in a negative test. Address-shaped runtime timing prefixes were distinguished from actual addresses by their log-line context. Actual address matches were documentation examples, loopback addresses and the unspecified bind address; IPv6 matches were local or documentation examples.

The two screenshots were inspected visually. No visible personal identifiers or credentials were found, both lacked EXIF fields, and one retained a standard color profile. The screenshots are flattened JPEGs. Original live logs, configuration exports, participant answers and machine credentials remain outside the candidate.

The archive is checked for member hashes, exact candidate membership and CRC integrity. Public evidence manifests and their offline verifiers are checked after packaging. The test results retained from V11 are historical results; a privacy-only packaging pass is not a new software or model experiment.

## Limits

No sensitive personal identifiers or real credentials were detected within this scoped package review. This is not a guarantee that every possible identifier format or encoded secret can be detected, nor a claim that public author attribution is absent. GitHub branches, tags, history, issues, releases and separately uploaded files remain outside the inspected scope. Publication still requires its separate approval and freshness checks.
