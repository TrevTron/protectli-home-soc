"""Small local syslog receiver and loopback-only dashboard. Python standard library."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import http.server
import json
import pathlib
import re
import socket
import threading
import time
import urllib.parse
import soc_evidence

PRI = re.compile(r"^<(\d{1,3})>(.*)$", re.S)
RFC5424 = re.compile(r"^1 (\S+) (\S+) (\S+) (\S+) (\S+) (.*)$", re.S)
SEVERITIES = ("emergency", "alert", "critical", "error", "warning", "notice", "info", "debug")


def add_suricata_detail(item: dict) -> dict:
    """Derive a display summary while preserving the original datagram verbatim."""
    if item.get("app") == "suricata":
        match = re.search(r"(\{.*\})\s*$", item.get("raw", ""), re.S)
        if match:
            try:
                eve = json.loads(match[1])
                if isinstance(eve, dict) and eve.get("event_type") == "alert" and isinstance(eve.get("alert"), dict):
                    item["eve"] = eve
            except json.JSONDecodeError:
                pass
    return item


def event_from_datagram(data: bytes, address: str) -> dict:
    raw = data.decode("utf-8", errors="replace").rstrip("\r\n\x00")
    item = {"received_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source": address, "raw": raw, "severity": "unknown", "app": "unknown"}
    match = PRI.match(raw)
    if match and 0 <= int(match[1]) <= 191:
        priority = int(match[1])
        item.update(priority=priority, facility=priority // 8, severity=SEVERITIES[priority % 8])
        rfc = RFC5424.match(match[2])
        if rfc:
            item.update(source_timestamp=rfc[1], hostname=rfc[2], app=rfc[3])
        else:
            # Preserve RFC3164 and vendor formats verbatim; avoid inventing a year/timezone.
            label = re.search(r"\b([\w.-]+)(?:\[\d+\])?: ", match[2])
            if label:
                item["app"] = label[1]
    return add_suricata_detail(item)


class Store:
    def __init__(self, path: pathlib.Path, max_bytes: int, segment_bytes=None):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.items = collections.deque(maxlen=500)
        self.alerts = collections.deque(maxlen=500)
        self.lock = threading.Lock()
        self.accepted = self.rejected = 0
        self.started = time.time()
        self.full = False
        self.storage_error = None
        self.segment_writer = soc_evidence.SegmentWriter(path,max_bytes,segment_bytes) if segment_bytes else None
        self.capacity_samples = collections.deque(maxlen=64)
        # Read only a bounded tail for restart display. Original evidence is never truncated.
        if path.exists() or soc_evidence.index_path(path).exists():
            with soc_evidence.open_evidence(path) as stream:
                stream.seek(0,2)
                _,manifest = soc_evidence.layout(path)
                floor = (manifest or {}).get('base_offset',0)
                stream.seek(max(floor, stream.tell() - 2_000_000))
                if stream.tell()>floor:
                    stream.readline()
                for line in stream:
                    try:
                        self.remember(json.loads(line))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass

    def remember(self, item: dict):
        add_suricata_detail(item)
        self.items.append(item)
        if item.get("eve", {}).get("event_type") == "alert":
            self.alerts.append(item)

    def add(self, item: dict):
        encoded = (json.dumps(item, ensure_ascii=False) + "\n").encode("utf-8")
        with self.lock:
            if self.storage_error:return
            if self.segment_writer:
                try:
                    if not self.segment_writer.append(encoded):
                        self.full=True
                        return
                except (OSError,ValueError) as error:
                    self.storage_error=str(error)
                    self.full=True
                    return
                self.remember(item)
                self.accepted+=1
                self.full=False
                return
            size = self.path.stat().st_size if self.path.exists() else 0
            if size + len(encoded) > self.max_bytes:
                self.full = True
                return
            with self.path.open("ab") as stream:
                stream.write(encoded)
            self.remember(item)
            self.accepted += 1

    def maintenance(self):
        with self.lock:
            writer=self.segment_writer
            if self.storage_error or not writer or not hasattr(writer,'maintain'):return
            if time.monotonic()-writer.last_maintenance<300:return
            try:writer.maintain()
            except (OSError,ValueError) as error:
                self.storage_error=str(error);self.full=True

    def snapshot(self):
        with self.lock:
            stored = self.segment_writer.total if self.segment_writer else self.path.stat().st_size if self.path.exists() else 0
            now = time.monotonic()
            if not self.capacity_samples or now-self.capacity_samples[-1][0]>=5:
                self.capacity_samples.append((now,stored))
            first_time,first_bytes = self.capacity_samples[0]
            elapsed = now-first_time
            rate = (stored-first_bytes)/elapsed if elapsed>=60 else None
            remaining_seconds = (self.max_bytes-stored)/rate if rate and rate>0 else None
            capacity_warning = stored>=self.max_bytes*0.8 or (remaining_seconds is not None and remaining_seconds<86400)
            rolling = self.segment_writer.status() if self.segment_writer and hasattr(self.segment_writer,'status') else {}
            if rolling:
                # Hot usage is reclaimed by verified archiving. Its slope is not
                # a countdown to collection stopping.
                rate=remaining_seconds=None
                capacity_warning=bool(self.storage_error or rolling['early_expired_segments'] or
                    rolling['deferred_cleanup_files'] or rolling['cold_bytes']>=rolling['cold_max_bytes']*0.8)
            return {"accepted_this_run": self.accepted, "rejected_sources": self.rejected,
                    "uptime_seconds": round(time.time() - self.started),
                    "retention_full": self.full, "max_bytes": self.max_bytes,
                    "storage_error": self.storage_error,
                    "segment_count": len(self.segment_writer.value['closed'])+1 if self.segment_writer else 1,
                    "stored_bytes": stored, "capacity_warning": capacity_warning, "rolling_retention": rolling,
                    "growth_bytes_per_second": round(rate,3) if rate is not None else None,
                    "estimated_hours_remaining": round(remaining_seconds/3600,2) if remaining_seconds is not None else None,
                    "events": list(reversed(self.items)),
                    "security_events": list(reversed(self.alerts))}


HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Protectli Home SOC • Local logs</title>
<style>body{background:#101721;color:#e7eef6;font:16px system-ui;margin:0 auto;max-width:1450px;padding:30px}
h1{font-size:27px}p{color:#b5c5d6}.cards{display:flex;gap:18px;flex-wrap:wrap}.card{background:#1b2736;padding:18px;border-radius:8px;min-width:180px}
strong{display:block;font-size:25px}input,select{padding:9px;background:#1b2736;color:#fff;border:1px solid #4a617b;border-radius:5px;margin:18px 8px 18px 0}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #2b3c51;vertical-align:top}td:last-child{font:12px ui-monospace,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-width:750px}
.warn{color:#ffbd69}small{color:#8fa8c1}</style>
<h1>Protectli Home SOC</h1><p>Local syslog receipt • Pacific display time • Raw timestamps retained</p>
<div class="cards"><div class="card">Received this run<strong id="accepted">0</strong></div><div class="card">Stored evidence<strong id="size">0</strong></div><div class="card">Receiver state<strong id="state">Starting</strong></div><div class="card">Alerts in retained view<strong id="alertcount">0</strong></div></div>
<select id="view" aria-label="Event view"><option value="alerts">Suricata alerts</option><option value="all">All recent logs</option></select>
<input id="search" placeholder="Filter message or application" size="38"><select id="severity"><option value="">All severities</option><option>emergency</option><option>alert</option><option>critical</option><option>error</option><option>warning</option><option>notice</option><option>info</option><option>debug</option></select>
<p id="notice">Waiting for data. A running receiver does not prove the Vault is forwarding logs.</p>
<table><thead><tr><th>Received (Pacific)</th><th>Device timestamp</th><th>Application</th><th>Severity</th><th>Message</th></tr></thead><tbody id="events"></tbody></table>
<p><small>Separate views retain up to 500 recent logs and 500 Suricata alerts. Restart reloads a bounded 2 MiB tail. Device and receiver clocks may differ; timestamp differences are not network latency. UDP can lose messages and has no cryptographic authentication. Check the analyst health page for retention mode, hot and cold budgets, expiry and preserved case records. Rolling mode compresses sealed segments before reclaiming hot space; ordinary records can expire. The one-time original baseline and explicitly reviewed case records have independent budgets.</small></p>
<script>let data={events:[]};const $=id=>document.getElementById(id);
function render(){const search=$('search').value.toLowerCase(),sev=$('severity').value;const view=$('view').value==='alerts'?(data.security_events||[]):data.events;const rows=view.filter(e=>(!sev||e.severity===sev)&&(!search||(e.raw+' '+e.app).toLowerCase().includes(search)));$('events').replaceChildren();for(const e of rows){const tr=document.createElement('tr');const a=e.eve;const message=a?'SID '+a.alert.signature_id+' | '+a.alert.action+' | '+a.alert.signature+'\n'+a.proto+' '+a.src_ip+':'+a.src_port+' → '+a.dest_ip+':'+a.dest_port+'\n'+e.raw:e.raw;for(const text of [new Date(e.received_utc).toLocaleString('en-US',{timeZone:'America/Los_Angeles'}),a?a.timestamp:(e.source_timestamp||'Unparsed'),e.app,e.severity,message]){const td=document.createElement('td');td.textContent=text;tr.append(td)}$('events').append(tr)}$('accepted').textContent=data.accepted_this_run;$('alertcount').textContent=(data.security_events||[]).length;$('size').textContent=(data.stored_bytes/1048576).toFixed(2)+' MiB';$('state').textContent=data.retention_full?'Storage full':'Listening';$('notice').textContent=data.retention_full?'Storage limit reached. New events are not being retained. Preserve and archive the existing evidence.':'Showing '+rows.length+' of '+view.length+' events in this view. Raw records remain in the private evidence file.';}
async function refresh(){try{const r=await fetch('/api/events',{cache:'no-store'});if(!r.ok)throw Error(r.status);data=await r.json();render()}catch(e){$('state').textContent='Disconnected'}}$('search').oninput=render;$('severity').onchange=render;$('view').onchange=render;refresh();setInterval(refresh,3000);</script></html>'''


def run(args):
    store = Store(pathlib.Path(args.output), args.max_mib * 1024 * 1024, min(args.segment_mib,args.max_mib)*1024*1024)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind((args.bind, args.port))
    udp.settimeout(1)
    stopping = threading.Event()

    def receive():
        while not stopping.is_set():
            try:
                data, address = udp.recvfrom(65535)
            except socket.timeout:
                store.maintenance()
                continue
            except OSError:
                break
            if address[0] not in args.allow_source:
                with store.lock:
                    store.rejected += 1
                continue
            store.add(event_from_datagram(data, address[0]))

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            allowed_hosts = {f"127.0.0.1:{args.dashboard_port}", f"localhost:{args.dashboard_port}"}
            if self.headers.get("Host") not in allowed_hosts:
                self.send_error(403, "Local dashboard host required")
                return
            path = urllib.parse.urlparse(self.path).path
            direct_page_navigation = path == "/" and self.headers.get("Sec-Fetch-Mode") == "navigate"
            if self.headers.get("Sec-Fetch-Site") == "cross-site" and not direct_page_navigation:
                self.send_error(403, "Cross-site access denied")
                return
            if path == "/api/events":
                body = json.dumps(store.snapshot()).encode()
                content_type = "application/json"
            elif path == "/":
                body = HTML.encode()
                content_type = "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *unused):
            pass

    dashboard = http.server.ThreadingHTTPServer(("127.0.0.1", args.dashboard_port), Handler)
    worker = threading.Thread(target=receive, daemon=True)
    worker.start()
    print(f"Syslog UDP {args.bind}:{args.port}; allowed sources={args.allow_source}", flush=True)
    print(f"Dashboard http://127.0.0.1:{args.dashboard_port}/; evidence={store.path}", flush=True)
    try:
        dashboard.serve_forever(poll_interval=0.5)
    finally:
        stopping.set()
        udp.close()
        dashboard.server_close()
        worker.join(timeout=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", required=True, help="Owned LAN adapter IPv4; never 0.0.0.0")
    parser.add_argument("--allow-source", required=True, action="append", help="Vault LAN IPv4")
    parser.add_argument("--port", type=int, default=5514)
    parser.add_argument("--dashboard-port", type=int, default=8765)
    parser.add_argument("--output", default="private/logs/syslog.jsonl")
    parser.add_argument("--max-mib", type=int, default=1024)
    parser.add_argument("--segment-mib", type=int, default=32)
    options = parser.parse_args()
    if options.bind == "0.0.0.0" or not 1 <= options.max_mib <= 1024 or not 1 <= options.segment_mib <= options.max_mib:
        parser.error("Use a specific owned interface and storage bounds: 1-1024 MiB total, segment no larger than total")
    run(options)
