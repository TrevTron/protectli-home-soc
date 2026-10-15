"""Verify the reviewed October 7 CPU and constructed-case export offline.

No model requests, sockets, subprocess model runners or device access. Separate
Python verification processes prevent historical frozen-module collisions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_manifest(root):
    root=Path(root).resolve()
    value=load(root/'PUBLIC_EXPORT_MANIFEST.json')
    entries=value['files']
    actual={p.relative_to(root).as_posix() for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.name!='PUBLIC_EXPORT_MANIFEST.json'}
    require(actual==set(entries),'Export file membership differs')
    for relative,entry in entries.items():
        path=root/relative
        require(not path.is_symlink() and path.resolve().is_relative_to(root),'Unsafe export path')
        raw=path.read_bytes()
        require(digest(raw)==entry['public_sha256'] and len(raw)==entry['public_bytes'],'Public file hash/size differs: '+relative)
        if entry['transformation']=='exact source bytes':
            require(entry['public_sha256']==entry['source_sha256'] and entry['public_bytes']==entry['source_bytes'],'Exact-source declaration differs')
    return entries


def trace_check(root,directory,outcome,raw,guard,entries):
    p=directory/'runtime-request.stderr.bin'
    proof=guard.assess(p.read_bytes(),context=8192,prompt_tokens=raw['prompt_eval_count'])
    original=outcome['input_context']
    entry=entries[p.relative_to(root).as_posix()]
    require(original['trace_sha256']==entry['source_sha256'] and original['trace_bytes']==entry['source_bytes'],'Original trace declaration differs')
    require(proof['verified_full_context'],'Public trace does not prove full context')
    for key in proof:
        if key not in ('trace_sha256','trace_bytes'):
            require(proof[key]==original[key],'Redaction changed context proof: '+key)


def output_check(directory,outcome,a,*,cpu):
    request=(directory/'request.json').read_bytes()
    response=(directory/'response.raw.json').read_bytes()
    raw=load(directory/'response.raw.json');payload=load(directory/'request.json')
    content=raw['message'].get('content','');thinking=raw['message'].get('thinking','')
    require(digest(request)==outcome['request_sha256'],'Request hash differs')
    if not cpu: require(digest(response)==outcome['response_sha256'],'Response hash differs')
    require(raw['done'] is True and raw['done_reason']=='stop' and content and not thinking,'Response not naturally complete')
    require(digest(a.canonical({'content':content,'thinking':thinking}).encode())==outcome['combined_output_sha256'],'Output channel hash differs')
    require(outcome['options']==payload['options'] and payload['think'] is False and payload['keep_alive']==0,'Request options differ')
    require(not load(directory/'pre-request-ps.json')['models'],'Runtime not idle before request')
    require(not load(directory/'release-observations.json')[-1]['ps']['models'],'Runtime not idle after request')
    return payload,raw,content


def cpu(root,entries):
    sys.path.insert(0,str(root/'cpu/frozen-tools'))
    import soc_analyst as a
    import soc_context_guard as guard
    source=root/'cpu';protocol=load(source/'protocol.json');completed=load(source/'complete.json')
    installed={m['name']:m['digest'] for m in load(source/'installed-models.json')}
    counts={};written={};outcomes={}
    for job in protocol['schedule']:
        d=source/f"{job['number']:03}";o=load(d/'outcome.json');brief=load(d/'brief.json')
        require(all(o[k]==v for k,v in job.items()) and o==completed[job['number']-1],'Scheduled CPU outcome differs')
        require(o['status']=='delivered' and o['model_digest']==installed[job['model']],'CPU delivery/artifact differs')
        payload,raw,content=output_check(d,o,a,cpu=True)
        options={**a.generation_options('common','cpu'),'num_thread':16,'num_ctx':8192,'num_predict':2048}
        require(payload['options']==options and payload['model']==job['model'],'CPU configuration differs')
        require(payload['messages']==[{'role':'system','content':a.SYSTEM if job['structured'] else a.FREEFORM_SYSTEM},
                                    {'role':'user','content':a.canonical(a.model_input(brief))}],'CPU prompt cannot be regenerated')
        require(digest(a.canonical(brief).encode())==o['brief_sha256']==protocol['source_briefs'][job['case']],'CPU source brief differs')
        require(o['spare_memory_before_bytes']>=protocol['memory_floor_bytes'],'CPU memory floor differs')
        require(o['deadline_seconds']==(300 if job['structured'] else 600),'CPU deadline differs')
        require(o['eval_count']==raw['eval_count'] and o['prompt_eval_count']==raw['prompt_eval_count'],'CPU token counts differ')
        trace_check(root,d,o,raw,guard,entries)
        models=[m for s in load(d/'ps-observations.json') for m in s['ps'].get('models',[])]
        require(models and all(m['digest']==installed[job['model']] and m['size_vram']==0 for m in models),'CPU execution proof differs')
        if job['structured']:
            require(payload['format']==a.schema(brief),'CPU schema differs')
            report=a.validate(a.strict_json(content),brief)
            require(report==load(d/'accepted-report.json'),'Accepted CPU report differs')
            counts[job['model']]=counts.get(job['model'],0)+1
        else: written[job['number']]=(d,o,payload,content)
        outcomes[job['number']]=o
    reviews=[json.loads(s) for s in (source/'content-review/WRITTEN_RESOURCE_MANUAL_REVIEW_20261007.jsonl').read_text().splitlines()]
    require(len(outcomes)==72 and len(written)==24 and {r['number'] for r in reviews}==set(written),'CPU request/review membership differs')
    for review in reviews:
        d,o,payload,content=written[review['number']]
        require(review['response_file_sha256']==digest((d/'response.raw.json').read_bytes()) and review['outcome_file_sha256']==digest((d/'outcome.json').read_bytes()),'Written assessment not bound to output')
        supplied=json.loads(payload['messages'][1]['content'])
        eg={g['id'] for g in supplied['groups']};ee={r for g in supplied['groups'] for r in g['evidence_refs']}
        foundg=set(re.findall(r'G-[0-9a-f]{12}',content));founde=set(re.findall(r'E-[0-9a-f]{16,}',content))
        scan={'supplied_groups':len(eg),'cited_valid_groups':len(foundg&eg),'invalid_groups':sorted(foundg-eg),
              'cited_valid_evidence':len(founde&ee),'invalid_evidence':sorted(founde-ee)}
        require(scan==review['citation_scan'],'Written citation scan differs')
    return {'study':'cpu','requests_verified':72,'structured_contracts_verified':sum(counts.values()),'written_assessment_bindings_verified':24,
            'limit':'Semantic judgment is an agent assessment. Hash verification does not certify prose accuracy or a resource root cause.'}


def fresh(root,entries):
    sys.path.insert(0,str(root/'fresh/frozen-tools'))
    import soc_analyst as a
    import soc_context_guard as guard
    import soc_fresh_cases as cases
    import soc_investigation_eval as e
    import soc_investigation_v8 as v8
    import soc_investigation_v5 as v5
    import soc_investigation_v2 as v2
    source=root/'fresh';seal=load(source/'cases/PRE_REQUEST_SEAL.json');unique=set();rows=[];reviewrows=[];total=0
    for n in (1,2,3):
        pack=source/f'cases/batch-{n}';result=source/f'results/batch-{n}'
        e.verify(pack)
        require(digest((pack/'manifest.json').read_bytes())==seal['packs'][f'batch-{n}'],'Original case seal differs')
        for case in load(pack/'manifest.json')['cases']:
            folder=pack/case['id'];origin=load(folder/'origin.json');salt=('fresh-constructed-'+str(origin['seed'])+'-'+str(origin['number'])).encode()
            cases.independent_design_check((folder/'records.jsonl').read_bytes(),load(folder/'brief.json'),load(folder/'sources.json'),origin['design_specs'],salt)
            unique.add(digest((folder/'records.jsonl').read_bytes()))
        complete=load(result/'completion.json')
        require(not complete['halt_reason'] and complete['actual_requests']==56,'Fresh pack incomplete')
        selected=load(result/'assistance.json');locked=load(result/'answers.json');assessment=load(result/'v2-assessment.json');protocol=load(result/'protocol.json')
        for role in ('analyst','investigator','reviewer'):
            jobs=load(result/(role+'-jobs.json'))['jobs']
            require(len(jobs)==(8 if role=='analyst' else 24),'Fresh role schedule differs')
            for job in jobs:
                d=result/role/job['job_id'];o=load(d/'outcome.json')
                regenerated,reason=v8.make_job(pack,job,role,selected,locked,job['payload']['model'])
                require(not reason and regenerated==job,'Fresh job cannot be regenerated')
                payload,raw,content=output_check(d,o,a,cpu=False)
                require((d/'request.json').read_bytes()==e.encoded(job['payload']),'Exact fresh request differs from job')
                answer=a.strict_json(content)
                if role=='investigator':answer=v5.decode(answer)
                require(answer==o['answer'] and o['status']=='completed','Fresh saved answer differs')
                require(o['timeout_seconds']==300 and all(o['options'].get(k)==v for k,v in v8.OPTIONS.items()),'Fresh actual execution budget differs')
                trace_check(root,d,o,raw,guard,entries)
                models=[m for s in load(d/'ps-observations.json') for m in s['ps'].get('models',[])]
                expected=protocol['model_roles'][role]['digest']
                require(models and all(m['digest']==expected and m.get('size_vram',0)>0 for m in models),'Fresh GPU execution proof differs')
                if role=='analyst':a.validate(answer,load(pack/job['case_id']/'brief.json'))
                elif role=='investigator':
                    grade=v2.grade(answer,load(pack/job['case_id']/'oracle.json'))
                    prior=next(r for r in assessment['rows'] if r['job_id']==job['job_id'])
                    require(all(grade[k]==prior[k] for k in grade),'Investigation grade differs')
                    rows.append({'batch':n,'job_id':job['job_id'],'phase':o['phase'],'condition':o['condition'],**grade})
                else:
                    oracle=load(pack/job['case_id']/'oracle.json');expected=v2.review_expected(locked[job['job_id']]['answer'],oracle)
                    grade=v2.review_grade(answer,expected)
                    prior=next(r for r in assessment['review_rows'] if r['job_id']==job['job_id'])
                    require(expected==prior['expected_checklist'] and all(grade[k]==prior[k] for k in grade),'Supplementary review grade differs')
                    reviewrows.append(grade)
                total+=1
    require(total==168 and len(unique)==24,'Fresh study membership differs')
    measured=[r for r in rows if r['phase']=='measured'];practice=[r for r in rows if r['phase']=='practice']
    summary=load(source/'audit/summary.json')
    require(sum(r['correct'] for r in measured)==summary['measured_correct']==52 and len(measured)==54,'Fresh measured aggregate differs')
    require(sum(r['correct'] for r in practice)==summary['practice_correct']==18 and len(practice)==18,'Practice aggregate differs')
    require(sum(r['correct'] for r in reviewrows)==summary['review_correct']==49 and len(reviewrows)==72,'Supplementary aggregate differs')
    conditions={k:sum(r['correct'] for r in measured if r['condition']==k) for k in 'ABC'}
    require(conditions=={'A':18,'B':17,'C':17},'Condition outcomes differ')
    return {'study':'fresh','requests_verified':total,'source_cases_verified':len(unique),'measured':{'correct':52,'total':54},'conditions':conditions,
            'practice':{'correct':18,'total':18},'supplementary_review':{'correct':49,'total':72},'human_assignment':'omitted; not publicly verified'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--study',choices=('cpu','fresh'))
    args=parser.parse_args();root=args.root.resolve();entries=verify_manifest(root)
    if args.study:print(json.dumps((cpu if args.study=='cpu' else fresh)(root,entries),sort_keys=True));return
    results=[]
    for study in ('cpu','fresh'):
        done=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--root',str(root),'--study',study],capture_output=True,text=True,timeout=120)
        require(done.returncode==0,done.stderr)
        results.append(json.loads(done.stdout))
    print(json.dumps({'files_verified':len(entries),'results':results},indent=2))


if __name__=='__main__':main()
