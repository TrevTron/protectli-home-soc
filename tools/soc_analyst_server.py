"""Loopback report viewer and bounded periodic local analyst worker.

This is an explicit launcher, not a Windows service. GET requests never start
inference or change files. Protected POST requests append operator notes only.
The worker has a finite run count and each model
request is bounded. Original evidence is read only and hashes are rechecked.
"""
import argparse
import datetime as dt
import html
import http.server
import json
import os
import pathlib
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse

import soc_analyst as analyst
import soc_flow_review as flow_review
import soc_endpoint_context as endpoint_context
import soc_operator as operator
import soc_evidence
import soc_index
import soc_dashboard
import soc_preserved_evidence
from soc_retained_evidence import EvidenceExpired


def read_latest(root):
    value = json.loads((root/'latest.json').read_text(encoding='utf-8'))
    name = value['run']
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', name):
        raise ValueError('Invalid run name')
    return root/'runs'/name, value


def original_event(run, ref):
    if not re.fullmatch(r'E-[a-f0-9]{16}', ref):
        raise ValueError('Invalid evidence reference')
    index = json.loads((run/'sources.json').read_text(encoding='utf-8'))
    location = index['sources'][ref]
    if not 1 <= location['byte_length'] <= analyst.MAX_LINE or location['byte_offset'] < 0:
        raise ValueError('Invalid source locator')
    data=soc_preserved_evidence.read_record(index['source_path'],location,pin_root=run.parent.parent)
    return data.decode('utf-8')


def worker(args, stopping):
    state = {'pid': os.getpid(), 'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
             'max_runs': args.max_runs, 'period_seconds': args.interval,
             'model': args.model, 'generation_profile': args.generation_profile}
    state['acceleration_requested'] = getattr(args, 'acceleration', 'cpu')
    def state_update(**values):
        state.update(values)
        temp = args.data/'worker-state.pending'
        analyst.write_json(temp, state)
        temp.replace(args.data/'worker-state.json')
    receipts = args.data/'worker-receipts'
    receipts.mkdir(exist_ok=True)
    for iteration in range(args.max_runs):
        if stopping.is_set():
            state_update(status='stopped')
            return
        run_name = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        run = args.data/'runs'/run_name
        command = [sys.executable, str(pathlib.Path(__file__).with_name('soc_analyst.py')),
                   '--log', str(args.log), '--client', args.client, '--salt-file', str(args.data/'aliases.key'),
                   '--output', str(run), '--minutes', str(args.minutes), '--endpoint', args.endpoint,
                   '--model', args.model, '--generation-profile', args.generation_profile]
        command += ['--acceleration', getattr(args, 'acceleration', 'cpu')]
        started = time.monotonic()
        state_update(status='analyzing', iteration=iteration+1, run=run_name,
                     run_started_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        try:
            # Fixed owned script, argv-only. No shell/model-produced commands.
            result = subprocess.run(command, capture_output=True, text=True, timeout=150)
            (receipts/(run_name+'.stdout.txt')).write_text(result.stdout, encoding='utf-8')
            (receipts/(run_name+'.stderr.txt')).write_text(result.stderr, encoding='utf-8')
            value = {'run': run_name, 'worker_exit': result.returncode, 'iteration': iteration+1,
                     'max_runs': args.max_runs, 'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                     'period_seconds': args.interval, 'elapsed_s': time.monotonic()-started,
                     'status': 'completed' if result.returncode == 0 else 'model_withheld_or_error'}
        except (OSError, subprocess.TimeoutExpired) as error:
            value = {'run': run_name, 'worker_exit': None, 'iteration': iteration+1,
                     'max_runs': args.max_runs, 'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                     'status': 'worker_error', 'reason': str(error)}
        analyst.write_json(receipts/(run_name+'.json'), value)
        # Preserve the previous completed report if a worker failed before
        # rendering. The failure remains visible in the separate worker state.
        if (run/'report.html').is_file():
            temp = args.data/'latest.pending'
            analyst.write_json(temp, value)
            temp.replace(args.data/'latest.json')
        state_update(status='waiting' if value['status'] == 'completed' else value['status'],
                     result=value, next_due_utc=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=max(0, args.interval-(time.monotonic()-started)))).isoformat())
        if iteration+1 < args.max_runs and stopping.wait(max(0, args.interval-(time.monotonic()-started))):
            state_update(status='stopped')
            return
    state_update(status='bounded_monitor_complete')
    analyst.write_json(args.data/'worker-finished.json', {'status': 'bounded_monitor_complete', 'runs': args.max_runs,
                                                        'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat()})


def health_worker(args, stopping):
    """Explicit finite read-only collection, independent of model output."""
    state={'pid':os.getpid(),'max_runs':args.max_runs,'period_seconds':args.interval,'collector_failures':0}
    for iteration in range(args.max_runs):
        if stopping.is_set():break
        started=time.monotonic()
        stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        command=[args.powershell,'-NoProfile','-NonInteractive','-File',str(pathlib.Path(__file__).with_name('Collect-SocHealth.ps1')),
                 '-DataDirectory',str(args.data),'-VaultAddress',args.vault_address,'-Port',args.serial_port]
        if args.health_backup:command+=['-BackupPath',str(args.health_backup)]
        state.update(iteration=iteration+1,status='collecting',started_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        analyst.write_json(args.data/'native-health-state.json',state)
        receipt={'started_utc':state['started_utc'],'iteration':iteration+1}
        try:
            result=subprocess.run(command,capture_output=True,text=True,timeout=25)
            receipt.update(exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
            state['status']='waiting' if result.returncode==0 else 'collection_error'
        except (OSError,subprocess.TimeoutExpired) as error:
            receipt.update(exit_code=None,reason=str(error))
            state['status']='collection_error'
        receipt['completed_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
        if receipt['exit_code']!=0:state['collector_failures']+=1
        state['last_exit_code']=receipt['exit_code']
        analyst.write_json(args.data/('health-worker-'+stamp+'.json'),receipt)
        state['completed_utc']=receipt['completed_utc']
        analyst.write_json(args.data/'native-health-state.json',state)
        if iteration+1<args.max_runs and stopping.wait(max(0,args.interval-(time.monotonic()-started))):break
    state['status']='stopped' if stopping.is_set() else 'bounded_collection_complete'
    analyst.write_json(args.data/'native-health-state.json',state)


def index_worker(args, stopping):
    """Independent read-only ingestion; inference never owns the index lock."""
    database=args.data/'evidence.sqlite'
    while not stopping.is_set():
        started=time.monotonic()
        try:
            value=soc_index.sync(database,args.log)
            value.update(status='ready',pid=os.getpid(),elapsed_s=time.monotonic()-started)
        except (OSError,ValueError,sqlite3.Error) as error:
            value={'status':'index_error','reason':str(error),'pid':os.getpid()}
        value['checked_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
        temp=args.data/'index-state.pending'
        analyst.write_json(temp,value)
        temp.replace(args.data/'index-state.json')
        stopping.wait(0.1 if value.get('new_records') and not value.get('caught_up') else 10)


def handler(root, port, monitoring=True, client=None):
    csrf = secrets.token_urlsafe(32)
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, body, content='text/html; charset=utf-8', status=200, forms=False, location=None):
            self.send_response(status)
            self.send_header('Content-Type', content)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            policy = analyst.CONTENT_SECURITY_POLICY
            if forms:
                policy = policy.replace("form-action 'none'", "form-action 'self'")
            self.send_header('Content-Security-Policy', policy)
            if location:
                self.send_header('Location', location)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            host = self.headers.get('Host')
            if (host not in (f'127.0.0.1:{port}', f'localhost:{port}') or
                self.headers.get('Origin') != 'http://'+host or
                self.headers.get('Sec-Fetch-Site', 'same-origin') != 'same-origin'):
                self.respond(b'Invalid request origin', 'text/plain', 403)
                return
            if self.path != '/review':
                self.respond(b'Not found', 'text/plain', 404)
                return
            try:
                if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type') != 'application/x-www-form-urlencoded':
                    raise ValueError('Invalid request format')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 8192:
                    raise ValueError('Invalid request bound')
                self.connection.settimeout(3)
                data = self.rfile.read(length)
                if len(data) != length:
                    raise ValueError('Incomplete request')
                fields = urllib.parse.parse_qs(data.decode('utf-8'), keep_blank_values=True, strict_parsing=True, max_num_fields=7)
                if set(fields) != {'csrf','run','group','brief_hash','state','note'} or any(len(v)!=1 for v in fields.values()):
                    raise ValueError('Invalid fields')
                values = {k:v[0] for k,v in fields.items()}
                if not secrets.compare_digest(values.pop('csrf'), csrf):
                    self.respond(b'Invalid review token', 'text/plain', 403)
                    return
                operator.append_review(root, values['run'], values['group'], values['brief_hash'], values['state'], values['note'], original_event)
                self.respond(b'', status=303, location='/review/'+values['run'])
            except (ValueError, UnicodeError, KeyError, TypeError):
                self.respond(b'Review refused: invalid input or changed evidence.', 'text/plain', 400)
            except OSError:
                self.respond(b'Review unavailable; original logging is separate.', 'text/plain', 503)

        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{port}', f'localhost:{port}'):
                self.respond(b'Invalid host', 'text/plain', 403)
                return
            try:
                path = urllib.parse.urlsplit(self.path).path
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query, max_num_fields=4)
                if any(len(values)!=1 for values in query.values()):
                    raise ValueError('Duplicate query fields')
                state = {} if monitoring else {'status':'snapshot_viewer'}
                if monitoring and (root/'worker-state.json').is_file():
                    state = json.loads((root/'worker-state.json').read_text(encoding='utf-8'))
                    if state.get('pid') != os.getpid():
                        state = {'status': 'worker_state_not_current'}
                if path == '/health':
                    try:
                        _, latest = read_latest(root)
                    except (OSError, ValueError, KeyError, TypeError):
                        latest = None
                    self.respond(operator.health_page(root, latest, state, monitoring).encode())
                    return
                if path.startswith('/review/'):
                    name = path.removeprefix('/review/')
                    self.respond(operator.review_page(root, name, csrf, original_event).encode(), forms=True)
                    return
                if path == '/history':
                    self.respond(operator.history_page(root).encode())
                    return
                database=root/'evidence.sqlite'
                if database.is_file() and (path=='/' or path.startswith('/indexed/') or path=='/api/index'):
                    minutes=int(query.get('minutes',['15'])[0])
                    offset=int(query.get('offset',['0'])[0])
                    as_of=analyst.timestamp(query['as_of'][0]) if 'as_of' in query else None
                    if not 1<=minutes<=1440:raise ValueError('Invalid received window')
                    if path=='/api/index':
                        value=soc_index.groups(database,minutes=minutes,client=client,offset=offset,now=as_of)
                        value['index_state']=json.loads((root/'index-state.json').read_text()) if (root/'index-state.json').exists() else {'status':'unknown'}
                        self.respond(json.dumps(value).encode(),'application/json')
                    elif path=='/':
                        try:_,latest=read_latest(root)
                        except (OSError,ValueError,KeyError,TypeError):latest=None
                        self.respond(soc_dashboard.dashboard(root,database,latest,state,client,minutes,offset,as_of).encode(), forms=True)
                    elif path.startswith('/indexed/group/'):
                        group=path.removeprefix('/indexed/group/')
                        if not re.fullmatch(r'(?:[a-f0-9]{64}|single-[0-9]{1,20})',group):raise ValueError('Invalid group')
                        before=int(query['before'][0]) if 'before' in query else None
                        now=analyst.timestamp(query['as_of'][0]) if 'as_of' in query else None
                        self.respond(soc_dashboard.group_page(database,group,minutes,before,now).encode())
                    elif path.startswith('/indexed/source/'):
                        match=re.fullmatch(r'/indexed/source/([0-9]{1,20})/([a-f0-9]{64})',path)
                        if not match:raise ValueError('Invalid source reference')
                        self.respond(soc_dashboard.source_page(database,int(match[1]),match[2]).encode())
                    else:self.respond(b'Not found','text/plain',404)
                    return
                run, latest = read_latest(root)
                if path == '/review':
                    self.respond(operator.review_page(root, latest['run'], csrf, original_event).encode(), forms=True)
                    return
                if path == '/api/status':
                    value = dict(latest)
                    value['age_seconds'] = (dt.datetime.now(dt.timezone.utc)-analyst.timestamp(latest['completed_utc'])).total_seconds()
                    value['worker_finished'] = state.get('status') == 'bounded_monitor_complete'
                    value['worker'] = state
                    value['monitoring_mode'] = 'bounded_periodic' if monitoring else 'snapshot_viewer'
                    self.respond(json.dumps(value).encode(), 'application/json')
                elif path in ('/', '/report'):
                    content = (run/'report.html').read_text(encoding='utf-8')
                    age = (dt.datetime.now(dt.timezone.utc)-analyst.timestamp(latest['completed_utc'])).total_seconds()
                    health = 'Bounded monitor finished; report is historical.' if state.get('status') == 'bounded_monitor_complete' else 'Periodic monitor active; each report is a snapshot.'
                    if state.get('status') in ('worker_error', 'model_withheld_or_error', 'stopped', 'worker_state_not_current'):
                        health = 'Monitor needs review: '+state['status']+'. Check the retained worker receipt.'
                    if not monitoring:
                        health = 'Snapshot viewer only; periodic inference is not running.'
                    if age > 2*latest.get('period_seconds', 300):
                        health = 'Report is stale. Check worker state before relying on it.'
                    banner = '<nav><a href="/health">Health and coverage</a> · <a href="/review">Review queue</a> · <a href="/history">Saved reports</a> · <a href="/review/'+latest['run']+'">Review this saved snapshot</a> · <a href="http://127.0.0.1:8765/">Original logs</a></nav><p>'+html.escape(health)+f' Snapshot age: {age:.0f} seconds.</p>'
                    content = content.replace('<h1>', '<meta http-equiv="refresh" content="30">'+banner+'<h1>', 1)
                    # Legacy snapshots keep their bytes; qualify their links in
                    # the served page so later refreshes cannot change a source.
                    content = content.replace('href="/evidence/E-', 'href="/evidence/'+latest['run']+'/E-')
                    self.respond(content.encode())
                elif path.startswith('/evidence/'):
                    ref = path.removeprefix('/evidence/')
                    match = re.fullmatch(r'([A-Za-z0-9_-]{1,100})/(E-[a-f0-9]{16})', ref)
                    if match:
                        run = root/'runs'/match[1]
                        ref = match[2]
                    raw = original_event(run, ref)
                    flow_link = '<a href="/investigate/'+run.name+'/'+ref+'">Review this flow across PF and Suricata</a>' if client else ''
                    body = '<!doctype html><meta charset="utf-8"><title>Original source evidence</title><h1>Hash-checked private evidence</h1><p><a href="/">Analyst report</a> '+flow_link+'</p><pre>'+html.escape(raw)+'</pre>'
                    self.respond(body.encode())
                elif path.startswith('/investigate/') and client:
                    match = re.fullmatch(r'/investigate/([A-Za-z0-9_-]{1,100})/(E-[a-f0-9]{16})', path)
                    if not match:
                        raise ValueError('Invalid flow reference')
                    run = root/'runs'/match[1]
                    raw = original_event(run, match[2])
                    index = json.loads((run/'sources.json').read_text(encoding='utf-8'))
                    review = flow_review.investigate(pathlib.Path(index['source_path']), analyst.strict_json(raw), client)
                    context=endpoint_context.load(root,raw,client)
                    if context:
                        review['recorded_endpoint_context']=context
                        review['interpretation'].append('Recorded Windows process observation: '+context['process_name']+'; parent service '+context['service_name']+'. Applies to this exact historical flow and observation time. Intent and current state remain unknown.')
                    context_section=''
                    if context:
                        observed_time='<time data-pacific datetime="'+html.escape(context['captured_utc'],quote=True)+'">'+html.escape(context['captured_utc'])+' (UTC fallback)</time>'
                        context_section='<section><h2>Recorded local process context</h2><p><strong>'+html.escape(context['process_name'])+'</strong> · parent service '+html.escape(context['service_name'])+'</p><p>Observed '+observed_time+'. '+html.escape(context['meaning'])+'</p><p>'+html.escape(context['signature_limit'])+'</p><small>Receipt SHA256: '+html.escape(context['receipt_sha256'])+'</small></section>'
                    body = '<!doctype html><meta charset="utf-8"><title>Exact flow evidence review</title><style>body{font:16px system-ui;background:#101721;color:#e7eef6;margin:25px auto;padding:0 24px;max-width:1200px}a{color:#8fcaff}li{margin:12px 0}section{background:#26364b;padding:18px;border-radius:8px}pre,small{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:24px 0}</style><h1>PF and Suricata flow review</h1><p><a href="/">Analyst report</a></p>'+context_section+'<ul>'+''.join('<li>'+html.escape(v)+'</li>' for v in review['interpretation'])+'</ul><p>Read-only correlation of the exact bidirectional tuple within 60 seconds of the anchor receipt. NAT translation and client outcomes are not guessed.</p><details><summary>Sensor matches, coverage and source hashes</summary><pre>'+html.escape(json.dumps(review,indent=2))+'</pre></details><script>'+analyst.DISPLAY_SCRIPT+'</script>'
                    self.respond(body.encode())
                else:
                    self.respond(b'Not found', 'text/plain', 404)
            except EvidenceExpired:
                self.respond(b'This original record has expired from rolling retention and is not available in the migration baseline or a saved case. Its old byte offset is never reused. Review the saved report and collection coverage; this is not evidence that the event did not occur.', 'text/plain; charset=utf-8', 410)
            except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
                self.respond(b'No completed report or valid source evidence is available yet. Original logging remains separate.', 'text/plain; charset=utf-8', 503)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=pathlib.Path, required=True)
    parser.add_argument('--client', required=True)
    parser.add_argument('--data', type=pathlib.Path, required=True)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--minutes', type=int, default=15)
    parser.add_argument('--interval', type=int, default=300)
    parser.add_argument('--max-runs', type=int, default=12)
    parser.add_argument('--endpoint', default='http://127.0.0.1:11435')
    parser.add_argument('--view-only', action='store_true')
    parser.add_argument('--model', choices=sorted(analyst.OPERATIONAL_MODELS), default=analyst.DEFAULT_MODEL)
    parser.add_argument('--generation-profile', choices=('native', 'common'), default=analyst.DEFAULT_PROFILE)
    parser.add_argument('--acceleration', choices=('cpu','vulkan'), default='cpu')
    parser.add_argument('--no-index', action='store_true')
    parser.add_argument('--native-health', action='store_true')
    parser.add_argument('--vault-address')
    parser.add_argument('--serial-port', default='COM3')
    parser.add_argument('--health-backup', type=pathlib.Path)
    parser.add_argument('--powershell', default=shutil.which('pwsh.exe'))
    args = parser.parse_args()
    analyst.local_endpoint(args.endpoint)
    if args.acceleration=='vulkan' and urllib.parse.urlsplit(args.endpoint).port!=11436:
        parser.error('Vulkan requires the separate admitted endpoint on 11436')
    if not 30 <= args.interval <= 86400 or not 1 <= args.max_runs <= 288 or not 1024 <= args.port <= 65535:
        parser.error('Use bounded interval, run count and an unprivileged port')
    if args.native_health:
        try:
            import ipaddress
            ipaddress.IPv4Address(args.vault_address)
            if not re.fullmatch(r'COM[1-9][0-9]?',args.serial_port):raise ValueError('Invalid serial port')
            if not args.powershell or pathlib.Path(args.powershell).name.lower()!='pwsh.exe' or not pathlib.Path(args.powershell).is_file():raise ValueError('Installed PowerShell 7 required')
        except (ValueError,TypeError):parser.error('Native health requires a Vault IPv4 address, COM port and installed PowerShell 7')
    args.data.mkdir(parents=True, exist_ok=True)
    stopping = threading.Event()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler(args.data, args.port, not args.view_only, args.client))
    if not args.view_only:
        threading.Thread(target=worker, args=(args, stopping), daemon=True).start()
    if not args.no_index:
        threading.Thread(target=index_worker,args=(args,stopping),daemon=True).start()
    if args.native_health:
        threading.Thread(target=health_worker,args=(args,stopping),daemon=True).start()
    try:
        server.serve_forever()
    finally:
        stopping.set()
        server.server_close()


if __name__ == '__main__':
    main()
