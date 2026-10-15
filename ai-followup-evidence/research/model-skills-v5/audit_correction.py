"""Regrade original response bytes, verify input receipts and preserve thinking-budget observations."""
import json
import sys
from collections import defaultdict
from bench import HERE,BASE,PROFILES,DIMENSIONS,canonical,sha,write,grade,input_value,prompt,schema
sys.path.insert(0,'C:/REDACTED_PROJECT/tools')
import soc_context_guard as guard

def verify_files(seal_path):
    project=BASE.parents[1];seal=json.loads(seal_path.read_text())
    for relative,expected in seal['files'].items():assert sha((project/relative).read_bytes())==expected,relative
    return len(seal['files'])

def audit_native(lane):
    output=HERE/lane;protocol=json.loads((output/'protocol.json').read_text())
    assert json.loads((output/'complete.json').read_text())['requests']==len(protocol['jobs'])
    assert json.loads((output/'owned-child-cleanup.json').read_text())['only_owned_child_stopped'] is True
    rows=[]
    for job in protocol['jobs']:
        folder=output/job['name'];request=json.loads((output/(job['name']+'-request.json')).read_text())
        response=json.loads((folder/'response.json').read_text());outcome=json.loads((folder/'outcome.json').read_text())
        assert sha(canonical(request).encode())==job['request_sha256']
        assert request['messages']==[{'role':'system','content':prompt(job['profile'])},
            {'role':'user','content':canonical(input_value(job['case_id'])[0])}]
        assert request['response_format']['json_schema']['schema']==schema()
        message=response['choices'][0]['message'];answer=json.loads(message['content'])
        assert answer==outcome['selection'];judgment=grade(job['case_id'],answer)
        assert judgment==outcome['grade']
        assert response['choices'][0]['finish_reason']=='stop' and outcome['natural_complete']
        proof=json.loads((folder/'context-proof.json').read_text())
        assert proof['verified_full_context'] and outcome['full_input_verified']
        trace=(folder/'runtime-trace.log').read_bytes()
        assert guard.assess(trace,context=8192,prompt_tokens=response['usage']['prompt_tokens'])==proof
        # Verify actual native generation prefix and rendered thinking option, not just request flags.
        thinking=PROFILES[job['profile']]['thinking']
        import re
        rendered=re.search(r"reasoning budget: tokens=(\d+), generation_prompt='([^']*)'",trace.decode())
        assert rendered is not None
        assert rendered.group(2).endswith('<think>' if thinking else '<think></think>')
        assert int(rendered.group(1))== (3072 if 'long' in lane else 1024)
        chars=len(message.get('reasoning_content','') or '')
        assert (chars>0)==thinking
        assert sha((message.get('reasoning_content','') or '').encode())==outcome['reasoning_sha256']
        assert sha(message['content'].encode())==outcome['final_sha256']
        assert sha(canonical(message).encode())==outcome['combined_channels_sha256']
        forced=b'common_reaso: budget exhausted, forcing end sequence' in trace
        row={**job,'accepted':judgment['accepted'],'dimensions':judgment['dimensions'],
            'reasoning_characters':chars,'reasoning_budget_forced_closure_observed':forced,
            'complete_final_json':True,'full_input_verified':True,'answer':answer,
            'trace_sha256':sha(trace),'response_sha256':sha((folder/'response.json').read_bytes())}
        rows.append(row)
    return rows

def audit_cpu():
    output=HERE/'correction-ollama-01';protocol=json.loads((output/'protocol.json').read_text())
    assert json.loads((output/'complete.json').read_text())['requests']==len(protocol['requests'])
    rows=[]
    for job in protocol['requests']:
        p=json.loads((output/'requests'/(job['name']+'.json')).read_text());folder=output/job['name']
        assert sha((output/'requests'/(job['name']+'.json')).read_bytes())==job['proposal_sha256']
        assert sha(canonical(p['request']).encode())==job['request_sha256']
        assert p['request']['messages']==[{'role':'system','content':prompt('clean-off')},
            {'role':'user','content':canonical(input_value(job['case_id'])[0])}]
        assert p['request']['format']==schema()
        response=json.loads((folder/'response.json').read_text());outcome=json.loads((folder/'outcome.json').read_text())
        answer=json.loads(response['message']['content']);judgment=grade(job['case_id'],answer)
        assert judgment==outcome['grade'] and answer==outcome['selection']
        assert response['done'] and response['done_reason']=='stop' and not response['message'].get('thinking')
        assert outcome['full_input_verified'] and outcome['cpu_residency_observed'] and outcome['natural_complete']
        proof=json.loads((folder/'context-proof.json').read_text())
        assert guard.assess((folder/'runtime-trace.log').read_bytes(),context=8192,prompt_tokens=response['prompt_eval_count'])==proof
        rows.append({**job,'accepted':judgment['accepted'],'dimensions':judgment['dimensions'],
            'reasoning_characters':0,'complete_final_json':True,'full_input_verified':True,'answer':answer,
            'response_sha256':sha((folder/'response.json').read_bytes())})
    return rows

def totals(rows):
    result={}
    for row in rows:
        key=row['model_key']+'/'+row['profile']
        r=result.setdefault(key,{'cases':0,'full_passes':0,'dimensions':dict.fromkeys(DIMENSIONS,0),
            'complete_final_json':0,'full_input_verified':0,'reasoning_budget_closures':0})
        r['cases']+=1;r['full_passes']+=row['accepted'];r['complete_final_json']+=row['complete_final_json']
        r['full_input_verified']+=row['full_input_verified'];r['reasoning_budget_closures']+=row.get('reasoning_budget_forced_closure_observed',False)
        for d in DIMENSIONS:r['dimensions'][d]+=row['dimensions'][d]
    return result

def select():
    count=verify_files(HERE/'calibration-ling-01/PRE_EXECUTION_SEAL.json')
    rows=audit_native('calibration-ling-01');summary=totals(rows)
    order=['clean-off','clean-think','clean-native']
    selected=max(order,key=lambda p:(summary['ling3-tiny/'+p]['full_passes'],-order.index(p)))
    write(HERE/'CALIBRATION_VERIFIED_RESULTS.json',{'rows':rows,'totals':summary,'sealed_files_verified':count,
        'budget_observation_correction':'Outcome legacy detector searched a different phrase. This additive audit uses the actual pinned runtime budget-exhaustion line and retains the original outcomes unchanged.'})
    write(HERE/'SELECTED_LING_PROFILE.json',{'selected_profile':selected,'profile':PROFILES[selected],
        'selection_rule':'Greatest strict development count, ties clean-off then clean-think then clean-native; legacy control excluded.',
        'calibration_result_sha256':sha((HERE/'CALIBRATION_VERIFIED_RESULTS.json').read_bytes()),'scores':summary,
        'transfer_cases_created':False,'evaluation_answers_seen':False})
    print(canonical({'selected':selected,'totals':summary}))

def select_extended():
    import bench_long
    count=verify_files(HERE/'calibration-long-01/PRE_EXECUTION_SEAL.json')
    original=json.loads((HERE/'CALIBRATION_VERIFIED_RESULTS.json').read_text())
    rows=audit_native('calibration-long-01');summary=totals(original['rows']+rows)
    order=['clean-off','clean-think','clean-native','clean-think-long','clean-native-long']
    selected=max(order,key=lambda p:(summary['ling3-tiny/'+p]['full_passes'],-order.index(p)))
    write(HERE/'CALIBRATION_EXTENDED_VERIFIED_RESULTS.json',{'rows':rows,'combined_totals':summary,'sealed_files_verified':count})
    write(HERE/'SELECTED_LING_PROFILE_EXTENDED.json',{'selected_profile':selected,'profile':PROFILES[selected],
        'selection_rule':json.loads((HERE/'calibration-long-01/protocol.json').read_text())['selection'],
        'original_selection_sha256':sha((HERE/'SELECTED_LING_PROFILE.json').read_bytes()),
        'extended_calibration_sha256':sha((HERE/'CALIBRATION_EXTENDED_VERIFIED_RESULTS.json').read_bytes()),
        'scores':summary,'transfer_cases_created':False,'evaluation_answers_seen':False})
    print(canonical({'selected':selected,'totals':summary}))

def final():
    import bench_long
    count=verify_files(HERE/'TRANSFER_PRE_EXECUTION_SEAL.json')
    lane=json.loads((HERE/'TRANSFER_PROTOCOL.json').read_text())['native_lane']
    rows=audit_cpu()+audit_native(lane)
    summary=totals(rows)
    # All common-profile answers must have the five artifacts on every case.
    for n in range(1,13):assert len([r for r in rows if r['case_id']==f'N{n:02}' and r['profile']=='clean-off'])==5
    write(HERE/'TRANSFER_VERIFIED_RESULTS.json',{'rows':rows,'totals':summary,'sealed_files_verified':count,
        'matched_common_skill_input_and_schema':True,'original_case_scores_unchanged':True,
        'limits':'Author-known synthetic family transfer, one draw per case/profile. Negative boundary claims only; selected recipe is bounded thinking.'})
    print(canonical({'totals':summary,'requests':len(rows)}))

if __name__=='__main__':
    import bench_corrected
    count=verify_files(HERE/'CORRECTION_PRE_EXECUTION_SEAL.json')
    rows=audit_cpu()+audit_native('correction-ling-long-01')
    original=json.loads((HERE/'TRANSFER_VERIFIED_RESULTS.json').read_text())
    sensitivity={k:v['full_passes'] for k,v in original['totals'].items()}
    pairs=[]
    for r in rows:
        old=next(x for x in original['rows'] if x['case_id']=='N05' and x['model_key']==r['model_key'] and x['profile']==r['profile'])
        key=r['model_key']+'/'+r['profile'];sensitivity[key]+=int(r['accepted'])-int(old['accepted'])
        pairs.append({'model_key':r['model_key'],'profile':r['profile'],'original_case_pass':old['accepted'],'corrected_case_pass':r['accepted'],'same_outcome':old['answer']['client_outcome']==r['answer']['client_outcome']})
    write(HERE/'CORRECTION_VERIFIED_RESULTS.json',{'rows':rows,'pairs':pairs,'sensitivity_full_passes':sensitivity,'requests':6,'sealed_files_verified':count,'original_twelve_case_scores_preserved':True,'timestamp_field_changed':True,'oracle_unchanged':True})
    print(canonical({'pairs':pairs,'sensitivity_full_passes':sensitivity,'requests':6}))
