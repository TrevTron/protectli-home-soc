"""Append-only operator review notes and bounded local health presentation.

Notes are outside model input and never suppress alerts or change policy.
Existing evidence is immutable; new group evidence needs fresh review.
"""
import datetime as dt
import html
import json
import os
import pathlib
import re
import threading
import urllib.request

import soc_analyst as a
import soc_preserved_evidence

MAX_JOURNAL = 1024*1024
LOCK = threading.Lock()
STATES = {'reviewed': 'Reviewed this snapshot',
          'investigate': 'Needs investigation',
          'expected_context': 'Operator recorded expected context'}


def load_journal(root):
    path = pathlib.Path(root)/'operator-review.jsonl'
    if not path.exists():
        return []
    if path.stat().st_size > MAX_JOURNAL:
        raise ValueError('Review journal exceeds its bound; preserve and archive it manually')
    result=[]
    previous='0'*64
    for line in path.read_bytes().splitlines():
        value=a.strict_json(line.decode('utf-8'))
        digest=value.pop('entry_sha256')
        if value['previous_sha256'] != previous or digest != a.digest(a.canonical(value).encode()):
            raise ValueError('Review journal integrity changed; notes are withheld')
        if value['sequence'] != len(result)+1:
            raise ValueError('Review sequence changed')
        value['entry_sha256']=digest
        result.append(value)
        previous=digest
    return result


def read_brief(root, run_name):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',run_name):
        raise ValueError('Invalid run')
    path=pathlib.Path(root)/'runs'/run_name/'brief.json'
    if path.stat().st_size > 256*1024:
        raise ValueError('Report brief exceeds bound')
    raw=path.read_bytes()
    return a.strict_json(raw.decode()),a.digest(raw)


def evidence_fingerprint(group):
    return a.digest(a.canonical({k:group[k] for k in
        ('id','sid','action','severity','protocol','count','prior_count','change','evidence_refs')}).encode())


def append_review(root, run_name, group_id, brief_hash, state, note, verify_source):
    if state not in STATES or not isinstance(note,str) or not note.strip() or len(note)>1000:
        raise ValueError('Invalid bounded operator note')
    if any(ord(c)<32 and c not in '\n\r\t' for c in note):
        raise ValueError('Control characters refused')
    brief,actual_hash=read_brief(root,run_name)
    if actual_hash != brief_hash:
        raise ValueError('Saved brief changed; review is not recorded')
    matches=[g for g in brief['groups'] if g['id']==group_id]
    if len(matches)!=1:
        raise ValueError('Unknown group')
    group=matches[0]
    verified_records=[]
    for ref in group['evidence_refs']:
        verified_records.append(verify_source(pathlib.Path(root)/'runs'/run_name,ref).encode('utf-8'))
    with LOCK:
        previous=load_journal(root)
        entry={'sequence':len(previous)+1,'recorded_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
               'run':run_name,'group_id':group_id,'brief_sha256':actual_hash,
               'evidence_fingerprint':evidence_fingerprint(group),'state':state,'note':note,
               'previous_sha256':previous[-1]['entry_sha256'] if previous else '0'*64}
        entry['preserved_sources']=[{'sha256':sha,'byte_length':len(raw)} for sha,raw in
                                    sorted({a.digest(raw):raw for raw in verified_records}.items())]
        entry['entry_sha256']=a.digest(a.canonical(entry).encode())
        line=(a.canonical(entry)+'\n').encode()
        path=pathlib.Path(root)/'operator-review.jsonl'
        if (path.stat().st_size if path.exists() else 0)+len(line)>MAX_JOURNAL:
            raise ValueError('Review journal full; original sensor logging is separate')
        # Preserve the exact records before accepting an important-case note.
        # Pins are independent of ordinary seven-day rolling evidence.
        soc_preserved_evidence.pin_records(root,verified_records)
        with path.open('ab') as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
    return entry


def page(title,body,forms=False):
    esc=html.escape
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>'+esc(title)+'</title><style>body{font:16px system-ui;background:#101721;color:#e7eef6;margin:25px auto;padding:0 24px;max-width:1400px}a{color:#8fcaff}section{background:#1c2938;padding:20px;margin:18px 0;border-radius:8px}small{color:#b5c5d6}li{margin:10px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}textarea{width:95%;min-height:65px}select,textarea,button{font:inherit;background:#26364b;color:#fff;border:1px solid #8fa8c1;border-radius:5px;padding:8px}button{cursor:pointer}label{display:block;margin:10px 0}.warn{color:#ffbd69}</style>'
        '<nav><a href="/">Analyst</a> · <a href="/health">Health and coverage</a> · <a href="/review">Review queue</a> · <a href="/history">Saved reports</a> · <a href="http://127.0.0.1:8765/">Original logs</a></nav>'
        '<h1>'+esc(title)+'</h1>'+body+'<script>'+a.DISPLAY_SCRIPT+'</script></html>')


def review_page(root,run_name,token,verify_source=None):
    brief,brief_hash=read_brief(root,run_name)
    journal=load_journal(root)
    last={e['group_id']:e for e in journal}
    esc=lambda v:html.escape(str(v),quote=True)
    body='<p>Review status is your local annotation. It never means proven safe, hides an alert, changes a priority floor or reaches the model. New evidence requires a fresh review.</p>'
    body+='<p>Saved run '+esc(run_name)+' · window ended <time data-pacific datetime="'+esc(brief['window']['end_utc'])+'">'+esc(brief['window']['end_utc'])+'</time>. <a href="/history">Browse saved reports</a>.</p>'
    body+='<p>Showing '+esc(len(brief['groups']))+' groups; '+esc(brief['coverage']['omitted_groups'])+' groups beyond this report bound. Comparison '+('available for retained records' if brief['coverage']['comparison_complete_for_retained_records'] else 'incomplete; novelty is unknown')+'. UDP cannot prove complete delivery.</p>'
    for group in brief['groups']:
        if verify_source:
            for ref in group['evidence_refs']:
                verify_source(pathlib.Path(root)/'runs'/run_name,ref)
        previous=last.get(group['id'])
        status='Not reviewed'
        if previous:
            status=STATES[previous['state']] if previous['evidence_fingerprint']==evidence_fingerprint(group) else 'New evidence since recorded review'
        links=', '.join('<a href="/investigate/'+esc(run_name)+'/'+esc(ref)+'">'+esc(ref)+'</a>' for ref in group['evidence_refs'])
        body+='<section><h2>SID '+esc(group['sid'])+' · '+esc(group['action'])+' · '+esc(group['priority_floor'])+'</h2><p>'+esc(status)+' · '+esc(group['count'])+' received alert records · '+esc(group['change'])+'</p><p>Severity '+esc(group['severity'])+' · '+esc(group['protocol'])+' · prior-window records '+esc(group['prior_count'])+'</p><p>'+links+'</p>'
        if previous:
            body+='<p>Last operator note: '+esc(previous['note'])+'</p>'
        body+='<form action="/review" method="post">'
        for name,value in [('csrf',token),('run',run_name),('group',group['id']),('brief_hash',brief_hash)]:
            body+='<input type="hidden" name="'+name+'" value="'+esc(value)+'">'
        body+='<label>Status <select name="state">'+''.join('<option value="'+key+'">'+esc(label)+'</option>' for key,label in STATES.items())+'</select></label><label>Evidence or follow-up note (1000 characters maximum)<textarea name="note" maxlength="1000" required></textarea></label><button type="submit">Save operator review</button></form></section>'
    if not brief['groups']:
        body+='<section><h2>No alert groups in this snapshot</h2><p>This does not establish complete capture or absence of an intrusion. Historical notes remain below. Review a saved report through its run-qualified review link.</p></section>'
    body+='<h2>Recent operator history</h2>'
    for entry in journal[-30:][::-1]:
        body+='<section><p>'+esc(STATES[entry['state']])+' · <time data-pacific datetime="'+esc(entry['recorded_utc'])+'">'+esc(entry['recorded_utc'])+'</time></p><p>'+esc(entry['note'])+'</p><p><a href="/review/'+esc(entry['run'])+'">Saved report review</a> · '+esc(entry['group_id'])+'</p></section>'
    if not journal:body+='<p>No operator notes recorded yet.</p>'
    return page('Operator review queue',body,forms=True)


def history_page(root):
    esc=lambda v:html.escape(str(v),quote=True)
    runs=pathlib.Path(root)/'runs'
    folders=sorted((p for p in runs.iterdir() if p.is_dir() and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',p.name)),key=lambda p:p.stat().st_mtime,reverse=True)[:200] if runs.exists() else []
    entries=[]
    for folder in folders:
        try:
            brief,_=read_brief(root,folder.name)
            stamp=a.timestamp(brief['window']['end_utc'])
            entries.append((stamp,folder.name,brief))
        except (OSError,ValueError,KeyError,TypeError):
            entries.append((dt.datetime.fromtimestamp(folder.stat().st_mtime,dt.timezone.utc),folder.name,None))
    entries.sort(key=lambda e:e[0],reverse=True)
    body='<p>Up to 30 recent saved snapshots ordered by window time. Quiet current windows do not remove historical evidence. Source links recheck original bytes. Operator notes never mean proven safe.</p>'
    if len(folders)==200:body+='<p class="warn">History index is bounded to the 200 most recently modified run folders. Older files remain on disk.</p>'
    for _,name,brief in entries[:30]:
        try:
            if brief is None:raise ValueError('Invalid brief')
            stamp=brief['window']['end_utc']
            status='Validated model report saved' if (runs/name/'accepted-report.json').is_file() else 'No accepted model report; inspect this saved snapshot'
            body+='<section><h2><a href="/review/'+esc(name)+'">'+esc(name)+'</a></h2><p>'+esc(len(brief['groups']))+' alert groups · '+esc(status)+'</p><p>Window ended <time data-pacific datetime="'+esc(stamp)+'">'+esc(stamp)+'</time></p></section>'
        except (OSError,ValueError,KeyError,TypeError):
            body+='<section><h2>'+esc(name)+'</h2><p class="warn">Incomplete or invalid saved run. Original logging remains separate.</p></section>'
    if not entries:body+='<p>No saved runs yet.</p>'
    return page('Saved reports',body)


def receiver_status():
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8765/api/events',timeout=2) as r:
        raw=r.read(4*1024*1024+1)
    if len(raw)>4*1024*1024:raise ValueError('Receiver status response exceeds bound')
    value=a.strict_json(raw.decode())
    latest=max((a.timestamp(e['received_utc']) for e in value.get('events',[])),default=None)
    return {k:value.get(k) for k in ('accepted_this_run','retention_full','stored_bytes','max_bytes','segment_count','storage_error','capacity_warning','growth_bytes_per_second','estimated_hours_remaining','rolling_retention')},latest


def health_page(root,latest,state,monitoring):
    esc=lambda v:html.escape(str(v),quote=True)
    now=dt.datetime.now(dt.timezone.utc)
    age=(now-a.timestamp(latest['completed_utc'])).total_seconds() if latest else None
    mode='Snapshot viewer. Inference paused.' if not monitoring else 'Finite periodic monitor. '+str(state.get('iteration',0))+'/'+str(state.get('max_runs','?'))+' runs; state '+str(state.get('status','unknown'))+'.'
    report_text = 'No valid completed report. Delivery is unknown.' if latest is None else 'Latest completed report: '+esc(round(age))+' seconds old. '+('Stale. Review collection/worker status.' if age>2*latest.get('period_seconds',300) else 'A recent snapshot, not continuous packet coverage.')
    body='<section><h2>Analyst delivery</h2><p>'+esc(mode)+'</p><p>'+report_text+'</p><p>Last delivery status: '+esc((latest or {}).get('status','unknown'))+'</p><p>No model has firewall-policy or operator-note control. Each child monitor is finite; configured Windows recovery is shown below.</p></section>'
    startup=pathlib.Path(root)/'startup-state.json'
    try:
        if startup.stat().st_size>16384:raise ValueError('Recovery state too large')
        recovery=a.strict_json(startup.read_text(encoding='utf-8-sig'))
        recovery_age=round((now-a.timestamp(recovery['checked_utc'])).total_seconds())
        paused=(pathlib.Path(root)/'recovery'/'paused.flag').exists()
        body+='<section><h2>Windows startup recovery</h2><p>'+('Paused for maintenance.' if paused else 'Last recorded check: '+esc(recovery['status']))+' '+esc(recovery_age)+' seconds ago. '+('Recovery observation is stale.' if recovery_age>600 else '')+'</p><p>User sign-in required; this is not a pre-login Windows service. Five-minute ownership checks reuse recorded processes and renew completed finite batches. No credentials are stored. USB native sampling requires console login after a Vault reboot.</p><p>'+esc(recovery.get('reason',''))+'</p></section>'
    except (OSError,ValueError,KeyError,TypeError):
        body+='<p>No valid Windows recovery check is recorded. Autostart status is unknown.</p>'
    try:
        sampler_path=pathlib.Path(root)/'native-health-state.json'
        if sampler_path.stat().st_size>16384:raise ValueError('Sampler state too large')
        sampler=a.strict_json(sampler_path.read_text(encoding='utf-8'))
        if sampler['pid']!=os.getpid():raise ValueError('Previous sampler')
        body+='<p>Native health collection: '+esc(sampler['status'])+' · '+esc(sampler['iteration'])+'/'+esc(sampler['max_runs'])+' observations, '+esc(sampler['period_seconds'])+' seconds between starts; collector process failures '+esc(sampler['collector_failures'])+'. Model output cannot initiate collection.</p>'
    except (OSError,ValueError,KeyError,TypeError):
        body+='<p>No current native-health sampler is recorded. The timestamped observation below may be from manual collection.</p>'
    try:
        receiver,last=receiver_status()
        receipt_age=round((now-last).total_seconds()) if last else None
        body+='<section><h2>Original log receiver</h2><p>'+('Retention limit reached. New evidence is not being retained.' if receiver['retention_full'] else 'Receiver responded; retention below limit.')+'</p><p>'+esc(round(receiver['stored_bytes']/1048576,2))+' / '+esc(round(receiver['max_bytes']/1048576))+' MiB stored across '+esc(receiver.get('segment_count',1))+' append-only segments. Last retained receipt: '+esc(receipt_age)+' seconds ago.</p><p>'+esc(receiver.get('storage_error') or '')+'</p><p>UDP delivery is unauthenticated and incomplete delivery cannot be excluded. A running receiver is not proof that every source is forwarding.</p></section>'
        rolling=receiver.get('rolling_retention') or {}
        if rolling.get('mode')=='rolling-v2':
            body+='<p>Rolling retention: '+esc(round(rolling['hot_bytes']/1048576,2))+' MiB hot and '+esc(round(rolling['cold_bytes']/1048576,2))+' / '+esc(round(rolling['cold_max_bytes']/1048576))+' MiB compressed cold storage. Sealed segments expire after '+esc(rolling['retention_days'])+' days; capacity can shorten this window. Verified compression reclaims hot space before collection reaches its cap.</p>'
            body+='<p>Expired segments: '+esc(rolling['expired_segments'])+'; expired early for capacity: '+esc(rolling['early_expired_segments'])+'. First retained byte offset: '+esc(rolling['first_retained_offset'])+'. Deferred file cleanup: '+esc(rolling['deferred_cleanup_files'])+' files, '+esc(rolling['deferred_cleanup_bytes'])+' bytes. Saved case records have a separate 64 MiB / 4,096-record limit; a full case budget prevents new notes, not log collection.</p>'
            if receiver.get('capacity_warning'):body+='<p class="warn">Review cold capacity, early expiry, deferred cleanup and storage errors above.</p>'
        else:
            estimate=receiver.get('estimated_hours_remaining')
            if receiver.get('capacity_warning'):
                body+='<p class="warn">Storage needs review: at least 80% used or less than 24 hours remaining at the recently observed growth rate.</p>'
            body+='<p>Estimated log capacity remaining: '+esc(str(estimate)+' hours' if estimate is not None else 'unknown until at least one minute of samples')+'. Recent growth is an estimate, not a retention guarantee. Legacy archives preserve evidence; they do not reclaim log capacity.</p>'
    except (OSError,ValueError,KeyError,TypeError):
        body+='<section><h2>Original log receiver</h2><p class="warn">Status unavailable. Logging health is unknown.</p></section>'
    for filename,title in (('observation-state.json','48-hour operation observation'),('archive-state.json','Private evidence checkpoint')):
        try:
            checkpoint=pathlib.Path(root)/filename
            if checkpoint.stat().st_size>65536:raise ValueError('Checkpoint state too large')
            observation=a.strict_json(checkpoint.read_text(encoding='utf-8-sig'))
            body+='<section><h2>'+title+'</h2><p>Status: '+esc(observation['status'])+'</p>'
            if filename=='observation-state.json':
                body+='<p>'+esc(observation['samples'])+' / '+esc(observation['max_samples'])+' samples; '+esc(observation['gap_count'])+' gaps longer than ten minutes. Window ends <time data-pacific datetime="'+esc(observation['ends_utc'])+'">'+esc(observation['ends_utc'])+'</time>.</p><p>A finished observation window requires review of gaps, failures and temperatures before acceptance. User sign-in is required.</p>'
            else:
                body+='<p>Last attempt <time data-pacific datetime="'+esc(observation['checked_utc'])+'">'+esc(observation['checked_utc'])+'</time>. '+esc(observation.get('source_references_verified','unknown'))+' original citation hashes checked. '+esc(observation.get('reason',''))+'</p><p>Checkpoints run every six hours during the 48-hour window. With rolling retention they verify the current managed segments and saved-case references, then replace one bounded state receipt. They do not create repeated full-history ZIPs. Earlier legacy archives remain preserved under their original bounds. In legacy mode, archiving does not reclaim original log storage.</p>'
            body+='</section>'
        except (OSError,ValueError,KeyError,TypeError):
            body+='<section><h2>'+title+'</h2><p>No valid checkpoint state is recorded.</p></section>'
    path=pathlib.Path(root)/'health-snapshot.json'
    try:
        if path.stat().st_size>65536:raise ValueError('Health snapshot too large')
        health=a.strict_json(path.read_text(encoding='utf-8-sig'))
        snapshot_age=round((now-a.timestamp(health['collected_utc'])).total_seconds())
        body+='<section><h2>Native Vault and host observation</h2><p>Captured <time data-pacific datetime="'+esc(health['collected_utc'])+'">'+esc(health['collected_utc'])+'</time> · '+esc(snapshot_age)+' seconds ago. '+('Observation is stale; collect a new one before relying on it.' if snapshot_age>600 else 'Timestamped read-only observation.')+'</p>'
        vault=health['vault']
        if vault['status']=='observed':
            body+='<p>Vault core temperatures: '+esc(', '.join(str(v)+' °C' for v in vault['core_temperatures_c']))+'</p><p>Pools: '+esc(vault['pools'])+' · Suricata process observed: '+esc(vault['suricata_pid'])+'</p><p>Configuration matches retained backup: '+esc(vault['configuration_matches_backup'])+'</p>'
        else:body+='<p class="warn">Native Vault observation unavailable. Temperature, storage and engine state are unknown.</p>'
        host=health['host']
        body+='<p>Owned Ethernet route: '+esc(host['vault_route_status'])+' · Ethernet DNS: '+esc(host['vault_dns_status'])+' · Wi-Fi state: '+esc(host['wifi_state'])+'</p><p>Tailscale: '+esc(host['tailscale_status'])+' · spare host memory: '+esc(host['available_memory_gib'])+' GiB</p></section>'
    except (OSError,ValueError,KeyError,TypeError):
        body+='<section><h2>Native Vault and host observation</h2><p class="warn">No valid collected observation. Run the read-only health collector; no current temperature or coverage claim is made.</p></section>'
    body+='<section><h2>Coverage and outstanding setup</h2><ul><li>The configured reference client is the Minisforum through the Vault-facing Ethernet path. Existing apartment Wi-Fi is outside this path.</li><li>DNS ad blocking, Proton routing and Vault Tailscale subnet/exit-node access have not been configured in this phase.</li><li>VPN-encrypted content is not decrypted. Devices on the same LAN may communicate without crossing the router.</li><li>Whole-network physical coverage, long-duration operation and public release remain unfinished. Windows recovery requires the separate recorded boot/restart acceptance.</li></ul></section>'
    return page('Health and coverage',body).replace('<h1>','<meta http-equiv="refresh" content="30"><h1>',1)
