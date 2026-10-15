# Simulated acceptance testing

This round expands the earlier controlled IDS/IPS checks with upstream regression fixtures, private replay of the installed IDS policy, isolated packet exchange, and pipeline fault tests. Tests run on the owned Vault or on loopback in temporary local directories. Marauder remains deferred until tomorrow.

## What each lane establishes

| Lane | Inputs and oracle | Verified result | Boundary |
|---|---|---|---|
| Independent upstream engine regressions | OISF `suricata-verify`, pinned commit `ddab1fde8de8dca2eb53f12e61a7aa4a4a4f133a`; original PCAPs, rules and expected assertions | 23 distinct cases passed; one SSH case requires Suricata 9 and was skipped | Tests engine behavior under upstream test configurations, not coverage of the installed rules |
| Installed policy on upstream captures | 20 unchanged upstream PCAPs; engine-resolved installed policy; 11 rule files copied byte for byte | All 20 completed; zero alerts; 273 configuration fields independently matched | Zero alerts is an observed outcome, not a security pass or all-clear |
| Isolated packet exchange | Three ephemeral FreeBSD VNET stacks; point-to-point virtual links; authored core PF mirror; packet captures and rule counters | All eight cases passed independent packet/counter checks | Mirrors core LAN pass, WAN deny, NAT and anti-spoof behavior. Does not import all OPNsense anchors/tables or measure physical forwarding capacity |
| Installed IDS on original virtual captures | Eight captured cases; installed rules/settings | HTTP UID produced one allowed SID 2100498 alert; other cases produced no alerts | TCP captures contained invalid checksums. HTTPS stream inspection cannot be inferred from the original replay |
| Checksum-controlled replay | Explicit derivatives correcting only invalid TCP checksum bytes; original captures preserved; same IDS settings | All eight completed; zero invalid TCP checksums; HTTPS produced one TLS event and no UID alert; HTTP produced three allowed alerts, including SID 2100498 | Payload, addresses, ports, sequence numbers, timestamps and packet order remain unchanged. Requires TLS-parser evidence and zero invalid TCP checksums |
| Four enabled TLS drop rules | Nine inert authored PCAPs: four exact SNI positives, four suffix negatives, one reserved-domain control | All nine passed exact expectations: four blocked matches with drop records, four suffix negatives and one benign negative | No DNS lookup, external connection, exploit or malware execution. Offline drop selection does not establish physical-wire blocking |
| Actual simulated engine output through the pipeline | 17 cases through a separate loopback UDP receiver, evidence builder and real dashboard handlers | 153 datagrams received; exact SID/action counts; seven original references verified; all report/source routes returned HTTP 200 | New ingestion receipts are explicitly replay times; production logs untouched; no model inference in this lane |
| Local pipeline and fault handling | Existing tests using temporary stores, mocked unavailable model/resource conditions and isolated loopback receivers | 75 tests passed | Verifies software behavior, not loss-free UDP delivery or multi-day availability |
| Four-model assessment | Frozen historical/edge study and separate simulation-source holdout | First 200 complete with all 48 written outcomes reviewed; simulation-source 168 complete with source-linked assessments; common-settings 48 complete with all outcomes individually reviewed | CPU-only, isolated runtime. Scheduled deadlines remain 120 seconds; separate written-analysis lane uses its recorded 300-second deadline. Qwen3.5 4B/common selected; fresh operating report verified |

## Actual packet-exchange checks

| Case | Observed evidence |
|---|---|
| HTTP UID control | HTTP 200, exact 39-byte body/hash, allowed LAN traffic, NAT peer verified |
| HTTPS control | Same endpoint/body/hash; the plaintext UID string is absent from captured TCP payloads |
| LAN ICMP | Three echo requests and three replies; six packets on the allow counter |
| Unsolicited WAN TCP ports | Eight distinct SYN packets arrived; eight deny-counter increments; none forwarded to the virtual LAN |
| WAN source spoof | Five UDP datagrams carrying a LAN-range source alias arrived on the virtual WAN; five anti-spoof-counter increments |
| WAN UDP burst | 200 packets at a configured 100 packets per second; 200 deny-counter increments; none forwarded |
| WAN SYN burst | 100 finite connection attempts; 100 SYN packets and deny-counter increments; none forwarded |
| WAN ICMP | Three echo requests arrived; three deny-counter increments; none forwarded |

The burst cases are finite blocking checks. They do not demonstrate volumetric DoS resistance, ISP-link protection, saturation capacity or protection of apartment Wi-Fi devices outside the Vault path.

## Coverage and evidence

The upstream cases cover ICMP ID/sequence matching, DHCP parse volume, flow drop behavior, ARP, truncated IPv4, IPv6 parsing, fragmented TCP, malformed HTTP/HTTP2, DNS flags/opcodes/negative controls, TLS fingerprints, protocol mismatch, SMB/DCERPC, TCP urgent/reset handling and threshold behavior. These are a selected reproducible matrix, not the entire upstream suite or every possible attack.

Private originals, frozen protocols, source hashes, commands, PCAPs, EVE output, expected counts, failures and cleanup receipts are retained under `private/upstream-suricata-verify-20261005`. Installed-policy archives include private appliance configuration and must not be copied wholesale into a public repository.

Independent local verifiers:

- `private/Verify-UpstreamVaultStudy-20261005.py`: original first four cases, 25 input hashes and 13 exact upstream assertions.
- `private/Verify-SimulationPolicy-20261005.py`: 88 pinned inputs, 11 installed rule files, 273 resolved settings and all 20 raw policy outputs.
- `private/Verify-VnetSimulation-20261005.py`: original packet timestamps/headers/payloads, per-case capture slices, NAT peer receipts and PF-counter deltas.
- `private/Verify-CapturedPolicyReplays-20261005.py`: input hashes, installed snapshot, engine rule-load counts and exact alert/action checks.
- `private/Repair-CaptureChecksums-20261005.py`: explicit derivative audit proving byte changes are confined to TCP checksum fields.

## Preserved failures and corrections

The first expanded upstream run had one missing YAML include and a guessed rule-path failure. The missing file was fetched from the same pinned commit and only the affected upstream case was rerun. The policy replay was rebuilt from Suricata's resolved configuration rather than the top-level YAML. Both failed runs remain recorded.

The first VNET launch stopped before traffic because the fixture server shadowed Python's `http` module. All created jails/interfaces were removed and host PF, XML and live IDS identity remained unchanged. The repaired run used a new evidence directory. Original virtual TCP captures also revealed invalid checksums; their failure counters are retained rather than bypassing checksum validation.

A transfer and scheduled native sampler also collided on COM3. The missing reading remains retained as unavailable; it was not a healthy temperature observation. The serial helper now uses a shared named mutex. A separate COM99 fixture verified cross-process refusal, lock release and failure propagation without opening the real device. Unavailable native collection now returns a failure after retaining its snapshot, so future worker failure counts reflect it. The existing five-minute sampler picked up the changed collector helper on subsequent calls.

A later artifact-export launch missed a Python import after all replay cases had finished. The existing archive was exported through a separately owned, bounded helper. The failure receipt is preserved. Temporary exports bind only the Vault LAN address and serve only an artifact/hash directory for at most ten minutes; completed exports are explicitly stopped.

## Resource and isolation checks

The installed-policy upstream and TLS replays peaked at a sampled 58 degrees Celsius. The packet-exchange lab peaked at a sampled 55 degrees; the checksum-controlled replay peaked at 59 degrees. These remain below the unchanged 75-degree stop bound. A later native check read 39 degrees on all four cores, with healthy pools and the expected configuration hash. This is bounded test evidence, not a general thermal certification.

No physical network interface was attached to a VNET jail. No bridge, apartment route, default WAN route, persistent jail service, host firewall reload or live IDS restart was introduced. Three private jails and their owned interfaces were removed after testing. Host PF rules and configuration hashes matched before and after; the live IDS process stayed the same. The model study separately pauses periodic inference while raw logging and native sampling continue.

## Remaining acceptance work

- Both native-settings model phases are complete. See [expanded results](MODEL_COMPARISON_EXPANDED_RESULTS.md). The simulation holdout covers four unchanged upstream outputs plus 17 actual-policy outputs, all four models and two repeats: 166 delivered, two Gemma HTTP timeouts. All 168 outcomes and 166 returned hashes verify. These 21 source cases yield nine canonical model inputs, including 13 identical empty briefs. Source-linked agent assessment and exact-repeat reuse preserve omissions and duplicate citations separately from packet/engine passes. Both maintenance recoveries produced fresh validated normal reports. The later common-profile decision and live acceptance are recorded in the expanded results.
- The 48-request exploratory common-settings pass is complete, its actual outcomes individually reviewed, and native-configuration results preserved alongside it. It changes several generation controls together and cannot isolate one penalty as the cause of a result. See [the completed model results](MODEL_COMPARISON_EXPANDED_RESULTS.md).
- Measured results are reconciled into the article, NotebookLM materials and local repository draft, with the accepted disclosure and captions preserved.
- Review the actual 48-hour observation when its window ends. Simulation cannot replace that elapsed-time evidence.
- Keep the next connected Marauder radio test separate; it is not currently connected.

Primary sources: [OISF regression suite](https://github.com/OISF/suricata-verify/tree/ddab1fde8de8dca2eb53f12e61a7aa4a4a4f133a), [Suricata 8.0.7 configuration source](https://github.com/OISF/suricata/blob/suricata-8.0.7/suricata.yaml.in), and [FreeBSD VNET jail documentation](https://docs.freebsd.org/en/books/handbook/jails/).

The original VNET policy protocol contains an authoring placeholder in its `frozen_utc` field. File and transfer receipts, plus the stored runner source, establish its actual pre-execution ordering. The frozen original is preserved; later derivative and model-holdout protocols have actual creation timestamps. One inherited remote launcher filename was reused, so the first traceback survives in its captured private console receipt rather than that overwritten remote launcher file. Original run directories, PCAPs and verification archives remain separate.
