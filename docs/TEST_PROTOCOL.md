# Owned-device validation protocol

This build covers one owned Windows client behind the Vault. Preserve raw results privately and create separately sanitized derivatives. Other Wi-Fi is a separate traffic path. Do not scan or enroll upstream devices.

## Configuration and recovery

Record actual OPNsense, FreeBSD, Suricata and firmware versions after every upgrade. Retain a current off-device XML with a device/local SHA256 comparison and a named ZFS recovery environment. A boot environment shares the SSD; it does not replace the external XML. Confirm LAN-only HTTPS management, disabled SSH, password-protected serial/VGA console, retained WAN deny rules and correct owned-client routing.

## Detection and selected prevention

1. Record capture interface/mode, exact HOME_NET, ruleset download date and enabled rules. Review startup warnings and packet-drop counters.
2. Bind the client's test request to its Vault-facing LAN IP. Use a certificate-validated HTTPS request and a DNS lookup through the Vault as benign controls. Record local IP/port, remote address, status, exit code and timing.
3. Fetch the harmless standard test response from `http://testmyids.com/`. On October 5 it returned the standard `uid=0(root)` string. This is a signature test, not malware execution. Official quickstart endpoint `testmynids.org/uid/index.html` failed DNS in this run; retain that negative rather than hiding it.
4. Match SID 2100498 in the Vault's EVE record to the exact connection ports and times, then to the local receiver. An alert-only test must show allowed. A returned HTTP 200 alone is not detection proof.
5. For the prevention stage, change only the selected test signature's action to drop, with the remaining reviewed rules alert-only. Use an actual supported inline capture mode with offloads disabled. Keep the physical console available. Verify generated action and runtime mode before testing.
6. Repeat the same positive test and benign controls. Require an actual blocked EVE action and corresponding withheld test response. A timeout by itself does not prove IPS. Preserve negative controls and any unrelated alerts.
7. Revert the test rule to alert, reload and repeat it to prove recovery. Decide the final retained policy from the measured result. The standard uid test rule is not an appropriate blanket production security policy.

Encrypted HTTPS payloads are not decrypted by this build. TLS metadata and DNS rules do not establish complete encrypted-content inspection. A controlled signature pass does not certify general attack detection.

## LAN endpoint measurement

`tools/vault_bounded_checks.py serve` binds TCP 5201 to the explicit Vault LAN IP, accepts only the named owned client, sends at most four 128 MiB downloads and closes within a 90-second server bound. `tools/measure_owned_lan.py` binds the source explicitly, records connection time, bytes, complete/incomplete status and application payload Mbps. No listener is bound to WAN and no persistent firewall rule is added.

Record the negotiated link separately. This workload terminates on the Vault and measures an owned LAN endpoint path. It is not forwarded WAN throughput, an Internet speed test or a sustained 2.5 Gbps certification. Compare only matching modes, byte counts and timing definitions. Preserve individual trials; summarize a median only for complete trials.

## CPU and thermal check

`tools/vault_bounded_checks.py stress --seconds 180` creates four owned `yes` children, samples all four core sensors and load every five seconds, stops at 80 C, and terminates only those child processes. Native kernel thermal controls remain enabled. A sensor/read failure also triggers cleanup. Retain baseline, maximum, end temperature, sample duration, stop reason and recovery readings. Three minutes describes this exact short load check; it does not establish long-term thermal equilibrium or ambient-temperature tolerance.

Inspect kernel logs and SMART thermal/error counters before and after. Keep historical counters distinct from new deltas. Reconfirm HTTPS/DNS, logging receipt and temperature-widget persistence afterward.

## Log pipeline

Prove both local tests and actual Vault event forwarding. Keep receiver and device timestamps separate until their measured clock offset is resolved. The UDP source-IP filter is not authentication, UDP receipt is not guaranteed, and the local receiver is not an autostart service. Retain raw messages even when EVE parsing fails. Verify alerts remain visible despite background logs and after receiver restart.

References: [OPNsense IPS settings](https://docs.opnsense.org/manual/ips.html), [Suricata quickstart](https://docs.suricata.io/en/suricata-8.0.3/quickstart.html), [OPNsense maintenance](https://docs.opnsense.org/manual/updates.html).
