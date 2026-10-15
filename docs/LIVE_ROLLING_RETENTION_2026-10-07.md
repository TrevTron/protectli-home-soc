# Live rolling retention, October 7

The owned live collector was migrated at 17:36:54 UTC after its receiver and inference viewer were stopped with their ownership-checked helpers. Recovery was paused. The receiver returned at 17:36:57 UTC and the recovery check was ready at 17:37:03 UTC. This maintenance interval can have lost UDP messages; it remains part of the original operating observation, whose end time has not changed.

Before switching manifests, the activation tool copied and verified all 310,110,946 original bytes across nine members. This immutable baseline includes earlier setup records and failed attempts. Its descriptor SHA256 is `4b1b9a709f18a0fea5dd1d0e9ceeceb4d91550a7a629d984582bcbfd5830bd6a`. Existing legacy checkpoint ZIPs, source locators, operator notes and earlier study outputs were preserved. The baseline is a one-time copy, not another full-history archive every six hours.

## What now happens at capacity

The current budgets are 1 GiB of hot originals and 4 GiB of compressed cold segments. The active part rolls over at 32 MiB; the larger original first file retains its exact bytes. When hot space is needed, a sealed segment is compressed once, restored and compared against its complete original hash before the hot file is reclaimed. Readers retain the same global byte offset and length across storage tiers. New records never reuse an expired offset.

Sealed segments expire seven days after sealing. This is a segment-based review window, not an exact seven-day deadline for each record. The active part remains until it rolls over. Maintenance runs on appends and at five-minute idle checks. Cold capacity and the bounded manifest can shorten the review window; early expirations are counted and visible. This is bounded retention, not a promise of lossless or indefinite capture. Disk failures, permission failures, crashes and UDP bursts remain operating limitations.

SQLite removes expired ordinary records and reuses its pages. Its 1 GiB budget is separate from raw storage. Original-record routes return an explicit HTTP 410 for an expired, unpreserved source, rather than returning another record or treating missing evidence as an all-clear. The dashboard now distinguishes retained bytes from the cumulative logical offset.

## What should be saved

Ordinary records need not all be archived permanently. The migration baseline keeps the original setup evidence. Saving a new operator review preserves the cited raw records by their full SHA256 before accepting the note. These records have an independent 64 MiB / 4,096-record budget. If that budget fills, a new review note is refused; collection continues. A saved note and report still need their context and any separate endpoint receipts. Pinning one raw record does not establish a client outcome or preserve every record in an old unreviewed report.

Unreviewed reports generated after migration can lose their original sources when ordinary retention expires. Earlier reports whose sources are in the migration baseline remain retrievable through that baseline. Reads never create preservation pins. Changed records, compressed archives, baselines or cited hashes are withheld instead of silently replaced.

Scheduled managed checkpoints stream-verify sealed original hashes, saved-note source references and the baseline, then replace one bounded state file. They no longer create repeated full-history ZIPs. A successful managed checkpoint is a source-integrity check, not a full application disaster-recovery claim. The first live managed checkpoint verified eight sealed segments, both original-note references and both notes at 17:38:43 UTC.

## Validation and recovery

The full regression suite passed 250 tests before live activation. Targeted tests also cover collection beyond the hot cap, exact cold-source retrieval, restart after the initial filename expires, age and capacity expiry, crash recovery, temporary Windows file locks, immutable baseline retrieval, post-migration source pins, tamper refusal, HTTP 410, idle maintenance and 70 checkpoints without repeated ZIP growth.

The live receiver subsequently reported `rolling-v2`, new Vault receipts, no full condition and no storage error. Windows recovery and the analyst launcher now accept a valid segment manifest after the initial filename expires. The fresh index reached its observed source boundary. A native sample at 17:37:08 UTC showed four 42°C cores, healthy pools and the retained configuration hash. These are timestamped observations; the seven-day expiry has been tested on disposable fixtures, not yet observed through seven days of live operation.

Maintenance receipts, baseline descriptor, test logs, source checks and the dashboard screenshot are private under `private/resource-retention-20261007/`. No public release or deployment occurred.
