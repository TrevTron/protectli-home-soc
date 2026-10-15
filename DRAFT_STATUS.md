# Additional private-repository security review, October 14, 2026

Read [the additional security review](docs/SECURITY_REVIEW_2026-10-14.md). The private repository now rejects empty/noncanonical/wildcard receiver bind values before storage or sockets, including direct callers, and pins CI actions to verified full upstream commits. Three added regressions bring the local suite to 270 passing tests. The full final-commit hosted result remains a separate check.

Independent Bandit, Semgrep, TruffleHog and detect-secrets scans and synthetic detector controls are recorded with their findings and limits. No unresolved real credential was identified in the reviewed match set. Legacy research caveats and the trusted `sysctl` search path remain documented. This does not certify the project as vulnerability-free.

The running collector and canonical private operating tools were not modified or restarted. Its current UDP listener was checked and was not a wildcard. Deploying the updated receiver requires a coordinated owner/recovery update, so do not blindly copy the repository file into that running installation. Historical experiments and sealed V13 remain unchanged. The repository stays private, and the second analyst article and later raw export remain unfinished.

# Private GitHub review repository, October 14, 2026

This repository is now staged privately at https://github.com/TrevTron/protectli-home-soc. Public release remains pending. It starts from the sealed V13 review package, with only repository-status wording and its manifest updated for this private upload. Original experiment exports, operating code, failures and license terms are unchanged.

The first build article has been submitted for partner review. The second analyst article remains in development. The later targeted-check/LoRA work still has a summary only here and needs its own reviewed raw-evidence export; uploading this repository does not close that gap.

Before upload, all 267 software tests passed locally, both the October 7 and 219-request AI-follow-up evidence verifiers passed, and all 7,457 initial Git blobs matched the sealed V13 package. Hosted CI status must be checked separately. No Vault or model was contacted by these checks. Raw operational logs, configuration backups, credentials and private correspondence are excluded.

The V13 ZIP remains unchanged: SHA256 `312c76878f7ba85df59f434c23459800db246c4af23a8486d364d9742ea64363`. The earlier dated candidate entries below describe their packaging state at that time.

# V13 local review candidate, October 14, 2026

V13 carries the verified receiver-owner/sign-in recovery repair in two PowerShell launch/recovery scripts. See [the repair and verification](docs/RECOVERY_OWNER_REPAIR_2026-10-14.md). All operating Python code, experiment exports, original model responses, evaluation tools and evidence manifests are byte-identical to V12. No historical result was rewritten. Full Python suite results remain historical; this repair has isolated launcher/refusal tests, PowerShell parsing and actual scheduled recovery checks.

The internal partner email remains excluded, public attribution remains intentional, and private originals stay outside the package. The earlier [privacy review](docs/PRIVACY_REVIEW_2026-10-14.md) describes the V12 baseline; V13's narrow changes were checked separately. The first article is prepared for partner review; the analyst article remains in development for further improvements. Neither article nor this repository is published by this packaging step.

The fixed 48-hour release clause remains dropped. Existing quickstart, rolling-v2 retention, MIT code and separately attributed media terms are unchanged. The later targeted-check/LoRA full raw export remains outstanding. No publication, push or partner message was sent.
