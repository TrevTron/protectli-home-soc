The first implementation results below are historical. The current [operator workflow](OPERATOR_WORKFLOW.md) and [equal development/new-case study](MODEL_REFINEMENT_RESULTS.md) record the next completed local phase. No external release occurred.

# Protectli local analyst evidence, October 5, 2026

This records the bounded local expansion. No external message, repository push, website change, deployment or publication occurred. The original firewall-build receipts remain separate.

## Research and host decision

The actual [Marauder Reddit feedback](https://www.reddit.com/r/ESP32Marauder/comments/1wcnth3/i_built_a_local_capture_analyst_for_my_marauder/) recommends deterministic measured facts and explicit observed/inferred/unknown claims with source references. The [GPX hardening PR](https://github.com/TrevTron/marauder-analyst/pull/1) and [CI PR](https://github.com/TrevTron/marauder-analyst/pull/2) address parser and workflow safety separately. The original free-prose/selected-regex checker was inspected, not copied or modified.

Concrete community requests include [explaining blocks across sensors](https://www.reddit.com/r/opnsense/comments/1fwwwxf/does_anyone_have_a_method_of_proper_logging_and/) and [SSD/backup recovery](https://www.reddit.com/r/opnsense/comments/1vacso9/my_opnsense_os_drive_just_died/). Existing [TriageWall](https://github.com/aaronphifer/triagewall), [agentic-soc-triage](https://github.com/FabulaNox/agentic-soc-triage) and [pfELK](https://github.com/pfelk/pfelk) show that local triage and broader log aggregation already exist. These are examples of demand and design work, not a market-size measurement. No third-party implementation was imported.

The chosen first host is the Minisforum with a separate CPU-only 4B runtime. X1S and Nova were offline in the actual local Tailscale status; Pi was online but its inference capacity and pinned SSH identity were not inspected. X1S remains a possible dedicated host after restoration/testing. Pi and Nova are unmeasured alternatives, not benchmark conclusions.

The existing model runtime and its metadata remained unchanged. No invocation, unload, restart, fine-tuning file access/edit or user/system environment change was performed. A separate project-private Ollama 0.35.1 process uses loopback port 11435. The official qwen3:4b-instruct Q4_K_M digest is `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`, 2,497,293,803 bytes on disk. Runner logs establish CPU execution, two threads and cloud disabled; loaded-model metadata shows 3,184,001,022 bytes and zero VRAM.

## Actual evaluation

Four synthetic cases were frozen before their answers. Each received one free-form and one structured request using the same supplied facts and model/settings, with intentionally different presentation prompts. Eight requests stopped normally. This is a semantic/delivery comparison, not a matched runtime contest.

| Original case | Structured delivery | Actual issue/review |
|---|---|---|
| Cold-start unknown rule | Accepted | Unknown novelty and intent retained |
| Reported block | Withheld | One invented/mistyped evidence reference |
| Decreasing STUN count | Withheld | Selected new/increased context despite decrease |
| UID fixture | Accepted | Conditional fixture context, exact fields and unknowns |

The free-form answers preserved many counts and caveats, but the block and UID answers called received alert counts connection counts. The UID answer also turned not-proof-of-intrusion into a stronger negative conclusion. Some answers confused incomplete log delivery with unproven traffic delivery. Actual outputs and the agent's semantic review are retained, including those disagreements.

The group-bound schema revision then ran six cases: the two error regressions and four new cases (mixed priority, empty owned-client window, high-severity cold start, future/invalid source records). All six stopped normally, passed the independent validator and included their frozen useful-code targets. Reading the actual outputs found repeated caution/citation text and limited interpretation coverage in the mixed case. Rendered duplicates are collapsed; saved model answers are unchanged.

Baseline eight-run request durations were 31.203 to 46.843 seconds; minimum sampled Windows available memory was 30.424 GiB. Revised six-run durations were 8.250 to 51.750 seconds; minimum sampled available memory was 31.704 GiB. Different prompts and answer lengths prevent a speed-winner claim. The small set does not establish a general hallucination rate or model accuracy.

## Live and operational proof

The first real snapshot counted 12 STUN alerts against 16 in the prior window, selected possible NAT traversal and retained unknown intent/visibility. It completed in 42.828 seconds with 544 actual generated tokens. Source links opened original hash-checked records in Brave; Pacific timestamps were visibly correct without rewriting originals.

A fresh source-bound UID fixture returned HTTP 200/39 bytes, with one exact SID 2100498/allowed raw receipt. The flow review found no exact pre-NAT PF receipt in that bounded snapshot. It correctly reported the missing evidence instead of inferring a PF decision. Cross-layer pass/block behavior is covered by synthetic exact-tuple tests, not claimed as a new live block demonstration.

The first periodic tick completed in 44.078 seconds, second in 42.656 seconds, third in 42.375 seconds, all exit 0. The second and third delivered UID-fixture possibility with matching references and required unknowns. The original monitor used loopback 8766, 12 runs/300-second cadence, with the base receiver separate. It was deliberately stopped after the third tick to prevent overlapping candidate evaluation. The replacement viewer was view-only during evaluation. After the comparison, the bounded monitor resumed the bounded 12-run/300-second monitor at 16:04 PDT. The first two resumed ticks accepted empty-window reports in 9.000 and 9.188 seconds. Empty alert groups are not an all-clear. The actual Brave page displayed the active monitor banner, retained-record coverage, mandatory unknowns and Pacific timestamps. This verifies bounded periodic operation, not reboot persistence or 24/7 reliability.

After deployment the Vault reported all four cores at 37 C, the same Netmap engine, healthy pools and an unchanged configuration fingerprint. The existing backup still matches. The 180-second thermal peak of 62 C belongs to the earlier workload, not this analyst run. New model work runs on the Minisforum, not the firewall.

The latest local source has 38 meaningful ingestion/grounding/viewer/flow/delivery checks passing, including explicit evaluation-only model admission with protected-model refusal. Start/stop ownership, source-hash failure, malformed/capped/unavailable output, cold-start coverage, clipped history and priority floors are checked separately from actual model correctness. The maximum-group v3 test selected 16 of 17 groups, retained the blocked priority floor and displayed one omitted group. It stopped normally in 90.25 seconds, 661 generated/2280 prompt tokens, passed the independent validator and selected the block, STUN, UID and Tailscale possibilities. This is a synthetic regression, not a live attack or general accuracy result.

The SID 2071648 flow was investigated directly on Windows. At the saved observation time its complete TCP address/port tuple matched an active connection owned by tailscaled.exe, with the process parent matching the running Tailscale service PID. Connection creation time matched the alert second; process creation preceded it. The installed service binary had a valid Tailscale Inc. signature. This is positive local context for this specific flow, not an automatic benign verdict or proof that every Tailscale-related alert has that origin. The hash-validated historical receipt now appears in an actual browser investigation card outside the model. Its Pacific observation time and explicit attribution limits were verified visually; the earlier failed render and its correction remain retained. The browser's actual PF/Suricata investigation page was also clicked and saved; the fresh UID fixture had an EVE receipt and no exact pre-NAT PF receipt in the bounded snapshot.

## Current community-informed comparison

Trevor requested current community evidence before selecting a larger candidate. [The dated research note](MODEL_COMMUNITY_RESEARCH.md) supersedes the initial Qwen2.5 7B choice. Qwen3.5 4B/9B and Gemma 4 12B QAT were evaluated alongside the existing Qwen3 4B. The frozen protocol precedes all answers, using three known regression briefs and the same explicit prompt/schema/request bounds, one run each. Different templates, tokenizers, quantization/defaults and natural output lengths are disclosed. No general accuracy, pure model-size or throughput winner claim is justified. All 12 requests are complete. [The exact comparison results](MODEL_COMPARISON_RESULTS.md) record baseline delivery 3/3 and each researched candidate 1/3, with missing unknowns and timeouts withheld. All accepted/rejected responses and errors remain private; actual synthetic comparison responses are also included in the reviewed candidate. The bounded default remains Qwen3 4B for this contract and host. Minimum sampled available memory was 26.979 GiB; all loaded-model samples reported zero VRAM and runner logs establish two CPU threads.

Operational instructions are in [AI_ANALYST_GUIDE.md](AI_ANALYST_GUIDE.md). UDP loss/authentication, finite report/retention windows, explicit finite launch, unmeasured alternate hosts, generally absent endpoint-process/payload evidence (except the specifically registered historical receipt) and semantic limits remain unresolved properties of this reference pipeline. Optional future work is longer health observation, an operator-reviewed baseline and wider sensor adapters; it is not represented as completed here.

Post-comparison native check found all four Vault cores at 40 C, the same Netmap engine, healthy pools and unchanged backup-matching configuration hash. Direct Vault DNS returned two example.com IPv4 records; source-bound HTTPS returned 200 with certificate verification success. Final runtime, raw-prefix and original-evidence preservation receipts remain private. The 40 C observation is bounded health evidence, not a sustained thermal test.
