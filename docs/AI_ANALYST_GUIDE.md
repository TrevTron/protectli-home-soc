# Local evidence analyst

Current release note, October 7: Trevor dropped the fixed 48-hour clause. [Observed operation and recovery](OPERATING_REVIEW_2026-10-07.md) retains interruptions and failures. Current storage uses activated rolling-v2; [Quickstart](QUICKSTART.md) is the operating path. Earlier dated budgets, test counts and pending labels below are historical.

Current first-run instructions are in [Quickstart](QUICKSTART.md). The live selected artifact remains Qwen3.5 4B/common on the isolated Vulkan runtime. [Model identity and selection](MODEL_IDENTITY_AND_SELECTION.md) separates that deployment choice from the larger CPU results. [October 7 verification](OCTOBER7_EVIDENCE_VERIFICATION.md) rechecks saved outcomes offline.

October 6 SQLite/GPU revision: the CPU setup below remains an explicit fallback and the historical model-study configuration. The current reference host uses the isolated opt-in Vulkan runtime. See [deployment](SQLITE_GPU_AND_DEPLOYMENT_2026-10-06.md) and [executed automated investigation results](AUTOMATED_INVESTIGATION_RESULTS_2026-10-06.md). The new overview works independently of inference. The 134-test count belongs to that October 6 checkpoint. Later software checks and complete October 7 experiment receipts are listed in [current draft status](../DRAFT_STATUS.md). The 48-hour observation is unaccepted and includes a maintenance checkpoint gap.

The firewall and Suricata stay on the Vault. A separate owned Windows host receives logs and runs a local first-pass analyst. Tested on the Minisforum with Python 3.12, PowerShell 7.6.5 and Ollama 0.35.1. Other host performance is untested.

## Start the isolated runtime

Use an installed Ollama executable from its official source. The launcher sets process-only environment values, a separate model store and loopback port 11435. It refuses an occupied port. It does not change the default runtime, user/system environment or existing models.

```powershell
.\tools\Start-SocAnalystModel.ps1 -OllamaPath '<official-installed-ollama-executable>'
```

Pull `qwen3.5:4b` into that separate runtime through its own API, following the [official pull documentation](https://docs.ollama.com/api/pull). Confirm the listener owner and endpoint before pulling. Do not run a default `ollama pull` against another project's runtime. The tested model digest is `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`, Q4_K_M, approximately 3.3 GB on disk. Model weights are not included here.

```powershell
.\tools\Start-SocAnalyst.ps1 `
  -PythonPath '<Python-3.12-executable>' `
  -LogPath '<absolute-owned-original-syslog-jsonl-path>' `
  -ClientAddress '<owned-client-LAN-IP>' `
  -MaxRuns 12 -IntervalSeconds 300 `
  -ModelName qwen3.5:4b -ModelProfile common
```

Open http://127.0.0.1:8766/. The original receiver remains at http://127.0.0.1:8765/. The analyst runs 12 snapshots with five minutes between starts, approximately one hour. This command is an explicit finite launcher. Optional automatic recovery after sign-in is a separate task described in [startup and restart](STARTUP_AND_RESTART.md), not a pre-login service or verified 24/7 operation. `-ViewOnly` serves the model-independent SQLite overview and saved views without periodic inference. `Stop-SocAnalyst.ps1` verifies the owned process and refuses an active request; it leaves the receiver and model services alone.

Requests use two CPU threads, zero GPU layers, one request at a time, context 4096, token cap 700, temperature 0, seed 17, thinking off and keepalive 0. Windows spare-memory preflight refuses below 16 GiB. Runtime logs and API loaded-model metadata, rather than a flag alone, established CPU execution and zero GPU memory here. The existing fine-tuning runtime is protected; requests to port 11434 are refused.

## Interpret the output

Deterministic code reads a fixed 16 MiB tail, groups only the owned client's EVE alerts and counts current/prior receipt windows. Alert counts are not unique connections. A group includes SID, action, severity, protocol and endpoint aliases. New refers only to these observed windows. Clipped or invalid history can make novelty unknown. Blocked/severity-1 groups retain their review-first floor, and the report shows omitted group counts.

The model selects observed fields, cited possible interpretations, unknowns and read-only review steps. Group-bound schema limits reference/code choices, and an independent validator still rejects wrong values, invented citations, unsupported meanings, malformed output or a token-capped response. There is no autonomous tool execution, alert suppression, allowlisting or firewall change. Raw URLs, hostnames, signatures, payloads and addresses do not reach the model.

Evidence links pin their original snapshot and recheck the record SHA256. Pacific display time uses America/Los_Angeles timezone rules; raw timestamps are unchanged. From an original alert page, the flow review compares full bidirectional protocol/IP/port tuples across PF and Suricata within 60 seconds of receipt. The inspected IPv4 TCP/UDP filterlog format is supported. It does not guess NAT translation, IPv6, unlogged policy decisions or client outcomes. Missing PF evidence means unknown.

A rule match is not proof of intrusion. Allowed is not proof of safety. A reported block is not proof that every request failed. Intent and incomplete visibility remain explicit. Known STUN, UID-fixture and inspected Tailscale control-plane rule contexts are possibilities, not application attribution.

## Tests and evidence

```powershell
Set-Location tools
py -3.12 -m unittest test_soc_analyst test_soc_analyst_server test_soc_flow_review test_soc_endpoint_context -v
```

These checks exercise ingestion, coverage, wrong facts/references, untrusted text exclusion, priority floors, source integrity, safe rendering, memory refusal, evaluation-only model admission, unavailable/capped models, exact flow correlation and false endpoint attribution. They are not a model-accuracy score. See [the actual local evaluation](AI_ANALYST_RESULTS.md) for failures and measured runs.

An optional operator-captured Windows connection receipt can be bound to an exact original alert hash through a private endpoint-context index. The viewer validates its tuple, connection creation against EVE flow start, process/service lineage, observation bounds and receipt hash before display. That is historical positive context, outside the model. No match remains unknown. This version does not automatically collect endpoint activity, reconstruct past connections, prove the running binary from an installed-file signature or declare traffic benign.

## Reproduce model-candidate delivery

[The dated research](MODEL_COMMUNITY_RESEARCH.md) explains why the current candidates include Qwen3.5 4B/9B and Gemma 4 12B QAT. Download only the candidates you intend to test into the separately owned runtime, verify its listener and model metadata, and stop the periodic analyst before replay. Keep the original receiver running. Operating-model admission remains narrower than explicit evaluation admission.

```powershell
py -3.12 tools/evaluate_analyst_models.py `
  --fixtures examples/analyst-evaluation `
  --output private/new-model-evaluation `
  --models qwen3:4b-instruct qwen3.5:4b qwen3.5:9b gemma4:12b-it-qat
```

The output directory must not exist. The harness freezes saved synthetic briefs before requests, refuses a preloaded isolated runtime, records complete responses/model metadata/rejections and waits for normal unload before the next request. Missing candidates are refused rather than downloaded or substituted. Request limits are unchanged. Model templates, tokenizers, quantization, defaults, cold loads and unequal natural answer lengths are disclosed; one run per case is exploratory, not a general accuracy or throughput ranking. The original private experiment additionally sampled available memory and loaded-model metadata during each request.

Legacy storage stops retaining new records at the aggregate cap. The current activated rolling-v2 policy uses 1 GiB hot and 4 GiB compressed cold storage, with seven-day sealed-segment expiry and visible early expiry under capacity pressure. [Quickstart](QUICKSTART.md) covers activation; [current retention](LIVE_ROLLING_RETENTION_2026-10-07.md) covers baseline and source pins.

The [earlier three-case comparison](MODEL_COMPARISON_RESULTS.md) retained the baseline at that checkpoint: three accepted deliveries from three known regression cases, versus one per researched candidate. This small CPU-host test is not a general model ranking.

## Earlier operator checkpoint, before sign-in recovery

The current dashboard includes Health and coverage, a source-bound Review queue and Saved reports. Operator annotations persist across viewer restarts in an append-only, hash-chained private journal. New evidence requires fresh review; notes never enter model input, change a priority floor or suppress an alert. A 1MiB journal cap and changed-source refusal preserve the original record. See [the operating workflow](OPERATOR_WORKFLOW.md).

The explicit native-health sampler runs the fixed read-only USB collector at the launcher's finite cadence, independently of inference. Its two-observation/30-second verification completed without collector failures; readings were 38 C then 36 C, with healthy pools and unchanged configuration. The resumed 300-second sampler read 38 C. Its current state, timestamp, receiver freshness/retention and wider-coverage gaps are visible. At this earlier checkpoint, neither sampler nor analyst was autostart or 24/7. The later optional sign-in recovery task is documented in [startup and restart](STARTUP_AND_RESTART.md); its bounded observation remains unaccepted.

[The equal development/new-case study](MODEL_REFINEMENT_RESULTS.md) supersedes the first exploratory model choice. All four received two common development requests and one additional request after a single shared grammar revision. The old 4B supplied every required context in 3/3 new cases, so it remained the bounded default at that earlier checkpoint. No weight training occurred. A fresh live UID-fixture report under the selected v5 schema passed in 33.094 seconds. Historical controlled-block and Tailscale annotations remain separate from current alerts.

## Current model choice, October 6

The [completed expanded comparison](MODEL_COMPARISON_EXPANDED_RESULTS.md) supersedes the small earlier choice. The optional default is Qwen3.5 4B with the common profile. It delivered 12/12 final tasks and displayed every required context on 7/10 nonempty tasks, with remaining omissions and repeated follow-up recorded. Use --model and --generation-profile on the one-shot CLI, or -ModelName and -ModelProfile on the PowerShell launcher. The original 4B/native profile remains an explicit fallback. Recovery requires ModelName, ModelDigest and ModelProfile in its private configuration and refuses an active viewer with a different selection. It never downloads a missing model.

The common profile adds top_k 20, top_p 1, min_p 0, repeat_penalty 1, presence_penalty 0 and frequency_penalty 0 to the unchanged resource bounds. The evaluation harness defaults explicitly to native settings for historical reproductions; pass --generation-profile common for the common profile. Neither changes the shared prompt or schema. Start with --no-model for a deterministic report. The latest full software suite has 84 passing checks; those checks are separate from model judgments.

## October 7 AI follow-up, integrated October 8

The [follow-up guide](AI_FOLLOWUP_RESULTS_AND_VERIFICATION.md) records a selectable saved-result workbench, 15/15 permitted-menu demonstrations, the 60-request harder F-pack and 102-request Ling calibration/transfer/addendum phase. All 219 follow-up requests are included in the reviewed public derivative with an offline verifier. Gemma's first-pack 8/12 and Qwen3 4B's revised-pack 4/12 belong to different prompts/cases; revised Ling reasoning reaches 3/12 strict. Original failures, the guard stop and one-fixture sensitivity remain visible. No new weights were trained, main-dashboard integration or human-benefit claim is established, and the ordinary Qwen3.5 4B/common Vulkan deployment is unchanged. Earlier tables above are dated observations.
