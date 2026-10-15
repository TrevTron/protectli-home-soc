# Larger CPU resource budget: delivery and content results

Complete reviewed inputs, outputs, synthetic sources and runtime evidence for the October 7 studies are now in [the offline verification export](OCTOBER7_EVIDENCE_VERIFICATION.md). Original private evidence remains unchanged; path redactions and omitted human material are declared.

The separate October 7 retest completed all 72 requests naturally: twelve structured tasks and six written tasks for each of four installed models. These are exposed tasks from the earlier study, not new accuracy holdouts. Every original result remains preserved. No production model was substituted.

The common profile requested 16 CPU threads, an 8,192-token context and a 2,048-token answer allowance, with temperature zero, seed 17, thinking disabled and cold keepalive zero. The structured deadline was 300 seconds; the written deadline was 600 seconds. Exact request reconstruction, canonical brief hashes, both output channels, runtime input traces, installed model digests, CPU observations with zero VRAM allocation, and idle release were independently rechecked for all 72 outcomes. Each input reached the runtime intact.

| Installed artifact | Structured delivery / 12 | Strict structured utility / 12 | Written delivery / 6 | Written answers materially rejected / 6 |
| --- | ---: | ---: | ---: | ---: |
| Qwen3 4B Instruct | 12 | 2 | 6 | 4 |
| Qwen3.5 4B | 12 | 5 | 6 | 5 |
| Qwen3.5 9B | 12 | 3 | 6 | 3 |
| Gemma4 12B IT QAT | 12 | 9 | 6 | 3 |

Strict structured utility checks required context, list length, duplicate inferences/citations, next review and review-first attention, in addition to the existing fact contract. The larger Gemma artifact met more of those checks in this retest. This is a workload-specific result, not a general intelligence ranking.

All 24 written answers were read individually beside the exact submitted input and assessed under the unchanged October 5 rubric. The five separate dimensions are facts/citations, supplied context, priorities, uncertainty and read-only next review. A material false fact, invalid citation or unsupported verdict rejects an answer regardless of its other strengths. These are agent assessments, not independent human grades. Answers without an individual rejection still have recorded weaknesses and are not certified correct.

Examples explain why natural completion is insufficient. Three models miscounted supplied dense groups. A Qwen3.5 4B block report changed counts, assigned STUN traffic to Tailscale and described unknown processes as safe. The 9B dense edge report mistyped an evidence reference; another 9B answer called signature IDs session IDs. Gemma inferred internal topology from anonymous endpoint aliases and misstated destinations in its blocked case. Some other answers used connections or packets where the input contained alert records, or asked an EVE reference for payload/process data it does not contain.

The larger answer allowance resolves the observed completion problem for these six written tasks. It does not repair those factual or interpretive errors. Compared with the earlier two-thread, 4,096-context, 700-output study, threads, context, output allowance and deadlines changed together. This comparison cannot assign the improvement to any one of them.

The separate development check changed only CPU threads on the same dense Qwen3.5 9B task. At 2, 8 and 16 threads it completed in 183.094, 125.563 and 88.765 seconds, generating 906, 963 and 918 tokens. Different natural output lengths and text prevent a fixed-output throughput claim. Periodic SOC work and maintenance also ran on the host during the comparison.

The admitted live dashboard remains Qwen3.5 4B in constrained structured mode on its owned Vulkan runtime. The larger CPU retest is a separate resource experiment; its settings are not silently applied to historical studies or to scheduled reporting. The protected model environment was not restarted or used for inference.

Source-bound reviews and 72-request verification are private under `private/resource-retention-20261007/cpu-semantic-review-01/`. The original protocol, requests, responses and runtime traces remain in `comparison-cpu-01/`. Earlier outcomes still say semantic review pending because measured receipts are immutable; this separate assessment supersedes that review status. No weights were trained, downloaded or changed.

See also [fresh investigations](FRESH_INVESTIGATION_RESULTS_2026-10-07.md), [live rolling retention](LIVE_ROLLING_RETENTION_2026-10-07.md) and [the earlier model study](MODEL_COMPARISON_EXPANDED_RESULTS.md).
