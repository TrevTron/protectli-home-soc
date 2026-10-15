# Bounded path and thermal measurements

Measured October 5, 2026. Final platform: OPNsense26.7.5, Suricata8.0.7_1. Individual private receipts are retained. This document is a separately prepared result derivative.

## Routed Internet path

Measure-VaultInternet.ps1 binds the owned Ethernet source, retains certificate validation, checks HTTP200/curl0/exact bytes/source/destination, and uses one1,000,000-byte warmup plus three25,000,000-byte requests with30-second limits. Final modes use fixed Cloudflare172.66.0.218, hostname speed.cloudflare.com. Rate is bytes*8/time_total/1,000,000, including connection/TLS. Other client traffic and upstream/endpoint behavior are not isolated.

| Final condition | Trial | Total seconds | Mbps | Complete |
|---|---:|---:|---:|---|
| PCAP IDS, ten categories | 1 | 0.372428 | 537.017 | Yes |
| PCAP IDS, ten categories | 2 | 0.374797 | 533.622 | Yes |
| PCAP IDS, ten categories | 3 | 0.363742 | 549.840 | Yes |
| Netmap IPS, four Critical TLS C2 drops | 1 | 0.405657 | 493.027 | Yes |
| Netmap IPS, four Critical TLS C2 drops | 2 | 0.416113 | 480.639 | Yes |
| Netmap IPS, four Critical TLS C2 drops | 3 | 0.320995 | 623.063 | Yes |

Medians:537.017Mbps IDS and493.027Mbps IPS. These brief Internet-path observations do not isolate inspection overhead or establish maximum forwarding capacity. Do not calculate a device performance winner from them.

Resource sampler:15 iterations, approximately2-second cadence, each vmstat1 2 discards its cumulative first row for busy calculations. IDS sampled maximum60C, maximum4% busy, minimum12.328GiB free pages. IPS maximum48C, maximum18% busy, minimum12.425GiB free pages. Free pages are not total available memory. Short transfers can occur between samples; these are sampled values, not certified request peaks. All sampler processes exited.

Historical26.1.2 IDS observations were586.053/292.352/360.099Mbps, median360.099. They used an earlier platform and lack native resource samples. They are retained as history, not compared to the final modes. Original duration/byte receipts remain unchanged.

## Owned LAN endpoint

The Vault server binds only the explicit LAN address, accepts only the named client, sends at most four128MiB payloads and closes within90seconds. The client uses the same unchanged Python3.12 script and time.monotonic timing definition in both modes, excluding the protocol header and including payload receive until EOF.

| Condition | Trial rates, Mbps | Median Mbps | Largest sampled core temperature |
|---|---|---:|---:|
| PCAP IDS | 2370.291,2370.291,2370.291,2370.291 | 2370.291 | 60C |
| Netmap IPS | 848.137,827.866,848.808,848.137 | 848.137 | 55C |

All eight payloads were exactly134,217,728bytes and complete. Each server exited after four transfers and port5201 was absent afterward. Windows monotonic resolution was approximately15.6ms in the earlier run; connection times include0/16ms quantization. Rates are approximate. This workload terminates on the Vault and is not a forwarded WAN benchmark or proof of fully inspected2.5Gbps.

## CPU load and recovery

Four owned yes children,180seconds, samples every5seconds,80C stop and sensor-failure cleanup, native protections retained.36 samples,181.132seconds start-to-cleanup, maximum62C, end53/53/53/52C, cooldown47C. No thermal stop. Parent/owned children absent afterward. The extra30-second guarded browser-chart recheck ended at49C; final later reading45C. Its result does not replace the180-second run.

The browser CPU-percentage chart disagreed with native99-100% busy intervals during the first run. A six-second native stream probe produced fresh intervals; the cause of the browser discrepancy remains unproven. Use native interval values for load evidence. Temperature widget values were visually verified and persisted.

Final storage: ZFS ONLINE/zero known errors, NVMe critical warning0/media errors0/error log0/thermal transitions0. Composite43.85C and sensor251.85C after LAN. Power cycles10/unsafe shutdowns6 unchanged. These short tests are not a thermal-equilibrium or longevity study.

## Capture and stability limitations

PCAP cumulative kernel counters later showed962,578packets/313,268drops across its full40+minute runtime. No immediate pre-LAN boundary was retained. Do not attribute all drops to that one workload or call all payloads inspected.

The controlled-test Netmap engine snapshot showed123blocked packets:1rule,16flow_drop,106stream_error. Final engine after policy restart: at14:28:34PDT, uptime5m14s,610,614packets,610,426accepted,188stream-error discards (~0.031%). No kernel-drop counter was emitted in this Netmap snapshot; absence is not a zero-loss certificate. Final stream errors span background traffic and tests and have no proven cause. Native protections remain enabled.

A two-minute sampler retained the same final engine PID through12samples with ordinary traffic; temperatures41-45C. Later guard-load samples are separate. No reboot/thermal error was observed, and HTTPS/DNS continued to pass. This is a bounded stability observation, not an unattended soak or general false-positive certification.

Source: [Cloudflare endpoint documentation](https://github.com/cloudflare/speedtest). Protocol: TEST_PROTOCOL.md. Raw Internet, LAN, resource, CPU, counters and storage receipts remain private.

