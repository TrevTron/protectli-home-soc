# Attribution and review state

This local, unpublished candidate contains original project scripts and documentation prepared for Trevor Unland. Trevor selected standard MIT for original code and textual software documentation, with separate attributed-media terms in [LICENSE_MEDIA.txt](LICENSE_MEDIA.txt). Third-party components and metadata retain their own terms. This is a local review candidate; public release has not occurred.

The appliance runs [OPNsense](https://opnsense.org/), which integrates [Suricata](https://suricata.io/). Consult their own distributions for their licenses. The lab downloads selected [Emerging Threats Open](https://community.emergingthreats.net/) rules through OPNsense; the rule archive is kept on the appliance and is not part of this candidate. A sanitized event identifies the standard SID 2100498 signature for reproducibility.

The harmless `testmyids.com` response is used as a controlled detection fixture. It is an external test endpoint, so availability and content must be checked before interpreting a failure. Routed download measurements use Cloudflare's documented speed-test endpoint. This package does not bundle those services or their code.

Python scripts use the standard library. PowerShell helpers use Windows facilities and installed Python/curl. The generated dashboard is served by the project's local receiver. No external JavaScript or chart library is loaded.

Protectli provided the V1610 for this project. The testing and opinions are my own. This is the approved disclosure for the article and repository README.

The optional analyst uses separately downloaded models through [Ollama](https://ollama.com/). Model weights are not bundled. Qwen and Google model cards describe their own licenses and use terms: [Qwen3.5](https://huggingface.co/Qwen/Qwen3.5-9B), [Gemma 4 QAT](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf). Recorded native templates/defaults in the synthetic evaluation are upstream model metadata, not original project code covered by the project MIT grant. The Ling follow-up uses the separately downloaded [official Ling-3.0-tiny GGUF](https://huggingface.co/inclusionAI/Ling-3.0-tiny-GGUF) and [llama.cpp b11429 CPU runtime](https://github.com/ggml-org/llama.cpp/releases/tag/b11429); neither distribution is bundled. Their publishers retain their own terms. Actual synthetic API answers are retained as experiment outputs, not a model-license grant or independent accuracy certification.
