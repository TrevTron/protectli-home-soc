# How this build relates to TriageWall

October 7 update: activated rolling-v2 now reclaims verified sealed hot segments and expires ordinary sealed originals under time/capacity bounds. Baseline/pins and same-disk source restoration are checked; full host-loss restoration and seven-day live operation remain unproved. Earlier October 6 storage comparisons below describe that dated implementation, not the current storage policy. [Current retention](RETENTION_ARCHIVAL_AND_OBSERVATION.md) and [quickstart](QUICKSTART.md) supply current operating instructions.

Reviewed October 6, 2026 against the current [TriageWall README](https://github.com/aaronphifer/triagewall), [operations guide](https://github.com/aaronphifer/triagewall/blob/main/docs/operations.md) and [threat model](https://github.com/aaronphifer/triagewall/blob/main/docs/THREAT_MODEL.md). This is a source/documentation comparison. TriageWall has not been installed or benchmarked in this project.

Both projects use local inference, retained sensor evidence and human review. Those capabilities are established prior work. The Home SOC analyst plan already listed TriageWall as a design reference. Our contribution is a measured Protectli/OPNsense reference build and a small Windows evidence-review workflow.

| Area | TriageWall's documented approach | This tested reference build |
| --- | --- | --- |
| Main unit of work | Suricata/Wazuh alert review and classification | Bounded current/prior windows, grouped evidence and constrained review suggestions |
| Model role | Local classifier for alerts remaining after deterministic policy | Selects eligible interpretation codes and read-only next steps; code owns counts, actions and priority floors |
| Operator feedback | Reviewed decisions and explicitly activated, versioned filtering policy | Append-only snapshot notes; notes cannot suppress alerts, lower priority or enter the model |
| Inputs | Source-specific Suricata projection and optional Wazuh input | Vault system/PF/EVE logs; typed numeric/enumerated brief and opaque endpoint aliases, with raw text kept out of the prompt |
| Storage and runtime | SQLite, Docker Compose and a GPU recommended for the default model | Windows/Python receiver and viewer, original JSONL segments, derived SQLite, PowerShell sign-in recovery and verified isolated Vulkan inference on the Minisforum |
| Appliance proof | Integrates with configured sensors | V1610 wiring, routed client, native temperature/storage/configuration checks, physical inline block and rollback, actual restart acceptance |
| Investigation evidence | Alert/asset context and review workbench | Exact original-record hashes/offsets, bounded full-tuple PF/EVE correlation, separately timestamped endpoint context and restored citations |
| Evaluation package | Documented operator-labeled release evaluation and gold-set tooling | Pinned upstream engine fixtures, installed-policy replays, isolated packet controls and all 416 model outcomes, including failures |

These are differences in this implementation and its scope, not a claim that each feature is unique across all tools. Privacy, validation, source-aware review and human control overlap. Neither model controls the firewall. TriageWall has Wazuh integration, policy lifecycle and richer classification capabilities that ours does not implement. Its documented accuracy and latency numbers use different data, labels, hardware and tasks; they are not comparable to our delivery counts.

The useful explanation for this project is: build a Protectli Home SOC, prove what its firewall and sensors did, preserve the original evidence, and use an optional local model to prepare the next manual review. Readers can reproduce the packet-to-report path and inspect what the model missed.

The strongest next analyst-quality evidence would be independently reviewed investigations and measured operator usefulness. The current agent reviews and repeated fixed briefs do not establish either. Adding a larger on-demand investigation model remains a possible experiment, not an implemented feature.

Historical October 6 comparison (before rolling-v2): Trevor selected the Vault plus Minisforum as the default. Exact repetition is expandable and does not suppress records. TriageWall additionally documents bounded search, configuration revision/preview/rollback and verified backup/pruning operations. At that checkpoint those capabilities were not implemented here. Current storage reclamation/source preservation is described above; equivalent full backup/pruning, Wazuh integration and activated policy lifecycle are not claimed. Its current README identifies AGPL-3.0; no TriageWall code was copied. The separate broader investigation experiment and its retained failures are discussed in [the correction protocol](INVESTIGATION_CONTRACT_CORRECTION_2026-10-06.md). It is research-only. The source/documentation comparison was refreshed on October 6; no cross-project benchmark was executed.
