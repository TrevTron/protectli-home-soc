# Ling revision and fresh comparison results

The historical Ling score remains **0/12**. On the fresh twelve-case pack, the frozen revised Ling profile `clean-think-long` passed **3/12** strict six-dimension cases. All 72 new comparison requests returned complete, input-verified final JSON. A complete answer and a correct answer are counted separately.

## Matched common profile

All five artifacts received identical revised skill text, original records, unclassified receipts and answer schema. This table uses greedy sampling with thinking disabled.

| Artifact | Strict full passes | Complete answers |
|---|---:|---:|
| Qwen 3 4B Instruct 2507 | 4/12 | 12/12 |
| Gemma 4 12B IT QAT | 3/12 | 12/12 |
| Qwen 3.5 9B | 1/12 | 12/12 |
| Qwen 3.5 4B | 0/12 | 12/12 |
| Ling 3.0 tiny Q4_K_M | 0/12 | 12/12 |

Observed common-profile leader: Qwen 3 4B Instruct 2507. This is a task/configuration result from one draw per constructed case, not a model-family ranking.

## Frozen Ling revision

Selected on development evidence before creating the transfer pack: `clean-think-long`. Temperature 0, top-p 1, top-k 20, seed 17, native Bailing template, thinking enabled. The enabled reasoning cap is 3,072 tokens, inside a 4,096-token overall completion ceiling and 8,192-token context. CPU-only, sixteen threads, finite 300-second requests.

On the same fresh cases, common non-thinking Ling passed 0/12 and the selected profile passed 3/12. Its enabled reasoning was forcibly closed by the budget on 12/12 requests. Every final JSON stopped normally; that does not mean every reasoning trace ended naturally.

| Development profile | Strict full passes | Reasoning-budget closures |
|---|---:|---:|
| legacy-off | 0/4 | 0/4 |
| clean-off | 0/4 | 0/4 |
| clean-think | 1/4 | 4/4 |
| clean-native | 0/4 | 4/4 |
| clean-think-long | 2/4 | 4/4 |
| clean-native-long | 0/4 | 4/4 |

The consistent prompt corrected development success/failure classifications. A larger bounded reasoning budget was tested because all initial thinking traces reached their cap. Selection uses strict full-case passes and the predeclared tie order. The publisher sampling recipe was tested; it is not assumed to win locally.

## Decision dimensions on the fresh pack

| Artifact/profile | Contexts | Checks | Client outcome | Client refs | Intrusion boundary | Delivery boundary |
|---|---:|---:|---:|---:|---:|---:|
| Gemma 4 12B IT QAT / clean-off | 3/12 | 11/12 | 8/12 | 9/12 | 12/12 | 12/12 |
| Ling 3.0 tiny Q4_K_M / clean-off | 3/12 | 8/12 | 4/12 | 4/12 | 11/12 | 12/12 |
| Ling 3.0 tiny Q4_K_M / clean-think-long | 7/12 | 5/12 | 11/12 | 11/12 | 12/12 | 12/12 |
| Qwen 3 4B Instruct 2507 / clean-off | 6/12 | 8/12 | 10/12 | 9/12 | 12/12 | 12/12 |
| Qwen 3.5 4B / clean-off | 1/12 | 9/12 | 5/12 | 6/12 | 12/12 | 12/12 |
| Qwen 3.5 9B / clean-off | 2/12 | 7/12 | 4/12 | 5/12 | 12/12 | 12/12 |

Both boundary dimensions only test unsupported positive claims. No fixture proves an intrusion or complete UDP delivery. This evaluation does not establish positive intrusion-detection ability.

## Preserved earlier result

| Artifact | Original F-pack strict passes |
|---|---:|
| Gemma 4 12B IT QAT | 8/12 |
| Qwen 3 4B Instruct 2507 | 4/12 |
| Qwen 3.5 4B | 4/12 |
| Qwen 3.5 9B | 3/12 |
| Ling 3.0 tiny Q4_K_M | 0/12 |

The original prompt, cases, answers, grades and seals remain. The original Ling failure pattern included an unsupported comparison check on every case. The fresh pack changes source windows and near-match receipt distractors, so its scores cannot be used as a controlled old-to-new accuracy delta. The development contrasts and the two Ling lanes provide the matched comparisons.

## Evidence and limits

The twelve new cases are author-known synthetic variants of the same development families. They change attempt identifiers, timestamps, tuples, counts/order and near-match receipts. Even empty cases carry fresh window metadata. No real unseen incidents or human-benefit test is claimed. Artifact sizes, quantization and runtimes differ; timings are not pooled into a speed ranking. One stochastic seed cannot establish repeatability.

Raw response bytes were independently parsed and regraded against the sealed source cases. The audit checked identical common prompts/inputs/schemas, native thinking prefixes and returned channels, complete-input traces, CPU residency for the Ollama lane, runtime/model identities and owned-child cleanup. No answers were repaired or retried. The original log-phrase detector and the initial audit parser were preserved; an additive auditor uses the actual native generation-prefix and budget-exhaustion lines. A future-case generator briefly changed during calibration and was restored to exact sealed bytes before a separate version was created. It was not read by the calibration executor.

The ordinary Qwen 3.5 4B Vulkan reporter completed a fresh report at 2026-10-07T16:27:40.181224-07:00. Current viewer socket/process ownership was verified. The maintenance pause is absent and the temporary Ling listener is gone. The collector and existing native health monitoring remain separate; the protected default model endpoint was not invoked. No new host thermal certification is claimed.

Research: [official Ling card](https://huggingface.co/inclusionAI/Ling-3.0-tiny), [community observations](https://www.reddit.com/r/LocalLLaMA/comments/1w7y3sa/aa_update_heres_how_the_small_models_score/), and the local research/protocol documents.

Reproduction files: `soc-decision-skill-v2.md`, `SELECTED_LING_PROFILE_EXTENDED.json`, `TRANSFER_PROTOCOL.json`, `TRANSFER_PRE_EXECUTION_SEAL.json`, `TRANSFER_VERIFIED_RESULTS.json`, the two calibration result files and immutable per-request source/response/trace receipts.

## Retry timestamp correction addendum

The authored N05 retry fixture had one collection timestamp earlier than its event. The original twelve-case pack and all scores remain intact. A separately sealed variant changes only that collection time to two seconds after the event. Its receipt join fields and source-derived oracle are unchanged. Each artifact and both Ling profiles received this corrected case as six additional requests with identical recipes.

| Artifact/profile | Original N05 pass | Corrected N05 pass | Twelve-case sensitivity total |
|---|---:|---:|---:|
| Gemma 4 12B IT QAT / clean-off | False | False | 3/12 |
| Qwen 3.5 4B / clean-off | False | False | 0/12 |
| Qwen 3 4B Instruct 2507 / clean-off | False | False | 4/12 |
| Qwen 3.5 9B / clean-off | False | False | 1/12 |
| Ling 3.0 tiny Q4_K_M / clean-off | False | False | 0/12 |
| Ling 3.0 tiny Q4_K_M / clean-think-long | False | False | 3/12 |

Sensitivity totals replace only N05 with the corrected-case result. They are supplemental and do not overwrite the predeclared primary scores. Read the new set as authored synthetic tasks rather than a real-world clock-validation benchmark. The corrected fixture is internally time-consistent.

## Native resource guard and continuation

The original native transfer batch completed nineteen requests, then stopped at its pre-request 16 GiB spare-memory guard. The next five requests were never sent. Its completed outcomes, raw logs, nonzero execution receipt, owned-child cleanup and ordinary recovery remain intact. A separately sealed continuation sent only those five unchanged request bodies with server RAM prompt caching disabled. It also monitored spare memory during each answer and kept the same floor. All five completed without a threshold breach. Inputs, weights, skill, schema, sampling, seed, context, output/reasoning budgets and deadlines remain as declared. Runtime resource conditions differ, so these results are not a pure resource-uncontrolled causal or pooled throughput comparison. No completed request was repeated.

## Corrected-case receipt sensitivity

Replacing only N05 with its separately tested timestamp-corrected version raises the revised Ling client-outcome and client-reference totals from 11/12 each to 12/12 each. Its strict full-case total remains 3/12, with context decisions correct on 7/12 and next checks on 5/12. This is a supplemental sensitivity result, not a second independent twelve-case run. The remaining errors are concentrated in context and check selection.

The strict score measures the declared six-field code policy, including its predeclared useful-check restrictions. It is not a free-prose evaluation or a general measure of intelligence. The check codes have no per-attempt target argument, so scope-sensitive investigation beyond this contract remains future work.

The private revised configuration is in `LING_REVISED_CONFIGURATION.json`; the exact system procedure is `soc-decision-skill-v2.md` and its schema is `SOC_DECISION_SCHEMA.json`. The publisher sampling recipe was tested on development but the greedy reasoning recipe received the highest strict score there. Community reports remain anecdotal, with mixed setup-dependent experiences.
