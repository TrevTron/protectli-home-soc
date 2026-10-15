# Corrected retry fixture addendum

Source review during the frozen transfer run found an authoring mistake in N05. Its later allowed attempt has event time `2026-10-07T18:05:50+00:00` but originally had collection time `2026-10-07T18:05:19+00:00`. The source fixture was constructed by this agent, not captured live evidence. I did not model clock skew, so this is a fixture inconsistency.

The original case, source hashes, requests, responses and twelve-case score remain. A separate corrected fixture sets that one collection timestamp to `2026-10-07T18:05:52+00:00`. The event time, attempt identifier, network tuple, receipts and expected outcome do not change. Its exact seven-field receipt join and original oracle remain independently decidable. The correction makes collection occur after the event.

The sealed addendum schedules six requests: the four Ollama artifacts under the common revised profile, Ling under that common non-thinking profile, and Ling under its frozen selected reasoning profile. All receive the same corrected input. The prompt, answer schema, sampling, reasoning budget, seed, deadlines and runtime guards remain as previously declared. This is a new input variant, with no answer repairs or repeated original request.

Report original N05 and corrected N05 outcomes side by side. Supplemental sensitivity totals replace only that one original case with the corrected result. They cannot silently replace the primary predeclared score or be described as an independent twelve-case rerun. The final results document contains the actual outcomes after execution.

The corrected source and all six requests are under `model-skills-v5/correction-case`, `correction-ollama-01` and `correction-ling-long-01`. `CORRECTION_PROTOCOL.json`, `CORRECTION_PRE_EXECUTION_SEAL.json` and the validation receipt preserve the declaration, changed field, unchanged oracle and common-input/schema checks.
