# Build and recover a bounded Home SOC lab

Current October 7 entrypoint: [First working Home SOC](QUICKSTART.md) combines the receiver, model-independent overview, source verification, rolling-retention activation, optional inference and sign-in recovery. This guide supplies appliance setup and the original tested wiring. Explicit launcher behavior below is not the whole recovery path.

Local review draft, tested October 5, 2026. Maintenance, the selected block/recovery test and bounded measurements are complete. Follow the measured result files before making performance or prevention claims.

## Cable and access path

Keep a monitor/keyboard or working USB serial console available. On this V1610, the verified mapping is physical Port 1 to `igc0` (LAN) and Port 2 to `igc1` (WAN). Confirm your own interface map before connecting the upstream cable. Leave unused ports unassigned until a deliberate network design needs them.

Connect one owned client to LAN and the authorized upstream Ethernet connection to WAN. The USB-C COM connection carries a serial console, not Ethernet management traffic. This unit's FTDI console uses 115200 baud, 8 data bits, no parity, one stop bit, no flow control. A line-feed newline produced its login prompt in the actual test. Keep the console password enabled; VGA can remain primary with Serial as secondary.

Open the LAN management address using HTTPS. The existing root password is entered privately. A local self-signed certificate requires a human browser trust decision; automation should not bypass a browser interstitial. Save the appropriate timezone, which for this build is America/Los_Angeles, so daylight saving time follows local Pacific time.

Keep GUI listeners on LAN, SSH disabled unless separately justified, and WAN management closed. The upstream network is outside this lab's administration. Do not enumerate other residents, copy their traffic, spoof an approved device's MAC or change upstream services.

## Recovery before maintenance

Download a current XML outside the Vault, verify a SHA256 hash, and keep it private. It contains account hashes and cryptographic material. Preserve an older known-good export as well. Create a named ZFS recovery environment before each major change and verify the new environment appears while the current environment remains active. A same-disk snapshot does not replace the off-device export.

Use OPNsense's production firmware channel and its offered supported sequence. Major upgrades install offline and normally reboot twice. Keep power and direct console access available; a missing web page during installation is expected. Verify the resulting version, WAN/DNS path, sensor display, firewall scope and logging before changing inspection policy.

## Temperature display

For the N6005, save the Intel Core temperature sensor setting. Check the actual kernel attachment and the Thermal Sensors widget. In this build, the sensor was attached but the service had cached an empty sensor list. Restarting System Configuration Daemon refreshed discovery. Save the dashboard layout and verify after reload and reboot. Read the chart itself: the browser accessibility tree can omit canvas values.

Record workload, timestamp and all four core readings. The fanless case releases heat through its exterior; case warmth alone is not a junction-temperature measurement. The side plugs described in this build cover antenna openings and were left in place. Use the bounded temperature-guarded load procedure only after light-load sensors work.

## Inspection and local logs

Start with alert-only capture on the owned LAN interface. Set HOME_NET to that LAN CIDR, review rule dependencies and preserve benign controls. Keep unnecessary packet/payload logging off. Configure a local remote-log target for selected system, firewall and Suricata EVE events while retaining appliance logs.

Start the receiver with the explicit owned-client LAN address and Vault source address. It listens for UDP 5514 on that LAN address and serves the dashboard on loopback port 8765. Keep raw JSONL private. Record device and receipt timestamps separately; fix host time before interpreting apparent event delay. UDP source filtering does not provide cryptographic authentication or guaranteed delivery.

The selected inline test requires disabled checksum, TSO, LRO and VLAN hardware offload, supported Netmap on the physical LAN NIC, one explicitly selected test signature, an unaffected benign control and a demonstrated rollback. An alert or HTTP timeout alone does not prove prevention. See TEST_PROTOCOL.md and the final result ledger for actual status.

Restrict automatic host discovery to the owned LAN. OPNsense HostWatch passively captures ARP/NDP; its default scope must be checked so a local lab does not inventory the shared upstream segment.

## Measurement and release

Explicitly bind client requests to the owned LAN address. Keep the alternate Wi-Fi route separate. Test LAN endpoint transfer, routed Internet observations and bounded CPU load as different workloads. Compare IDS/IPS on the same final platform, endpoint, payload and number of trials. Include latency, resource/thermal samples, duration and failures. A negotiated 2.5 Gbps link is not measured forwarding capacity.

Keep raw exports, addresses, original screenshots, device serial numbers and correspondence out of the public package. Copy only allowlisted files, retain sanitized derivatives separately, and verify their hashes and claims. Review the article and partner message before any repository push, website deployment or external send.

Primary references: [OPNsense updates](https://docs.opnsense.org/manual/updates.html), [IPS configuration](https://docs.opnsense.org/manual/ips.html), [HostWatch](https://github.com/opnsense/hostwatch).

## Verified final configuration

This unit finished on OPNsense 26.7.5-amd64, FreeBSD 15.1-RELEASE-p3 and Suricata 8.0.7_1. The installed ten-category feed contains 37,125 active rules and passed the native configuration test. Netmap runs on the physical LAN with eight workers. HostWatch is explicitly restricted to that LAN.

The retained policy selects original-alert rules from emerging-malware.rules only when all these metadata criteria match: confidence High, signature severity Critical, deployment Perimeter, attack target Client_Endpoint, command-and-control classification and TLS state TLSEncrypt. At the inspected feed snapshot, SIDs 2072081, 2072083, 2072087 and 2072089 became drop; the remaining 37,121 rules remained alert. Review new matches after feed updates. Do not infer broad malware prevention from the four selected rules or from the harmless fixture test.

SID 2100498 was temporarily changed to drop, produced an exact correlated blocked event and failed HTTP request, then returned to alert with an exact correlated allowed response. Normal certificate-validated HTTPS and DNS controls passed. The IPv4 path was tested; the owned client had no global IPv6 address or default route. This build does not establish equivalent IPv6 protection.

The 180-second guarded CPU load peaked at 62 C and cooled normally. The final native storage checks found ZFS online with no known errors and no NVMe critical warning, media errors or thermal transitions. The current off-device configuration export matched the Vault's SHA256; five inactive recovery environments were retained. See [individual results and limitations](PERFORMANCE_RESULTS.md) and [the claim ledger](CLAIM_LEDGER.md). Capture and stream-error discards prevent a lossless-inspection claim.

Use Windows time-service status and an independent clock comparison before interpreting event timing. This installation's repair retained time.windows.com, selected automatic polling with 0x8, restarted W32Time and completed a successful resync. The host then reported no synchronization warning and an approximately 46 ms difference from the Vault. The original pre-repair records are preserved. Follow [Microsoft's polling guidance](https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/w32time-sync-specialpollInterval-ignored) for the applicable host; this is a point-in-time check, not a clock-drift study.

The log receiver is an explicit launcher, not an autostart service. Check its Listening state and disk limit after a client reboot. Both recent views have finite 500-record windows; an informational alert flood can evict a controlled event from the view while leaving its original raw record intact.
