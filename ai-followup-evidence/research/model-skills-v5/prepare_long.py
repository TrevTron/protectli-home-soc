"""Freeze a second development-only calibration because the first budget forcibly closed reasoning."""
from bench_long import HERE,PROFILES,canonical,sha,write,ling_payload
from prepare_calibration import seal

def main():
    output=HERE/'calibration-long-01';output.mkdir(exist_ok=False)
    source=(HERE/'run_ling.py').read_text()
    source=source.replace('from bench import','from bench_long import').replace("'--reasoning-budget', '1024'","'--reasoning-budget', '3072'")
    source=source.replace("('calibration-ling-01','transfer-ling-01')","('calibration-long-01','transfer-ling-long-01')")
    (HERE/'run_ling_long.py').write_text(source,encoding='utf-8')
    wrapper=(HERE/'launch-ling.ps1').read_text().replace('calibration-ling-01','calibration-long-01').replace('transfer-ling-01','transfer-ling-long-01').replace('run_ling.py','run_ling_long.py')
    (HERE/'launch-ling-long.ps1').write_text(wrapper,encoding='utf-8')
    jobs=[]
    for profile in ('clean-think-long','clean-native-long'):
        for cid in ('D03','D04','D08','D12'):
            name=f'{len(jobs)+1:03}-ling3-tiny-{cid}-{profile}';request=ling_payload(cid,profile)
            write(output/(name+'-request.json'),request)
            jobs.append({'name':name,'model_key':'ling3-tiny','case_id':cid,'skills':True,'profile':profile,
                'request_sha256':sha(canonical(request).encode())})
    write(output/'protocol.json',{'jobs':jobs,'phase':'additive_development_reasoning_budget_contrast',
        'requests':8,'cases':['D03','D04','D08','D12'],'thinking_budget':3072,'overall_output_ceiling':4096,
        'context':8192,'threads':16,'request_deadline_seconds':300,'load_deadline_seconds':120,
        'minimum_available_memory_bytes':16*1024**3,'sequential':True,'retries':0,
        'trigger':'Initial calibration reasoning was forcibly closed by its 1024-token budget. Preserve that run and test 3072 without changing task, skill, schema, evidence, seed or overall completion ceiling.',
        'selection':'Across original clean-off, clean-think, clean-native, clean-think-long and clean-native-long choose greatest strict development pass count; ties in that order. Preserve initial selection file and write a separate extended selection. Freeze before creating transfer cases.'})
    seal(output,'PRE_EXECUTION_SEAL.json')
    print(canonical({'prepared':8,'thinking_budget':3072,'evaluation_requests':0}))

if __name__=='__main__':main()
