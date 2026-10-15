"""Additive final seal for the completed harder comparison."""
import json
from pathlib import Path
from comparison import HERE, BASE, canonical, sha

def main():
    project=BASE.parents[1]
    result=json.loads((HERE/'VERIFIED_RESULTS.json').read_text())
    assert result['requests']==60 and len(result['rows'])==60
    assert all(r['natural_complete'] and r['full_input_verified'] and r['cpu_verified'] for r in result['rows'])
    recovery=json.loads((HERE/'recovery-final.json').read_text(encoding='utf-8-sig'))
    assert recovery['socket_owner_verified'] and not recovery['maintenance_pause_present'] and not recovery['ling_listener_present']
    assert recovery['worker']['result']['worker_exit']==0
    case_seal=json.loads((BASE/'cases-v3/PRE_EVALUATION_SEAL.json').read_text())
    for rel,expected in case_seal['files'].items():
        assert sha((BASE/'cases-v3'/rel).read_bytes())==expected,rel
    paths=[p for p in HERE.rglob('*') if p.is_file() and p.name!='api-key.txt' and '__pycache__' not in p.parts]
    paths += [project/'docs/ai-followup-20261007'/name for name in
              ('HARDER_COMPARISON_PROTOCOL_V1.md','HARDER_COMPARISON_RESULTS_V1.md')]
    files={str(p.relative_to(project)).replace('\\','/'):sha(p.read_bytes()) for p in paths}
    target=HERE/'FINAL_SEAL.json'
    with target.open('x',encoding='utf-8',newline='\n') as f:
        f.write(canonical({'files':files,'case_files_verified':len(case_seal['files']),
                           'requests':60,'observed_leaders':result['observed_leaders'],
                           'api_key_files_excluded':True,'previous_sealed_files_verified':508})+'\n')
    saved=json.loads(target.read_text())
    for rel,expected in saved['files'].items():assert sha((project/rel).read_bytes())==expected,rel
    print(canonical({'sealed_files_verified':len(files),'case_files_verified':len(case_seal['files']),
                     'requests':60,'ordinary_report_completed':True,'seal':str(target)}))

if __name__=='__main__':main()
