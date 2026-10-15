# Additional security and privacy review

This review covers the private repository's tracked files and Git history. It adds independent scanners to the earlier Gitleaks, identifier-pattern, archive/hash and screenshot checks. Results are bounded automated checks with source review, not a penetration test or security certification.

## Issues corrected

**Receiver bind validation:** the original CLI rejected the literal unspecified address but accepted an empty string and noncanonical forms. A direct caller of `run()` also bypassed the CLI check. The receiver now validates a literal, specific unicast IPv4 address before opening storage or creating a socket, including when called directly. Empty values, hostname/abbreviated forms, unspecified addresses, multicast and limited broadcast are rejected. Regression tests exercise the CLI and direct-call boundaries. Existing valid loopback/LAN behavior remains covered by the receiver integration tests.

**CI supply-chain hardening:** `actions/checkout` and `actions/setup-python` now reference verified full upstream commit SHAs instead of movable major-version tags. The workflow retains read-only repository permissions and does not persist checkout credentials.

These changes apply to this repository. The running collector was inspected and was using a specific address rather than a wildcard. It was not restarted or modified during this review; original operational evidence remains untouched. Deploying the new receiver into that installation requires the normal coordinated ownership/recovery procedure.

## Additional tools

| Tool | Scope and result |
| --- | --- |
| Bandit 1.9.4 | Scanned all 165 tracked Python files, including tests and frozen research sources, with inline suppressions ignored. The post-fix full scan reports 276 findings: 259 low, 17 medium and none high. The active tools/tests account for 33. The added rejection/subprocess tests themselves add scanner matches. Findings are retained rather than hidden by broad suppressions. |
| Semgrep OSS 1.181.0 | Ran the Python and GitHub Actions rules, 162 rules across all 165 Python files plus the workflow. The initial two mutable-action findings were corrected. The remaining subprocess warning is reviewed below. Metrics were disabled and no cloud token was used. |
| TruffleHog 3.99.2 | Scanned full main-branch Git history with credential verification and update checks disabled. Its one match was the deliberately invalid basic-auth URL in the endpoint-rejection test, not a real credential. The downloaded executable's archive matched the official release checksum. |
| detect-secrets 1.5.0 | Scanned tracked files with network verification disabled and inline-allowlist filtering disabled. All 28,089 initial matches were classified against their source context: 28,044 declared/verified hashes, 43 local completion identifiers, one excluded-runtime license filename and the same synthetic negative URL. No unresolved credential finding remained in that reviewed set. |

Synthetic controls outside the repository confirmed that Bandit detected an unsafe shell-call example and both additional secret scanners detected synthetic AWS credential patterns. No control code was executed and no potential credential was sent to a provider for validation. A positive control demonstrates that a detection path operates, not exhaustive detection recall.

All 270 software tests passed locally after the receiver fix and three added regression tests. Hosted CI is recorded separately for the final commit.

## Warning review

SQLite's flagged string construction uses code-defined field/condition names and bound values for log content, client filters and group identifiers. An additional regression test supplies SQL metacharacters and verifies that the table and original source remain intact.

The Semgrep warning concerns the offline verifier invoking its own fixed Python script with an argument list, without a shell. Its user-selected data directory is passed as a separate argument. No command-injection path was identified in that call; applying shell quoting would not be an appropriate fix for an argv list.

Other Bandit findings include explicit subprocess APIs/imports, deterministic randomization of test order, fixed-loopback HTTP calls in tests and historical research downloads. The all-interface string in negative tests is intentionally rejected input. Legacy research assertions and broad observation-error handling remain visible as limitations of those frozen sources. The appliance's bounded-check helper still relies on a trusted executable search path for `sysctl`; this is a remaining hardening opportunity, not a demonstrated remote exploit. These contextual reviews are not a claim that every potential misuse is impossible.

## Coverage boundaries

The application has no declared third-party Python dependency manifest, and the active tool imports use the standard library/local modules. This review does not claim a dependency-vulnerability audit of Windows, Python, OPNsense, Suricata, Ollama, model files or the scanners' own environment.

Semgrep reported two partial-parsing warnings where Bash-oriented Actions rules encountered the explicitly PowerShell script block. Python and applicable YAML rules still ran. The broader scan skipped 30 data files larger than its default 1 MB limit; all tracked Python files and the workflow were included. Separate secret/privacy scans cover the evidence exports. PowerShell syntax checks and hosted tests are separate checks, not a complete PowerShell security analysis.

Both bundled screenshots were visually rechecked; no sensitive identifier was observed, and prior metadata checks found no EXIF fields. OCR was not performed. Intentional author/copyright credit, public rule identifiers, timestamps and experiment hashes remain in the repository. No scanner can prove the absence of all sensitive information or vulnerabilities.

Detailed findings and control fixtures are private audit material and are not included in this repository. The repository remains private pending publication review. Historical experiment bytes and sealed review packages are preserved.
