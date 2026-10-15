# Where the installed models fit

Qwen3 4B Instruct and Qwen3.5 4B are different generations, so their similar size labels do not make them the same model with a different prompt. Qwen3.5 9B is a larger artifact in the newer generation, while Gemma4 12B IT QAT comes from Google and uses a different architecture, tokenizer, instruction format and quantization approach. Our test can compare these installed systems on a defined job; it cannot isolate parameter count as the cause of their differences.

## What is actually installed

| SOC tag | Local metadata | Quantization | Recorded manifest digest |
| --- | --- | --- | --- |
| `qwen3:4b-instruct` | Qwen3 4B Instruct 2507, 36 blocks, 4,022,468,096 parameters in GGUF header | Q4_K_M | `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` |
| `qwen3.5:4b` | qwen35, 32 blocks, installed size label 4.2B | Q4_K_M | `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04` |
| `qwen3.5:9b` | qwen35, 32 blocks, installed size label 9.0B | Q4_K_M | `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90` |
| `gemma4:12b-it-qat` | gemma4, 48 blocks, installed size label 11.9B, QAT/IT header naming | Q4_0 | `38044be4f923e5a55264ed7df4eaac2676651a905f735197c504045140c02bd3` |

[The local metadata receipt](../../ai-followup-evidence/research/installed-artifacts-audit.json) includes GGUF headers, layer hashes, templates, defaults and config renderer/parser names. These are manifest digests, not hashes of only the weights. No project weight training or fine-tuning occurred.

The old Qwen header explicitly names Instruct-2507 and links its license to that publisher repository. The [Qwen publisher card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) describes that variant as non-thinking only. The wrapper's broader capability labels include thinking, but those labels do not establish that this particular instruction artifact has a usable thinking mode. The saved tests explicitly set thinking false and retained both returned channels.

The [Qwen3.5 4B](https://huggingface.co/Qwen/Qwen3.5-4B) and [9B](https://huggingface.co/Qwen/Qwen3.5-9B) cards describe vision-language models with interleaved Gated DeltaNet and full attention. Their individual configurations describe dense feed-forward layers. The family introduction also discusses mixture-of-experts, which should not be copied into a description of these two dense artifacts. The publisher's 4B label and installed 4.2B metadata use different labeling; this audit does not establish the exact accounting behind that difference. These SOC tasks used text, not vision.

[Google's QAT card](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf) identifies instruction-tuned Gemma4 12B and ready-to-use Q4_0 weights from a quantization-aware training pipeline. QAT means quantization was part of the publisher's training preparation. It does not mean I trained this model for the SOC. Its dense 12B architecture mixes sliding-window and global attention. Our Q4_K_M and Q4_0 artifacts are not a matched experiment on quantization alone.

These primary pages were inspected October 7. Their architecture descriptions are external facts; our local receipt binds the installed artifacts. A publisher model card does not establish performance or complete conversion ancestry for a local GGUF.

## The template and resource budget matter too

Qwen3 has a full Go chat template with ChatML delimiters. Both Qwen3.5 manifests contain a small `{{ .Prompt }}` template, but their config selects the `qwen3.5` renderer/parser. Gemma's config selects `gemma4`; its manifest has no separate template layer. Comparing template strings alone would miss the built-in renderers. A future run needs the runtime binary/version, config and effective rendered prompt trace, not an assertion that every model received identical tokenization. The recorded retest runtime was Ollama 0.40.0.

The manifests also carry different sampling defaults. The common profile overrides temperature, top-k/top-p, penalties and seed, while retaining native instruction formats and stop behavior. Thinking remains explicitly disabled in the proposed primary study. A later thinking experiment would be a separate lane, with its own output budget and both channels retained.

The published maximum context is not the context actually used. The historical study requested 4,096; the larger CPU study requested 8,192. Complete-input proof matters more than an advertised long-context number. Likewise, 700 or 2,048 is an allowance, while the receipt's actual generated-token count and stop reason establish whether an answer finished.

The historical two-minute job favored the newer 4B's delivery under that bound. The larger CPU budget let Gemma complete and meet more structured checks. Both observations can be true because the task and resource budget affect the practical choice. The single GPU acceptance used a different brief/output and cannot establish a CPU/GPU speed winner. Larger parameters, a newer generation, GPU execution or natural completion each leave semantic correctness to be tested against exact evidence.
