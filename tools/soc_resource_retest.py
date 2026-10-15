"""Replay exposed SOC tasks under a separately recorded larger CPU budget.

This is not a fresh-case accuracy study. No downloads, service changes, retries,
unloading calls, or protected-port requests. Every output and failure is retained.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait
import datetime as dt
import json
from pathlib import Path
import random
import shutil
import time
import urllib.request

import soc_analyst as a
import soc_context_guard as guard

ENDPOINT = 'http://127.0.0.1:11435'
MODELS = sorted(a.EVALUATION_MODELS)

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

class Client:
    def __init__(self):
        class RefuseRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                raise ValueError('Redirect refused')
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RefuseRedirect())

    def read(self, route, payload=None, timeout=5):
        if route not in ('/api/ps','/api/tags','/api/version','/api/show','/api/chat'):
            raise ValueError('Unadmitted route')
        request = urllib.request.Request(ENDPOINT+route,
            data=a.canonical(payload).encode() if payload is not None else None,
            headers={'Content-Type':'application/json'})
        with self.opener.open(request,timeout=timeout) as response:
            raw=response.read(a.MAX_MODEL_RESPONSE+1)
        if len(raw)>a.MAX_MODEL_RESPONSE:
            raise ValueError('Response byte bound exceeded')
        return raw,a.strict_json(raw.decode())

def spare_memory():
    memory=a.available_memory()
    if memory is None or memory<16*1024**3:
        raise ValueError('At least 16 GiB measured spare memory required')
    return memory

def idle(client, timeout=90):
    deadline=time.monotonic()+timeout
    samples=[]
    while True:
        _,state=client.read('/api/ps')
        samples.append({'utc':utc(),'ps':state})
        if not state.get('models'):
            return samples
        if time.monotonic()>deadline:
            raise ValueError('Existing runtime work remains loaded; subsequent requests stopped')
        time.sleep(1)

def execute(client, job, brief, trace, output, installed_digest):
    directory=output/str(job['number']).zfill(3)
    directory.mkdir(exist_ok=False)
    options=a.generation_options('common','cpu')
    options.update(num_thread=job['threads'],num_ctx=8192,num_predict=2048)
    payload={'model':job['model'],'stream':False,'think':False,'keep_alive':0,
             'options':options,'messages':[{'role':'system','content':a.SYSTEM if job['structured'] else a.FREEFORM_SYSTEM},
                                         {'role':'user','content':a.canonical(a.model_input(brief))}]}
    if job['structured']:
        payload['format']=a.schema(brief)
    body=a.canonical(payload).encode()
    (directory/'request.json').write_bytes(body)
    a.write_json(directory/'brief.json',brief)
    outcome={**job,'started_utc':utc(),'request_sha256':a.digest(body),
             'brief_sha256':a.digest(a.canonical(brief).encode()),'options':options,
             'deadline_seconds':300 if job['structured'] else 600,
             'model_digest':installed_digest,'status':'not_sent'}
    observations=[]
    offset=None
    start=time.monotonic()
    try:
        outcome['spare_memory_before_bytes']=spare_memory()
        _,pre=client.read('/api/ps')
        a.write_json(directory/'pre-request-ps.json',pre)
        if pre.get('models'):
            raise ValueError('Runtime busy; do not contend or unload')
        offset=guard.start(trace)
        outcome['status']='request_sent'
        a.write_json(directory/'outcome.json',outcome)
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending=executor.submit(client.read,'/api/chat',payload,outcome['deadline_seconds'])
            while not pending.done():
                _,ps=client.read('/api/ps')
                observations.append({'utc':utc(),'ps':ps,'spare_memory_bytes':a.available_memory()})
                wait([pending],timeout=2)
            raw,response=pending.result()
        (directory/'response.raw.json').write_bytes(raw)
        content=response.get('message',{}).get('content','')
        thinking=response.get('message',{}).get('thinking','')
        outcome.update(elapsed_s=time.monotonic()-start,done=response.get('done'),
            done_reason=response.get('done_reason'),prompt_eval_count=response.get('prompt_eval_count'),
            eval_count=response.get('eval_count'),eval_duration_ns=response.get('eval_duration'),
            content_characters=len(content),thinking_characters=len(thinking),
            combined_output_sha256=a.digest(a.canonical({'content':content,'thinking':thinking}).encode()))
        trace_bytes=guard.capture(trace,offset)
        (directory/'runtime-request.stderr.bin').write_bytes(trace_bytes)
        proof=guard.assess(trace_bytes,context=8192,prompt_tokens=response.get('prompt_eval_count'))
        outcome['input_context']=proof
        active=[entry for sample in observations for entry in sample['ps'].get('models',[])]
        outcome['runtime_model_seen']=bool(active)
        if not active or any(entry.get('digest')!=installed_digest or entry.get('size_vram')!=0 for entry in active):
            raise ValueError('Actual CPU model/digest observations absent or inconsistent')
        if not proof['verified_full_context']:
            outcome['halt_following_requests']=True
            raise ValueError('Complete input not proved by runtime trace')
        if response.get('done') is not True or response.get('done_reason')!='stop' or thinking or not content:
            raise ValueError('Unfinished, capped, empty or unexpected thinking output')
        if job['structured']:
            report=a.validate(a.strict_json(content),brief)
            a.write_json(directory/'accepted-report.json',report)
        outcome['status']='delivered'
        outcome['semantic_review']='pending; completion is not accuracy'
    except Exception as error:
        outcome.update(status='withheld',reason=str(error),elapsed_s=time.monotonic()-start)
        if offset is not None and not (directory/'runtime-request.stderr.bin').exists():
            (directory/'runtime-request.stderr.bin').write_bytes(guard.capture(trace,offset))
    outcome['completed_utc']=utc()
    a.write_json(directory/'ps-observations.json',observations)
    a.write_json(directory/'outcome.json',outcome)
    a.write_json(directory/'release-observations.json',idle(client))
    return outcome

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--owner',type=Path,required=True)
    parser.add_argument('--phase',choices=['development','comparison'],required=True)
    args=parser.parse_args()
    owner=json.loads(args.owner.read_text(encoding='utf-8-sig'))
    if owner.get('endpoint')!=ENDPOINT or owner.get('gpu_request_layers')!=0 or not owner.get('cloud_disabled'):
        raise ValueError('Recorded isolated CPU owner required')
    trace=Path(owner['stderr'])
    client=Client()
    spare_memory()
    _,state=client.read('/api/ps')
    if state.get('models'):
        raise ValueError('Existing isolated work detected')
    _,tags=client.read('/api/tags')
    installed={entry['name']:entry for entry in tags['models']}
    if any(name not in installed for name in MODELS):
        raise ValueError('All four existing SOC models required; no substitutions/downloads')
    args.output.mkdir(parents=True,exist_ok=False)
    shutil.copy2(args.owner,args.output/'cpu-owner.json')
    _,version=client.read('/api/version')
    a.write_json(args.output/'runtime-version.json',version)
    a.write_json(args.output/'installed-models.json',[installed[name] for name in MODELS])
    frozen=args.output/'frozen-tools'
    frozen.mkdir()
    for name in ['soc_resource_retest.py','soc_analyst.py','soc_evidence.py','soc_context_guard.py']:
        shutil.copy2(Path(__file__).parent/name,frozen/name)
    cases={p.parent.name:a.strict_json(p.read_text(encoding='utf-8')) for p in sorted((args.source/'cases').glob('*/brief.json'))}
    if len(cases)!=12:
        raise ValueError('Expected the 12 exposed historical tasks')
    jobs=[]
    if args.phase=='development':
        jobs=[{'model':'qwen3.5:9b','case':'real_dense_post_restart','structured':False,'threads':n} for n in (2,8,16)]
    else:
        written={json.loads(p.read_text())['case'] for p in (args.source/'execution').glob('*/outcome.json')
                 if json.loads(p.read_text()).get('phase')=='written_analysis'}
        jobs=[{'model':model,'case':name,'structured':True,'threads':16} for model in MODELS for name in cases]
        jobs += [{'model':model,'case':name,'structured':False,'threads':16} for model in MODELS for name in sorted(written)]
        random.Random(6100716).shuffle(jobs)
    jobs=[{'number':i+1,**job} for i,job in enumerate(jobs)]
    a.write_json(args.output/'protocol.json',{'frozen_utc':utc(),'phase':args.phase,'schedule':jobs,
        'context':8192,'answer_cap':2048,'profile':'common','thinking':False,'seed':17,'cold_keepalive':0,
        'memory_floor_bytes':16*1024**3,'source_briefs':{k:a.digest(a.canonical(v).encode()) for k,v in cases.items()},
        'boundary':'Exposed-task resource retest, not fresh accuracy. Development varies threads only; full comparison changes the recorded service budget.'})
    outcomes=[]
    for job in jobs:
        outcome=execute(client,job,cases[job['case']],trace,args.output,installed[job['model']]['digest'])
        outcomes.append(outcome)
        a.write_json(args.output/'progress.json',outcomes)
        print(a.canonical({k:outcome.get(k) for k in ['number','model','case','threads','status','elapsed_s','done_reason','eval_count','reason']}),flush=True)
        if outcome.get('halt_following_requests'):
            raise RuntimeError('Following requests halted; inspect preserved proof')
    a.write_json(args.output/'complete.json',outcomes)

if __name__=='__main__':
    main()
