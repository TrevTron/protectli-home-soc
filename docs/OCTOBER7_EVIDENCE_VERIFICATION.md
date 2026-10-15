# Verify the October 7 studies without running a model

The [reviewed export](../october7-evidence/PUBLIC_EXPORT_MANIFEST.json) contains every input, response and per-request runtime observation for 72 larger-budget CPU requests and 168 fresh constructed investigation requests. It also includes all 24 written-answer assessments, synthetic source records/oracles, original batch job schedules and the frozen evaluation dependency closures.

```powershell
py -3.12 tools/verify_october7_evidence.py --root october7-evidence
```

The verifier uses no network, Vault, model service or weights. It verifies public file membership/hashes, reconstructs CPU prompts and fresh jobs, checks both output channels, natural stops, actual settings/token counts, full input traces, CPU/GPU digest/VRAM observations and idle release. It independently rechecks synthetic source totals, grades investigator answers and supplementary review checklists, and recomputes 18/18 evidence-alone and 17/18 for each assisted condition. It verifies written-review output bindings and citation scans; prose grades remain agent judgments, not independently certified human scores.

## Exact sources and declared derivatives

Requests, responses, case sources, briefs, oracles and frozen code are exact source bytes. Local user/project/program path prefixes are replaced in runtime/model metadata. Each file has original and public hashes and byte counts in the manifest. Recomputed context proof must match all original fields except the trace's intentionally changed byte count/hash. Original private traces remain untouched. An original hash attestation does not make an omitted original publicly verifiable.

The raw CPU briefs are already normalized and aliased; they do not include the underlying live syslog or alias key. Those briefs support exact prompt replay but do not independently prove their private real-source provenance. Fresh JSONL uses documentation-only addresses and authored synthetic records, which are included and independently checked.

Human assignments, participant answers/timing, private process-owner records, configuration XML, packet captures and live raw syslog are excluded. The original case seal retains a private human-assignment hash; the public verifier does not claim to verify that omitted assignment. The continuation driver hardcodes private paths and is omitted; its hash stays in the original continuation seal. The portable verifier reconstructs and checks all measured jobs without executing that driver. Public hashes detect changes against this package, not independent signing or protection against replacing the manifest too.

## Metadata and failures to keep

The original batch protocol's requested-options section describes legacy base settings. The pre-request seal, role-options files and every actual request record the overridden 16 threads, 8,192 context, 2,048 output tokens and GPU path. They are deliberately not rewritten into a cleaner-looking protocol. An immutable progress-write interruption occurred after batch 2; only the never-requested third batch continued, with no completed request retried.

Earlier CPU outcomes still say semantic review pending. The separately bound `cpu/content-review/` assessment supersedes that review status without editing outcomes. Both one-character citation failures and the reviewer misses remain included. [CPU results](RESOURCE_RETEST_RESULTS_2026-10-07.md) and [fresh investigation results](FRESH_INVESTIGATION_RESULTS_2026-10-07.md) explain the conclusions and limits.

This is a complete saved-request export for these two studies, not a universal replay package for a different model/hardware stack, proof of resource root cause or an independent human investigation study.
