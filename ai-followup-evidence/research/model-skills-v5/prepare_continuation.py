"""Only never-sent requests after the retained native memory-guard stop."""
import json
import datetime as dt
from bench_long import HERE,canonical,sha,write

def main():
    parent=HERE/'transfer-ling-long-01';protocol=json.loads((parent/'protocol.json').read_text())
    completed=[job for job in protocol['jobs'] if (parent/job['name']/'outcome.json').exists()]
    assert completed==protocol['jobs'][:19] and not (parent/'complete.json').exists()
    assert json.loads((parent/'execution-exit.json').read_text(encoding='utf-8-sig'))['exit_code']==1
    assert json.loads((parent/'owned-child-cleanup.json').read_text())['only_owned_child_stopped']
    jobs=protocol['jobs'][19:];assert len(jobs)==5
    output=HERE/'transfer-ling-long-02';output.mkdir(exist_ok=False)
    for job in jobs:
        assert not (parent/job['name']).exists(),job['name']
        source=parent/(job['name']+'-request.json')
        assert sha(canonical(json.loads(source.read_text())).encode())==job['request_sha256']
        with (output/source.name).open('xb') as f:f.write(source.read_bytes())
    source=(HERE/'run_ling_long.py').read_text()
    source=source.replace("('calibration-long-01','transfer-ling-long-01')","('transfer-ling-long-02',)")
    source=source.replace("'--batch-size', '512',", "'--cache-ram', '0', '--batch-size', '512',")
    source=source.replace("                response = api('/v1/chat/completions', request, 300)","""                import concurrent.futures
                available_before=memory();observed=[]
                write(target/'memory-preflight.json',{'available_memory_bytes':available_before,'minimum_bytes':16*1024**3})
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future=pool.submit(api,'/v1/chat/completions',request,300)
                    while not future.done():
                        spare=memory();observed.append({'monotonic_elapsed_s':time.monotonic()-start,'available_memory_bytes':spare})
                        if spare<16*1024**3:
                            child.terminate()
                            write(target/'memory-observations.json',observed)
                            raise RuntimeError('During-request memory guard stopped only owned Ling child; retain sent request, no retry')
                        time.sleep(1)
                    response=future.result()
                write(target/'memory-observations.json',observed)""")
    (HERE/'run_ling_continuation.py').write_text(source,encoding='utf-8')
    wrapper=(HERE/'launch-ling-long.ps1').read_text().replace("'calibration-long-01','transfer-ling-long-01'","'transfer-ling-long-02'")
    wrapper=wrapper.replace("$RunName='calibration-long-01'","$RunName='transfer-ling-long-02'").replace('run_ling_long.py','run_ling_continuation.py')
    (HERE/'launch-ling-continuation.ps1').write_text(wrapper,encoding='utf-8')
    protocol2={**protocol,'jobs':jobs,'total_requests':5,'continuation':{
        'parent':'transfer-ling-long-01','completed_original_requests':19,'only_never_requested_jobs':True,
        'original_completed_outcome_hashes':{job['name']:sha((parent/job['name']/'outcome.json').read_bytes()) for job in completed},
        'change':'Disable native server RAM prompt cache, retain request cache_prompt=false, add per-second spare-memory observations and during-request owned-child stop at the same 16 GiB floor.',
        'boundary':'Inputs, source cases, skill, schema, weights, threads, context, output/reasoning ceilings, sampling, seed and deadlines unchanged. Resource/runtime conditions differ; no pooled speed or pure resource-uncontrolled causal claim.'}}
    write(output/'protocol.json',protocol2)
    project=HERE.parents[2]
    files={str(p.relative_to(project)).replace('\\','/'):sha(p.read_bytes()) for p in list(HERE.glob('*.py'))+list(HERE.glob('*.ps1'))+list(output.glob('*.json'))}
    write(output/'PRE_EXECUTION_SEAL.json',{'files':files,'parent_retained':True,'unsent_jobs_only':True})
    print(canonical({'remaining_never_sent_requests':5,'cache_ram_mib':0,'spare_memory_floor_gib':16,'retries':0}))

if __name__=='__main__':main()
