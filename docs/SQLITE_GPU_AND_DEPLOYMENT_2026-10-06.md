# SQLite, GPU analysis and deployment

Updated October 7 for activated rolling retention. [Quickstart](QUICKSTART.md) is the current installation path. The larger CPU retest and fresh constructed study are separate from the live reporting configuration; see [their public verification](OCTOBER7_EVIDENCE_VERIFICATION.md).

October 6, 2026. This implementation extends the existing owned Windows reference build. The Vault remains the firewall and inspection point. The analyst has no control over its policy.

## The default build uses two machines

The Protectli Vault runs OPNsense and Suricata. The Minisforum receives UDP syslog, preserves original JSONL segments, maintains a derived SQLite index, serves the local dashboard and runs optional local inference. A third computer is not required.

The current deployment recovers after Windows sign-in. Turning off this host stops its collection and dashboard. The Vault continues enforcing its own rules and retaining its own local logs. Optional inference is separate from firewall enforcement.

An SBC split is an optional future deployment. The SBC would receive and store records, index them and serve the dashboard. The Minisforum would process bounded analysis jobs when available. The SBC does not need to run a model. Collection would continue without the inference host; reports would show unavailable or stale status. This requires explicit job transfer, verified source identity, bounded queues, freshness and recovery controls. The current code has not been deployed or verified across two hosts. It does not already provide a remote inference queue.

Trevor selected the Vault plus Minisforum as the default. A K1 is not set up. Nova may be powered on, but the last recorded Tailscale inventory reported its connection offline with an expired key. X1S was also unavailable in that inventory. The Pi already carries a media lab and remains outside this migration. Device presence is not a resource or application-health test. No SBC was reconfigured.

## Original records and the index

`soc_index.py` indexes complete records from the logical JSONL source and its append-only segments. Original bytes remain authoritative. The database stores physical segment identity, logical offset, byte length, SHA-256 and parsed event fields. It reparses original EVE text instead of trusting a cached event field.

Transactions persist checkpoints. Partial final lines wait for the next pass. Restart is idempotent. Truncation, changed checkpoint bytes, source-path changes and sealed-segment changes refuse continuation. An original-source request rechecks the complete record hash before displaying it. A copied source at a new host needs a new derived index and verified original bytes; saved Windows source mappings are not silently rewritten.

The database uses SQLite WAL, synchronous FULL and a 1 GiB page budget. WAL checkpoint and journal retention settings reduce sustained journal growth; they are not an absolute peak disk-use guarantee. Activated rolling-v2 retention now uses 1 GiB hot originals and 4 GiB compressed cold segments. Sealed ordinary segments expire seven days after sealing; capacity can shorten the window with visible early-expiry counts. Cold bytes are restored and verified before a hot copy is reclaimed. The preserved setup baseline and new review-note pins have separate preservation paths. See [current retention](LIVE_ROLLING_RETENTION_2026-10-07.md) and [the activation steps](QUICKSTART.md#5-enable-bounded-rolling-retention). The October 6 no-reclamation state is historical.

## Dashboard and repetition

The overview at port 8766 shows the latest Vault temperature and its age, indexed evidence, grouped alerts, model state and collection coverage. The original receiver diagnostic remains on port 8765. The analyst report, saved reports, review notes and health remain separate links.

Grouping requires the same SID, GID, revision, signature, action, alert severity, protocol and complete source/destination IP and port tuple. Missing context stays separate. Counts and first/last receipt remain visible. Blocked and severity 1 events stay first. Expand a group to see individual records and their hash-bound original-source links. Group and member pages use a fixed received-time window so pagination does not drift with fresh traffic.

This first noise-reduction step collapses exact repetition. It does not suppress alerts, change firewall rules or declare traffic harmless. Scoped expected-context policies remain future work, requiring version, reason, reviewed evidence, expiry, preview and rollback. TriageWall is related work and a design influence; its code was not copied into this implementation.

Index refresh, native-health collection and page rendering operate separately from inference. GET requests do not trigger generation. If the model takes longer or becomes unavailable, the page can still display evidence. This separation is exercised locally; simultaneous multi-user load and another host's capacity have not been measured.

## Isolated GPU runtime

The CPU fallback remains on loopback port 11435. The opt-in Vulkan runtime uses loopback port 11436 and the SOC-only model store. The unrelated port 11434 service remains protected. No model weights were downloaded for this upgrade.

`Start-SocGpuProbe.ps1` starts the isolated runtime with Vulkan enabled, one visible Vulkan device, one parallel request, one queued request, one loaded model, a 4096 context and keepalive zero. `Start-SocAnalyst.ps1 -Acceleration vulkan` selects it; CPU remains the launcher's explicit default. Recovery configuration must match the chosen backend and recorded runtime directory.

Actual runtime logs identify AMD Radeon 8060S Graphics and 33/33 offloaded layers for Qwen3.5 4B. The GPU shares system memory. One live common-profile report returned 309 generated tokens in 20.781 seconds, stopped naturally and passed the report validator. It still gave limited generic follow-up and did not establish complete investigation usefulness. This is an observed acceptance run, not a matched CPU/GPU performance comparison.

The existing deadline, spare-memory guard, fixed common options, source validation and no-autonomous-action boundaries remain. Historical CPU studies are preserved as separate experiments. GPU acceleration does not establish higher semantic accuracy. See [Ollama's hardware documentation](https://docs.ollama.com/gpu) for backend support, and verify actual logs on a different host. An SBC's advertised GPU or NPU TOPS does not establish compatibility with this installed GGUF runtime.

## Optional remote access

Phone access does not require an SBC or a different collector OS. The current viewer is loopback-only; no new Tailscale Serve route or WAN exposure was enabled. A future tailnet HTTPS route needs an explicit audience, authentication/access checks, correct proxy host/origin handling and separately protected review writes. [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) is the candidate access mechanism. The phone-sized layout has been inspected locally; a real phone connection is still untested.
