# Retention, preservation and operating review

Current policy, October 7, 2026. [Quickstart](QUICKSTART.md) is the executable installation/activation path. [The verified live migration](LIVE_ROLLING_RETENTION_2026-10-07.md) records the original baseline, maintenance interval and checks.

## What is retained automatically

The rolling-v2 writer rolls complete records at 32 MiB, keeps at most 1 GiB of hot originals and up to 4 GiB of compressed cold segments. Before reclaiming a sealed hot copy, it restores the cold copy and compares the complete original hash. Logical byte offsets never get reused. Readers and SQLite use the same locators across hot/cold storage; ordinary expired records leave the derived index. A citation whose source has expired without preservation returns HTTP 410.

Ordinary sealed segments expire seven days after sealing, rather than exactly seven days after each event. Capacity and bounded manifest size can shorten that window; early-expiry counts are visible. The active part remains until it rolls. Maintenance runs on appends and five-minute idle checks. Disk/permission/lock errors and deferred cleanup remain visible; these budgets do not establish lossless UDP delivery.

SQLite has a separate 1 GiB page budget. WAL and temporary files can add peak disk use. The immutable initial migration baseline is separately retained; it contains 310,110,946 original bytes across nine members in this build. It includes initial setup and failed attempts and is not repeatedly copied by every checkpoint.

## What deserves deliberate preservation

Routine repeated logs can age out under the managed policy. Preserve a source when it supports an investigation, a disputed conclusion, a controlled detection/block/rollback result or a published claim. New review notes pin original records and context under a separate 64 MiB/4,096-record budget. If preservation refuses a write, retain that error and do not claim the source was saved. Older notes still resolve against the preserved baseline or their historical verified archive.

The six-hour managed checkpoint verifies current sources and pins without making another complete-history ZIP. Original legacy checkpoint ZIPs remain private and unchanged. An archive on the same disk does not cover loss of that disk; take private off-device backups for configuration and important evidence. Model weights, full Windows recovery and training environments are outside these evidence checkpoints.

## Legacy mode and history

Launching a fresh receiver alone keeps the legacy aggregate-cap policy. It stops preserving new messages at its cap. Activation requires an owned maintenance pause, stopped verified components, a fresh preflight and a verified baseline. Do not hand-author a preflight to bypass those checks. The complete [October 5/6 protocol](RETENTION_ARCHIVAL_HISTORY_2026-10-06.md) retains its older budgets, repeated archives and failed attempts as historical evidence.

## Retained operating observations

The original observer was configured from October 5 at 19:19:41 Pacific through October 7 at 19:19:41 Pacific. Trevor has dropped that fixed-duration release requirement; the original timestamps and gaps remain historical. Its start and end have not been reset by maintenance. The observer records up to 576 five-minute samples, retains gaps longer than ten minutes and records receipt/storage state, report age and native-health age. Finishing the timer records only that the window finished.

Review the complete journal, immutable failed/capped outcomes, pauses and recovery receipts, stale/missing native samples, temperature peaks, configuration/storage state, capacity/expiry and archive/source verification. A missing checkpoint is not itself proof of lost syslog; a stopped UDP receiver creates a possible receipt gap. Treat the original mixed-configuration window honestly rather than calling it 48 hours of the final configuration. The [operating review](OPERATING_REVIEW_2026-10-07.md) describes actual observed operation, interruptions and recovery without claiming continuous overnight service.

Seven-day expiry and failure handling have been exercised on disposable fixtures. Seven days of live operation and full machine-loss restoration have not been demonstrated.
