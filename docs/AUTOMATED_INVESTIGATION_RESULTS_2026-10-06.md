# Automated investigation regression results

October 6, 2026. All 56 scheduled requests and outcomes are retained. This is a historical exposed-case automated evaluation with zero human participants. It is separate from the original 416 CPU model outcomes and does not establish unseen-case accuracy or human investigation usefulness.

The analyst and investigator used the same installed Qwen3.5 4B digest. The reviewer used the distinct installed Qwen3.5 9B digest. All used the isolated Vulkan runtime, common options, 4096 context, thinking off, a 700-token ceiling, one request at a time, keepalive zero and a 120-second deadline. The saved randomized schedule used seed 61006. No request was retried or repaired. Actual runtime logs identify Radeon 8060S, and every request's retained runtime observations show its expected model digest and GPU memory use. The GPU shares system memory.

| Role or condition | Scheduled | Result |
| --- | ---: | --- |
| Constrained analyst | 8 | Eight returned reports passed the existing source-bound report validator |
| Investigator A, deterministic context without selected analyst assistance | 6 measured | Zero passed the full decision/evidence checklist |
| Investigator B, same context plus validated analyst assistance | 6 measured | Zero passed |
| Investigator C, same facts plus assistance and reversible repetition encoding | 6 measured | Zero passed |
| Practice investigators | 6 | All returned; none passed, excluded from the measured denominator |
| Different-model reviewer | 24 | Every response generated 700 tokens, stopped at the length cap and was withheld |

Delivery is distinct from correctness. All 24 investigator responses returned normally and were parseable. The independent deterministic oracle rejected all of them. Validated analyst reports did not make this broader decision contract reliable.

## What the answers got wrong

The root review read all 18 measured answers beside the original oracles. M01 and M06 repeated `no_alerts_in_supplied_records` while also listing the three real alert groups correctly. M06 did not select the required missing-collection-context decision. M02 correctly copied the blocked event but still claimed no supplied alerts; its assisted answer also omitted the explicit reported-block decision. These are substantive contradictions, not just formatting defects.

M03 and M04 had no alert groups. Their answers invented two zero-count groups with fabricated IDs/SIDs. Assisted versions labeled those invented groups blocked and selected block context without evidence. M05's evidence-only answer preserved all four groups and their counts but made the same no-alerts claim. Both assisted versions omitted the third repeated allowed group. Repetition encoding did not establish better correctness or reduced human effort.

The grader records duplicate decision and next-check codes as contract failures. Where a list contains duplicates it stops further checking that field; its cached missing/unsupported lists therefore do not enumerate every semantic contradiction in those rows. The full raw answers and this manual review retain those contradictions. They remain failures without changing the grader or original scores after seeing the answers.

All measured answers kept client outcome unknown, intrusion unestablished and complete delivery unproven. Those were correct uncertainty boundaries. That partial success does not repair the observation and decision failures.

The 9B review is a failed delivery experiment under this fixed generation budget. All partial prose is retained as withheld diagnostics. One diagnostic criticized `complete_delivery_proven: false` and `client_outcome: unknown` despite evidence supporting those uncertainty boundaries. No completed review, reviewer agreement rate or independent semantic endorsement is claimed. The evidence oracle owns the scores.

## What this changes

Keep the operational analyst constrained to its existing validated explanation-selection contract. Do not deploy the new investigator or model-reviewer decisions in the live dashboard. Code continues to own alert counts, sensor actions, priorities, source links and permitted context. The model cannot activate suppression or firewall changes.

Future development could clarify this separate decision prompt and constrain it to the actual evidence, then freeze a new protocol and test new controlled cases. This run stays unchanged. It does not prove that every model is unsuitable, that GPU changes correctness, or that human reviewers would fail these cases. The next checks were selected, not executed; no actual uncertainty resolution or usability improvement was demonstrated.

## Reproducibility

The [protocol](AUTOMATED_INVESTIGATION_EVALUATION_2026-10-06.md) describes case construction and A/B/C context. The candidate's [public evidence subset](../investigation-evidence/PUBLIC_SUBSET_PROVENANCE.json) contains exact selected requests, raw API responses, outcomes, per-request GPU observations and deterministic oracles. Original private source records, source mappings and complete ownership/runtime logs are excluded and declared. Private construction independently rechecks raw record bytes and counts; that part needs the private pack and is not claimed as portable from the public subset.

Wrong answers and capped reviews remain visible. No headline accuracy, speed winner, time saving, stronger firewall protection or human-usability claim follows from this evaluation.
