"""Generate four human-pilot assistance displays from sealed participant inputs.

No answer keys enter requests. Each request is retained, validated and checked
against runtime context and GPU observations. Original preparation is untouched.
"""
import argparse
import json
from pathlib import Path
import shutil

import soc_analyst as a
import soc_investigation_run as run
import soc_investigation_eval as ev


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--preparation',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--owner',type=Path,required=True)
    p.add_argument('--pause',type=Path,required=True)
    p.add_argument('--resume-remaining',action='store_true')
    args=p.parse_args()
    if args.pause.read_text(encoding='utf-8-sig').strip()!='human-pilot-preparation-20261007-owned-pause':
        raise ValueError('Owned periodic inference pause required')
    owner=json.loads(args.owner.read_text(encoding='utf-8-sig'))
    if owner['endpoint']!=run.ENDPOINT or not owner['cloud_disabled']:
        raise ValueError('Isolated GPU owner required')
    seal=ev.load(args.preparation/'PRE_PARTICIPANT_SEAL.json')
    for file,digest in seal['files'].items():
        if ev.digest((args.preparation/file).read_bytes())!=digest:
            raise ValueError('Original participant preparation changed')
    client=run.Client(run.ENDPOINT)
    _,tags=client.request('/api/tags')
    installed=next(t for t in tags['models'] if t['name']=='qwen3.5:4b')
    if args.resume_remaining:
        protocol=ev.load(args.output/'protocol.json')
        if protocol['model']['digest']!=installed['digest'] or protocol['participant_seal_sha256']!=ev.digest((args.preparation/'PRE_PARTICIPANT_SEAL.json').read_bytes()):
            raise ValueError('Resume source or model changed')
        ev.write(args.output/'resume-receipt.json',{'utc':run.utc(),'tool_sha256':ev.digest(Path(__file__).read_bytes()),
            'reason':'Coordinator summary used an exclusive-create writer. Existing request outcomes are retained; only unrequested tasks continue.'})
    else:
        args.output.mkdir(parents=True,exist_ok=False)
        frozen=args.output/'frozen-tools';frozen.mkdir()
        for name in ('soc_pilot_reports.py','soc_analyst.py','soc_investigation_run.py','soc_investigation_eval.py','soc_context_guard.py'):
            shutil.copy2(Path(__file__).parent/name,frozen/name)
        shutil.copy2(args.owner,args.output/'gpu-owner.json')
        ev.write(args.output/'protocol.json',{'created_utc':run.utc(),'participant_seal_sha256':ev.digest((args.preparation/'PRE_PARTICIPANT_SEAL.json').read_bytes()),
            'cases':['T01','T03','T05','T06'],'model':installed,'human_answers':0,
            'boundary':'Model report generation for a later human pilot, not participant answers. Cases become exposed to this analyst.'})
    reports={}
    for cid in ('T01','T03','T05','T06'):
        brief=ev.load(args.preparation/'participant-inputs'/cid/'brief.json')
        if (args.output/cid).exists():
            outcome=ev.load(args.output/cid/'outcome.json')
            if outcome['status']=='completed':
                a.validate(outcome['report'],brief)
                reports[cid]={'report':outcome['report'],'display_source':'Validated local model selection','outcome_sha256':ev.digest(ev.encoded(outcome))}
            continue
        options=a.generation_options('common','vulkan')
        options.update(num_ctx=8192,num_predict=2048,num_thread=16,num_gpu=99)
        job={'job_id':cid,'case_id':cid,'role':'analyst','phase':'human-pilot-display','condition':None,
             'brief_sha256':ev.digest(ev.encoded(brief)),'deterministic_context_sha256':ev.digest(ev.encoded(a.model_input(brief))),
             'payload':{'model':'qwen3.5:4b','stream':False,'think':False,'keep_alive':0,'options':options,
                        'format':a.schema(brief),'messages':[{'role':'system','content':a.SYSTEM},{'role':'user','content':a.canonical(a.model_input(brief))}]}}
        outcome=run.one_request(client,job,args.output/cid,runtime_log=Path(owner['stderr']))
        if outcome['status']=='completed':
            try:
                report=a.validate(outcome['answer'],brief)
                observations=ev.load(args.output/cid/'ps-observations.json')
                active=[m for sample in observations for m in sample.get('ps',{}).get('models',[])]
                if not active or any(m.get('digest')!=installed['digest'] or not m.get('size_vram',0)>0 for m in active):
                    raise ValueError('Actual model digest and GPU allocation not verified')
                outcome['report']=report
                reports[cid]={'report':report,'display_source':'Validated local model selection','outcome_sha256':ev.digest(ev.encoded(outcome))}
            except Exception as error:
                outcome.update(status='withheld',reason=str(error))
        ev.write(args.output/cid/'outcome.json',outcome)
        ev.write(args.output/cid/'release-observations.json',run.wait_idle(client))
        a.write_json(args.output/'reports.json',reports)
        print(a.canonical({'case':cid,'status':outcome['status'],'elapsed_s':outcome['elapsed_s'],'reason':outcome.get('reason')}),flush=True)
        if outcome.get('halt_following_requests'):
            raise ValueError('Full-input or ownership guard stopped subsequent requests')
    ev.write(args.output/'completion.json',{'completed_utc':run.utc(),'validated_displays':len(reports),'required_displays':4,'human_answers':0})


if __name__=='__main__':main()
