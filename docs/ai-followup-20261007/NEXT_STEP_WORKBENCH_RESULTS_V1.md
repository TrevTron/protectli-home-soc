# Selectable local analyst workbench

The next step now runs locally. The workbench lets me select Qwen, Gemma or the current Ling-3.0-tiny artifact, inspect the same source case and read its retained result. The model receives reusable procedures for sensor triage, scoped client outcomes and resolving next checks. Code preserves the facts, coverage notices and every original citation.

Open the [local workbench](http://127.0.0.1:8771/). Its selector displays saved development results. It does not change the scheduled SOC model or start another inference request when an option is selected. Source records and their hashes expand in the page; technical request details stay behind a separate disclosure. This is an isolated working demonstration under `private/ai-followup-20261007/model-skills-v2`, with the ordinary Qwen3.5 4B/Vulkan reporter restored afterward.

The visible browser was checked with all five model options on case D05. Each displayed its retained permitted-check result with the code/model attribution intact. The [saved current Ling view](../../assets/model-workbench-ling.jpg) and recorded browser checks (private host receipts) preserve that verification. Thirteen offline software checks passed. The independent audit verified 563 original evidence files, 28 prior sealed files and 216 prepared case files unchanged.

To reopen after this local server stops, run the existing Python interpreter with `-B` and `private/ai-followup-20261007/model-skills-v2/server.py` from the project root, then open the workbench URL. The server binds only to loopback and serves retained results; starting it does not load a model.

## What is working

The final operator contract supplies verified context through code and asks the selected model to choose one useful read-only check from an evidence-derived menu. Fifteen requests completed naturally, retained the complete prompt and passed the independent source-case check:

| Exact model choice | Runtime lane | Accepted operator demonstrations |
| --- | --- | --- |
| Qwen3 4B Instruct 2507, Q4_K_M | Existing isolated Ollama CPU | 3/3 |
| Qwen3.5 4B, Q4_K_M | Existing isolated Ollama CPU | 3/3 |
| Qwen3.5 9B, Q4_K_M | Existing isolated Ollama CPU | 3/3 |
| Gemma4 12B IT QAT, Q4_0 | Existing isolated Ollama CPU | 3/3 |
| Ling-3.0-tiny, Q4_K_M | Separate pinned llama.cpp Windows CPU | 3/3 |

The three constructed development cases cover allowed events without a client receipt, blocked events without a client receipt, and an original block followed by a distinct successful client attempt. All models use those same cases. This is a bounded permitted-menu task. The model chooses a supported check; code supplies the mandatory context and source bindings. These results do not establish open-ended investigation quality, a family winner, or human benefit. Offline adversarial checks also cover all twelve prepared development families, including mismatched receipts, process-only evidence, missing coverage, changed signatures and instructions inside log text.

The page remains useful when model context does not pass validation. It displays the verified evidence and the context/check menu supplied by code, clearly attributed to code. A block stays visible even when the later retry has a success receipt. Grouped repetitions retain first and last receipt times and all original members. The model never transcribes the original E/G identifiers.

## How the skill package developed

I first ran the same broader context-selection contract with and without the three procedure modules: 24 requests across the four installed artifacts. Then I added a shared worked example distinguishing unproved UDP delivery from an unavailable retained prior window and ran another twelve development requests. Gemma and Qwen3.5 9B each passed all three refined development cases. Both 4B artifacts improved on the basic sensor cases, while the retry/receipt case still justified a narrower responsibility.

The final operator contract changes the responsibility assigned to the model. Required warnings and receipt scope are fixed by code, and the model selects one resolving check from the verified menu. Its 15/15 result belongs to that smaller task. It is not a repaired score for the earlier context-selection outputs. The [complete private ledger](../../ai-followup-evidence/research/model-skills-v2/VERIFIED_LEDGER.json) retains every request, original answer, validation result, source proof and contract identity across all 57 new requests. The older strict case-list score is retained separately from the predeclared optional STUN-context rubric.

This package loads procedures into the request. It does not train model weights, install domain procedures into MoE experts or demonstrate that a family intrinsically understands a particular skill better. Model-specific thinking or sampling changes remain separate factors. Here all requests explicitly disable thinking, use 8,192 context, a 2,048-token output ceiling, sixteen CPU threads and bounded deadlines. Actual generated-token counts and stop reasons are retained.

## Current Ling route

Only Ling-3.0-tiny is a candidate in this workbench. The publisher's older main-card Ollama recipe described a custom Apple Silicon MLX build. Further inspection found the [official GGUF artifact](https://huggingface.co/inclusionAI/Ling-3.0-tiny-GGUF) and [merged BailingMoE3 support in llama.cpp](https://github.com/ggml-org/llama.cpp/pull/26608). Those provided a usable local Windows CPU route, which is now directly tested here. The earlier research note that Windows/AMD fit was unverified is superseded for this exact CPU configuration.

The model is pinned to inclusionAI revision `01b850e29ed5b44e2b810160ff980a9bb353296f`, file `Ling-3.0-tiny-Q4_K_M.gguf`, 4,823,894,944 bytes, SHA256 `246d67d45f5b0c7447ca0ce0bdb8b46b8a47b593c5068635dc16422c051d7be9`. The [official Windows CPU release](https://github.com/ggml-org/llama.cpp/releases/tag/b11429) is build 11429, commit `d81235049384534c167caea52b85a694f6103d14`; its archive SHA256 is `1283323272b04cd07905816a597a0da810918102de958f4ff6f7bbaa70ed2efe`. Full model bytes and runtime files were verified before execution. The GGUF identifies architecture `bailingmoe3`, twenty-four blocks and its native chat template.

Ling runs as an owned, temporary child on `127.0.0.1:11437`, using the CPU-only release, device `none`, zero GPU layers and host-operation offload disabled. Its native template explicitly disables thinking. It uses one slot, sixteen threads, 8,192 context, finite output/load/request deadlines and a spare-memory guard. Its local API is authenticated and the owned child is cleaned up after the batch. The default Ollama endpoint on 11434 and the active SOC model store are untouched.

The model download was resumed after an HTTPS read timeout; its original prefix and full final SHA256 were verified. The initial compatibility request returned naturally, but its default log verbosity did not provide the complete-input proof required by the guard. The remaining five, never-requested proposals ran after enabling the required trace detail. Originals were preserved and that first request was not retried. The later three-request operator demonstration is a separately sealed contract. This resolves execution and instrumentation for the recorded CPU path; it does not establish a Vulkan path or unrestricted model quality.

Ling uses a different runtime and a resident server, while the Ollama requests release their model after each request. Their timing observations are separate. No pooled runtime-speed ranking is supported.

## Operational record and next implementation boundary

The first maintenance interval exposed a recovery race: a second SOC launcher wrote a different viewer owner. The isolated snapshot viewer was identified from its exact saved receipt, executable, command line, process creation and socket ownership, then reconciled. Later wrappers held the existing recovery lock throughout maintenance and verified their own snapshot owner before cleanup. Every later batch restored a ready ordinary reporter. Raw collection remained separate throughout. The earlier overlap is recorded; it is not described as perfectly isolated operation.

The new work stays outside active tools, the repository release candidate and website. The first human pilot and all original inspected evidence retain their hashes. No firewall setting, public content, push, deployment or external message was changed. Hardware/kernel protections and memory/deadline controls remain enabled. There is no new host thermal measurement or completed operating-observation acceptance claim.

The working boundary is now a selectable local demonstration with five executed model artifacts, reusable task procedures, stable deterministic evidence and validated model next-check selections. Live source adaptation, promotion into the main dashboard and a measured operator-benefit study remain separate implementation work. The current artifact gives those steps a concrete package and retained evidence to build on.
