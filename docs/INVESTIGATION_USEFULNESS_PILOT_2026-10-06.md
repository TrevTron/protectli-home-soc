# Single-operator investigation pilot

Protocol prepared October 6, 2026. Not executed. Trevor is the participant; the assistant prepares evidence, coordinates sessions and scores against a frozen source-backed rubric. The assistant is not an independent human reviewer. This pilot can demonstrate usefulness for Trevor on specified cases, not general analyst performance or consumer-market validation.

## Question

Does the analyst help Trevor make an evidence-supported decision and find the next useful check, compared with the same available evidence without model selections? Does repetition collapsing reduce effort while preserving important observations?

The model selects from code-owned interpretations and steps, so the evidence-only condition must expose the same deterministic rule context and available explanation catalogue. Hiding that information in the baseline would create an unfair advantage. Avoid comparing a polished assisted UI against a deliberately poor raw-log table.

## Conditions

| Code | Participant sees |
| --- | --- |
| A | Evidence, rule context, deterministic counts/actions/priorities and all eligible explanation/step text; no model-selected findings |
| B | Identical information and navigation plus the analyst's validated selected findings |
| C | B plus visible repetition collapsing; all records remain accessible |

Keep all conditions' fonts, timestamps, evidence links, deterministic health warnings and available next checks equivalent except the intended feature. No active suppression policy is tested in this first study. Narrow policies need their own later new-case evaluation.

## Preparation

Create two practice cases excluded from results, then an initial six-case pilot (two matched triplets). If the session workflow works, expand with fresh cases to 18 measured cases total (six triplets), across three short sessions. Do not reuse the same case in another condition.

Each triplet contains distinct cases of approximately matched difficulty and evidence volume. Cover expected routine activity with supporting context, a controlled blocked fixture with a recorded client result, suspicious activity that genuinely needs more investigation, missing collection that prevents an all-clear, endpoint/context changes among repeats, and contrasting allowed/blocked records. Suspicious does not mean confirmed compromise. Synthetic or replayed cases must be labeled in the methods; do not manufacture a real incident claim.

Truth comes from known fixture construction, verified original records, actual controlled client results or independently recorded endpoint evidence. An alert signature alone cannot label intent. Freeze case files, source hashes, exact known facts, acceptable unknowns and grading criteria before generating model answers. Keep answer keys outside participant/model inputs. Case preparation and grading by the same assistant remain a disclosed limitation.

Randomize which matched case receives each condition. Counterbalance condition order across triplets using different A/B/C permutations. Preserve the assignment and its generation seed privately before the first session. Anonymize case titles and opaque IDs so names do not reveal the expected conclusion. Record prior exposure; a case Trevor has already investigated becomes practice, not an unseen result.

## Each task

1. Open the assigned case and start a local timer. Record pause intervals, navigation errors and time spent waiting for analysis separately.
2. Trevor records what happened, whether it was allowed or blocked, and whether that proves the client outcome.
3. Trevor chooses: expected activity with recorded support, investigate further, or insufficient evidence to decide. An appropriate uncertainty answer earns credit.
4. Trevor records the exact evidence reference supporting the conclusion, the important unknown and the next read-only check.
5. Lock the initial answer before hints, model discussion or rubric reveal. No coaching during a measured case.
6. Reveal the relevant next-check evidence if requested. Record whether it changes or supports the conclusion, then lock the final answer.
7. Collect an effort rating from 1 (easy) to 5 (hard), and one sentence on what helped or confused Trevor. Debrief after the matched block, not midway through it.

Use a monotonic local timer, not chat timestamps or server model time, for task effort. Track both interaction time and total elapsed time. The primary timing endpoint is a correct completed investigation, not merely the fastest submission. Wrong fast answers stay wrong. Breaks and incomplete tasks stay recorded; do not delete them or rerun the same case as a fresh trial.

## Frozen rubric and metrics

Grade source-bound factual observations, sensor/client distinction, appropriate uncertainty, original evidence choice and usefulness of the next check separately. Use 0 = wrong/unsupported, 1 = materially incomplete, 2 = correct/sufficient for each, with case-specific criteria written before answers. Record unsupported claims, missed important events and false reassurance as separate flags so a high summed score cannot hide a serious error. Record model delivery failures and manual-mode usability.

The next check is useful if it resolves a defined uncertainty, tests a plausible competing explanation or identifies the precise missing evidence. Generic "monitor the network" wording is not sufficient when the case requires a particular record or endpoint observation. A read-only check may validly conclude that the question remains unresolved.

Compare descriptive per-condition correct-completion counts, rubric components, median times among correct completions, all failure/timeout counts, evidence retrieval time, effort ratings and serious-error flags. Show individual rows and matched-case differences. With one participant and a small set, do not claim statistical significance, general accuracy or superiority for all users. An optional external reviewer can later check labels and grading without seeing condition labels; no outreach is authorized by this protocol.

## Integrity and later work

Hash cases, assignment, rubric, model/profile/runtime settings, displayed reports and locked answers. Verify evidence links independently. Preserve any disagreement and the original grade, with a separate reasoned correction rather than overwriting it. These cases become exposed after use and cannot become a future model holdout. No training on measured cases during the pilot.

Repetition controls must prove that counts remain correct, original links work, changed endpoints/actions/severities remain visible and an important event inside many routine repeats is still found. Later policy testing must include scope changes, missing context, expiry and rollback. A single successful case does not establish policy safety.

## Participant answer form

| Field | Value to record |
| --- | --- |
| Case ID / condition | Assigned privately |
| Start / finish / pauses | Local timer receipt |
| What happened | Trevor's initial description |
| Allowed or blocked | Observed sensor action |
| Client outcome | Supported result or unknown |
| Disposition | Expected with support / investigate / insufficient evidence |
| Supporting original reference | Exact record ID |
| Important unknown | What this evidence cannot establish |
| Next check and reason | Specific read-only action |
| Conclusion after next check | Final locked answer |
| Effort / confusion | 1-5 and a sentence |

Next execution step: build and verify the two practice and six initial measured cases with their private sealed rubric. No participant result exists yet.
