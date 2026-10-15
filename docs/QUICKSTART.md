# First working Home SOC

This is the current Windows reference path. The Vault runs OPNsense and Suricata; the Windows host receives logs, serves the evidence overview and optionally runs a local model. Start with evidence browsing so the first successful run does not depend on inference. Only devices whose routed traffic crosses the Vault are covered.

## 1. Prerequisites and wiring

Use an owned lab, an installed Python 3.12 executable and PowerShell 7. The tested build used PowerShell 7.6.5. Python needs no third-party packages. Optional inference requires a separately installed Ollama and at least 16 GiB of measured spare host memory under the current guard. Reserve disk space for the 1 GiB hot logs, 4 GiB cold logs, 1 GiB derived index, preserved baseline, saved reports and optional model store. These budgets are separate.

Keep the repository and its `private/` directory on a local disk. `private/` must stay out of Git and public web roots. Back up the Vault configuration privately, because it contains account/security material and network details. Follow the [build guide](BUILD_GUIDE.md) and [settings checklist](../examples/opnsense-profile.json) for appliance setup; record actual interface assignments rather than guessing from port labels.

In this build, upstream Ethernet connects to Port 2/WAN and the owned Windows client connects to Port 1/LAN. Verify the client's route, Internet access and direct Vault DNS before enabling tests. Existing Wi-Fi clients do not gain protection unless their traffic also routes through the Vault. Keep WAN management closed.

Run the following from the repository root in PowerShell 7. Replace all placeholders once:

```powershell
$socRoot = (Get-Location).Path
$socPython = '<absolute Python-3.12 executable>'
$socClient = '<owned client LAN IPv4>'
$socVault = '<Vault LAN IPv4>'
$socLog = Join-Path $socRoot 'private\logs\syslog.jsonl'
$socData = Join-Path $socRoot 'private\analyst'
```

## 2. Receive the logs

```powershell
& .\tools\Start-SocReceiver.ps1 -LanAddress $socClient `
  -VaultAddress $socVault -PythonPath $socPython -MaxMiB 1024
```

If Windows blocks receipt, run [Allow-SocSyslog.ps1](../tools/Allow-SocSyslog.ps1) in an elevated shell with your actual executable, interface and addresses. It scopes the rule to the Vault and UDP 5514. Configure OPNsense's remote syslog destination as the owned client's address, UDP 5514, RFC5424, with selected system/firewall/Suricata applications. Keep local appliance logs too.

Open `http://127.0.0.1:8765/`. Check that a new Vault record arrives and `accepted_this_run` increases. A listening socket alone does not establish receipt. Source-IP filtering is not authentication, and UDP can lose messages. Starting this launcher creates or resumes legacy bounded storage; rolling retention is enabled explicitly in step 5.

## 3. Open the overview without a model

```powershell
& .\tools\Start-SocAnalyst.ps1 -PythonPath $socPython `
  -LogPath $socLog -ClientAddress $socClient -DataDirectory $socData -ViewOnly
```

Open `http://127.0.0.1:8766/`. Wait for indexing to catch up, then expand a repeated-alert group and open an original source. The overview, SQLite index and source routes work without an AI report. Exact repetition is collapsed for browsing; records are not suppressed. A missing temperature is a missing native observation, not a zero reading.

## 4. Verify one original record

From the owned client, make a benign request while the installed harmless UID signature is in alert mode:

```powershell
curl.exe --max-time 10 http://testmyids.com/
```

Check the actual response and the resulting Suricata record. If the external endpoint or rule is unavailable, keep that failure and use [the controlled test protocol](TEST_PROTOCOL.md) to establish the cause. Do not interpret absence from the 500-event receiver buffer as proof there is no retained record. In the overview, follow the exact source link and inspect its action, tuple, timestamp and hash. An allowed sensor event alone does not establish client success; the client receipt supplies that separate observation.

The first-run check passes when new receipt is observed, the index reaches that source boundary, and an original record opens with its complete hash verified. Selected blocking and rollback are separate tests in the protocol.

For a saved deterministic brief, use a new output directory:

```powershell
& $socPython .\tools\soc_analyst.py --log $socLog --client $socClient `
  --salt-file (Join-Path $socData 'alias-key.bin') `
  --output (Join-Path $socData ('manual-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ'))) `
  --no-model
```

## 5. Enable bounded rolling retention

For a fresh manual installation, record the receiver's actual process before maintenance. This block refuses a foreign executable, script or socket owner. It creates only a new private maintenance configuration and recovery-owner record; it does not register a task or stop a process.

```powershell
$socRecovery = Join-Path $socData 'recovery'
New-Item -ItemType Directory -Path $socRecovery -Force | Out-Null
$socConfig = Join-Path $socRecovery 'retention-config.json'
$socOwner = Join-Path $socRecovery 'receiver-owner.json'
if ((Test-Path -LiteralPath $socConfig) -or (Test-Path -LiteralPath $socOwner)) {
  throw 'Existing configuration/owner: inspect and reuse its verified configuration instead.'
}
$socReceiverId = [int](Get-Content -LiteralPath (Join-Path $socRoot 'private\logs\receiver.pid'))
$socProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$socReceiverId"
$socScript = [IO.Path]::GetFullPath((Join-Path $socRoot 'tools\soc_receiver.py'))
$socUdp = @(Get-NetUDPEndpoint -LocalPort 5514 -ErrorAction SilentlyContinue)
$socHttp = @(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)
if (-not $socProcess -or $socProcess.ExecutablePath -ne $socPython -or
    $socProcess.CommandLine -notlike ('*"' + $socScript + '"*') -or
    $socUdp.Count -ne 1 -or $socUdp[0].OwningProcess -ne $socReceiverId -or
    $socUdp[0].LocalAddress -ne $socClient -or $socHttp.Count -ne 1 -or
    $socHttp[0].OwningProcess -ne $socReceiverId -or $socHttp[0].LocalAddress -ne '127.0.0.1') {
  throw 'Receiver ownership differs. Nothing stopped.'
}
@{DataDirectory=$socData;LogPath=$socLog;PythonPath=$socPython;
  ClientAddress=$socClient;VaultAddress=$socVault;RawMaxMiB=1024} |
  ConvertTo-Json | Set-Content -LiteralPath $socConfig -Encoding utf8
@{pid=$socReceiverId;executable=$socProcess.ExecutablePath;
  started_utc=$socProcess.CreationDate.ToUniversalTime().ToString('o')} |
  ConvertTo-Json | Set-Content -LiteralPath $socOwner -Encoding utf8
```

An existing recovery-managed installation uses its verified full configuration instead. Do not overwrite its owner or create a second task. Check the manifest version first; **skip activation if already rolling-v2**. The activation tool intentionally refuses a second migration.

For an existing managed installation, set `$socConfig` to its verified full configuration and define `$socOwner = Join-Path $socRecovery 'receiver-owner.json'` and `$socScript = [IO.Path]::GetFullPath((Join-Path $socRoot 'tools\soc_receiver.py'))` before the block below. Pause recovery, stop only owned idle components, then migrate. Each helper refuses a conflicting owner or active bounded worker. Leave the pause in place after any failure and inspect the receipt before resuming. Messages sent while the receiver is stopped may be lost.

```powershell
$socPause = Join-Path $socRecovery 'paused.flag'
if (Test-Path -LiteralPath $socPause) { throw 'Recovery already paused; preserve its reason.' }
Set-Content -LiteralPath $socPause -Value 'Rolling retention maintenance'
& .\tools\Stop-SocAnalyst.ps1 -DataDirectory $socData
& .\tools\Stop-SocReceiver.ps1 -ConfigPath $socConfig
$socReceipt = Join-Path $socRoot ('private\retention-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ'))
& .\tools\Activate-SocRollingRetention.ps1 -ConfigPath $socConfig -ReceiptDirectory $socReceipt
& .\tools\Start-SocReceiver.ps1 -LanAddress $socClient `
  -VaultAddress $socVault -PythonPath $socPython -MaxMiB 1024
# Re-record the restarted receiver for future ownership-checked maintenance.
$socReceiverId = [int](Get-Content -LiteralPath (Join-Path $socRoot 'private\logs\receiver.pid'))
$socProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$socReceiverId"
if (-not $socProcess -or $socProcess.ExecutablePath -ne $socPython -or
    $socProcess.CommandLine -notlike ('*"' + $socScript + '"*')) { throw 'Restart owner differs.' }
@{pid=$socReceiverId;executable=$socProcess.ExecutablePath;
  started_utc=$socProcess.CreationDate.ToUniversalTime().ToString('o')} |
  ConvertTo-Json | Set-Content -LiteralPath $socOwner -Encoding utf8
$socState = Invoke-RestMethod 'http://127.0.0.1:8765/api/events'
if ($socState.rolling_retention.mode -ne 'rolling-v2' -or
    $socState.storage_error -or $socState.retention_full) { throw 'Inspect activation receipts before resuming.' }
```

Verify the immutable baseline descriptor, reopen the step-4 original citation, and observe a new real Vault receipt. After those checks, preserve the pause marker in the receipt directory with `Move-Item -LiteralPath $socPause -Destination (Join-Path $socReceipt 'completed-pause.flag')`. Restart the view-only overview with step 3, or run the existing recovery task if its full configuration is already installed.

Current policy: 32 MiB rollover, 1 GiB hot originals and 4 GiB compressed cold storage. A cold segment is restored and hash-checked before its hot copy is reclaimed. Ordinary sealed segments expire seven days after sealing; capacity can expire them sooner, with visible early-expiry counts. The initial immutable baseline stays separately preserved. New review notes pin sources under a separate 64 MiB/4,096-record budget. An expired unpreserved source returns HTTP 410. [The retention guide](RETENTION_ARCHIVAL_AND_OBSERVATION.md) explains these boundaries and the original migration.

## 6. Optional CPU or GPU reports

The deterministic workflow above needs no model. For inference, install the official runtime separately, start the isolated CPU service and inspect its owner/listener before pulling anything:

```powershell
$socOllama = '<absolute installed Ollama executable>'
& .\tools\Start-SocAnalystModel.ps1 -OllamaPath $socOllama
# Explicit SOC endpoint and separate store, not another project's default service.
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:11435/api/pull' `
  -ContentType 'application/json' -Body '{"model":"qwen3.5:4b","stream":false}' -TimeoutSec 1800
Invoke-RestMethod 'http://127.0.0.1:11435/api/tags'
```

Compare the artifact digest with [the analyst guide](AI_ANALYST_GUIDE.md). A changed upstream tag is a new artifact to evaluate, not an automatic substitution. Stop the view-only viewer with its owned helper, then restart without `-ViewOnly`, explicitly using `-ModelName qwen3.5:4b -ModelProfile common -Acceleration cpu`. Normal reporting retains its 4,096 context and 700-token allowance; the 16-thread/8,192-context resource experiment is separate.

For an opt-in Vulkan path with the same SOC-only store:

```powershell
& .\tools\Start-SocGpuProbe.ps1 -OllamaPath $socOllama `
  -ModelsDirectory (Join-Path $socData 'model-runtime\models') `
  -DataDirectory (Join-Path $socData 'gpu-runtime')
# After the owned viewer is idle and stopped:
& .\tools\Start-SocAnalyst.ps1 -PythonPath $socPython -LogPath $socLog `
  -ClientAddress $socClient -DataDirectory $socData `
  -ModelName qwen3.5:4b -ModelProfile common -Acceleration vulkan
```

Verify the actual device, layer offload and loaded-model digest in runtime receipts; a flag alone does not prove GPU execution. Keep port 11434 and other projects' stores unchanged. A validated answer is constrained reporting, not proof of intrusion or human investigation benefit. [Saved experiment verification](OCTOBER7_EVIDENCE_VERIFICATION.md) needs no runtime or model weights.

## 7. Native temperature and sign-in recovery

Native health needs the existing authenticated USB console, the correct COM port and a privately retained configuration backup. Confirm/adapt the documented hostname guard for your own appliance. `-NativeHealth -VaultAddress $socVault -HealthBackup '<private config.xml>' -SerialPort '<COM port>'` adds the read-only sampler to the analyst launcher. An appliance reboot requires a new manual console login; passwords are not stored.

The current recovery task expects inference and native-health configuration. It is not a view-only autostart mode. If keeping the deterministic-only installation, use the explicit launchers above until that additional recovery mode is implemented and tested.

For the full tested path, save a new private recovery JSON using your actual paths and verified model/backup hashes:

```json
{
  "DataDirectory": "<absolute repo>\\private\\analyst",
  "LogPath": "<absolute repo>\\private\\logs\\syslog.jsonl",
  "PythonPath": "<absolute Python executable>",
  "OllamaPath": "<absolute Ollama executable>",
  "ClientAddress": "<owned client IPv4>",
  "VaultAddress": "<Vault IPv4>",
  "HealthBackup": "<private configuration backup>",
  "BackupSha256": "<verified lowercase SHA256>",
  "ModelName": "qwen3.5:4b",
  "ModelDigest": "<verified installed digest>",
  "ModelProfile": "common",
  "Acceleration": "vulkan",
  "GpuRuntimeDirectory": "<absolute repo>\\private\\analyst\\gpu-runtime",
  "SerialPort": "<verified COM port>",
  "RawMaxMiB": 1024
}
```

Use `Acceleration: cpu` to select the isolated CPU fallback. Existing ownership files must correspond to the components above. Inspect before registering:

```powershell
& .\tools\Restore-SocAfterLogin.ps1 -ConfigPath '<private full config.json>' -InspectOnly
& .\tools\Install-SocRecovery.ps1 -ConfigPath '<private full config.json>'
Start-ScheduledTask -TaskName 'Protectli Home SOC recovery'
```

Check `startup-state.json`, new receipt, source links, report age and native temperature age. This is limited-user recovery after Windows sign-in, with five-minute checks, not pre-login service operation. Review [startup/restart](STARTUP_AND_RESTART.md) before a planned reboot. The retained operating journal records failures and gaps separately; a fixed-duration run is not required for this release. [Observed operation](OPERATING_REVIEW_2026-10-07.md) describes the actual checks and interruptions.
