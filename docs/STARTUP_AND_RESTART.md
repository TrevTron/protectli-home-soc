Current recovery repair: [receiver ownership and scheduled recovery](RECOVERY_OWNER_REPAIR_2026-10-14.md). Manual and recovery launches now keep the owner receipt synchronized. Earlier dated acceptance and legacy retention descriptions below remain historical; current retention is rolling-v2 as described in the current quickstart.

# Startup and restart recovery

Current release note, October 7: Trevor dropped the fixed 48-hour clause. [Observed operation and recovery](OPERATING_REVIEW_2026-10-07.md) retains interruptions and failures. Current storage uses activated rolling-v2; [Quickstart](QUICKSTART.md) is the operating path. Earlier dated budgets, test counts and pending labels below are historical.

Updated October 7: follow [Quickstart](QUICKSTART.md) for the current recovery configuration and [rolling retention](LIVE_ROLLING_RETENTION_2026-10-07.md) for storage. The chronological restart/rehearsal receipts below retain their original budgets and results. Current recovery accepts a valid segment manifest after the initial filename expires; deterministic-only autostart is not implemented by this task.

October 6 SQLite/GPU revision: the CPU setup below remains an explicit fallback and the historical model-study configuration. The current reference host uses the isolated opt-in Vulkan runtime. See [deployment](SQLITE_GPU_AND_DEPLOYMENT_2026-10-06.md) and [executed automated investigation results](AUTOMATED_INVESTIGATION_RESULTS_2026-10-06.md). The new overview works independently of inference. All 134 software checks pass; recovery and one fresh GPU report are verified. The 48-hour observation is unaccepted and includes a maintenance checkpoint gap.

Prepared and tested locally October 5, 2026. Trevor authorized the Vault reboot, user sign-in recovery and then a Minisforum reboot. The actual Windows reboot/sign-in acceptance is now verified, including a new OS boot, automatically started owned processes, later accepted source-bound report, fresh native observation and exact client/EVE control. Initial collection/model failures remain retained. This is bounded restart evidence, not multi-day reliability.

## What starts automatically

The limited-user Task Scheduler task `Protectli Home SOC recovery` runs at Trevor's Windows sign-in and checks every five minutes while that user is signed in. It stores no Windows or appliance password. It is not a pre-login service and does not enable automatic Windows login. The task action uses installed PowerShell 7 without changing execution policy.

Restore-SocAfterLogin.ps1 takes a private configuration file. It verifies the saved Vault-facing client address and retained backup, then reuses or starts the original receiver, separate project model runtime and analyst viewer. Socket ownership, executable/script and creation time must match recorded owners. Foreign/conflicting processes are never terminated. Missing model/digest fails closed; nothing is pulled or substituted. The default protected model runtime is outside this task.

The child analyst/native sampler retains bounded requests and a finite 288-start batch at 300-second cadence. Recovery renews a completed batch at the next check. An active batch is reused. This renews operation while Windows is signed in; it does not prove complete traffic/log delivery or multi-day stability. Native sampling never supplies a password or attempts login. A Vault reboot clears the console session; restore that login manually before relying on temperature/configuration/storage observations. Windows reboot alone may leave the appliance console authenticated, but that must be observed.

Current activated rolling-v2 storage uses 1 GiB hot originals and 4 GiB compressed cold segments. Ordinary sealed segments expire after seven days or earlier under capacity pressure. The immutable initial baseline and new pinned note sources remain separate. A storage error remains visible in recovery. The old 200 MiB no-deletion behavior belongs to the original restart test below. Source-bound historical reports/notes survive process restart. Task check receipts are retained up to 4096 files; the current state remains separate after that cap. During the bounded 48-hour window, the same task records operation and attempts six-hour verified private checkpoints. With rolling-v2 these verify managed sources and pins rather than copying complete history into another ZIP; the 4 GiB budget is the compressed cold tier. Legacy checkpoint ZIPs remain preserved. [The current retention protocol](RETENTION_ARCHIVAL_AND_OBSERVATION.md) specifies restored-source/journal checks, automatic bounded segment expiry and visible errors. Earlier archive rehearsal below is historical.

## Pause and resume

Create `paused.flag` in the private analyst recovery directory before stopping/replacing any owned SOC component or running a model evaluation. Recovery honors it without touching running components. This prevents a manual stop from being immediately undone. Remove only that maintenance marker when ready to resume, then run the named task. Preserve other receipts and evidence.

```powershell
# Replace placeholders with your private data/configuration paths.
Set-Content -LiteralPath '<analyst-data>\recovery\paused.flag' -Value 'Maintenance'
# Stop only verified owned components using their documented helpers.
# After maintenance:
Remove-Item -LiteralPath '<analyst-data>\recovery\paused.flag'
Start-ScheduledTask -TaskName 'Protectli Home SOC recovery'
```

The original Stop-SocAnalyst helper still refuses active model/native collection and verifies ownership. The recovery script's InspectOnly mode inspects decisions without launching/stopping components. Do not stop all Python/Ollama processes by name.

## Reboot acceptance

Record the original raw-log prefix length/hash, journal/configuration hashes, Windows boot time and owned/protected process metadata before reboot. For a Vault reboot, retain the actual console shutdown/boot receipt and compare native boot time, configuration, pools, temperature and rule/engine state after console login. Check owned routed HTTPS, direct Vault DNS and exact harmless UID client/EVE correlation. Booting to a login page alone does not prove inspection health.

For the authorized Windows reboot, the private configuration records the previous Windows boot time and baseline path. A pending-reboot marker causes recovery to write one uniquely named receipt only after a newer Windows boot. Test-SocWindowsRecovery.ps1 hashes the original raw prefix/journal/backup, records receiver/viewer/native state and owned process creation, and runs bounded HTTPS/DNS/harmless UID controls. It records evidence and unresolved fields rather than asserting blanket success. Inspect the new report/native timestamp and exact EVE tuple separately after returning.

Use a normal non-forced Windows restart so applications may block closure for unsaved work. A reboot interrupts running applications and the separate model environment; Trevor authorized that interruption for this test. This project does not change that environment's own startup settings. Save the handoff before the restart because the local Codex session may disconnect.

## Checks completed before Windows reboot

- Vault reboot reached its login prompt in about 59 seconds; routed certificate-valid HTTPS and direct Vault DNS passed afterward.
- Scheduled task registered as Interactive/Limited, with sign-in and five-minute triggers; its first actual scheduled run returned success while respecting the maintenance pause.
- An unrecognized live port owner test failed closed without stopping the original receiver or protected runtime.
- All 58 Python tests passed, including visible stale recovery/pause/error state and escaped error text. PowerShell scripts parsed.
- Actual scheduled recovery renewed the completed batch; its first report accepted in 98.031 seconds. A second ownership check reused all active processes. Post-Vault native boot time changed, all four cores were 38-39 C, pools were healthy and the configuration hash matched the backup. Four exact drop SIDs, 37,121 alerts and UID alert action remained intact. The HTTP200/39-byte UID response has an exact bidirectional original EVE match. The actual post-Windows acceptance is recorded below.

This step adds startup recovery. Multi-day observation, archival, wider network coverage and external release remain separate checklist work.

## Console login correction

The old helper searched for any `login:` substring after password entry, including the successful `Last login:` banner. The restart test demonstrated accepted credentials and the authenticated menu while that helper reported rejection. Connect-VaultConsole.ps1 now recognizes a new login prompt only as its own line, retains `Login incorrect` rejection and verifies entry into the diagnostic shell before reporting success. Three classifier regressions passed. This establishes the cause of this false rejection; older failed attempts are preserved and not all reclassified.

Official reference: https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskprincipal and https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/shutdown. The restart helper delays separately, then uses a zero-timeout, non-forced restart; a positive shutdown timeout would imply force closure.

## Actual Windows reboot and sign-in

The new Windows boot was October 5 at18:48:35PDT. Automatic sign-in recovery started all three SOC components, and the next five-minute check reused their owners without duplicates. Original raw-log prefix, review journal and configuration-backup hashes remained intact. Certificate-valid HTTPS and direct appliance DNS passed; the new harmless HTTP control has one exact allowed original EVE match.

The first model request returned HTTP500 after67.875seconds. Its cause is unestablished. The next scheduled run accepted in93.656seconds without changing requests, validation or runtime. Its16groups and46original source hashes were rechecked; the new client control is included. The first native process timed out on completion detection, although its private receipt contained temperatures/configuration/healthy pools. A kernel diagnostic followed the root prompt in the same read. The serial helper now drains historical queued input before requesting a fresh prompt and recognizes a line-anchored root prompt with subsequent diagnostics. The actual retained failure case, five negative prompt cases and syntax passed. The next scheduled native collection succeeded within the original bounds; its historical failure count remains visible.

Postboot native cores were35-38C in later bounded observations, with healthy pools, the same engine and backup-matching configuration. The actual Brave dashboard persisted after reload, displayed48-49C at its own timestamps and correct Pacific time, and showed Intrusion Detection running. These samples were not simultaneous. The SOC health page visibly showed recovery, native observations and accepted delivery; its screenshot timed out, so that visual check uses the actual AX state and retained HTTP source. Two actual appliance dashboard captures remain private.

The separate protected runtime was interrupted by the specifically authorized Windows reboot. SOC recovery neither starts nor configures it and changed no training data/startup settings. This completes the bounded restart/sign-in checklist item. It does not establish pre-login operation, multi-day reliability, archival capacity or complete UDP delivery.

## Earlier archive rehearsal, before scheduled rollover checkpoints

A non-destructive private checkpoint archive now contains a40,296,637-byte original log prefix,27saved report bundles (including the historical controlled-block/preview bundles), two pinned operator notes and their endpoint-context receipts. The archive has191source files. All261original citation offsets/hashes, the note chain and pinned brief/group hashes, every archive member hash and archive CRC passed. Original log prefix and notes remained unchanged. A first rehearsal omitted two historical bundles because they lacked periodic-worker completion status; it is preserved, and the corrected archive admits stable complete saved bundles while explicitly excluding an active unfinished worker.

This is an executed archive/restore-of-citations rehearsal, not log rotation, storage reclamation, an automatically scheduled archive or a full application/OS disaster restore. The200MiB live cap remains. At this rehearsal, multi-day operation and source-preserving rollover were still pending. Later rollover and scheduled checkpoint checks are recorded in [retention and observation](RETENTION_ARCHIVAL_AND_OBSERVATION.md); the 48-hour observation remains unaccepted. The next scheduled model run also accepted in95.141seconds and native collection succeeded again. Public release remains unexecuted.

## Selected model/profile acceptance, October 6

Recovery now passes the explicit ModelName and ModelProfile into the viewer and worker. The selected Qwen3.5 4B digest is verified before launch. Active viewer ownership must match this selection. The owned viewer was replaced only after the previous bounded request and native collection finished. Recovery reached ready and a fresh normal report using the selected model/profile passed source-bound validation: 16 retained groups, 631 generated tokens, natural stop, 86.625 seconds. The actual request options match the frozen common profile. Sealed raw-log and configuration-backup hashes still match, protected model tags match, and native collection remains independent. This is one fresh operating acceptance, not multi-day reliability.


The October 6 capacity migration now records `RawMaxMiB: 1024` in recovery configuration. This must equal the receiver and segment-index bound. Older missing-field configurations retain 200 MiB; never silently migrate an existing index. See the updated retention protocol for the explicit stopped-receiver migration and source checks.
