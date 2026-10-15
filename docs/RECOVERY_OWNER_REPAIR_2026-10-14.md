# Receiver ownership and sign-in recovery repair

October 14, 2026. The scheduled sign-in/five-minute recovery task was executing, but refused the current receiver because a manual launch had not updated the separate recovery-owner receipt. The receiver continued collecting; the analyst dashboard remained unavailable.

The receiver launcher now records its verified process ID, native process creation time and executable after confirming UDP socket ownership. It replaces the owner receipt atomically inside the private project directory. Recovery passes its configured owner destination to that launcher. Refusal of an unrecognized process remains; it does not automatically adopt an arbitrary process on the port.

The running receiver was explicitly reconciled after comparing its executable, exact configured arguments, UDP/HTTP socket ownership, reviewed source code and storage state. It was not restarted. A verified before-copy preserved the current raw logs, saved reports, notes, archives and state. Existing immutable file bytes and growing-file prefixes were checked afterward; expected state/index updates are separate from originals.

The actual scheduled task restored the dashboard and isolated reporting runtime. A controlled stop of the idle dashboard followed by the same scheduled action restored it again without stopping collection. A fresh harmless HTTP fixture returned 200/39 bytes, matched the exact client port in a Suricata event and reached a checked report and hash-verified source link. The overview, report, health, history and review routes returned 200; indexing caught up and native readings refreshed.

An isolated loopback rehearsal checks launcher-generated ownership, exact creation time, synthetic receipt, duplicate-launch refusal, unchanged owner metadata after refusal and rejection of an owner path outside the private directory. Both modified PowerShell scripts parse successfully. Earlier invalid rehearsal settings and failed attempts remain in private evidence.

This verifies the configured sign-in recovery action and real scheduled execution. It is not a newly observed Windows sign-out/sign-in or reboot. The task remains Interactive/Limited and requires Windows sign-in; native USB collection still requires an authenticated Vault console after an appliance reboot. No firewall policy, network access or retention policy changed. No credentials were stored, and unrelated model endpoints were not touched.
