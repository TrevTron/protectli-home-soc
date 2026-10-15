# Observed operation and recovery

The project has developed over weeks of Trevor's work. It includes an overnight run alongside normal network activity on the night of October 5 into October 6. The dated snapshot below reviews one retained monitoring period and does not represent the start or total duration of the project. The project no longer requires a fixed 48-hour observation before release. The original journal and its start/end timestamps remain unchanged as historical evidence; no missing interval has been filled or relabeled.

## Retained operating snapshot (checked October 7 at 13:45 Pacific)

The interim read covered 352 timestamped observations from October 5 at 19:19:41 Pacific through October 7 at 13:44:42 Pacific. Sampled core temperatures were 30–56 °C, separate from the guarded load test's 62 °C peak. No sampled receiver-full condition, storage error or capacity warning was recorded. Configuration comparisons that returned a known value matched the backup; known pool readings were healthy. One native observation reported unknown storage/engine/configuration fields, and another was stale.

The retained worker receipts completed during that interval include 272 completed ticks and one withheld/error tick. The latter records a refused local Vulkan connection at 08:47 Pacific on October 7. The first observation also carries a withheld report that completed shortly before the window began; it stays in the record. Completed ticks include empty-window reports, so this count is not 272 independently useful model investigations.

The overview remained available during deliberate pauses in model reporting, and recovery, indexing and ordinary reporting were ready again at the latest check. The receiver was using rolling-v2, with about 334 MB of hot original evidence, zero cold bytes and no expiry at that sample. Latest native cores were 39–41 °C and matched the retained configuration, with healthy pools. New receipts and source-backed reports continued after maintenance.

## Interruptions and freshness

Five observation gaps exceed ten minutes: about 27 minutes, 12 minutes, 11 hours 57 minutes, 20 minutes and 12 minutes. Windows recorded EventLog service stop at 20:49 Pacific October 6 and start at 08:41 Pacific October 7. The long gap is consistent with that overnight host interruption; it cannot be represented as continuous overnight collection. Model/native worker receipts likewise stop around the beginning of that period and resume afterward. The record does not independently identify every trigger of that shutdown or establish how many UDP messages were missed.

The journal contains 86 observations where the latest report was more than ten minutes old, including deliberate model-evaluation/maintenance pauses. It also contains two observations of a withheld/error report. An old report is not a fresh assessment, even while original collection or browsing continues. Separate process recovery after sign-in is verified; pre-login collection and an always-on service are not implemented here.

Storage budgets and model/backend configuration changed during the retained period. This is evidence of operation and recovery across the documented build, rather than a uniform-duration test of only the final configuration. Missing checkpoints do not themselves prove missing syslog, while a stopped UDP receiver creates a possible receipt gap.

## Claim to use in the article

Over the weeks I've been working on this, I also left the SOC running overnight alongside my normal network activity and checked collection, source links, report age and Vault health. It recovered after Windows sign-in and the documented maintenance, with new receipts and source-backed reports afterward. The log also keeps the pauses and failed requests, so an old report or a missing reading stays visible rather than looking current.

This supports the demonstrated operation/recovery workflow. It does not establish lossless UDP delivery, uninterrupted overnight service, seven days of live expiry or full machine-loss restoration. Seven-day retention behavior was tested on disposable fixtures.

The private interim copy is SHA256-bound: observation journal `2e2f72b07aa49d304ba3db659d0f1969d41747de7f138d5d9c81d02c79628e98`, 272,501 bytes. It includes state snapshots, worker-receipt bindings and selected Windows event metadata. Original live records remain private. Final source/package, voice and publication checks still apply independently of a duration clause.
