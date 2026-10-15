"""Private loopback operator-pilot interface. No inference or answer-key routes."""
import argparse
import hashlib
import http.server
import json
import math
import secrets
from pathlib import Path

import soc_analyst as a
import soc_evidence as evidence


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def record_view(directory):
    raw=(directory/'records.jsonl').read_bytes()
    refs=read(directory/'sources.json')
    for ref,row in refs.items():
        record=raw[row['byte_offset']:row['byte_offset']+row['byte_length']]
        if a.digest(record)!=row['sha256'] or ref!='E-'+row['sha256'][:16]:
            raise ValueError('Original participant locator verification failed')
    rows=[]
    for line in raw.splitlines(keepends=True):
        record=a.strict_json(line.decode())
        eve=a.eve_from_record(record)
        ref='E-'+a.digest(line)[:16]
        alert=eve.get('alert',{}) if eve else {}
        key=a.canonical([eve.get(k) for k in ('proto','src_ip','src_port','dest_ip','dest_port')]+[alert.get(k) for k in ('signature_id','gid','rev','action','severity')]) if eve else ref
        rows.append({'ref':ref,'received':record.get('received_utc'),'raw':record.get('raw',''),
                     'app':record.get('app'),'sid':alert.get('signature_id'),'action':alert.get('action'),
                     'severity':alert.get('severity'),'protocol':eve.get('proto') if eve else None,
                     'flow':str(eve.get('src_ip'))+':'+str(eve.get('src_port'))+' → '+str(eve.get('dest_ip'))+':'+str(eve.get('dest_port')) if eve else '',
                     'key':key,'sha256':a.digest(line)})
    return rows


def prepare(preparation,reports,practice,output):
    seal=read(preparation/'PRE_PARTICIPANT_SEAL.json')
    for relative,digest in seal['files'].items():
        if a.digest((preparation/relative).read_bytes())!=digest:
            raise ValueError('Participant seal changed')
    assistance=read(reports/'reports.json')
    if set(assistance)!= {'T01','T03','T05','T06'}:
        raise ValueError('All four validated assistance displays are required')
    forms=read(preparation/'answer-forms-private.json')['rows']
    cases=[]
    catalogue=read(preparation/'participant-inputs/T01/catalogue.json')
    cases.append({'id':'Practice','practice':True,'collapsed':False,'brief':read(practice/'brief.json'),
                  'context':read(practice/'context.json'),'records':record_view(practice),'report':None})
    for row in forms:
        if row['session']!=1:continue
        directory=preparation/'participant-inputs'/row['opaque_case']
        brief=read(directory/'brief.json')
        report=assistance[row['opaque_case']]['report'] if row['condition']!='A' else None
        if report:a.validate(report,brief)
        cases.append({'id':row['opaque_case'],'practice':False,'collapsed':row['condition']=='C',
                      'brief':brief,'context':read(directory/'context.json'),
                      'records':record_view(directory),'report':report})
    value={'version':1,'cases':cases,'catalogue':catalogue,
           'participant_seal_sha256':a.digest((preparation/'PRE_PARTICIPANT_SEAL.json').read_bytes()),
           'reports_sha256':a.digest((reports/'reports.json').read_bytes()),
           'timing_boundary':'Client monotonic measurements, not independently verified human interaction time.'}
    output.mkdir(parents=True,exist_ok=False)
    a.write_json(output/'participant-data.json',value)
    (output/'index.html').write_text(PAGE,encoding='utf-8')
    a.write_json(output/'display-seal.json',{'sha256':a.digest((output/'participant-data.json').read_bytes()),
        'html_sha256':a.digest((output/'index.html').read_bytes()),'human_answers':0})
    return value


PAGE=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Protectli investigation review</title>
<style>body{font:16px/1.6 system-ui;background:#101721;color:#e7eef6;margin:0}main{max-width:1440px;margin:auto;padding:28px}a{color:#93d2ff}h1{margin:0;font-size:30px}h2{font-size:21px}section,.panel{background:#1b2736;border:1px solid #35465b;border-radius:10px;padding:20px;margin:18px 0}button,input,select,textarea{font:inherit}button{padding:9px 15px;background:#7ac8ee;border:0;border-radius:6px;cursor:pointer;color:#101721;margin:5px 8px 5px 0}button:disabled{opacity:.5;cursor:default}textarea,input,select{box-sizing:border-box;background:#101721;color:#e7eef6;border:1px solid #536782;border-radius:5px;padding:10px;width:100%}textarea{min-height:80px}label{display:block;margin:12px 0}.grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(300px,1fr);gap:24px}.muted{color:#bdc9d9}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 monospace}.table{overflow-x:auto}table{width:100%;border-collapse:collapse}td,th{padding:10px;border-bottom:1px solid #35465b;text-align:left;vertical-align:top}code{overflow-wrap:anywhere}details{margin:12px 0}summary{cursor:pointer}#notice{color:#f3d19e}input[type=checkbox]{width:auto}#timer{font-variant-numeric:tabular-nums}@media(max-width:850px){.grid{grid-template-columns:1fr}main{padding:16px}td,th{font-size:14px;padding:7px}}</style>
<main><h1>Protectli investigation review</h1><p>I'm checking whether the local analyst actually helps someone understand the evidence and choose a useful next step. Start with the practice case, then work through six cases. These are constructed test logs, not real incidents.</p><p class="muted">Use what's on the page. No commands, network changes, or outside research are needed. Your answers stay on this PC. Save your first answer before discussing a measured case with me. You can pause or stop whenever you need to.</p>
<section id="welcome"><h2>What I'll ask you to review</h2><p>For each case: what happened, what the sensor allowed or blocked, what that tells you about the client, the record supporting your answer, and what you'd check next. Some cases include the analyst's selected findings. Others show the same evidence and available rule context without those selections.</p><p>This first session uses the current evidence and frozen questions. It has no extra client or process receipt to reveal after your answer, so a next check can leave the question unresolved.</p><button id="begin">Open practice case</button><button id="export">Download saved answers</button><p id="resume"></p></section>
<div id="task" hidden><div class="panel"><b id="case"></b> · <span id="timer">0:00</span><button id="pause">Pause</button><span id="notice"></span></div><div class="grid"><div><section><h2>Evidence and coverage</h2><div id="coverage"></div><div id="context"></div><div class="table" id="groups"></div></section><section id="assistance" hidden><h2>Local analyst findings</h2><div id="report"></div><p class="muted">These are validated model selections from the supplied interpretation options. Validation checks grounding; you still decide whether the findings help.</p></section><section><h2>Original records</h2><p id="recordnote"></p><div id="records"></div></section><details class="panel"><summary>Available rule context and read-only checks</summary><div id="catalogue"></div></details></div>
<section><h2>Your investigation</h2><p>Write this in your own words. A short answer is fine if it explains the evidence.</p><form id="form"><label>Have you already investigated these exact records?<select name="prior_exposure"><option value="no">No</option><option value="yes">Yes</option><option value="unsure">I'm unsure</option></select></label><label>What happened?<textarea name="what_happened" required></textarea></label><label>What did the sensor report as allowed or blocked?<textarea name="sensor_action" required></textarea></label><label>What do we know about whether the client's request worked?<textarea name="client_outcome" required></textarea></label><label>Your decision<select name="disposition"><option value="investigate">Investigate further</option><option value="insufficient">Insufficient evidence to decide</option><option value="expected">Expected activity with supporting evidence</option></select></label><label>Supporting original record reference, or the coverage detail if no record exists<input name="supporting_reference" required></label><label>What's still unknown?<textarea name="unknown" required></textarea></label><label>What specific read-only check would you make next, and why?<textarea name="next_check" required></textarea></label><button id="lock" type="submit">Save and lock my first answer</button></form><div id="final" hidden><p>Your first answer is saved. This case supplies no additional receipt for your next check, so don't assume the check was performed.</p><label>Your final conclusion<textarea id="conclusion"></textarea></label><label>How difficult was this case?<select id="effort"><option value="">Choose a rating</option><option value="1">1: Easy</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5: Hard</option></select></label><label>What helped or confused you?<textarea id="feedback"></textarea></label><button id="finish">Save final answer and continue</button></div><p id="saved" aria-live="polite"></p></section></div></div><section id="done" hidden><h2>First session saved</h2><p>Your answers are preserved. We'll review them against the frozen rubric, including uncertainty, supporting records, missed important evidence and the usefulness of the next check. A single operator session won't tell us how this works for everyone.</p><button onclick="download()">Download your answers</button></section></main>
<script>
const $=id=>document.getElementById(id);let data,token,state,index=0,started,pausedAt=null,pauses=[],firstEvidence=null,locked=false,resumed=null,interrupted=false;const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-Pilot-Token':token}:{},body:body?JSON.stringify(body):undefined});if(!r.ok)throw Error(await r.text());return r.json()}
function elapsed(){return Math.max(0,(performance.now()-started)/1000)}function timing(){return {elapsed_seconds:elapsed(),pause_intervals:pauses,open_pause_seconds:pausedAt===null?0:elapsed()-pausedAt,evidence_found_elapsed_seconds:firstEvidence,analysis_wait_seconds:0,interrupted,previous_initial_elapsed_seconds:resumed?.timing.elapsed_seconds??null,resume_from_initial_sha256:resumed?.sha256??null,timing_source:'browser performance.now; resumed sessions excluded from uninterrupted completion timing'}}
function markEvidence(){if(firstEvidence===null)firstEvidence=elapsed()}function originals(rows){return rows.map(r=>`<details data-evidence><summary><code>${esc(r.ref)}</code> · ${esc(r.app)} · ${esc(r.action||'syslog')} · ${esc(r.sid||'')}</summary><p>${esc(r.received)} · ${esc(r.protocol||'')} · ${esc(r.flow)}</p><pre>${esc(r.raw)}</pre><small>SHA256 ${esc(r.sha256)}</small></details>`).join('')}
function grouped(rows){const groups=new Map();for(const r of rows){if(!groups.has(r.key))groups.set(r.key,[]);groups.get(r.key).push(r)}return [...groups.values()].map(rs=>`<details><summary>${rs.length} record${rs.length===1?'':'s'} · ${esc(rs[0].action||'syslog')} · SID ${esc(rs[0].sid||'none')} · ${esc(rs[0].flow)}</summary>${originals(rs)}</details>`).join('')}
function textLists(value){let out='';for(const [k,v] of Object.entries(value)){out+=`<details><summary>${esc(k.replaceAll('_',' '))}</summary><pre>${esc(typeof v==='string'?v:JSON.stringify(v,null,2))}</pre></details>`}return out}
function findings(r){let result='';const sections=[['Observed',r.observed.map(c=>`${c.group_id}: ${c.field.replaceAll('_',' ')} = ${c.value}.`)],['Possible explanations',r.inferred.map(c=>`${data.catalogue.interpretation_options[c.code]} [${c.group_id}; ${[...new Set(c.evidence_refs)].join(', ')}]`)],['Still unknown',r.unknown.map(c=>({intent:'The alerts do not establish intent or whether an intrusion occurred.',complete_visibility:'UDP receipt and this bounded snapshot cannot prove complete traffic or log capture.',process_identity:'The responsible client process is not included in the alert.',payload:'Payload and encrypted application content are not supplied.'})[c.topic])],['Suggested checks',r.next_steps.map(c=>`${data.catalogue.available_read_only_checks[c.action]} [${c.group_id}]`)]];for(const [title,rows] of sections)result+=`<h3>${esc(title)}</h3><ul>${rows.map(s=>`<li>${esc(s)}</li>`).join('')}</ul>`;return result}
function coverage(c){const v=c.brief.coverage,w=c.brief.window;return `<p>Window: ${esc(w.start_utc)} to ${esc(w.end_utc)} (UTC). Compared with the previous ${w.minutes} minutes.</p><p>${v.current_records} records in the current window; ${v.prior_records} in the previous window. ${v.omitted_groups} groups omitted from this view.</p><p>Comparison ${v.comparison_complete_for_retained_records?'available for retained records':'incomplete; novelty is unknown'}. ${v.receiver_age_seconds===null?'No received records at snapshot time':v.receiver_age_seconds+' seconds since the last receipt at snapshot time'}. UDP delivery completeness is not established.</p><details><summary>Coverage details and source hash</summary><pre>${esc(JSON.stringify(v,null,2))}</pre></details>`}
function openCase(){const c=data.cases[index];started=performance.now();pausedAt=null;pauses=[];firstEvidence=null;locked=false;$('task').hidden=false;$('welcome').hidden=true;$('final').hidden=true;$('form').reset();for(const el of $('form').elements)el.disabled=false;$('pause').textContent='Pause';$('saved').textContent='';$('notice').textContent='';$('case').textContent=c.practice?'Practice case (excluded from results)':`Case ${index} of 6 · ${c.id}`;$('coverage').innerHTML=textLists(c.brief.coverage);$('context').innerHTML=textLists(c.context);$('groups').innerHTML='<table><tr><th>Group / rule</th><th>Sensor action</th><th>Current / prior count</th><th>Connection</th></tr>'+c.brief.groups.map(g=>`<tr><td><code>${esc(g.id)}</code><br>SID ${esc(g.sid)}</td><td>${esc(g.action)}<br>severity ${esc(g.severity)}</td><td>${g.count} / ${g.prior_count}<br>${esc(g.change)}</td><td>${esc(g.protocol)} ${esc(g.source_alias)} → ${esc(g.destination_alias)}<br>${g.evidence_refs.map(r=>`<code>${esc(r)}</code>`).join('<br>')}</td></tr>`).join('')+'</table>';$('records').innerHTML=c.collapsed?grouped(c.records):originals(c.records);$('recordnote').textContent=c.collapsed?'Identical flows are collapsed here. Expand a group to inspect every original record. Changed endpoints, ports, actions, rules or severities remain separate.':'Every original record is listed below. Expand a record to read the retained raw message.';$('assistance').hidden=!c.report;$('report').innerHTML=c.report?textLists(c.report):'';$('catalogue').innerHTML=textLists(data.catalogue);for(const el of document.querySelectorAll('[data-evidence]'))el.addEventListener('toggle',()=>{if(el.open)markEvidence()});sessionStorage.setItem('pilot-open-case',c.id)}
$('begin').onclick=()=>{index=state.answers.filter(x=>x.stage==='final').length;if(index>=data.cases.length){$('welcome').hidden=true;$('done').hidden=false;return}const prior=state.answers.find(x=>x.case===data.cases[index].id&&x.stage==='initial');interrupted=Boolean(sessionStorage.getItem('pilot-open-case')||prior);openCase();$('coverage').innerHTML=coverage(data.cases[index]);if(data.cases[index].report)$('report').innerHTML=findings(data.cases[index].report);if(prior){resumed=prior;locked=true;for(const [key,value] of Object.entries(prior.answer)){if($('form').elements.namedItem(key))$('form').elements.namedItem(key).value=value}for(const el of $('form').elements)el.disabled=true;$('final').hidden=false;$('conclusion').value=prior.answer.what_happened;firstEvidence=prior.timing.evidence_found_elapsed_seconds;$('notice').textContent='Resumed from a locked answer. Timing is marked interrupted.'}};
$('pause').onclick=()=>{if(pausedAt===null){pausedAt=elapsed();$('pause').textContent='Resume';$('notice').textContent='Paused. Avoid investigating the case during the break.'}else{pauses.push([pausedAt,elapsed()]);pausedAt=null;$('pause').textContent='Pause';$('notice').textContent=''}};
$('form').onsubmit=async e=>{e.preventDefault();if(pausedAt!==null){$('saved').textContent='Resume before saving.';return}try{const answer=Object.fromEntries(new FormData($('form')));const receipt=await api('/answer',{case:data.cases[index].id,stage:'initial',answer,timing:timing()});state.answers.push(receipt);locked=true;for(const el of $('form').elements)el.disabled=true;$('final').hidden=false;$('conclusion').value=answer.what_happened;$('saved').textContent='First answer saved and locked. SHA256 '+receipt.sha256}catch(error){$('saved').textContent=error.message}};
$('finish').onclick=async()=>{if(!locked||pausedAt!==null)return;if(!$('effort').value||!$('conclusion').value.trim()){ $('saved').textContent='Add your final conclusion and effort rating.';return}try{const receipt=await api('/answer',{case:data.cases[index].id,stage:'final',answer:{conclusion:$('conclusion').value,effort:Number($('effort').value),feedback:$('feedback').value,next_check_result:'not performed; no additional receipt supplied'},timing:timing()});state.answers.push(receipt);sessionStorage.removeItem('pilot-open-case');index++;if(index<data.cases.length)openCase();else{$('task').hidden=true;$('done').hidden=false}}catch(error){$('saved').textContent=error.message}};
async function download(){const value=await api('/answers');const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));link.download='protectli-operator-pilot-answers.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)}$('export').onclick=download;
setInterval(()=>{if(started){const t=Math.floor(elapsed());$('timer').textContent=Math.floor(t/60)+':'+String(t%60).padStart(2,'0')}},1000);
Promise.all([api('/data'),api('/answers')]).then(([d,s])=>{data=d;state=s;token=d.token;const interrupted=sessionStorage.getItem('pilot-open-case');$('resume').textContent=interrupted?'A previous case was open when the page was closed or refreshed. That interruption is retained; do not count a restart as an uninterrupted task.':''}).catch(error=>$('resume').textContent=error.message);
</script></html>'''

# Apply these exact display substitutions without changing sealed model selections.
PAGE=PAGE.replace("$('coverage').innerHTML=textLists(c.brief.coverage)","$('coverage').innerHTML=coverage(c)")
PAGE=PAGE.replace("$('report').innerHTML=c.report?textLists(c.report):''","$('report').innerHTML=c.report?findings(c.report):''")
PAGE=PAGE.replace('started=performance.now();pausedAt=null;',"started=performance.now();resumed=null;interrupted=Boolean(sessionStorage.getItem('pilot-open-case'));pausedAt=null;")
PAGE=PAGE.replace('if(prior){resumed=prior;locked=true;','if(prior){resumed=prior;interrupted=true;locked=true;')
PAGE=PAGE.replace('</style>','main{box-sizing:border-box;width:100%}.grid>*{min-width:0}section,details{min-width:0}summary,li{overflow-wrap:anywhere}</style>',1)


def serve(root,port):
    raw=(root/'participant-data.json').read_bytes()
    seal=read(root/'display-seal.json')
    if a.digest(raw)!=seal['sha256']:raise ValueError('Display seal changed')
    page=(root/'index.html').read_bytes()
    if a.digest(page)!=seal['html_sha256']:raise ValueError('Display HTML seal changed')
    data=json.loads(raw)
    token=secrets.token_urlsafe(32)
    journal=root/'answers.jsonl'
    def answers():
        if journal.exists() and journal.stat().st_size>1024**2:raise ValueError('Answer journal exceeds bound')
        return [json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,value,status=200,mime='application/json'):
            body=value if isinstance(value,bytes) else a.canonical(value).encode()
            self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.end_headers();self.wfile.write(body)
        def trusted(self):return self.headers.get('Host')==f'127.0.0.1:{port}'
        def do_GET(self):
            if not self.trusted():self.send({'error':'Host refused'},403);return
            if self.path=='/':self.send(page,mime='text/html; charset=utf-8')
            elif self.path=='/data':self.send({**data,'token':token})
            elif self.path=='/answers':self.send({'display_sha256':seal['sha256'],'answers':answers(),'human_participant':'Trevor, if personally completed','practice_excluded':True})
            else:self.send({'error':'Not found'},404)
        def do_POST(self):
            try:
                if not self.trusted() or self.path!='/answer' or self.headers.get('Origin')!=f'http://127.0.0.1:{port}' or self.headers.get('X-Pilot-Token')!=token:
                    raise ValueError('Same-origin token required')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<20000:raise ValueError('Bounded answer required')
                value=a.strict_json(self.rfile.read(length).decode())
                if value.get('stage') not in ('initial','final') or value.get('case') not in [c['id'] for c in data['cases']]:raise ValueError('Unknown task')
                timing=value['timing'];elapsed=timing['elapsed_seconds']
                if type(elapsed) not in (int,float) or not math.isfinite(elapsed) or not 0<=elapsed<=14400:raise ValueError('Invalid timer')
                answer=value['answer']
                if not isinstance(answer,dict) or not answer or any(not isinstance(k,str) or not isinstance(v,(str,int,float)) for k,v in answer.items()):raise ValueError('Invalid answer fields')
                expected_fields={'prior_exposure','what_happened','sensor_action','client_outcome','disposition','supporting_reference','unknown','next_check'} if value['stage']=='initial' else {'conclusion','effort','feedback','next_check_result'}
                if set(answer)!=expected_fields:raise ValueError('Required answer fields differ')
                if value['stage']=='initial' and (answer['prior_exposure'] not in ('yes','no','unsure') or answer['disposition'] not in ('expected','investigate','insufficient')):raise ValueError('Invalid investigation choice')
                if value['stage']=='final' and (type(answer['effort']) is not int or not 1<=answer['effort']<=5):raise ValueError('Effort rating required')
                with evidence.exclusive_lock(root/'answers.lock'):
                    old=answers();cid=value['case'];stage=value['stage']
                    finished=[r for r in old if r['stage']=='final']
                    expected=data['cases'][len(finished)]['id'] if len(finished)<len(data['cases']) else None
                    if cid!=expected or any(r['case']==cid and r['stage']==stage for r in old):raise ValueError('Answer already locked or task order changed')
                    if stage=='final' and not any(r['case']==cid and r['stage']=='initial' for r in old):raise ValueError('Lock initial answer first')
                    receipt={**value,'saved_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                             'display_sha256':seal['sha256'],'display_html_sha256':seal['html_sha256'],'practice':cid=='Practice'}
                    receipt['sha256']=a.digest(a.canonical(receipt).encode())
                    line=(a.canonical(receipt)+'\n').encode()
                    if (journal.stat().st_size if journal.exists() else 0)+len(line)>1024**2:raise ValueError('Answer journal full')
                    with journal.open('ab') as stream:
                        stream.write(line);stream.flush();__import__('os').fsync(stream.fileno())
                self.send(receipt)
            except (ValueError,KeyError,TypeError,OSError) as error:self.send({'error':str(error)},409)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Private review: http://127.0.0.1:{port}/',flush=True)
    server.serve_forever()


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('prepare')
    for name in ('preparation','reports','practice','output'):b.add_argument('--'+name,type=Path,required=True)
    s=sub.add_parser('serve');s.add_argument('--root',type=Path,required=True);s.add_argument('--port',type=int,default=8767)
    args=p.parse_args()
    if args.command=='prepare':prepare(args.preparation,args.reports,args.practice,args.output)
    else:
        if not 1024<=args.port<=65535:p.error('Unprivileged port required')
        serve(args.root,args.port)


if __name__=='__main__':main()
