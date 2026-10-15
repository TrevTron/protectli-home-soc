# Reader and partner review research

Checked October 5, 2026. This is a focused reading of current public discussions and primary documentation, not a community survey or a guarantee of reception. Reddit supplies reader concerns; technical claims are checked against documentation, code or actual lab receipts. Relative post ages below are what the fetched pages displayed. Cached pages may be older. No commenters or vendors were contacted.

## What readers are asking

| Public source | Observed concern | Consequence for this build |
|---|---|---|
| [r/homelab: Best homelab security setup](https://www.reddit.com/r/homelab/comments/1wwrqds/best_homelab_security_setup/), displayed two days old | A router IDS misses direct same-subnet conversations. Discussion distinguishes VLAN routing from switch-port mirroring. | Show the actual single Ethernet path. Existing apartment Wi-Fi and direct same-LAN traffic are outside the claim. AP/VLAN expansion belongs to its own measured phase. |
| [r/opnsense: IPS/IDS in 2026](https://www.reddit.com/r/opnsense/comments/1qv3jcy/ipsids_in_2026/), displayed eight months old, with later replies | Mixed views on IDS resource costs and encrypted traffic. Several participants prioritize patching, segmentation and limited service exposure. | Avoid a general prevention promise. Explain the harmless signature test, observable TLS metadata limits, and unchanged basic firewall controls. Opinions are not proof that IDS is useless or sufficient. |
| [r/opnsense: Hardware recommendations for 2.5/2.5 IDS/IPS](https://www.reddit.com/r/opnsense/comments/1tssyim/hardware_recommendations_for_2525_idsips/), displayed four months old | Builders ask about inspection throughput under an actual workload. | Keep negotiated link speed, Internet downloads and firewall-terminating LAN tests separate. Two-endpoint forwarding remains unmeasured. Do not import commenters' hardware/performance explanations as a diagnosed cause here. |
| [r/homelab: What monitoring for the lazy occasional homelabber?](https://www.reddit.com/r/homelab/comments/1vsjzcd/what_monitoring_for_the_lazy_occasional_homelabber/) | The author wants timely knowledge that the few services other people depend on are still reachable. | Lead with receiver freshness, report age, explicit gaps, native readings, restart and archive state. A colorful alert count alone does not answer operational health. |
| [r/protectli: V1610, how well does it run?](https://www.reddit.com/r/protectli/comments/1pxqi0d/v1610_how_well_does_it_run_im_choosing_protectli/), cached page displayed six months old | Setup/support, hardware value and future RAM expansion appear in the discussion. | State the supplied configuration and soldered fixed memory. There is no matched competitor, wall-power or support-response experiment in this project, so none should be implied. |

This sample supports specific editorial choices, not claims about what most homelab users prefer. A recent discussion is useful evidence of a current question; a handful of comments cannot establish demand size or a popularity ranking.

## What Protectli actually showcases

Protectli has [featured Home Network Guy's OPNsense guide](https://eu.protectli.com/news/featured-homenetworkguy-beginnersguide-opnsense/), dated November 6, 2023, emphasizing approachable setup and trusted/untrusted device separation. This is a concrete example of their featured material, not a new request from the partner.

Their [firewall guide](https://kb.protectli.com/kb/getting-started-with-vault-firewall/) describes network setup, VPN choices and IDS/IPS resource costs. Their [V1610 page](https://protectli.com/product/v1610/) documents the N6005, six Intel I226-V ports, fixed 16 GB memory, fanless aluminum case and NVMe installation recommendation. These establish hardware/features, not this unit's forwarding capacity or vendor endorsement of the Python tools.

My inference: a reproducible OPNsense build with clear wiring, console recovery, thermal troubleshooting and a useful owned-client test fits that educational pattern. The partnership record itself controls the promise: the open-source reference build, configuration guidance, logging/dashboard and build guide, with Protectli reviewing before publication. The optional AI experiment should support the reference build rather than become an unsupported product claim. Partner review still has to establish what they are comfortable sharing.

Firmware needs a precise note. The [coreboot information page](https://kb.protectli.com/kb/coreboot-information/) lists 0.9.4 and says V-series units are currently shipping with 0.9.3 because of an NVMe issue. The [technical bulletin](https://kb.protectli.com/kb/technical-service-bulletin/) specifically lists V1210/V1211/V1410, and says the issue has not been seen on V1610. Our tested 0.9.3 is recorded; we have neither demonstrated that this unit is affected nor tested a firmware upgrade. Do not attribute Netmap discards to the separate VP2440 ASPM bulletin.

## Related work and the optional model

[TriageWall](https://github.com/aaronphifer/triagewall) already describes local LLM triage for Suricata/Wazuh and keeps traffic blocking separate. Its documentation is related work, not an independently validated comparison. No code was imported. This project should not claim to invent local alert triage or outperform that system.

Our model chooses from code-defined explanations and read-only steps. Facts, grouping, priorities, source hashes and the possible explanation text are deterministic. A table/rule lookup can therefore expose the same available information without inference. The optional model is a bounded contract experiment; no independent user study demonstrates faster investigation or additional detection. The existing `--no-model` mode keeps the deterministic report usable. This admission belongs beside the model feature, not hidden at the end.

## Questions to resolve before a public claim

| Experienced-reader challenge | Concrete answer/evidence | Remaining gate |
|---|---|---|
| Did the request really cross the Vault? | Explicit Ethernet-bound client request, complete reversed response tuple and original allowed/blocked EVE. | No whole-apartment claim; prove new devices after physical expansion. |
| Did a timeout actually prove IPS? | Exact blocked EVE plus zero-body client timeout and allowed response after rollback. | Only the fixture validates the mechanism; real malware efficacy is unmeasured. |
| Why not enable every rule for drop? | Dependency-closed categories and four exact selected TLS C2 rules; fixture reverted to alert. | Feed changes and encrypted visibility still require review. |
| Is this a 2.5 Gb/s IPS benchmark? | Individual rates and terminating-endpoint method are published with boundaries. | Add two owned forwarding endpoints before capacity claims. |
| What does the model add to a SID lookup? | Strict selection experiment, optional deterministic mode, retained rejections. | No proven time saving, independent accuracy or novel detection. |
| Are bigger models worse? | Equal added development and three frozen new cases, all answers retained. | Tiny agent-authored set, different native templates/tokenizers/quantization; no general winner. |
| Why a custom receiver? | Small standard-library Windows reference, inspectable source and citations. | UDP is unauthenticated and lossy; no SIEM replacement, guaranteed delivery or production support claim. |
| What happens after restart or when storage fills? | Real Windows/Vault restart, verified owners, visible failures, stable segmented offsets and restored archive references. | User sign-in/USB login required; 200 MiB aggregate stop cap, 500 MiB archive cap, no deletion or indefinite operation. |
| Has it passed a long soak? | Bounded 48-hour observation started with gap/failure/thermal receipts. | Review the actual finished window. A timer ending is not acceptance. |
| Is the hardware sponsored? | Hardware provided at no charge, exact configuration disclosed. | Trevor/partner review and release permission remain unexecuted. |

## Release choices

Keep the existing title and slug around the practical Home SOC build. Place the harmless alert, controlled block and rollback together so readers can reproduce the evidence trail. Link methods/tools beside each result. Explain the thermal fix and console mistakes candidly. Preserve the failures and competing explanations.

Before posting, show a reviewed physical wiring image, the actual thermal widget and one source-linked report. Originals remain private; public image review is still open. Prepare a short firsthand community post with the disclosure and test method; check the chosen community's current rules before posting. Do not change the headline to a throughput, best-model or autonomous-security claim, and do not promise that knowledgeable readers will have no objections.
