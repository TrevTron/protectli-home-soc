# Four-model comparison and the selected operating profile

The three studies are complete: 200 requests, 168 simulation-source requests and 48 common-settings requests. My choice for this bounded dashboard is Qwen3.5 4B with the tested common profile, used only as an optional structured first pass. The deterministic evidence-only mode remains the starting point for reproduction. Delivery, context selection, written factual defects and actual displayed reports are reported separately below.

## What ran

Four installed artifacts were admitted: Qwen3 4B Instruct, Qwen3.5 4B, Qwen3.5 9B and Gemma 4 12B QAT. Each received the same two development replays. The shared prompt, schema, expected contexts and request schedule were frozen before the answers. No weights were trained, model-specific prompts substituted, answers repaired or requests retried.

The structured phase used twelve briefs: six saved historical snapshots and six authored edge cases, each repeated three times for every model. Ten briefs contained groups; two were empty. Historical snapshots can overlap. Repetitions establish behavior on the same fixed tasks, rather than independent intrusion examples.

All requests used two CPU threads, zero requested GPU layers, a 4096-token context, a 700-token generation cap, temperature zero, seed 17, thinking disabled and keep_alive 0 in the isolated runtime. The scheduled structured deadline stayed 120 seconds. Written reports had a separate 300-second deadline. Resource and process receipts retain backend, memory and native-temperature observations. Missing native readings remain recorded alongside valid samples.

Native templates, tokenizers, quantization, model defaults, cold loading and natural answer lengths differ. These are delivery and usefulness observations for this workflow, not a pure speed or model-size benchmark.

## Structured reports under the scheduled bound

| Installed artifact | Delivered, all 36 attempts | Delivered, nonempty 30 attempts | Strict utility complete, nonempty 30 attempts | Required contexts selected, out of 63 |
|---|---:|---:|---:|---:|
| Gemma 4 12B QAT | 12 | 6 | 6 | 6 |
| Qwen3.5 4B | 36 | 30 | 3 | 15 |
| Qwen3.5 9B | 30 | 24 | 3 | 30 |
| Qwen3 4B Instruct | 30 | 24 | 0 | 36 |

Gemma had 24 structured timeouts. The 9B had 6. The original 4B had 6 capped structured responses. The newer 4B delivered all 36, but omitted required specific context in 27 of the 30 nonempty reports.

The original 4B selected the most expected context in this phase, yet failed the strict utility checklist because of omissions, repeated citations and other contract defects. That zero does not mean its displayed report contained no useful information. The existing renderer deduplicates inference entries and citation links, while measured counts, actions, priorities, vetted rule labels and source references come from code. It does not add missing model explanations or deliver capped output. Repeated next steps remain visible.

Strict utility combines expected context selection, requested list bounds, citation/inference repetition and review-first attention. It is separate from mechanical fact grounding and semantic accuracy. Sixty-three context opportunities are repeated expected selections on fixed briefs, not 63 independent discoveries.

## Written reports under the longer bound

Six nonempty tasks were repeated twice per model: four historical briefs and two authored edge cases. All 48 requests returned text. Twenty finished naturally and were delivered; 28 reached the 700-token cap and were withheld. No written request timed out.

| Installed artifact | Delivered, out of 12 | Capped and withheld | Delivered answers with material defects |
|---|---:|---:|---:|
| Gemma 4 12B QAT | 8 | 4 | 2 repetitions of one defective answer|
| Qwen3.5 4B | 8 | 4 | 2 repetitions of one defective answer|
| Qwen3.5 9B | 0 | 12 | No delivered answer to grade|
| Qwen3 4B Instruct | 4 | 8 | None individually rejected; other defects recorded|

All four models capped on both repetitions of the historical controlled-block brief: eight delivery failures on one task. The newer 4B's completed dense historical answer claimed 14 groups instead of 16. Gemma's completed dense edge answer claimed 14 allowed events instead of 15 and added an internal/routine-communication explanation that the supplied aliases did not establish. Both answers were individually rejected under the recorded rubric, and each repeated exactly.

Other delivered answers have recorded shortcomings, including incomplete evidence citations, event-versus-connection wording and steps that suggest payload information beyond what an EVE reference contains. Absence of an individual material rejection does not certify an answer as fully accurate. Capped text was read for diagnostics only and receives no delivered-answer grade.

Every first-repeat written outcome was individually read beside its brief, expected contexts and interpretation catalog. Every second-repeat request and full answer message matched its first-repeat counterpart, along with prompt/generated-token counts, stop reason and status. Existing judgments were reused only after those checks, with explicit source-review provenance. This is 24 individually assessed answers on six fixed tasks, plus 24 identical repeats, not 48 independent semantic assessments. Reviews are agent assessments under a pre-recorded rubric, not independent human scoring.

The review dimensions remain separate: facts/citations, supplied context, priorities, uncertainty and read-only next review. A material false fact or unsupported verdict rejects the individual answer regardless of its other scores. No summed score selects the model.

## Verification and restoration

The independent auditor and portable offline verifier pass all 200 terminal receipts and 169 reconstructed returned-request hashes. All 60 original frozen files match. The auditor also verifies the 151 simulation-source and 52 common-settings frozen files, for 263 across the three phases.

There were 135 delivered and 65 withheld outcomes across development, structured and written lanes. Those totals mix different tasks and deadlines and are not an aggregate accuracy result. Thirty-one timeouts have no returned response; capped responses retain their actual content and stop reason.

All 48 written review records match the original outcome and response hashes. The twenty delivered saved analyses also have checked physical file hashes. Windows CRLF storage and API LF content are distinguished without changing the originals.

The first phase retained the protected runtime's model tags. Its owned maintenance wrapper reported recovery ready, and the restored worker produced a fresh accepted original 4B report: 560 generated tokens, natural stop, 93.688 seconds, sixteen groups and unchanged request bounds. That proves this recovery produced a valid source-bound report. It is not the final model decision or uninterrupted availability during maintenance.

Original runner outcomes and frozen protocols retain their creation-time pending/status fields. Later semantic reviews live in a separate hash-linked journal. The portable verifier checks inference consistency; it does not read or authenticate the semantic judgments. See [verification guide](MODEL_STUDY_VERIFICATION.md).

## Simulation briefs with alerts: both repetitions complete

At the 144-request checkpoint, all eight nonempty simulation briefs have both repetitions for every model. There are 64 nonempty outcomes: 62 delivered and two Gemma timeouts on the HTTP UID control. The remaining 24 scheduled requests repeat empty briefs. Independent and portable audits verify 144 outcomes, 142 returned request hashes and the unchanged frozen inputs.

| Installed artifact | Delivered, out of 16 nonempty attempts | Strict utility complete | Required contexts displayed |
|---|---:|---:|---:|
| Gemma 4 12B QAT | 14 | 14 | 14 |
| Qwen3.5 4B | 16 | 4 | 4 |
| Qwen3.5 9B | 16 | 14 | 16 |
| Qwen3 4B Instruct | 16 | 6 | 16 |

Every returned second-repeat nonempty answer matches its already reviewed first counterpart in full message, request settings, token counts, stop reason, status and utility fields. The displayed-context column combines the first-repeat renderer checks with that exact identity; it is not another independent display or semantic assessment. Both Gemma HTTP attempts timed out without a returned answer.

The newer 4B again copies the supplied actions correctly but omits the specific block or UID explanation on six of eight tasks. The original 4B and 9B retain those explanations, while the existing renderer removes repeated citations and some original4B inference entries. Gemma handles the shorter completed briefs well but fails the three-group HTTP task under the deadline. These results do not erase the earlier historical/edge failures or establish a universal model ranking.

## Completed simulation-source phase

The complete simulation-source phase covers 21 actual engine-output cases, with two repetitions and all four models: 166 delivered and two retained Gemma HTTP timeouts. Thirteen sources yield the same empty brief, so there are only nine distinct model inputs. All empty-case answers preserve empty findings and unknown intent/visibility. Empty-case delivery remains separate from useful nonempty interpretation.

All 168 terminal receipts, 166 returned request hashes and 151 frozen files pass the portable verifier. The independent auditor also rechecks the first 200 outcomes and all 263 frozen files across the three studies. The first repetition has 60 individual outcome readings and 24 assessments reused after exact identity checks on empty tasks. The second has 83 assessments reused after exact identity checks and one repeated timeout without an answer to grade. There are no changed second-repeat answers awaiting individual review. These are source-linked agent assessments, not 168 independent semantic assessments. The original pending labels remain unchanged as historical creation fields.

The holdout maintenance wrapper reported recovery ready at 09:57 UTC. The isolated runtime, protected runtime and receiver were reused by their recorded owners. Original sealed raw-log and configuration-backup hashes still match. The restored normal worker delivered a fresh sixteen-group original 4B report: 570 generated tokens, natural stop, 94.203 seconds and unchanged request bounds. Its full source hashes and accepted report verify, and it finished before common-settings maintenance began at 09:59:17 UTC. At that checkpoint, final normal-operation acceptance remained pending the last phase.

## Common settings and my practical choice

All 48 common-settings requests completed on October 6. Each of the same twelve historical/edge briefs received one request per model. Ten briefs were nonempty. All 48 outcomes were individually read against their supplied facts, catalog and expected contexts; withheld drafts remained ungraded. The offline display audit rendered all 35 delivered answers with the existing renderer.

| Installed artifact | Delivered, out of 12 | Delivered, nonempty 10 | All required contexts displayed, nonempty 10 | Raw strict utility complete, nonempty 10 | Context selections, out of 21 |
|---|---:|---:|---:|---:|---:|
| Qwen3.5 4B | 12 | 10 | 7 | 4 | 18 |
| Qwen3.5 9B | 9 | 7 | 5 | 2 | 9 |
| Qwen3 4B Instruct | 10 | 8 | 2 | 0 | 12 |
| Gemma 4 12B QAT | 4 | 2 | 2 | 2 | 2 |

The extra explicit settings were top_k 20, top_p 1, min_p 0, repeat_penalty 1, presence_penalty 0 and frequency_penalty 0. The original two CPU threads, zero GPU layers, context 4096, cap 700, temperature 0, seed 17, thinking off, keepalive 0 and 120-second deadline remained. Several settings changed together. This exploratory follow-up cannot identify one penalty as the cause, and one repeat per case is less repeat evidence than the native phase. Native templates, tokenizers and quantization still differ.

I would use Qwen3.5 4B with this common profile for the optional scheduled analyst. It delivered every final task, retained 18 of 21 specific context opportunities, and completed the dense omitted-group case with block, UID-fixture and Tailscale explanations in 69.157 seconds. The original 4B again capped on the decreasing-STUN and increased-unknown cases. The 9B timed out on three tasks, including the final dense case. Gemma timed out on eight. Those failures matter for a report with a fixed two-minute deadline.

This does not make the newer 4B's answers complete. It missed required context on three nonempty tasks, repeated citations in several answers, repeated a follow-up step, and often chose generic baseline checks. The renderer removes repeated inference entries and citation links; it does not add missing explanations or remove repeated next steps. Its native-settings simulation results were substantially less useful, and its written report included a material false count. I would keep the typed structured mode and read the deterministic evidence table first. I would not use the longer prose mode for this dashboard.

The model adds no new sensor capability, proven additional detection or measured investigation-time benefit. For a first reproduction, or a system that cannot spare the resource budget, use --no-model. It retains the same counts, priorities, rule context and source links without waiting for inference. Model output remains a conditional first pass for human review, never a firewall decision or an all-clear.

The selected installed artifact is Qwen3.5 4B, Q4_K_M, digest `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`. The CLI, worker, PowerShell launcher and recovery configuration now record both model and generation profile. The original 4B remains an explicit operational fallback with --model qwen3:4b-instruct --generation-profile native. The 9B and Gemma remain evaluation-only. Port 11434 remains refused, and recovery verifies the installed digest without downloading or substituting a model.

Recovery reached ready and a fresh normal report using the selected model/profile passed source-bound validation: 16 retained groups, 631 generated tokens, natural stop, 86.625 seconds. The actual request options match the frozen common profile. Sealed raw-log and configuration-backup hashes still match, protected model tags match, and native collection remains independent. This is one fresh operating acceptance, not multi-day reliability.

## Reproduce and inspect the evidence

The local candidate includes all 416 scheduled outcomes in three separate studies: 200 development/structured/written requests, 168 simulation-source requests and 48 common-profile requests. Keep those lanes separate. Independent and portable audits verify all terminal outcomes, 372 returned-request hashes and all 263 original frozen files. The independent helper's historical status string says partial_no_winner; its actual completed counts are 200/168/48. The verifier does not choose or semantically certify a model.

[The public evidence subset](../model-evidence/PUBLIC_SUBSET_PROVENANCE.json) retains exact model inputs, schemas, expected criteria, request/response artifacts, failures and source-bound agent review supplements. It uses a derived manifest and declares omitted private capture/source assets. Original private full manifests and raw packet evidence remain unchanged. [The offline verification guide](MODEL_STUDY_VERIFICATION.md) explains consistency checks and their boundaries. Reviews are agent judgments rather than independent human scoring. Exact repeats and identical empty inputs are not independent accuracy cases.

The separate 48-hour operating observation remains unaccepted until its elapsed window and receipts are reviewed. Marauder testing is deferred until it is connected. All artifacts here are local drafts; no GitHub repository, push or publication has occurred.
