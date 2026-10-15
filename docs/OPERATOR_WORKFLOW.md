# Running the local Home SOC

Current October 7 workflow: the [SQLite overview](SQLITE_GPU_AND_DEPLOYMENT_2026-10-06.md) is the entry page at port 8766. Expand grouped originals first; report/review-queue routes below are additional snapshot views. [Quickstart](QUICKSTART.md) covers installation and rolling activation.

This is the next practical phase after the firewall and analyst reference build. The Vault is the firewall/sensor. The Minisforum receives original logs and runs the bounded analyst. The local model receives a bounded brief and returns report fields; this implementation gives it no command executor, firewall credentials or note-writing tools. The operator reviews recommendations and makes any policy changes separately.

## Start a review

Open http://127.0.0.1:8766/ in Brave. Use Health and coverage first: check the receiver's retention and last receipt, report age and actual worker mode. The native Vault reading is a separate timestamped observation. The page refreshes its status every 30 seconds, but does not run a new native collection or model request. A native observation older than ten minutes is visibly stale. A recent report cannot establish complete packet/log delivery.

Use Review queue to annotate the current saved snapshot. Use Saved reports to recover older nonempty windows. The history indexes at most 200 recently modified run folders and displays up to 30 by observed window time. Older files remain on disk. The report table retains fixed blocked/severity-1 review priorities even if an operator records expected context.

Before writing a note, follow a group's exact source link. The viewer checks the full original record hash; PF/Suricata review checks the exact tuple within the bounded receipt window. Read any independently recorded endpoint context with its timestamp. Missing PF context, VPN-encrypted payloads, process intent and current connection state remain unknown unless separate evidence establishes them.

Save one of three annotations: Reviewed this snapshot, Needs investigation, or Operator recorded expected context. Record what was checked and what remains unresolved. Reviewed does not mean safe. A new group fingerprint, count/comparison change or evidence reference needs fresh review. Past annotations remain visible but do not silently certify new evidence.

## What a saved note does

Only a same-origin, token-checked local POST can append a note. Requests have bounded length and exact fields. The server rechecks the saved brief and every cited raw record before writing. Text is escaped for browser display. Notes never reach the model, suppress alerts, create an allowlist, execute a command or modify policy.

The private operator-review.jsonl journal appends sequence numbers, UTC time, run/group/brief fingerprints and a SHA256 chain. Writes flush to disk. This catches accidental/inconsistent edits; it is not a signed identity or protection against a local administrator rewriting the whole journal. The viewer has no remote authentication layer and remains loopback-only. The journal's 1 MiB cap stops new annotations without deleting old ones or affecting raw logging.

## Refresh the native health observation

The launcher can also collect native health at its finite cadence. Use `-NativeHealth -VaultAddress '<Vault-LAN-IP>' -HealthBackup '<retained-final-config.xml>'` with `Start-SocAnalyst.ps1`. Default monitoring is 12 starts, 300 seconds apart. `-ViewOnly -NativeHealth` collects health while periodic inference stays paused. Collection has a 25-second subprocess deadline, unique receipts and a visible completion/failure count. No browser refresh initiates it. Stop refuses a currently active collection; wait for its bound to finish before using another USB helper.

Use PowerShell 7 with the existing authenticated USB console. Only one helper may own the serial port. The collector verifies the expected root prompt before sending its fixed read-only sysctl/process/hash/ZFS command. It does not attempt a login or change appliance configuration.

```powershell
& .\tools\Collect-SocHealth.ps1 `
  -VaultAddress '<Vault-LAN-IP>' `
  -Port 'COM3' `
  -BackupPath '<retained-final-config.xml>'
```

The collector retains uniquely named native receipts and health-snapshot JSON files, then replaces only the latest pointer. It reads Windows route/DNS/Wi-Fi, spare memory and local Tailscale status. A Vault gateway route is not proof that every application follows it; VPN-specific routes may differ. Missing collection remains unknown. A native engine PID proves a process observation, not complete inspection health. A configuration hash comparison is meaningful only against the intended retained backup.

The supplied serial guard expects the lab hostname protectli-soc, 115200 8N1 and LF. Verify/adapt its hostname guard for another appliance rather than bypassing it. These files are not a generic authenticated appliance API or autostart service.

## Failure and recovery

If a model answer is rejected, the deterministic table and original receiver continue. Keep its response/rejection. Do not relax validation to make an answer appear. If a worker fails before rendering, the prior completed report remains and its age/error stay visible. Health and saved-report routes remain available without a valid latest-report pointer.

Stop and restart the viewer with the ownership-checked helpers after any active request finishes. Notes and historical source links remain on disk across restart; original evidence bytes are unchanged. Starting an occupied listener is refused. A stop never targets the original receiver, separate Ollama runtime or protected fine-tuning runtime.

If a journal/brief/source hash changes, review is withheld. Preserve the damaged file and copy first, then investigate; there is no automatic truncation or repair. Activated rolling-v2 collection reclaims verified sealed hot copies and expires ordinary sealed segments under its time/capacity policy. Watch hot/cold usage, early expiry, deferred cleanup and storage errors. A legacy installation still stops preserving new receipts at its aggregate cap; starting the launcher alone does not migrate it. [Quickstart](QUICKSTART.md) describes activation and [retention](RETENTION_ARCHIVAL_AND_OBSERVATION.md) describes the current policy, baseline and pinned evidence. An expired unpreserved source returns HTTP 410, which must stay visible in the investigation.

## Remaining project decisions

This phase makes the existing lab useful to review; it does not finish every future deployment choice. Whole-unit Wi-Fi requires an owned AP/switch and a demonstrated route through the Vault. DNS ad blocking, a Proton tunnel and Vault Tailscale subnet/exit-node access remain unconfigured. Existing per-device Tailscale SSH remains separate.

User sign-in recovery is now configured and scheduled/manual ownership/restart checks passed. See [Startup and restart](STARTUP_AND_RESTART.md). The authorized Windows reboot/sign-in acceptance is verified with initial failures preserved. Multi-day observation remains pending. A second-endpoint forwarding benchmark, public screenshot redaction and the website/repository release remain unfinished. Each requires its own measured acceptance criteria. The article and partner message are prepared local drafts, with no send, push, deployment or publication.

Pause the recovery checker before a manual component stop or model evaluation; otherwise it can renew a stopped/completed viewer at its next five-minute check. No password is stored. Native collection requires an authenticated appliance shell after a Vault reboot.
