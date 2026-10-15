"""Single consistent six-field contract, independently pinned cases and profiles."""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
V2=BASE/'model-skills-v2'
V4=BASE/'model-skills-v4'
sys.path.insert(0,str(V2))
import workbench as prior
KEYS,canonical,sha=prior.KEYS,prior.canonical,prior.sha
sys.path.insert(0,str(BASE))
from candidate import score_selection

DIMENSIONS=('contexts','next_checks','client_outcome','client_refs','intrusion_established','delivery_complete')
OUTCOMES=['unknown','supplied_attempt_success','supplied_attempt_failure','retry_success_first_attempt_unknown']
PROFILES={
 'legacy-off':{'prompt':'legacy','thinking':False,'temperature':0,'top_p':1},
 'clean-off':{'prompt':'clean','thinking':False,'temperature':0,'top_p':1},
 'clean-think':{'prompt':'clean','thinking':True,'temperature':0,'top_p':1},
 'clean-native':{'prompt':'clean','thinking':True,'temperature':1.0,'top_p':0.95}}

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:f.write(canonical(value)+'\n')

def read_case(cid):
    if cid.startswith('D'):
        return prior.read_case(cid,'development')
    if cid not in {f'N{i:02}' for i in range(1,13)}:raise ValueError('Unknown new sealed case')
    root=HERE/'transfer-cases';folder=root/cid
    seal=json.loads((root/'PRE_EVALUATION_SEAL.json').read_text())
    for name in ('case-private.json','evidence.jsonl','locators.json'):
        assert sha((folder/name).read_bytes())==seal['files'][f'{cid}/{name}']
    case=json.loads((folder/'case-private.json').read_text())
    raw=(folder/'evidence.jsonl').read_bytes();locators=json.loads((folder/'locators.json').read_text())
    return case,raw,locators,prior.groups(raw,locators)

def schema():
    return {'type':'object','additionalProperties':False,'required':list(DIMENSIONS),'properties':{
        'contexts':{'type':'array','uniqueItems':True,'maxItems':len(prior.CONTEXT),'items':{'enum':sorted(prior.CONTEXT)}},
        'next_checks':{'type':'array','uniqueItems':True,'minItems':1,'maxItems':3,'items':{'enum':sorted(prior.CHECKS)}},
        'client_outcome':{'enum':OUTCOMES},'client_refs':{'type':'array','uniqueItems':True,'items':{'type':'string'}},
        'intrusion_established':{'type':'boolean'},'delivery_complete':{'type':'boolean'}}}

def input_value(cid):
    case,raw,locators,rows=read_case(cid)
    value,roster,facts=prior.normalize(case,raw,locators,rows)
    del value['matched_receipts'],value['unmatched_receipts']
    value['original_records']=[prior.original(raw,locators,ref) for ref in locators]
    value['receipts']=case['receipts'];value['permitted_client_outcomes']=OUTCOMES
    return value,roster,facts

def prompt(profile):
    if PROFILES[profile]['prompt']=='legacy':
        text=prior.CONTRACT
        for name in prior.SKILL_NAMES:text+='\n\n'+(BASE/'model-skills-v1/skills'/(name+'.md')).read_text()
        text+='\n\n'+(V2/'skills-refinement-v1.md').read_text()
        # Exact inherited v4 extension, retained as a diagnostic control.
        import ast
        tree=ast.parse((V4/'comparison.py').read_text())
        extra=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXTRA' for t in n.targets))
        return text+'\n\n'+extra
    return 'Analyze the supplied synthetic SOC evidence using this procedure. Return exactly the six-field JSON object defined below.\n\n'+(HERE/'soc-decision-skill-v2.md').read_text()

def compose(model_key,cid,skills=True,profile='clean-off',seed=17):
    value,roster,facts=input_value(cid)
    artifact=next(a for a in json.loads((BASE/'installed-artifacts-audit.json').read_text()) if a['name']==KEYS[model_key])
    config=PROFILES[profile]
    request={'model':KEYS[model_key],'messages':[{'role':'system','content':prompt(profile)},
            {'role':'user','content':canonical(value)}],'format':schema(),
            'options':{'temperature':config['temperature'],'seed':seed,'num_ctx':8192,'num_predict':4096,
            'num_thread':16,'num_gpu':0,'top_k':20,'top_p':config['top_p'],'min_p':0,'repeat_penalty':1,
            'presence_penalty':0,'frequency_penalty':0},'think':config['thinking'],'stream':False,'keep_alive':0}
    return {'model_key':model_key,'case_id':cid,'skills':True,'profile':profile,
            'manifest_digest':artifact['manifest_digest'],'request':request,
            'request_sha256':sha(canonical(request).encode()),'input_sha256':sha(canonical(value).encode()),
            'skill_hashes':{'soc-decision-skill-v2':sha((HERE/'soc-decision-skill-v2.md').read_bytes())},
            'citation_roster':roster,'facts':facts}

def ling_payload(cid,profile,seed=17):
    p=compose('gemma4-12b',cid,profile=profile,seed=seed);config=PROFILES[profile]
    return {'model':'ling3-tiny','messages':p['request']['messages'],
            'response_format':{'type':'json_schema','json_schema':{'name':'soc_decision','strict':True,'schema':schema()}},
            'max_tokens':4096,'temperature':config['temperature'],'seed':seed,'top_k':20,'top_p':config['top_p'],
            'min_p':0,'repeat_penalty':1,'presence_penalty':0,'frequency_penalty':0,
            'cache_prompt':False,'stream':False,'chat_template_kwargs':{'enable_thinking':config['thinking']},
            'reasoning_format':'deepseek'}

def grade(cid,answer):
    case,raw,locators,rows=read_case(cid)
    if not isinstance(answer,dict) or set(answer)!=set(DIMENSIONS):
        return {'accepted':False,'errors':['schema'],'dimensions':dict.fromkeys(DIMENSIONS,False)}
    adjusted=copy.deepcopy(case)
    matched=[r for r in case['receipts'] if any(prior.link_receipt(prior.original(raw,locators,ref),r) is not None for ref in locators)]
    if any(r['fields'].get('sid')==2016149 for r in rows) and not any(r.get('kind')=='process_socket' for r in matched):
        adjusted['oracle']['eligible_contexts']=list(set(adjusted['oracle']['eligible_contexts'])|{'stun_process_unknown'})
    selected=score_selection(adjusted,{'case':cid,**{k:answer[k] for k in ('contexts','next_checks')}})
    refs=answer['client_refs']
    dimensions={'contexts':not any(e.startswith('contexts') for e in selected['errors']),
      'next_checks':not any(e.startswith('next_checks') or e.startswith('next_check_') for e in selected['errors']),
      'client_outcome':answer['client_outcome']==case['oracle']['client_outcome'],
      'client_refs':isinstance(refs,list) and all(isinstance(r,str) for r in refs) and len(refs)==len(set(refs)) and set(refs)==set(case['oracle']['client_refs']),
      'intrusion_established':answer['intrusion_established'] is False,'delivery_complete':answer['delivery_complete'] is False}
    return {'accepted':all(dimensions.values()),'errors':[k for k,v in dimensions.items() if not v],
            'dimensions':dimensions,'context_selection_grade':selected}
