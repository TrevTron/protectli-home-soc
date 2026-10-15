"""Freeze prompt, reasoning and sampling development contrasts before inference."""
import json
from bench import HERE,BASE,V2,V4,PROFILES,ling_payload,prompt,canonical,sha,write

def verify_previous():
    project=BASE.parents[1]
    for root in (V2,V4):
        seal=json.loads((root/'FINAL_SEAL.json').read_text())
        entries=seal['files']
        if isinstance(entries,list):entries={r['path']:r['sha256'] for r in entries}
        for rel,expected in entries.items():assert sha((project/rel).read_bytes())==expected,rel

def make_runners():
    cpu=(V4/'run_development.py').read_text().replace('from comparison import','from bench import')
    (HERE/'run_development.py').write_text(cpu,encoding='utf-8')
    ling=(V4/'run_ling.py').read_text().replace('from comparison import','from bench import')
    ling=ling.replace("'--jinja', '--reasoning', 'off',", "'--jinja', '--reasoning', 'auto', '--reasoning-format', 'deepseek',")
    ling=ling.replace("'--reasoning-budget', '0', '--chat-template-kwargs', '{\"enable_thinking\":false}'", "'--reasoning-budget', '1024', '--chat-template-kwargs', '{\"enable_thinking\":true}'")
    ling=ling.replace("natural = choice.get('finish_reason') == 'stop' and not message.get('reasoning_content') and not message.get('thinking')", "natural = choice.get('finish_reason') == 'stop'")
    needle="'model_file_sha256': EXPECTED, 'runtime': 'llama.cpp b11429 Windows CPU',"
    replacement="'reasoning_sha256': sha((message.get('reasoning_content', '') or '').encode()),\n                          'final_sha256': sha((message.get('content', '') or '').encode()),\n                          'combined_channels_sha256': sha(canonical(message).encode()),\n                          'reasoning_requested': request['chat_template_kwargs']['enable_thinking'],\n                          'reasoning_budget_exhaustion_observed': b'reasoning budget exhausted' in trace.lower(),\n                          "+needle
    assert needle in ling
    ling=ling.replace(needle,replacement)
    ling=ling.replace("execute(HERE / 'harder-ling-01')", "\n    name = sys.argv[1]\n    if name not in ('calibration-ling-01','transfer-ling-01'):\n        raise ValueError('Explicit new lane required')\n    execute(HERE / name)")
    (HERE/'run_ling.py').write_text(ling,encoding='utf-8')
    wrapper=(V4/'launch-ling.ps1').read_text().replace("$RunName='harder-ling-01'", "param([ValidateSet('calibration-ling-01','transfer-ling-01')][string]$RunName='calibration-ling-01')")
    wrapper=wrapper.replace('model-skills-v4','model-skills-v5').replace("(Join-Path $taskWork 'run_ling.py') 2>&1", "(Join-Path $taskWork 'run_ling.py') $RunName 2>&1")
    (HERE/'launch-ling.ps1').write_text(wrapper,encoding='utf-8')
    cpu_wrapper=(V4/'launch-ollama.ps1').read_text().replace("$RunName='harder-ollama-01'", "$RunName='transfer-ollama-01'").replace('model-skills-v4','model-skills-v5')
    (HERE/'launch-ollama.ps1').write_text(cpu_wrapper,encoding='utf-8')

def seal(output,name):
    project=BASE.parents[1]
    files={str(p.relative_to(project)).replace('\\','/'):sha(p.read_bytes())
           for p in list(HERE.glob('*.py'))+list(HERE.glob('*.ps1'))+list(HERE.glob('*.md'))+list(output.rglob('*.json'))}
    write(output/name,{'files':files,'previous_results_preserved':True})

def main():
    verify_previous();make_runners()
    output=HERE/'calibration-ling-01';output.mkdir(exist_ok=False)
    jobs=[]
    for profile in PROFILES:
        for cid in ('D03','D04','D08','D12'):
            name=f'{len(jobs)+1:03}-ling3-tiny-{cid}-{profile}'
            request=ling_payload(cid,profile)
            write(output/(name+'-request.json'),request)
            jobs.append({'name':name,'model_key':'ling3-tiny','case_id':cid,'skills':True,
                         'profile':profile,'request_sha256':sha(canonical(request).encode())})
    write(output/'protocol.json',{'jobs':jobs,'phase':'development_calibration','requests':16,
          'profiles':PROFILES,'cases':['D03','D04','D08','D12'],'context':8192,'output_ceiling':4096,
          'thinking_budget':1024,'threads':16,'request_deadline_seconds':300,'load_deadline_seconds':120,
          'minimum_available_memory_bytes':16*1024**3,'sequential':True,'retries':0,
          'primary_metric':'Strict six-field source-case pass count, unchanged rules and labels',
          'selection':'Among clean-off, clean-think and clean-native, choose greatest strict pass count; ties prefer clean-off then clean-think then clean-native. legacy-off is a diagnostic control, never promoted.',
          'contrasts':'clean-off minus legacy-off: prompt revision; clean-think minus clean-off: reasoning; clean-native minus clean-think: sampling. All have the same 4096 ceiling and 300s deadline.',
          'reasoning_boundary':'1024-token bounded reasoning, separate returned reasoning/final channels and final-only grade; record forced thinking-budget closure separately.',
          'transfer_plan':'After freezing the selected Ling profile, create twelve fresh constructed family variants and execute the four Ollama artifacts plus common clean-off Ling and the selected Ling revision if different. Common task/skill/schema. No general, speed or human-benefit winner.'})
    seal(output,'PRE_EXECUTION_SEAL.json')
    print(canonical({'prepared':len(jobs),'calibration_cases':4,'profiles':4}))

if __name__=='__main__':main()
