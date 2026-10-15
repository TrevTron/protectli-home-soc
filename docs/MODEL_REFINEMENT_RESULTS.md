# Equal model development and frozen new-case comparison

October 5, 2026. The earlier known-regression comparison remains intact in [MODEL_COMPARISON_RESULTS.md](MODEL_COMPARISON_RESULTS.md). That first experiment followed development with the old 4B and did not give candidates equal development opportunities. This phase addresses that gap through a bounded shared development protocol. No model weights, adapters or fine-tuning data were trained or changed.

## Common development contract

Every admitted model received the same two development briefs: decreasing STUN and mixed priority. The v4 schema adds complete allowed unknown arrays, each containing intent and incomplete visibility. The independent validator remains unchanged. Three new cases and expected useful contexts were frozen before the first request. Models never receive those expected answers.

| Model | Decreasing STUN, v4 | Mixed priority, v4 |
|---|---|---|
| Qwen3 4B instruct | Grounded and expected context, 50.672 s | Grounded and expected context, 50.187 s |
| Qwen3.5 4B | Grounded, but omitted STUN context, 28.282 s | Withheld: numeric SID returned as string, 47.469 s |
| Qwen3.5 9B | Grounded and expected context, 82.172 s | Grounded and expected context, 91.297 s |
| Gemma 4 12B IT QAT | Grounded and expected context, 105.484 s | Withheld: fixed 120-second deadline |

The single allowed shared revision binds each complete observed claim to the exact typed source field in the generation schema. It addresses the observed string-SID error without weakening post-generation validation or supplying expected interpretations. All four then received one additional development request, the same mixed-priority case, under v5. Qwen3 4B, Qwen3.5 4B and Qwen3.5 9B passed with expected contexts in 47.141, 44.906 and 85.828 seconds. Gemma retained its 120-second timeout. The shared v5 contract was selected at 23:39:48 UTC before any new-case model answers. No further revision or retries are permitted in this comparison.

Every returned development answer was manually reviewed by the agent. Some accepted answers repeat inference/citation entries or exceed the prompt's requested three observations while remaining within the independently enforced formal bounds. Those answers are preserved. A grounding pass is not independent human semantic scoring.

## New cases and limits

The three new agent-authored synthetic cases cover: a reported block with unchanged Tailscale records; decreased STUN and separately grouped severities for the UID fixture; and gapped/future/malformed history with an unknown SID, unchanged STUN and conflicting cached/raw EVE plus raw override text. Their private fixtures use reserved documentation addresses. The raw-message-derived event wins over a conflicting cache; attacker-controlled raw text does not reach the model. Unknown change and incomplete visibility remain explicit when coverage fails.

There is one final request per model/case. The common request uses Ollama 0.35.1, a separate loopback runtime/store, two CPU threads, no GPU layers, context 4096, cap 700, temperature 0, seed 17, thinking off, keepalive 0, at least 16 GiB spare-memory preflight and 120-second deadline. Runtime templates, tokenizer, quantization, defaults, cold-load cost and natural response lengths differ. All timeouts, returned response channels, token counts, stop reasons, resource samples and native model metadata are retained. The runtime unloads normally before the next request.

The frozen cases are new to this development experiment, not an independent third-party benchmark. Three synthetic cases, one request each, cannot establish population accuracy, consistent latency or a generally best model. Expected-code presence is a narrow usefulness measure; evidence validation and manual review remain separate. No live attack or general intrusion-detection accuracy was measured.

## Completed new-case results

All ten returned new-case answers were manually inspected by the agent, separately from mechanical validation. The selected meanings remain scoped catalog possibilities; gaps and unnecessary repeated citations remain visible in the saved answers. This is agent review, not independent human grading. All four timeout receipts and the earlier typed-value rejection in this 24-request study remain retained.

| Model | Grounded deliveries | Cases with all expected useful contexts | Required contexts selected |
|---|---|---|---|
| gemma4:12b-it-qat | 1/3 | 1/3 | 1/5 |
| qwen3.5:4b | 3/3 | 0/3 | 0/5 |
| qwen3.5:9b | 3/3 | 2/3 | 4/5 |
| qwen3:4b-instruct | 3/3 | 3/3 | 5/5 |

Qwen3.5 4B stayed grounded but selected only the generic rule-match caveat in all three new cases. Qwen3.5 9B explained the reported block/Tailscale case and gapped STUN case, but missed the STUN context in the mixed UID/STUN case. Gemma timed out on the first two cases and delivered the gapped STUN case. A missing context is a usefulness failure, not automatically a false claim. Timeouts have no returned answer to grade.

| Model | Block plus Tailscale | Decreasing STUN plus split UID | Gapped raw override |
|---|---|---|---|
| gemma4:12b-it-qat | Timeout | Timeout | 92.281 s / 384 generated tokens |
| qwen3.5:4b | 30.312 s / 280 generated tokens | 29.782 s / 256 generated tokens | 32.094 s / 322 generated tokens |
| qwen3.5:9b | 86.438 s / 564 generated tokens | 85.031 s / 537 generated tokens | 77.281 s / 510 generated tokens |
| qwen3:4b-instruct | 46.438 s / 538 generated tokens | 44.969 s / 476 generated tokens | 40.578 s / 482 generated tokens |

The minimum sampled available host memory across these development/new-case requests was 28.338 GiB. Every loaded-model sample had zero VRAM. Separate runner logs show two CPU threads. All requests returned without thinking text when an answer was available. Natural output lengths and cold loading differ; these timings do not isolate throughput.

The old Qwen3 4B stays the operational default for this bounded contract and host. It delivered all three new cases with all five expected specific contexts. This result follows equal additional development opportunities and a selected shared schema, not weight training. The initial common prompt/catalog originated during earlier 4B development, which is still a limitation of model-neutrality. Independent human cases, repetitions and a separate capacity test remain future work.

The study contains 24 new requests: eight initial development requests, four after the one shared revision and twelve new-case requests. The earlier twelve-request known-regression comparison remains separate and unchanged. Actual returned answers/outcomes, frozen briefs/expected labels/schema, source copies and protocols are retained; no results were retried or repaired. The public derivative omits live raw records, source locators and host/client receipts.

