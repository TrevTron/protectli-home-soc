"""Independent source audit and descriptive ranking. No inference or answer repairs."""
import json
from pathlib import Path
from comparison import HERE, BASE, V2, prior, canonical, sha

DIMENSIONS = ['contexts','next_checks','client_outcome','client_refs','intrusion_established','delivery_complete']

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def independent(case_id, answer):
    case,raw,locators,groups=prior.read_case(case_id,'evaluation')
    oracle=case['oracle']
    if not isinstance(answer,dict) or set(answer)!=set(DIMENSIONS):
        return dict.fromkeys(DIMENSIONS,False)
    records=[prior.original(raw,locators,r) for r in locators]
    join_fields=('attempt_id','event_utc','protocol','source_alias','source_port','destination_alias','destination_port')
    matched=[r for r in case['receipts'] if any(all(rec.get(k)==r.get(k) and rec.get(k) is not None for k in join_fields) for rec in records)]
    allowed=set(oracle['eligible_contexts'])
    if any(r.get('sid')==2016149 for r in records) and not any(r.get('kind')=='process_socket' for r in matched):
        allowed.add('stun_process_unknown')
    contexts,checks,refs=(answer[k] for k in ('contexts','next_checks','client_refs'))
    def valid_list(v):return isinstance(v,list) and all(isinstance(x,str) for x in v) and len(v)==len(set(v))
    result={
        'contexts':valid_list(contexts) and set(oracle['required_contexts'])<=set(contexts)<=allowed,
        'next_checks':valid_list(checks) and 1<=len(checks)<=3 and set(checks)<=set(oracle['useful_checks']),
        'client_outcome':answer['client_outcome']==oracle['client_outcome'],
        'client_refs':valid_list(refs) and set(refs)==set(oracle['client_refs']),
        'intrusion_established':answer['intrusion_established'] is False,
        'delivery_complete':answer['delivery_complete'] is False}
    expected_refs={r['receipt_id'] for r in matched if r.get('kind')=='client_result'}
    assert expected_refs==set(oracle['client_refs']),case_id
    return result

def main():
    project=BASE.parents[1]
    seal=load(HERE/'PRE_EXECUTION_SEAL.json')
    for rel,digest in seal['files'].items():assert sha((project/rel).read_bytes())==digest,rel
    for item in load(V2/'FINAL_SEAL.json')['files']:
        assert sha((project/item['path']).read_bytes())==item['sha256'],item['path']
    rows=[];workloads={}
    for lane in ('harder-ollama-01','harder-ling-01'):
        root=HERE/lane;protocol=load(root/'protocol.json')
        for job in protocol.get('requests',protocol.get('jobs')):
            path=root/job['name'];out=load(path/'outcome.json');resp=load(path/'response.json')
            if lane=='harder-ollama-01':
                proposed=load(root/'requests'/(job['name']+'.json'));req=proposed['request']
                assert sha((root/'requests'/(job['name']+'.json')).read_bytes())==job['proposal_sha256']
                message=resp['message'];stop=resp.get('done_reason');natural=resp.get('done') is True and stop=='stop' and not message.get('thinking')
                schema=req['format'];cpu=out['cpu_residency_observed']
            else:
                req=load(root/(job['name']+'-request.json'));choice=resp['choices'][0];message=choice['message']
                natural=choice['finish_reason']=='stop' and not message.get('thinking') and not message.get('reasoning_content')
                schema=req['response_format']['json_schema']['schema'];cpu=out['cpu_only_configuration']
                assert req==out['actual_request']
            assert sha(canonical(req).encode())==job['request_sha256']
            assert not natural or out['natural_complete']
            try:answer=json.loads(message.get('content',''))
            except (ValueError,TypeError):answer=None
            assert answer==out['selection']
            dimensions=independent(job['case_id'],answer)
            assert dimensions==out['grade']['dimensions'],job['name']
            proof=load(path/'context-proof.json')
            assert proof['trace_sha256']==sha((path/'runtime-trace.log').read_bytes())
            assert proof['returned_prompt_tokens']==out['prompt_eval_count']
            assert proof['verified_full_context']==out['full_input_verified']
            assert natural==out['natural_complete']
            accepted=all(dimensions.values()) and natural and proof['verified_full_context'] and cpu
            assert accepted==out['delivered']
            workload={'messages':req['messages'],'schema':schema}
            cid=job['case_id']
            if cid in workloads:assert workloads[cid]==workload,(lane,job['name'])
            else:workloads[cid]=workload
            value=json.loads(req['messages'][1]['content'])
            assert 'matched_receipts' not in value and 'unmatched_receipts' not in value and 'oracle' not in value
            case,raw,locators,groups=prior.read_case(cid,'evaluation')
            assert value['original_records']==[prior.original(raw,locators,ref) for ref in locators]
            rows.append({'lane':lane,'request_id':job['name'],'model':job['model_key'],'case':cid,'family':case['family'],
                         'accepted':accepted,'dimensions':dimensions,'natural_complete':natural,
                         'full_input_verified':proof['verified_full_context'],'cpu_verified':cpu,
                         'elapsed_s':out['elapsed_s'],'output_tokens':out['eval_count'],
                         'failed_dimensions':[k for k,v in dimensions.items() if not v],
                         'request_sha256':job['request_sha256'],
                         'response_sha256':sha((path/'response.json').read_bytes()),
                         'outcome_sha256':sha((path/'outcome.json').read_bytes()),
                         'trace_sha256':sha((path/'runtime-trace.log').read_bytes())})
        complete=load(root/'complete.json');assert complete['requests']==len(protocol.get('requests',protocol.get('jobs')))
        recovered=load(root/'recovery-after.json');assert recovered['status']=='ready'
    assert len(rows)==60 and len(workloads)==12
    models=sorted(set(r['model'] for r in rows));scores=[]
    for model in models:
        selected=[r for r in rows if r['model']==model]
        scores.append({'model':model,'strict_pass':sum(r['accepted'] for r in selected),'cases':12,
                       'alert_bearing_pass':sum(r['accepted'] for r in selected if r['case'] not in ('F08','F09')),
                       'alert_bearing_cases':10,'empty_pass':sum(r['accepted'] for r in selected if r['case'] in ('F08','F09')),
                       'dimensions':{k:sum(r['dimensions'][k] for r in selected) for k in DIMENSIONS},
                       'natural_complete':sum(r['natural_complete'] for r in selected),
                       'full_input_verified':sum(r['full_input_verified'] for r in selected)})
    scores.sort(key=lambda r:(-r['strict_pass'],r['model']))
    leaders=[s['model'] for s in scores if s['strict_pass']==scores[0]['strict_pass']]
    pairs=[]
    for i,a in enumerate(models):
        for b in models[i+1:]:
            ar={r['case']:r['accepted'] for r in rows if r['model']==a};br={r['case']:r['accepted'] for r in rows if r['model']==b}
            pairs.append({'a':a,'b':b,'a_only_pass':sum(ar[c] and not br[c] for c in ar),
                          'b_only_pass':sum(br[c] and not ar[c] for c in ar),
                          'both_pass':sum(ar[c] and br[c] for c in ar),'both_fail':sum(not ar[c] and not br[c] for c in ar)})
    result={'protocol':'unclassified_receipt_investigation_v1','requests':60,'case_clusters':12,
            'repeats_per_model_case':1,'observed_leaders':leaders,'scores':scores,'paired_counts':pairs,'rows':rows,
            'boundary':'Author-known constructed family-transfer cases, native templates and installed quantizations, different Ling runtime. Descriptive test-set leader only; no speed, general quality or human-benefit winner.',
            'pre_execution_sources_verified':len(seal['files']), 'previous_sealed_files_verified':508}
    target=HERE/'VERIFIED_RESULTS.json'
    with target.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(canonical({k:result[k] for k in ('requests','case_clusters','observed_leaders','scores')}))

if __name__=='__main__':main()
