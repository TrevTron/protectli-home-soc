# Corrected automated investigation results

October 6, 2026. Research-only. The Vault plus Minisforum is the selected default; the live constrained analyst is unchanged.

| Run | Measured investigator passes | Completed reviews | Strict review controls |
| --- | --- | --- | --- |
| Original frozen V1 | 0 / 18 | 0 / 24; all length-capped | Not executed |
| Intermediate V5 | 16 / 18 | 22 / 24; two lacked a completed investigation | 1 / 6 |
| Corrected V6 | 18 / 18 | 24 / 24; no output caps | 1 / 6 |

V5's two expanded mixed cases were truncated from 5,107/5,464 input tokens to 2,050. That invalidates its executed A/B/C comparison. Its failed outputs are preserved. A separate same-prompt development request changed only context 4096 to 8192 and completed correctly with all 5,107 input tokens and 360 generated tokens.

V6 retained all 56 scheduled requests: 8 constrained reports, 24 investigators including 6 practice, and 24 blind distinct-weight reviews. All 8 reports validated. All 24 investigators passed their independent source/decision checks, including all 18 measured rows. All 56 requests have model/digest/GPU observations and verified full-input runtime traces. Six separately scored reviewer controls also completed naturally with full context. The context guard refuses truncation, token/context mismatch, rotated or ambiguous traces.

| Measured condition | Correct / scheduled |
| --- | --- |
| A | 6 / 6 |
| B | 6 / 6 |
| C | 6 / 6 |

The observed investigator generation range was 148-360 tokens. The 700-token output cap, 120-second HTTP deadline, 16 GiB spare-memory floor, one request at a time and keepalive zero remain. Investigator context is 8192; analyst/reviewer context is 4096. Reported durations are HTTP request durations, not human task time. The intermediate and corrected contracts/cases are exposed regressions, not a general model benchmark.

The reviewer still cannot be trusted as a judge. Only 18 of 24 complete review checklists matched all independently defined categories, and only 1 of 6 deliberately corrupted answers passed its strict defect controls. It produced false alarms and missed real defects. One separate reasoning-mode trial capped at 2048 tokens with no final answer; it was not adopted. Completion and a larger model did not establish reliable criticism. Model opinions never override source scores.

All three conditions passed, so this run does not show that selected analyst assistance or grouping improves accuracy. It establishes correct bounded decisions for six constructed measured cases under this contract. It does not establish human benefit, unknown-incident accuracy, every-threat detection or an advantage over TriageWall. The broader decisions/reviewer are not deployed.

Read [the correction protocol](INVESTIGATION_CONTRACT_CORRECTION_2026-10-06.md), [the original failed results](AUTOMATED_INVESTIGATION_RESULTS_2026-10-06.md), [project status and messaging](PROJECT_STATUS_AND_MESSAGING_2026-10-06.md) and [copied provenance](../investigation-correction-evidence/PUBLIC_SUBSET_PROVENANCE.json). Exact copied request/response/outcome bytes are preserved. Original raw JSONL/source-path mappings, complete runtime traces and process ownership remain private. This is not a complete portable original-source replay.
