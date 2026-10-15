"""Freeze a new round using the previous guarded executors without editing them."""
import json
import sys
from pathlib import Path
from comparison import HERE, BASE, V2, KEYS, compose, canonical, sha

def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        f.write(canonical(value)+'\n')

def main():
    # Verify the full prior closeout before using any dependency.
    project = BASE.parents[1]
    old = json.loads((V2/'FINAL_SEAL.json').read_text())
    for item in old['files']:
        assert sha((project/item['path']).read_bytes()) == item['sha256'], item['path']
    cpu = (V2/'run_development.py').read_text()
    cpu = cpu.replace('from workbench import HERE, BASE, KEYS, compose, grade, canonical, sha',
                      'from comparison import HERE, BASE, KEYS, compose, grade, canonical, sha')
    (HERE/'run_development.py').write_text(cpu, encoding='utf-8')
    ling = (V2/'run_ling.py').read_text()
    ling = ling.replace('from workbench import HERE, BASE, compose, grade, canonical, sha',
                        'from comparison import HERE, BASE, V2, compose, grade, canonical, sha')
    ling = ling.replace("ROOT = HERE / 'ling-isolated'", "ROOT = V2 / 'ling-isolated'")
    ling = ling.replace("    if skills:\n        p['request']['messages'][0]['content'] += '\\n\\n' + (HERE / 'skills-refinement-v1.md').read_text()\n", '')
    # Execution only. New proposals and protocol are prepared below, not by its old development helper.
    start = ling.index('def main():')
    ling = ling[:start] + "if __name__ == '__main__':\n    execute(HERE / 'harder-ling-01')\n"
    (HERE/'run_ling.py').write_text(ling, encoding='utf-8')
    wrapper = (V2/'launch-development.ps1').read_text()
    wrapper = wrapper.replace("param([ValidateSet('development-01','development-02','development-03')][string]$RunName='development-01')",
                              "$RunName='harder-ollama-01'")
    wrapper = wrapper.replace("private\\ai-followup-20261007\\model-skills-v2", "private\\ai-followup-20261007\\model-skills-v4")
    (HERE/'launch-ollama.ps1').write_text(wrapper, encoding='utf-8')
    other = wrapper.replace("$RunName='harder-ollama-01'", "$RunName='harder-ling-01'")
    other = other.replace("(Join-Path $taskWork 'run_development.py') execute --output $taskOutput", "(Join-Path $taskWork 'run_ling.py')")
    (HERE/'launch-ling.ps1').write_text(other, encoding='utf-8')
    schedule = []
    for lane, keys in [('harder-ollama-01', list(KEYS)), ('harder-ling-01', ['ling3-tiny'])]:
        output = HERE/lane
        output.mkdir(exist_ok=False)
        jobs = []
        if lane == 'harder-ollama-01':
            (output/'requests').mkdir()
        for key in keys:
            for n in range(1,13):
                cid = f'F{n:02}'
                p = compose('gemma4-12b' if key=='ling3-tiny' else key, cid, True)
                name = f'{len(jobs)+1:03}-{key}-{cid}-skills'
                if key=='ling3-tiny':
                    request = {'model':key,'messages':p['request']['messages'],
                        'response_format':{'type':'json_schema','json_schema':{'name':'soc_investigation','strict':True,'schema':p['request']['format']}},
                        'max_tokens':2048,'temperature':0,'seed':17,'top_k':20,'top_p':1,'min_p':0,
                        'repeat_penalty':1,'presence_penalty':0,'frequency_penalty':0,
                        'cache_prompt':False,'stream':False,'chat_template_kwargs':{'enable_thinking':False}}
                    write(output/(name+'-request.json'),request)
                    job={'name':name,'model_key':key,'case_id':cid,'skills':True,'request_sha256':sha(canonical(request).encode())}
                else:
                    path=output/'requests'/(name+'.json')
                    write(path,p)
                    job={'name':name,'model_key':key,'case_id':cid,'skills':True,
                         'proposal_sha256':sha(path.read_bytes()),'request_sha256':p['request_sha256']}
                jobs.append(job)
                schedule.append({'lane':lane,**job})
        protocol={'jobs' if key=='ling3-tiny' else 'requests':jobs,
                  'endpoint':'http://127.0.0.1:11437' if key=='ling3-tiny' else 'http://127.0.0.1:11435',
                  'phase':'constructed_family_transfer_evaluation', 'total_requests':len(jobs),
                  'contract':'unclassified_receipt_investigation_v1',
                  'primary_metric':'Full six-dimension strict acceptance; all twelve cases included',
                  'secondary_metrics':'Separate six decision dimensions; alert-bearing and empty cases separate',
                  'ties':'Report ties. A highest observed score is a test-set leader, not a general or statistically established winner.',
                  'context':8192,'threads':16,'deadline_seconds':300,'thinking':False,
                  'minimum_available_memory_bytes':16*1024**3,'sequential':True,'retries':0,
                  'prior_case_exposure':'Author inspected; paired families were used for development; evaluation variants not previously sent to these models.',
                  'timing_boundary':'Ling uses a separate resident llama.cpp runtime; no pooled speed ranking',
                  'temperature_boundary':'Native monitoring and hardware/kernel protections unchanged; no new host thermal certification'}
        write(output/'protocol.json',protocol)
    write(HERE/'ROUND_PROTOCOL.json',{'schedule':schedule,'requests':60,'cases':12,'models':5,
        'failure_policy':'Retain every original. No retries, repairs or post-answer rubric changes.',
        'primary_metric':'Strict six-dimension pass count on all cases. Six dimension totals are secondary.',
        'leader_boundary':'Constructed transfer test leader only; twelve paired case clusters, one draw each; no human-benefit or population ranking claim.'})
    files={}
    for root in (HERE,V2):
        paths=list(root.glob('*.py'))+list(root.glob('*.ps1'))
        if root==HERE:
            paths+=list(root.rglob('*-request.json'))+list(root.rglob('requests/*.json'))+list(root.rglob('protocol.json'))+[HERE/'ROUND_PROTOCOL.json']
        else:
            paths += [V2/'skills-refinement-v1.md']
        for path in paths:
            files[str(path.relative_to(project)).replace('\\','/')]=sha(path.read_bytes())
    write(HERE/'PRE_EXECUTION_SEAL.json',{'files':files,'previous_seal_verified':len(old['files'])})
    print(canonical({'prepared':60,'prior_sealed_files_verified':len(old['files'])}))

if __name__=='__main__':
    main()

