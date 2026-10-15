Historical first exploratory comparison. The current shared development and new-case results are in [MODEL_REFINEMENT_RESULTS.md](MODEL_REFINEMENT_RESULTS.md). Original responses and failures below remain unchanged.

# Current model-candidate delivery results, October 5, 2026

This is an exploratory comparison of four models on three previously used synthetic regression briefs. It is not a held-out accuracy estimate, a live attack, a community poll or a pure throughput/parameter-size ranking. Community research selected the candidates; actual outputs determined the local default decision.

The same saved briefs, current system prompt and group-bound schema were frozen before requests. Each model/case had one cold-load request, two CPU threads, context 4096, cap 700, temperature 0, seed 17, thinking off, keepalive 0 and the unchanged 120-second HTTP deadline. Native model defaults/templates/tokenizers and quantization differ. Elapsed time includes model loading, prompt processing and unequal natural generations. Timeout callers do not prove runner completion; the harness waited for unload before each subsequent request.

| Model | Mixed priority | Cold-start unknown | Maximum 16 groups | Accepted delivery |
|---|---|---|---|---|
| qwen3:4b-instruct | Accepted (59.656 s, 619 generated tokens) | Accepted (31.281 s, 376 generated tokens) | Accepted (94.609 s, 661 generated tokens) | 3/3 |
| qwen3.5:4b | Withheld: required unknowns absent (28.422 s, 212 generated tokens) | Accepted (34.859 s, 396 generated tokens) | Withheld: required unknowns absent (46.281 s, 219 generated tokens) | 1/3 |
| qwen3.5:9b | Withheld: required unknowns absent (96.984 s, 604 generated tokens) | Accepted (55.828 s, 341 generated tokens) | Withheld: 120 s request timeout | 1/3 |
| gemma4:12b-it-qat | Withheld: 120 s request timeout | Accepted (84.875 s, 402 generated tokens) | Withheld: 120 s request timeout | 1/3 |

All four produced an accepted cold-start answer. The two Qwen3.5 variants omitted the required incomplete-visibility unknown on the mixed case. Qwen3.5 4B repeated that failure on the maximum case. Qwen3.5 9B and Gemma 4 12B QAT exceeded the request deadline on the maximum case; Gemma also timed out on mixed priority. These timed-out calls did not return a response for semantic review. All failures remain recorded; no longer-deadline or weakened-validator retry was used.

Reading every returned answer found useful block and UID context in the rejected Qwen3.5 9B mixed answer, plus repeated citations and repeated intent. Qwen3.5 4B mixed answer omitted its useful block interpretation as well as visibility. The baseline supplied useful specific contexts and retained unknowns, but its mixed/max answers repeated references and exceeded the prompt's requested inference count while remaining within the formal schema cap. That redundancy does not provide additional evidence. The accepted cold-start answers support narrow useful review, not diagnosis or verified model reliability.

Minimum sampled available Windows memory across the experiment was 26.979 GiB. Loaded-model samples and runner logs establish CPU execution, two threads and zero VRAM. Prompt input was not truncated in the recorded requests. Raw source logging, firewall configuration and the protected default model remained separate.

Decision: keep qwen3:4b-instruct as the bounded monitor default for this exact contract and host. This is a deployment-fit decision based on this small regression set, not a claim that older Qwen3 is generally better than current Qwen3.5 or Gemma. The researched candidates stay available in the isolated store for later contract/workload studies. More representative unseen cases, repetitions, explicit model-default normalization, schema-enforced mandatory unknown structure and longer observation are future work.

The candidate contains the exact synthetic briefs, original expected files (whose held-out wording describes their earlier first-use round), actual returned API responses, response metadata, outcomes and model properties. No raw live log, private source locator or endpoint receipt is shipped. The retained native private experiment also has resource samples, frozen source hashes and all request errors. The portable replay harness freezes briefs anew and refuses an existing output directory.
