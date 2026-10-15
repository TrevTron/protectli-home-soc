# Correcting the automated investigation contract

October 6, 2026. This is a separate research workflow. The live constrained analyst and firewall policy are unchanged.

The original study is frozen in the previous candidate with its zero of 18 measured passes and 24 capped reviews. The original source pack, requests, raw responses, scores and publication subset remain unchanged. New development and execution use separate directories and explicit versions.

## What changed and why

The original investigator received a schema for constrained decoding but lacked a complete description of the required output fields in the trusted system prompt. It returned real groups alongside contradictory no-alert decisions, invented empty-case observations and duplicate choices. The prose reviewer reached its 700-token cap on every request and sometimes criticized conservative uncertainty as if it were an affirmative finding.

Development retained four attempts, each with two investigator cases and two blind reviewer controls. V2 supplied field meanings with the evidence; V3 removed schema-constrained decoding; V4 placed the complete schema and semantics in trusted instructions. V2 and V3 failed the full checks. V4 fixed the empty case and both reviewer controls, but still contradicted the observed alerts and missed the missing-context decision on the second investigator case. These are observations under changing contracts, not proof that one isolated variable caused every failure.

V5 keeps the trusted instructions and gives each decision, context code and next check its own required boolean slot. The model selects true or false. It still authors the observation table, which must match original group IDs, SID/action/count values and citations. The decoder converts true slots into decision lists without correcting any value. It refuses missing slots, extra fields or non-boolean values. This removes duplicate decision choices by construction; it does not prove the model learned to avoid duplicates in arbitrary prose.

The reviewer has six boolean defect categories and an omitted-group-ID list. Its trusted instructions define each defect and distinguish unproved completeness from proved loss, and unestablished intrusion from an all-clear. Its output is a supplementary opinion. An independent deterministic source oracle determines the scores. The review contract tests these specific defects, not every possible narrative flaw. The first full V5 run exposed false alarms on all six empty-case reviews and five failures among six strict reviewer controls. Naturally completed reviews are not necessarily correct.

V5 recorded 16 of 18 measured investigator passes. The two expanded mixed-case requests capped, while the collapsed condition passed. Runtime stderr then showed that the 5,107- and 5,464-token expanded prompts had each been truncated to 2,050 under the 4,096 context. Exported equal-context hashes therefore did not establish equal actual model input. That A/B/C execution comparison is invalid; its raw outcomes remain unchanged.

V6 changes only the investigator context to 8,192. A development request on the same expanded case retained its exact V5 prompt, received all 5,107 tokens, completed naturally with 360 generated tokens, and passed the independent checks. The 700-token generation cap was sufficient after the input was preserved. Analyst and reviewer context remain 4,096. Every new request must retain an append-only runtime-log slice and verify one positive prefill, the requested context and matching returned prompt count, with no input-truncation warning. Empty startup warmups are retained separately. Unknown, rotated or ambiguous traces refuse delivery and halt subsequent requests.

A separately recorded 9B reasoning trial used thinking enabled and a 2,048-token generation cap. It produced a thinking channel but no final answer before capping. Its initial context-trace guard also refused an empty startup warmup; the corrected guard is covered by positive/negative tests. The reasoning mode is not adopted, and the unexecuted following development controls are not presented as results. No reasoning trace is treated as proof of correctness.

## Freeze, cases and equal conditions

The full run is preceded by a sealed plan, exact tool copies and a case manifest. No tuning occurs after execution begins. The new case pack uses unchanged historical source-record bytes with constructed multiplicities and new endpoint aliases. M01 has three copies of the UID stream, M02 two copies of the blocked TLS stream, M05 two copies of the mixed repetition stream and M06 four copies of the UID stream with explicitly unavailable comparison context. Negative cases retain their original zero-alert records. Practice remains separate from the six measured cases.

These are disclosed historical-source derivatives. They are not unseen incidents, fresh traffic, real attack bursts or observations of actual collection loss. A first preparation attempt chose the wrong client across unrelated fixture sources; the independent raw-count check rejected it before any model call. Its partial output is preserved. The corrected preparation derives each case's client from its original owned-client mapping.

All A/B/C variants carry the same deterministic facts, visibility, eligible interpretation catalogue, checks and output instructions. A omits selected analyst assistance. B includes its validated report. C also collapses the expanded membership representation without dropping any member. Within-case deterministic context hashes must match. Representation length can differ, so request duration is not an equal-workload speed benchmark.

The 4B analyst and investigator reuse the same installed digest. The reviewer uses the distinct installed 9B digest; correlated training is possible. Review input excludes condition, model identity, timing and expected verdicts. Six separately scored reviewer controls deliberately introduce unsupported certainty, a missing block decision, a missing blocked group among repetition, a missing visibility warning/check, a wrong count, and a duplicate context code. Defect labels and answer keys are not sent to the reviewer.

## Bounds and failure preservation

Every actual request retains its exact request and raw response hashes, content and thinking channels, naturally completed or capped stop reason, actual prompt/generated token counts, monotonic HTTP duration, and observed runtime model digest/GPU allocation. The final selected research bounds are 700 generated tokens, 8192 investigator context and 4096 analyst/reviewer context, a 120-second HTTP deadline, at least 16 GiB spare RAM, one request at a time and keepalive zero. The live analyst's settings remain unchanged. No retries, model downloads or protected-runtime requests are made.

All investigator/reviewer completions require natural stop and strict JSON parsing. A transport-completed JSON answer can still fail the independent semantic grade. Wrong, missing, refused, timed-out and capped rows remain in their scheduled denominator. Duplicate-array failures now also enumerate the underlying semantic contradictions in the new assessment; the stored original scores are never rewritten.

Periodic live inference is deliberately paused to prevent competition. The original receiver, SQLite index and finite native-health sampler remain active. A finite maintenance observer records collection, old-report freshness and native health while ordinary recovery is paused. The original observation dates and recorded gaps are retained. After the separate study finishes, only the verified study viewer/pause are stopped or archived, and a fresh live report plus recovery check is required.

## Reproducing the method

Use the installed project Python interpreter and an already owned isolated runtime on loopback 11436. Keep the unrelated 11434 service protected. Build and verify a private pack from the pinned source workflow first. These commands make requests only after explicit resource and ownership acceptance:

```powershell
python tools/soc_investigation_v6.py --pack <new-private-pack> --output <new-private-run> --backend-receipt <verified-private-backend-receipt> --runtime-log <owned-runtime-stderr>
python -m unittest discover -s tools -p 'test_*.py'
```

The public copied subset omits original raw JSONL, private source mappings, runtime process ownership and complete stderr. It declares those omissions and preserves copied request/response bytes. It is not a full portable replay of private original sources. Software tests build disposable source packs and include wrong-fact, false-all-clear, missing-block, uncertainty, malformed-slot and reviewer-defect controls.

## What the completed result establishes

V6 passed all 18 measured and six practice investigator checks with full input proof. All 24 reviews completed, but only 18 checklists matched the independent categories and only one of six strict reviewer defect controls passed. This establishes correct decisions and source fidelity for this bounded investigator contract on these constructed cases, alongside an unreliable reviewer. It does not establish reliable arbitrary incident investigation, improved human accuracy, faster human review or an advantage over TriageWall. All A/B/C conditions passed, so the result does not show analyst assistance or grouping improved accuracy. The human usefulness protocol remains a separate unexecuted test.

The executed V6 wrapper and exact tools are frozen before requests. After execution, the reusable CLI was corrected to require the same runtime-log argument and record the same role options. That packaging fix did not change prompts, responses or the executed study.
