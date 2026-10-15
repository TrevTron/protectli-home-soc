"""Predeclare and freeze a one-field fixture correction and six matched addendum requests."""
import datetime as dt
import json
from bench import HERE,BASE,KEYS,canonical,sha,write,read_case
from candidate import freeze_records
from prepare_transfer import oracle

def main():
    selected=json.loads((HERE/'SELECTED_LING_PROFILE_EXTENDED.json').read_text())['selected_profile']
    assert selected=='clean-think-long'
    case,raw,locators,groups=read_case('N05')
    records=[json.loads(line) for line in raw.splitlines()]
    changes=[]
    for e in records:
        if dt.datetime.fromisoformat(e['received_utc'])<dt.datetime.fromisoformat(e['event_utc']):
            before=e['received_utc'];e['received_utc']=(dt.datetime.fromisoformat(e['event_utc'])+dt.timedelta(seconds=2)).isoformat()
            changes.append({'attempt_id':e['attempt_id'],'field':'received_utc','before':before,'after':e['received_utc']})
    assert len(changes)==1
    corrected_oracle=oracle(records,case['receipts'],case['coverage'])
    assert corrected_oracle==case['oracle']
    root=HERE/'correction-case';root.mkdir(exist_ok=False)
    raw2,locators2=freeze_records(records)
    write(root/'case-private.json',case)
    with (root/'evidence.jsonl').open('xb') as f:f.write(raw2)
    write(root/'locators.json',locators2)
    write(root/'CASE_SEAL.json',{'files':{p.name:sha(p.read_bytes()) for p in root.iterdir() if p.is_file()},
        'source_case':'N05','variant':'corrected_collection_timestamp','changes':changes,
        'oracle_unchanged':True,'original_raw_sha256':sha(raw),'corrected_raw_sha256':sha(raw2)})
    import bench_corrected
    from bench_corrected import compose,ling_payload
    cpu=(HERE/'run_development.py').read_text().replace('from bench import','from bench_corrected import')
    (HERE/'run_development_corrected.py').write_text(cpu,encoding='utf-8')
    native=(HERE/'run_ling_long.py').read_text().replace('from bench_long import','from bench_corrected import')
    native=native.replace("('calibration-long-01','transfer-ling-long-01')","('correction-ling-long-01',)")
    (HERE/'run_ling_corrected.py').write_text(native,encoding='utf-8')
    wrapper=(HERE/'launch-ollama.ps1').read_text().replace('transfer-ollama-01','correction-ollama-01').replace('run_development.py','run_development_corrected.py')
    (HERE/'launch-correction-ollama.ps1').write_text(wrapper,encoding='utf-8')
    wrapper=(HERE/'launch-ling-long.ps1').read_text().replace("'calibration-long-01','transfer-ling-long-01'","'correction-ling-long-01'")
    wrapper=wrapper.replace("$RunName='calibration-long-01'","$RunName='correction-ling-long-01'").replace('run_ling_long.py','run_ling_corrected.py')
    (HERE/'launch-correction-ling.ps1').write_text(wrapper,encoding='utf-8')
    schedule=[]
    for lane in ('correction-ollama-01','correction-ling-long-01'):
        output=HERE/lane;output.mkdir(exist_ok=False);jobs=[];native_lane='ling' in lane
        if not native_lane:(output/'requests').mkdir()
        pairs=[('ling3-tiny','clean-off'),('ling3-tiny',selected)] if native_lane else [(k,'clean-off') for k in KEYS]
        for key,profile in pairs:
            name=f'{len(jobs)+1:03}-{key}-N05-{profile}'
            if native_lane:
                request=ling_payload('N05',profile);write(output/(name+'-request.json'),request)
                job={'name':name,'model_key':key,'case_id':'N05','skills':True,'profile':profile,
                    'request_sha256':sha(canonical(request).encode())}
            else:
                p=compose(key,'N05');path=output/'requests'/(name+'.json');write(path,p)
                job={'name':name,'model_key':key,'case_id':'N05','skills':True,'profile':profile,
                    'proposal_sha256':sha(path.read_bytes()),'request_sha256':p['request_sha256']}
            jobs.append(job);schedule.append({'lane':lane,**job})
        write(output/'protocol.json',{'jobs' if native_lane else 'requests':jobs,
            'endpoint':'http://127.0.0.1:11437' if native_lane else 'http://127.0.0.1:11435',
            'phase':'one_field_corrected_fixture_addendum','total_requests':len(jobs),
            'context':8192,'threads':16,'deadline_seconds':300,'request_deadline_seconds':300,
            'load_deadline_seconds':120,'thinking_budget':3072 if native_lane else None,
            'minimum_available_memory_bytes':16*1024**3,'sequential':True,'retries':0})
    write(HERE/'CORRECTION_PROTOCOL.json',{'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'schedule':schedule,
        'requests':6,'changes':changes,'oracle_unchanged':True,
        'trigger':'Source review found collection time earlier than event time in the authored retry fixture. Existing frozen batch continues unchanged. This separate input correction was declared before the other artifact answers were available.',
        'scoring':'Report original twelve-case totals unchanged and corrected-case outcomes separately. Also show a sensitivity total replacing only that one case, explicitly labelled; no calibration or recipe changes.',
        'no_retries_or_answer_repairs':True})
    project=BASE.parents[1]
    paths=list(HERE.glob('*.py'))+list(HERE.glob('*.ps1'))+list(root.rglob('*'))+[HERE/'CORRECTION_PROTOCOL.json',HERE/'SELECTED_LING_PROFILE_EXTENDED.json']
    for lane in ('correction-ollama-01','correction-ling-long-01'):paths+=list((HERE/lane).rglob('*.json'))
    write(HERE/'CORRECTION_PRE_EXECUTION_SEAL.json',{'files':{str(p.relative_to(project)).replace('\\','/'):sha(p.read_bytes()) for p in paths if p.is_file()}})
    print(canonical({'requests':6,'changed_fields':changes,'oracle_unchanged':True,'original_inputs_unchanged':True}))

if __name__=='__main__':main()
