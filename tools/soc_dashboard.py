"""Model-independent investigation dashboard for the derived SQLite index."""
import datetime as dt
import html
import json
from pathlib import Path
import urllib.parse

import soc_analyst as analyst
import soc_index as index

STYLE='''
:root{color-scheme:dark;--bg:#0c1118;--panel:#151e2a;--line:#2a3a4d;--muted:#aabacd;--accent:#86e0d0}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#edf3fa;font:16px/1.55 system-ui,sans-serif}
main{max-width:1320px;margin:auto;padding:28px}a{color:var(--accent);text-underline-offset:3px}
nav{display:flex;gap:20px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:18px}
h1{font-size:34px;letter-spacing:-1px;margin:25px 0 5px}h2{font-size:20px;margin:0 0 12px}p{margin:8px 0}
.muted,small{color:var(--muted)}.eyebrow{text-transform:uppercase;font-size:12px;letter-spacing:1.7px;color:var(--accent)}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:25px 0}.card,.panel,.event{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}
.card strong{display:block;font-size:26px}.card span{color:var(--muted);font-size:13px}.columns{display:grid;grid-template-columns:minmax(0,2fr) minmax(260px,1fr);gap:20px}.panel{margin-bottom:18px}
.event{margin:12px 0}.event h3{font-size:16px;margin:7px 0;overflow-wrap:anywhere}.event p{overflow-wrap:anywhere}
.tag{display:inline-block;font-size:12px;border:1px solid #426778;border-radius:20px;padding:2px 9px;margin-right:7px}.urgent{border-color:#d69658;color:#ffc082}.warn{color:#ffc082}
details{margin-top:13px}summary{cursor:pointer;color:var(--accent)}pre,code{overflow-wrap:anywhere;white-space:pre-wrap}pre{background:#0c1118;padding:16px;border-radius:8px;font-size:13px}
select,button{font:inherit;color:inherit;background:#1b2a3a;border:1px solid #536d84;border-radius:6px;padding:7px 12px}form{display:flex;gap:10px;align-items:center;flex-wrap:wrap}footer{border-top:1px solid var(--line);padding-top:18px;margin-top:26px;font-size:13px;color:var(--muted)}
@media(max-width:800px){.columns{grid-template-columns:1fr}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}main{padding:18px}h1{font-size:28px}nav{gap:12px}}
'''


def esc(value):return html.escape(str(value),quote=True)
def pacific(value):return '<time data-pacific datetime="'+esc(value)+'">'+esc(value)+'</time>'


def page(title, body, refresh=False):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            +('<meta http-equiv="refresh" content="30">' if refresh else '')
            +'<title>'+esc(title)+'</title><style>'+STYLE+'</style></head><body><main>'
            +'<nav><a href="/">Overview</a><a href="/report">Analyst report</a><a href="/health">Health and coverage</a><a href="/review">Review notes</a><a href="/history">Saved reports</a></nav>'
            +body+'<footer>Built by <a href="https://unland.dev">Trevor Unland</a> · Protectli Home SOC<br>Pacific display time. Original timestamps and raw evidence retained. Models cannot change firewall policy.</footer>'
            +'<script>'+analyst.DISPLAY_SCRIPT+'</script></main></body></html>')


def dashboard(root, database, latest=None, state=None, client=None, minutes=15, offset=0, as_of=None):
    wall_now=dt.datetime.now(dt.timezone.utc)
    now=as_of or wall_now
    value=index.groups(database,minutes=minutes,limit=25,now=now,client=client,offset=offset)
    status=index.status(database)
    try:
        health=json.loads((Path(root)/'health-snapshot.json').read_text(encoding='utf-8-sig'))
        health_age=(wall_now-analyst.timestamp(health['collected_utc'])).total_seconds()
        temperatures=health['vault']['core_temperatures_c'] if health['vault']['status']=='observed' else []
        temperature=f'{max(temperatures):g} °C' if temperatures else 'Unknown'
        temp_note=f'Sampled {health_age:.0f}s ago'+(' · stale' if health_age>600 else '')
    except (OSError,ValueError,KeyError,TypeError):
        temperature,temp_note='Unknown','No valid temperature sample'
    source_bytes=int(status.get('source_bytes',0));indexed_bytes=int(status.get('checkpoint',0))
    retained_floor=int(status.get('first_retained_offset',0))
    retained_bytes=max(0,source_bytes-retained_floor)
    try:
        worker_index=json.loads((Path(root)/'index-state.json').read_text(encoding='utf-8-sig'))
        index_warning='<p class="warn">Index needs review: '+esc(worker_index['reason'])+'</p>' if worker_index.get('status')=='index_error' else ''
    except (OSError,ValueError,KeyError,TypeError):
        index_warning='<p class="warn">Index worker receipt unavailable. Check the last index pass.</p>'
    age=(wall_now-analyst.timestamp(latest['completed_utc'])).total_seconds() if latest else None
    model_state={'waiting':'Ready','analyzing':'Analyzing','snapshot_viewer':'Reports paused',
                 'model_withheld_or_error':'Needs review','worker_error':'Needs review',
                 'worker_state_not_current':'Needs review','bounded_monitor_complete':'Batch complete'}.get((state or {}).get('status'),'Unknown')
    model_note='No completed report' if latest is None else f"Last completed report {age:.0f}s ago · {latest.get('status','unknown')}"
    body='<p class="eyebrow">Evidence first. Local analysis.</p><h1>Protectli Home SOC</h1><p class="muted">Investigate what the firewall recorded, follow the original evidence, and review the analyst’s explanation.</p>'
    cards=[('Vault temperature',temperature,temp_note),('Indexed records',f"{status['records']:,}",f"{retained_bytes/1048576:.2f} MiB retained original evidence"),
           ('Alert groups',str(value['total_groups']),f"Last {minutes} minutes · exact repetition"),('Analyst',model_state,model_note)]
    body+='<div class="cards">'+''.join('<div class="card"><span>'+esc(label)+'</span><strong>'+esc(main)+'</strong><small>'+esc(note)+'</small></div>' for label,main,note in cards)+'</div>'
    body+='<div class="columns"><section><h2>Alerts to investigate</h2><form method="get" action="/"><label for="window">Received window</label><select id="window" name="minutes">'+''.join('<option value="'+str(n)+'"'+(' selected' if n==minutes else '')+'>'+str(n)+' minutes</option>' for n in (15,60,240,1440))+'</select><button>Apply</button></form>'
    body+='<p class="muted">Blocked and severity 1 events remain first. Grouping changes the display, not the records or their review priority.</p>'
    if not value['groups']:body+='<div class="event"><h3>No alert groups in this received window</h3><p>This does not prove the absence of an intrusion. Check collection and source coverage.</p></div>'
    for group in value['groups']:
        urgent=group['action']=='blocked' or group['alert_severity']==1
        query=urllib.parse.urlencode({'minutes':minutes,'as_of':now.isoformat()})
        scope=f"{group['protocol']} · {group['source_ip']}:{group['source_port']} → {group['destination_ip']}:{group['destination_port']}"
        body+='<article class="event"><span class="tag'+(' urgent' if urgent else '')+'">'+esc('Review first' if urgent else 'Review')+'</span><span class="tag">'+esc(group['action'])+'</span><span class="tag">Severity '+esc(group['alert_severity'])+'</span><h3>'+esc(group['signature'] or 'Unparsed alert context')+'</h3><p>'+esc(scope)+'</p><p><strong>'+esc(group['count'])+' received records</strong> · SID '+esc(group['sid'])+' · revision '+esc(group['rev'])+'</p><small>'+pacific(group['first_received'])+' to '+pacific(group['last_received'])+'</small><p><a href="/indexed/group/'+esc(group['group_id'])+'?'+query+'">Expand records and verify sources</a></p>'+('<p class="warn">Incomplete or invalid context. Kept separately.</p>' if group['malformed'] or group['group_id'].startswith('single-') else '')+'</article>'
    body+='<p class="muted">Showing '+esc(len(value['groups']))+' of '+esc(value['total_groups'])+' groups. This page starts at group '+esc(offset+1)+'.</p>'
    for label,new_offset in [('Previous groups',max(0,offset-25))] if offset else []:
        body+='<p><a href="/?'+urllib.parse.urlencode({'minutes':minutes,'offset':new_offset,'as_of':now.isoformat()})+'">'+label+'</a></p>'
    if value['has_more']:
        body+='<p><a href="/?'+urllib.parse.urlencode({'minutes':minutes,'offset':value['next_offset'],'as_of':now.isoformat()})+'">Next groups in this fixed window</a></p>'
    if as_of:body+='<p class="muted">Fixed window ending '+pacific(now.isoformat())+'. <a href="/">Return to live overview</a></p>'
    body+='</section><aside><section class="panel"><h2>Collection and index</h2>'+index_warning+'<p>'+esc(indexed_bytes)+' / '+esc(source_bytes)+' source bytes indexed.</p><p>'+('Caught up at the last index pass.' if indexed_bytes==source_bytes else '<span class="warn">Index backlog: '+esc(source_bytes-indexed_bytes)+' bytes. Results are incomplete.</span>')+'</p><p>'+esc(status['malformed'] or 0)+' records have parsing issues.</p><p>Last index pass '+pacific(status.get('updated_utc','unknown'))+'</p><p>UDP delivery is not guaranteed. Syslog severity and Suricata severity are distinct.</p><a href="/health">Receiver capacity, temperatures and operating checks</a></section>'
    body+='<section class="panel"><h2>Local analyst</h2><p>'+esc(model_note)+'</p><p>Collection and this view do not wait for model inference. A completed report is a bounded snapshot and may omit groups.</p><a href="/report">Read the latest explanation</a></section><section class="panel"><h2>Noise reduction</h2><p>Exact repetition only. Same rule, revision, action, severity and connection tuple. Missing context stays separate.</p><p>No alert suppression or automatic firewall changes. <a href="/history">Saved reports</a> retain earlier investigations.</p></section></aside></div>'
    return page('Protectli Home SOC',body,refresh=as_of is None)


def group_page(database,group_id,minutes=15,before=None,now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    value=index.members(database,group_id,minutes=minutes,before=before,now=now)
    body='<h1>Original records in this group</h1><p>Fixed received window ending '+pacific(now.isoformat())+'. Up to 50 records on this page; source links verify the full original record hash.</p>'
    for record in value['records']:
        link='/indexed/source/'+str(record['offset'])+'/'+record['sha256']
        body+='<article class="event"><h3>'+esc(record['action'])+' · SID '+esc(record['sid'])+'</h3><p>'+pacific(record['received'])+'</p><small>'+esc(record['segment'])+' · segment byte '+esc(record['segment_offset'])+' · logical byte '+esc(record['offset'])+'</small><p><a href="'+link+'">Verify original record</a></p></article>'
    if value['has_more']:
        query=urllib.parse.urlencode({'minutes':minutes,'before':value['next_before'],'as_of':now.isoformat()})
        body+='<p><a href="/indexed/group/'+esc(group_id)+'?'+query+'">Earlier records</a></p>'
    if not value['records']:body+='<p>No records match this bounded window. Raw evidence remains retained.</p>'
    return page('Grouped source records',body)


def source_page(database,offset,expected_hash):
    raw=index.original(database,offset)
    if analyst.digest(raw.encode())!=expected_hash:raise ValueError('Source citation identity changed')
    return page('Verified original source','<h1>Hash-checked private evidence</h1><p>Logical byte '+esc(offset)+' · SHA256 '+esc(expected_hash)+'</p><pre>'+esc(raw)+'</pre>')
