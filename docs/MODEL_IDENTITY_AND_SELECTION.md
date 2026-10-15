# Qwen, Gemma and the current analyst choice

Qwen and Gemma are different model families. Qwen3 and Qwen3.5 are generations of the Qwen family; Gemma 4 is Google's family. Our installed tags identify four specific quantized instruction-following artifacts, not interchangeable model names. See the publishers' [Qwen3.5 4B card](https://huggingface.co/Qwen/Qwen3.5-4B) and [Gemma 4 12B IT QAT GGUF card](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf). Their advertised architecture/context differs from the context configured in our actual requests.

| Installed artifact | Role here | Larger CPU strict utility | Written material rejections |
| --- | --- | ---: | ---: |
| `qwen3:4b-instruct` | Original smaller reference | 2/12 | 4/6 |
| `qwen3.5:4b` | Current constrained report default, common profile | 5/12 | 5/6 |
| `qwen3.5:9b` | Larger Qwen comparison; supplementary reviewer in fresh experiment | 3/12 | 3/6 |
| `gemma4:12b-it-qat` | Different family, larger QAT comparison | 9/12 | 3/6 |

All 72 requests completed naturally in the larger CPU retest. Gemma met more strict structured utility checks there. The 9B supplied some useful context and fewer materially rejected written answers than the newer 4B, but its answers still contained an invalid reference and signature/session confusion. Those written grades are separate agent assessments, and an answer without a material rejection still has recorded weaknesses.

Qwen3.5 4B remains the deployed constrained reporter because its common profile met the earlier bounded delivery/validation requirements and its separate GPU path is verified in this build. That does not establish that it is smarter or more reliable than Gemma or the larger Qwen. Bigger models can have more capability while still failing our schema, deadline, context or evidence requirements. A deployed reporter and an open-ended investigator are different workloads.

The first CPU studies used two threads, 4,096 context and a 700-token generation ceiling. The larger retest changed threads, context, answer allowance and deadlines together. It resolved delivery on these exposed cases, so the original failures cannot all be treated as evidence of low capability. It also retained factual defects after completion. No one-variable test establishes how much each resource setting caused the earlier failures. Actual generated tokens and natural stops, rather than ceilings, remain in the export.

No weights were trained or fine-tuned for these tests. Development/refinement changed prompts, normalized inputs, schemas, settings and evaluation, equally within the recorded protocol. The fresh experiment uses Qwen3.5 4B investigations and 9B supplementary review; it does not compare Gemma investigation usefulness. The completed [AI follow-up](AI_FOLLOWUP_RESULTS_AND_VERIFICATION.md) adds Ling-3.0-tiny through its pinned Windows CPU llama.cpp route, a 15/15 permitted-menu demonstration and two harder packs. Gemma leads the first harder pack, while original Qwen3 4B leads the revised common-profile pack. Revised Ling reasoning is a separate lane. The default reporter remains unchanged.

The later [targeted-check and small-model training experiment](AI_TARGETED_CHECK_AND_LORA_SUMMARY_2026-10-11.md) is separate. It trained SmolLM2 adapters, while production Qwen weights and the comparisons above remained unchanged. This candidate includes its summary; its full reviewed export is still outstanding.
