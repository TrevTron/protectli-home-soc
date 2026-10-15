# Current small-model selection, October 5, 2026

Current release note, October 7: Trevor dropped the fixed 48-hour clause. [Observed operation and recovery](OPERATING_REVIEW_2026-10-07.md) retains interruptions and failures. Current storage uses activated rolling-v2; [Quickstart](QUICKSTART.md) is the operating path. Earlier dated budgets, test counts and pending labels below are historical.

Historical capacity checkpoint, October 6 (before rolling-v2): 1 GiB raw budget, 4 GiB private archives, streaming archive verification and early capacity warnings are deployed and verified. All 89 software checks pass. The 48-hour window remains collecting, with no elapsed-time acceptance. The 416 model outcomes and original evidence remain unchanged. No external release has occurred. Earlier dated checkpoint results below remain historical.

Latest local state, October 6: simulations and all 200/168/48 model requests are complete; actual-answer reviews and source-bound replay artifacts are included. Qwen3.5 4B/common is the selected optional analyst, verified in a fresh live report. The local article/repository/NotebookLM drafts are reconciled; 89 software checks pass. The 48-hour observation remains unaccepted, Marauder testing is deferred, and no external release has occurred. See [the current expanded results](MODEL_COMPARISON_EXPANDED_RESULTS.md). Earlier dated checkpoint statements below remain historical.

Trevor asked to inspect current community use before choosing the next model. The earlier automatic Qwen2.5 7B selection is superseded. Its download is retained privately, with no evaluation or production change. Existing measured Qwen3 4B results remain historical evidence; they are not Qwen3.5 results.

This is a dated qualitative source sample, not a poll, popularity ranking or proof of performance on network evidence. Search engines returned older threads even with date filters. Dates, task descriptions and original comments were checked before using them. Relative comment ages on cached Reddit pages are not treated as precise publication timestamps.

## What users are actually discussing

- [October 2 current daily-driver discussion](https://www.reddit.com/r/LocalLLM/comments/1wvhep7/whos_the_current_king_of_local_llms_for_you_qwen/): multiple commenters split Qwen for coding/agent work and Gemma for general text. One explicitly reports Qwen3.5 9B for quick triage/sorting; another describes Gemma for categorization, summaries and log analysis. These are user reports, not independently measured network-triage results.
- [September 30 local meeting analyst](https://www.reddit.com/r/LocalLLaMA/comments/1wu2lpa/five_local_models_68_gb_of_weights_my_opensource/): the builder retained Qwen3.5 4B for notes after a smaller candidate repeated and misassigned action items. Its Mac performance is not this Windows CPU performance.
- [September 28 limited-hardware agent discussion](https://www.reddit.com/r/LocalLLaMA/comments/1wsfo1j/need_small_model_that_can_work_for_tool_caling/): Gemma and Ling-3.0-tiny appear, including a warning about Ling prefill at longer context. That motivates inspecting alternatives; it does not establish one winner.
- [September small-assistant discussion](https://www.reddit.com/r/LocalLLaMA/comments/1wg28mu/is_there_a_better_small_model_than_qwen35_4b_for/): Gemma E4B and other small models are proposed, with mixed use cases and opinions.
- [Older small-model usage discussion](https://www.reddit.com/r/LocalLLaMA/comments/1uz6388/what_small_models_have_you_guys_been_using/): a user reports Gemma 4 12B succeeding at document processing where Qwen3.5 9B did not. Keep this older qualitative task report separate from October activity.

The strongest recurring families in this inspected sample are Qwen and Gemma. This does not mean all users prefer them, that a particular variant leads today, or that broad coding benchmarks establish our analyst quality.

## Verified candidates and practical decision

| Candidate | Reason to inspect | Verified source and limit |
|---|---|---|
| Qwen3.5 4B | Current small-model baseline for structured summaries | [Official card](https://huggingface.co/Qwen/Qwen3.5-4B), [Ollama tag](https://ollama.com/library/qwen3.5:4b). Distinct from the already tested Qwen3 4B. |
| Qwen3.5 9B | Same-family larger candidate; reported quick triage use | [Official card](https://huggingface.co/Qwen/Qwen3.5-9B), [Ollama tag](https://ollama.com/library/qwen3.5:9b). Actual local backend/digest/resources still require measurement. |
| Gemma 4 12B QAT | Different-family text/log candidate; larger memory/latency tradeoff | [Google model card](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf), [explicit Ollama QAT tag](https://ollama.com/library/gemma4:12b-it-qat). Its quantization differs from Qwen Q4_K_M. |
| Ling-3.0-tiny | Newer efficient alternative mentioned on September 28 | [Official inclusionAI card](https://huggingface.co/inclusionAI/Ling-3.0-tiny): 7.9B total, 1.3B active, MIT. Runtime/quantized-package fit remains unverified, so it is a researched alternative rather than an automatic installation. |

Gemma E4B is also relevant, but effective parameters are not total parameters or disk size. Avoid a misleading same-4B claim. The first bounded comparison uses the existing Qwen3 4B, Qwen3.5 4B/9B and Gemma 4 12B QAT, sequentially in the separate CPU runtime. It preserves the default analyst and protected fine-tuning runtime.

Qwen's card documents thinking enabled by default and an explicit API option for non-thinking mode. The comparison requests thinking off and records both output channels. All candidates receive the same frozen regression briefs, system prompt, schema and explicit two-thread/4096-context/700-token/120-second request bounds. Native templates, tokenizers, quantization and defaults are retained and disclosed. One run per model/case is exploratory. Natural answer lengths and cold loading prevent a pure throughput or parameter-size winner claim.

Selection will depend on independently validated claims, useful specific findings, honest unknowns, actual latency and memory. Popularity supplies candidates; our evidence determines whether they belong in this project.

## Adjacent alert-triage research

[HESP, submitted September 27](https://arxiv.org/abs/2609.33446), studies keeping investigation selection and termination outside the local model, with predictions journaled before observations. Its controlled environment and reported completion rates are the authors' results, not validation of this Protectli deployment. The applicable design lesson is to keep fixed read-only evidence collection, validation and stopping bounds in code, with saved inputs preceding answers. Our pipeline does not implement HESP's probability tables or agent probes.

[SOCrates](https://github.com/fa1829/SOCrates) documents schema failures in a 3B model, CPU request timeouts in an 8B model, and model severity escalation despite retrieved guidance. These are author-reported runs. They reinforce retaining rejected output and measuring semantic usefulness separately from schema acceptance. A RAG citation or larger model is not sufficient evidence for a verdict. No third-party implementation was imported.

## Completed comparison and final source refresh

The requests completed October 5. [Actual delivery results](MODEL_COMPARISON_RESULTS.md) retain the existing Qwen3 4B for this contract and CPU host, with failures unchanged. The final read of the current daily-driver thread also emphasizes Qwen3.8 for coding/agent work and Gemma 4 for text/creative use. Those broader preferences are not a vote for our exact small-model workflow. The official Ollama Qwen3.8 catalog inspected in this turn exposes a 27B model; the already-running fine-tuning model is specifically protected and was not tested. The small-model shortlist therefore reflects both relevant task reports and our isolation/resource bounds. Ling and other untested models remain research options. Community preference informed which candidates to test; it did not determine the deployment result.
