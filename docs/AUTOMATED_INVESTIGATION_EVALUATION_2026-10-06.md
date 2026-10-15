# Automated investigation evaluation

Prepared October 6, 2026. Software controls and real-source pack construction are checked. No inference requests, model-review outcomes or human investigations have been executed under this protocol. This is a separate new evaluation, not a revision of the completed 416 historical model outcomes.

Trevor asked for an automated model-team approach that can run while he is busy with his main job. That is practical for source-grounded decision checks, explanation review and regression detection. It cannot establish whether a person understands the dashboard, feels less overwhelmed, or finishes an investigation more easily. Public wording should call it an automated, source-backed investigation evaluation. It must not hide AI participation or describe automated model roles as independent human analysts.

## Roles and authority

1. A model under test produces the existing constrained analyst report. Deterministic validation remains mandatory. Failure, timeout, capped generation and unexpected thinking are retained outcomes, not silently repaired answers.
2. An investigator model receives the evidence in conditions A, B and C. It returns a structured investigation decision. Freeze this response before any reviewer sees it.
3. A different installed model digest reviews the locked answer for omitted evidence, unsupported claims and useful next checks. It does not receive the oracle, expected answer, source fixture name or condition label in its prompt. Runner receipts still retain condition and model identities for reproducibility.
4. A deterministic grader compares decisions, observed values and exact source references with the sealed oracle. Model consensus cannot turn a wrong answer into a pass. Reviewer disagreement is preserved alongside the original score.

Distinct model roles are not independent humans. Different weights and blinded prompts reduce direct contamination but do not eliminate correlated training, common failure modes or the case author's influence. If the same model digest must fill more than one role, disclose that reuse. No reviewer "independence" claim follows from separate processes.

The assistant prepares the protocol and source selection. The raw parser checks record bytes separately from the analyst's cached groups. This provides deterministic corroboration of counts and citations, not independent semantic certification of every interpretation. The interpretation catalogue remains the project's existing code-owned catalogue.

## Initial case pack

`tools/soc_investigation_eval.py build` creates a new directory and refuses to replace one. Its source is the existing frozen October 5/6 simulation tree. Six source cases are copied; two derivatives are clearly labeled. All source records and frozen historical results remain unchanged.

| ID | Phase | Source or construction | What is checked |
| --- | --- | --- | --- |
| P01 | Practice, excluded | Upstream `detect-icmp-seq` replay | Signature observation, source citation, uncertainty |
| P02 | Practice, excluded | Upstream `flow-drop-iponly-01` replay | Reported block versus unknown client outcome |
| M01 | Measured | Original UID HTTP simulation receiver records | Allowed rule matches, UID fixture possibility, supporting records |
| M02 | Measured | Exact positive TLS policy receiver records | Reported block, specific observed count, unresolved client outcome |
| M03 | Measured | Corresponding negative TLS policy receiver records | No supplied alerts is not an all-clear |
| M04 | Measured | Upstream DHCP parse replay | No alert does not establish healthy or complete collection |
| M05 | Measured | Twenty copies of the UID stream plus one copy of the blocked TLS stream | Repetition cannot conceal the blocked group or change counts |
| M06 | Measured | UID records with an explicitly constructed missing-context notice | Missing endpoint/continuity context must trigger a visibility check |

M05 duplicates original record lines without pretending they are new real network events. It tests multiplicity and presentation, not realistic burst timing. M06 does not claim production collection actually lost records. Its missing-context condition is constructed and disclosed.

These historical source cases were already used in model studies. They are exposed regression material, not a fresh unseen holdout, and they contain no confirmed live intrusion. Do not use these results to claim general detection accuracy, zero-day detection, human usefulness or improved protection of the apartment network. Fresh cases with new controlled evidence are a later extension. No new packet transmission or detector-policy edit is required to build this pack.

The complete pack has eight cases and 56 case files. Every file is SHA-256 bound in `manifest.json`. `oracle.json` is retained in the private pack, outside all exported model inputs. Each original source line is checked by byte offset, length and full digest. A separate raw EVE parser recomputes aggregate SID/action/severity/protocol alert counts and verifies the supplied group totals. The source binding is also verified for every group's cited record. Derived oracles are checked again against this construction, rather than trusting an editable answer key alone.

Keep the manifest hash in the execution receipt and compare it before and after model requests. Treat a changed manifest as a new pack, not a continuation of the old run. The software detects membership, content, source-byte, count and oracle mismatch; the external execution receipt is the seal against replacing the entire pack and manifest together.

## Equal-context A/B/C

| Condition | Automated investigator input |
| --- | --- |
| A | Same numeric observations, aliases, eligible interpretation catalogue, visibility/context and all read-only checks; expanded record membership; no selected analyst report |
| B | A plus the source-bound validated report from the analyst under test |
| C | B with repetition membership encoded as grouped reference/count pairs |

All groups, original reference IDs and record multiplicities remain available. A/B's expanded membership and C's grouped membership preserve the same members and counts. Code tests reconstruct the expanded rows from the collapsed view and compare them. The common deterministic context hash must be identical within each case triplet. No suppression policy is tested here.

This C condition tests model-facing information representation, not a person's navigation through a rendered dashboard. Model request latency and token use may change because expanded and collapsed encodings have different lengths. Do not call such a result an equal-workload inference-speed comparison. The dashboard's actual grouping and policy implementation needs its own UI and retention tests.

The jobs omit raw payloads, untrusted signature text, original source paths, descriptive fixture names and the oracle. A control puts instruction text in a test signature and verifies that it never enters the exported model request. This checks the normalization boundary; it does not prove immunity to every prompt-injection technique.

## Execution and timing

The tool currently builds/verifies packs, exports requests and grades returned decisions. It intentionally makes no network or inference calls. Actual request execution must use a separate owned and verified inference runner after root-agent resource acceptance. It must not contend with the normal report loop or touch the protected port 11434 model environment.

For every request, retain the installed model digest, model metadata, explicit backend, runtime version, exact request SHA-256, response content and thinking channels, start/completion times, monotonic request duration, prompt/evaluated token counts, natural/capped stop reason and every timeout/error. Defaults are the existing common profile: temperature 0, seed 17, context 4096, generation cap 700, two CPU threads and GPU 0. A later GPU evaluation must explicitly record its changed backend/settings and actual offload evidence. Do not silently alter bounds or compare it as the same historical CPU study.

Run all eight analyst-source jobs first and freeze accepted reports with their exact brief-file hashes. Then prepare 24 investigator jobs, including six practice requests and 18 measured requests. Run one model request at a time unless resource controls explicitly support concurrency. Use a predetermined randomized case/condition order and repetitions in the runner; save that schedule before executing. Different generation jobs are independent requests with no conversation history or in-context answer reuse.

The models can see the same case in all conditions because they have no retained session memory. This is a within-case automated comparison, not the human matched-case design from the earlier operator pilot. Record all attempts. Do not select the best retry. If one condition fails, the row remains in the comparison.

Reviewer jobs must be produced from locked investigator answers. They exclude duration, status, model name, condition, and selected assistance from reviewer prompt content. Code-owned evidence and the answer remain. Reviewers suggest disagreements and next checks; their prose does not replace deterministic grading.

## Decision contract and metrics

The investigator returns observed group IDs, exact typed SID/action/count values and evidence references; supported decision codes; eligible context codes; client outcome; intrusion status; delivery status; and read-only next-check codes. This is a bounded decision task, not open-ended proof that the model can perform a full incident investigation.

The oracle requires appropriate rule context, every retained group, correct source values, at least one valid reference per group, unknown client outcome, unestablished intrusion and no complete-delivery claim. A source-reported block cannot be converted into "the client failed." An alertless replay cannot be converted into "network is safe." The missing-context derivative requires a visibility check. A next-check selection earns credit only for choosing the specifically required check. The software does not execute that check or demonstrate that a real uncertainty was resolved.

Report every row, including practice separately. For measured rows, report correct completions out of 18 scheduled, missing/failure/timeout counts, unsupported claims, omitted groups, missed reported blocks, missed visibility warnings, and exact-citation/count errors. Report elapsed time and token use for correctly completed cases alongside all failure rows. Wrong fast answers remain failures. Never calculate human effort, time-to-find-record, workload reduction or usability from model request duration.

The scoring output is append-only by new filename. Corrected assessments get separate files with reasons and original hashes. No historical study row, private raw log or frozen oracle is overwritten. Automatic scores and model review comments remain separately attributable.

## Commands

Use the verified bundled Python path or another known project Python interpreter. Examples use `python` as a placeholder; on this Windows account the Store alias is not a working interpreter.

```powershell
python tools/soc_investigation_eval.py build --fixtures private/upstream-suricata-verify-20261005 --output private/investigation-eval-20261006/cases
python tools/soc_investigation_eval.py verify --pack private/investigation-eval-20261006/cases
python tools/soc_investigation_eval.py jobs --pack private/investigation-eval-20261006/cases --role analyst --output private/investigation-eval-20261006/analyst-jobs.json
```

`assistance.json` maps each case ID to `{ "brief_sha256": "exact hash of its brief.json", "report": { "observed": [], "inferred": [], "unknown": [], "next_steps": [] } }`. Those report arrays must contain the actual independently validated returned report; the empty example is a structure illustration, not a valid nonempty-case result.

```powershell
python tools/soc_investigation_eval.py jobs --pack private/investigation-eval-20261006/cases --role investigator --assistance private/investigation-eval-20261006/assistance.json --output private/investigation-eval-20261006/investigator-jobs.json
python tools/soc_investigation_eval.py score --pack private/investigation-eval-20261006/cases --answers private/investigation-eval-20261006/answers.json --output private/investigation-eval-20261006/scores-01.json
python tools/soc_investigation_eval.py jobs --pack private/investigation-eval-20261006/cases --role reviewer --answers private/investigation-eval-20261006/answers.json --output private/investigation-eval-20261006/reviewer-jobs.json
```

`answers.json` maps each scheduled ID, such as `M02-A`, to `{ "status": "completed", "elapsed_s": 12.3, "answer": { ...decision contract... } }`. Use the measured monotonic request duration, not a fabricated example value. Missing keys stay missing outcomes in the score table. Non-completed statuses cannot become correct completions even if diagnostic content resembles an answer.

## Verified software controls

The tests cover valid source packs; changed record bytes; rehashed but false oracles; wrong cached counts; changed source offsets; false client-failure conclusions; false all-clears; blocked events omitted among repetitions; missing-context omissions; fabricated/duplicate references; wrong numeric types; malformed group IDs; normalization of injected signature instructions; equal deterministic context; reversible repetition encoding; missing assistance refusal; preserved missing rows; timeout treatment; and refusal to replace an existing pack. These are software controls, not model outcomes.

The real-source construction smoke test independently checked P01/P02's one alert each, M01's three alerts, M02's one blocked alert, M03/M04's zero alerts, M05's 61 alerts with four distinct referenced records, and M06's three original UID-stream alerts. Temporary smoke-test output was removed; root-agent execution can create the permanent private pack and retain its manifest hash. No model calls or live detector changes were made for this verification.
