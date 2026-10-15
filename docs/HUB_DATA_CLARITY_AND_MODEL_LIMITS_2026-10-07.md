# Hub data clarity and model limits

Date: 2026-10-07. Local website revision only.

Trevor asked whether two CPU threads or the 4,096-token context explained the model failures, and requested an audit of the Hub's explanation of combined Protectli and MS-S1 data.

## What the model receipts establish

The four-model comparison ran on the Minisforum MS-S1 MAX, with two runtime CPU threads, zero GPU layers, context 4,096 and a 700-token answer cap. Structured answers had a 120-second deadline; written answers had 300 seconds. Two runtime threads do not mean that the host has only two physical cores.

Restricting CPU threads plausibly hurt deadline completion for the larger models. No matched thread-count sweep was performed, so the number of failures caused by that setting is unknown. The study evaluates the recorded report budget, not every model's best performance or general intelligence.

| Task | Model | Attempts | Finished | Recorded cause of unfinished answers |
| --- | --- | ---: | ---: | --- |
| Default sampling, structured | Qwen3 4B Instruct | 36 | 30 | 6 reached the 700-token output cap |
| Default sampling, structured | Qwen3.5 4B | 36 | 36 | None |
| Default sampling, structured | Qwen3.5 9B | 36 | 30 | 6 exceeded the 120-second deadline |
| Default sampling, structured | Gemma 4 12B QAT | 36 | 12 | 24 exceeded the 120-second deadline |
| Default sampling, written | Qwen3 4B Instruct | 12 | 4 | 8 reached the 700-token output cap |
| Default sampling, written | Qwen3.5 4B | 12 | 8 | 4 reached the 700-token output cap |
| Default sampling, written | Qwen3.5 9B | 12 | 0 | All 12 reached the 700-token output cap |
| Default sampling, written | Gemma 4 12B QAT | 12 | 8 | 4 reached the 700-token output cap |

All 48 written requests returned text; 28 were unfinished at the cap. None hit the 300-second deadline. An unfinished answer is withheld, not automatically a factual error. With no finished 9B written answer to assess, its factual-error metric is now displayed as **Not assessed**, rather than the confusing 0 / 0.

In the shared-sampling follow-up, Qwen3.5 9B had three timeouts and Gemma had eight. The original Qwen3 4B had two output-cap failures. Qwen3.5 4B finished all 12, but only four of the ten alert-bearing tasks met the full answer checklist. Completion is not complete correctness.

The separate GPU investigator test proved input truncation. Two expanded inputs of 5,107 and 5,464 tokens were cut to 2,050 under context 4,096. A same-prompt retry with context 8,192 received all 5,107 input tokens and answered correctly. The corrected V6 set verified full input and passed all 18 measured answers, using six already exposed cases in three conditions. These results do not demonstrate a benefit to human investigators or an accuracy advantage for assistance or grouping. The analyst and reviewer remained at 4,096; the investigator used 8,192. This diagnosis does not establish that all earlier four-model failures were context failures.

A matched rerun with CPU-thread changes, GPU execution and a larger output allowance is needed before a broader model ranking. Change these factors in separate controlled comparisons to identify their effects. No new inference requests were made during this audit.

Sources: MODEL_COMPARISON_EXPANDED_RESULTS.md, INVESTIGATION_CONTRACT_CORRECTION_2026-10-06.md, AUTOMATED_INVESTIGATION_CORRECTED_RESULTS_2026-10-06.md, and the per-request outcome receipts in review/repository-draft-v7-20261006/model-evidence/. The private audit folder contains a phase/model summary of all 416 recorded outcomes across the three model studies. That total includes development and repeated inputs; it is not an accuracy denominator.

## Hub changes

- Added a reading guide and described the actual path: saved test outputs and receipts, prepared website data records, searchable Hub and individual test pages. The Hub is not connected to live firewall collection.
- Explained the difference between a result row, a request, an explanation item, a repeated input and a test group. Local totals remain 91 rows across 15 groups, including the 24 Home SOC rows in six groups.
- Separated inference-rate results visually from workflow and hardware groups, with group titles and settings boundaries.
- Replaced raw strict utility with **Passed full answer checklist** and defined the checklist, completion and explanation checks. Defined the differing denominators directly beside each metric.
- Explained the shared-settings example: 12 total tasks, two empty tasks, ten tasks with alerts, seven fully explained, four full-checklist passes, and 18 of 21 expected explanation items selected. These are different checks on the same tasks.
- Showed the test host and backend on every Home SOC card. The Vault supplies firewall events; models run on the MS-S1 MAX. These additions do not report results from the separate MS-S1 knowledge-assistant or fine-tuning project.
- Distinguished output caps, deadlines and context truncation. Explained duplicate empty inputs and reused exact-repeat reviews.
- Kept the one GPU report as configuration acceptance, with no matched speedup claim. Kept the short Vault thermal test distinct from model accuracy and thermal-equilibrium claims.
- Clarified the comparison selector's inference scope and linked to the Home SOC studies. Published data licensing remains distinct from local draft review.

## Preservation and verification

All recorded metric values, denominators, units, runtime settings, IDs, source links, artifact digests and result states in the Home SOC JSON remain unchanged. The article Markdown/JSON, Projects page/styles, general project data and hub-data.ts match their pre-edit SHA256 values. Original before copies and logs remain preserved.

Native lint and build passed. The build verified complete HTML, canonical URLs and JSON-LD for 46 sitemap routes, five permanent redirects and eight missing-route controls. The dedicated Protectli Hub verification passed for six draft groups, 24 records, ten noindex pages and 11 supporting links. The visibility static audit passed; five pre-existing metadata warnings concern other articles.

Browser checks covered the normal 1280px desktop, a 1440px wide desktop and a 390px phone viewport. The guide stacks on phone, metric cards fit without horizontal overflow, the shared-sampling search returned four cards in one group, and navigation to the test and methods pages worked. The inspected console showed no errors or warnings. The temporary viewport override was reset. The updated Hub preview remains available at http://127.0.0.1:4175/hub.

Evidence: private/hub-clarity-20261007/. Includes before copies, receipt summary, measurement preservation, preserved hashes, build/lint/static logs, browser measurements and desktop/phone screenshots.

No live devices, SOC services, model configuration, underlying evidence or pending operating/investigation work changed. No commit, push, deployment or publication occurred. Blog V11 and Projects remain preserved. Draft pages remain noindex and excluded from sitemap/feed discovery.
