# Historical evidence retention and bounded observation

Implemented locally October 5, with an explicitly verified capacity update on October 6, 2026. Original source files and historical receipts remain in place. These controls prepare longer observation; they do not establish that it has passed.

## Stable sources across segments

The receiver's aggregate raw-log limit is now 1024 MiB (1 GiB). The former 200 MiB bound is retained in the historical receipts. A 32 MiB threshold starts another append-only segment at a complete record boundary. An already larger first file is retained and sealed on its first new append. `syslog.jsonl` stays the logical entrypoint; subsequent files use `.part000001`, `.part000002`, and contiguous names. The `.segments.json` sidecar records sealed sizes/hashes, active name and explicit budgets. No source file is truncated, rewritten or removed.

`soc_evidence.open_evidence` reads a captured logical byte layout across segments. Historical and new source locators use the same global offsets and exact record SHA256. Analyst snapshots, receiver restart and evidence routes share that reader. The receiver verifies sealed hashes on startup and refuses changed lengths, digests, unsafe names, partial-record rollover, unexpected nonempty rollover files or silently changed budgets. The per-record reader rechecks cited bytes. These checks detect inconsistency; a local administrator remains able to rewrite evidence and its metadata.

The 1 GiB limit is for all segments combined. When it fills or storage validation fails, new receipts stop being retained and status reports the problem. Archiving does not clear it. The receiver reports measured growth and estimated hours remaining after at least one minute of status samples. The health page warns at 80% usage or fewer than 24 estimated hours. Rates can change, and these estimates do not prove complete log delivery or indefinite retention.

The launcher records `-MaxMiB 1024`, and the private recovery configuration records `RawMaxMiB: 1024`. Existing recovery configurations without this field preserve their legacy 200 MiB setting. Recovery refuses a running receiver whose budget differs from its configuration. An existing segment index never silently adopts a new budget: stop its verified receiver with owned recovery paused, preserve the old index/configuration and segment hashes, explicitly update the sidecar's `max_bytes` and recovery configuration together, then verify old citation bytes and new live receipt. No sealed sizes, hashes, source offsets or record bytes may change. A fresh installation uses the new default directly.

## Six-hour private checkpoints

The existing five-minute Windows recovery task invokes `soc_operational_checkpoint.py`. During the 48-hour observation window it attempts a checkpoint immediately, then every six hours. Duplicate checks within four minutes are skipped. A failed archive is visible and is not retried every five minutes. OS-released advisory locks refuse overlapping checkpoint callers. Pending failed files remain preserved and count toward the archive budget.

Archives have a separate 4 GiB compressed budget and at most 64 completed/pending ZIP files. Input is bounded to 2 GiB/16,384 files, with at most 1 GiB of raw log data. Non-log members are bounded to 1 MiB and the manifest to 4 MiB. Raw data is copied and hashed in 256 KiB chunks. Verification uses a temporary disk stream for exact citation seeks rather than concatenating the full log in RAM. There is no automatic deletion. The checkpoint includes the fixed complete original-log prefix, segment index, stable report bundles, pinned operator notes and indexed endpoint context. An actively analyzing or incomplete report is excluded; a latest pointer to an excluded run is omitted. Pinned notes cannot silently lose their saved brief/group evidence.

Before a ZIP becomes a completed checkpoint, every member is read and hash/CRC checked, every restored citation is resolved against the archived logical log, and the review-note chain plus pinned brief/group fingerprints are independently checked. Original source prefix and journal are re-read afterward. A uniquely named receipt records the archive SHA256 and counts. This verifies restoration of these bytes and references, not full application/OS recovery, off-device backup, model weights or fine-tuning data. Export a reviewed private archive separately for device-loss protection.

For a deliberate manual checkpoint, pause the owned recovery checker first and run with private paths:

```powershell
py -3.12 -c "import sys; sys.path.insert(0,'tools'); import soc_archive; from pathlib import Path; print(soc_archive.checkpoint(Path('<logical-log>'), Path('<analyst-data>'), Path('<private-archives>')))"
```

The archive remains private. It contains original network identifiers and source paths.

## Bounded 48-hour observation

The configured window starts from its retained first observation and takes at most 576 five-minute samples. It records receiver aggregate bytes/segments/errors, latest analyst delivery status, native temperature/configuration/storage observation age and gaps longer than ten minutes. The sample journal is append-only with a 1 MiB bound. Missing or stale fields remain unknown. Original UTC timestamps display in Pacific time; no raw timestamp is rewritten.

The task samples even when process recovery reports an error, so retention-full or unavailable services remain in the record. User sign-in is required. A finished window stops this observer/archive cadence and records completion of the window, without asserting acceptance. The separate process-recovery task still renews finite analyst batches while signed in; that is distinct from observation completion.

Review the finished journal for gaps, capped/failed model outputs, stale/missing native readings, retention capacity, temperatures and archive failures. Count historical failures across batch restarts using their retained receipts, not just the current worker's reset counter. Do not claim complete UDP capture or independent model accuracy. A 48-hour observation is also not a controlled thermal equilibrium experiment: record ambient conditions and workload before that stronger test.

The first scheduled observation/archive ran on the original receiver before deployment. That receipt is preserved. The first segmented private checkpoint verified both old/new log bytes, saved reports and two pinned notes. A fresh owned-client fixture reached the new segment; original source locators were rechecked. Maintenance introduced a possible UDP receipt gap, explicitly recorded. The initial verifier incorrectly expected whole-file equality from a baseline taken while logging was still active; its failed assertion is preserved, and the corrected check compares that captured prefix plus the separate sealed digest.

Run all local tests with `py -3.12 -m unittest discover -s tools -p 'test_*.py' -v`. They cover archive restore/tampering, pinned notes, aggregate rollover limits, concurrency, failed scheduling, gaps and window completion. Appliance and client receipts remain separate live proof.


## October 6 capacity acceptance

The owned receiver/viewer maintenance preserved four original segment prefixes and checked 3,632 historical citations before changing only capacity metadata. A new private checkpoint restored 3,680 citation references and both pinned notes. The resumed receiver accepted real Vault records, and the selected analyst completed its next report in 81.187 seconds. The original 48-hour start/end and historical samples were not reset. A brief maintenance UDP gap remains possible.

The full suite passes 89 checks. New checks include an archive above the old 256 MiB input bound without whole-log reads, more than 4,096 archived artifacts, incomplete active records, capacity forecasting and early warning. Earlier bounds and failures remain in the old receipts. These budgets provide headroom for the observation; continued storage growth still needs review. Nothing is deleted automatically.
