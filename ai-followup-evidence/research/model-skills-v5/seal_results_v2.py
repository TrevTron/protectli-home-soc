"""Final additive closeout: prior evidence, fresh oracles, completed runs and ordinary recovery."""
import datetime as dt
import json
from pathlib import Path
from bench import HERE,BASE,sha,write,canonical
from prepare_calibration import verify_previous

def main():
    verify_previous();project=BASE.parents[1]
    originals=json.loads((BASE/'source-hashes-before.json').read_text())
    for path,expected in originals.items():assert sha(Path(path).read_bytes())==expected,path
    old_cases=json.loads((BASE/'cases-v3/PRE_EVALUATION_SEAL.json').read_text())
    for path,expected in old_cases['files'].items():assert sha((BASE/'cases-v3'/path).read_bytes())==expected,path
    for manifest,root in [(HERE/'transfer-cases/PRE_EVALUATION_SEAL.json',HERE/'transfer-cases')]:
        for path,expected in json.loads(manifest.read_text())['files'].items():assert sha((root/path).read_bytes())==expected,path
    transfer=json.loads((HERE/'TRANSFER_VERIFIED_RESULTS.json').read_text())
    recovery=json.loads((HERE/'recovery-final.json').read_text(encoding='utf-8-sig'))
    assert recovery['socket_owner_verified'] and recovery['fresh_report_completed']
    assert not recovery['maintenance_pause_present'] and not recovery['ling_listener_present']
    assert recovery['worker']['result']['worker_exit']==0
    assert all(r['complete_final_json'] and r['full_input_verified'] for r in transfer['rows'])
    for lane in ('calibration-ling-01','calibration-long-01','correction-ling-long-01',json.loads((HERE/'TRANSFER_PROTOCOL.json').read_text())['native_lane']):
        assert json.loads((HERE/lane/'owned-child-cleanup.json').read_text())['only_owned_child_stopped']
        assert json.loads((HERE/lane/'execution-exit.json').read_text(encoding='utf-8-sig'))['exit_code']==0
    correction=json.loads((HERE/'CORRECTION_VERIFIED_RESULTS.json').read_text())
    assert correction['requests']==6 and all(r['complete_final_json'] and r['full_input_verified'] for r in correction['rows'])
    paths=[p for p in HERE.rglob('*') if p.is_file() and p.name not in ('api-key.txt','FINAL_SEAL.json') and '__pycache__' not in p.parts]
    paths+=[project/'docs/ai-followup-20261007'/name for name in ('LING_REVISION_RESEARCH_V1.md','LING_REVISION_PROTOCOL_V1.md','LING_REVISION_RESULTS_V2.md','LING_RETRY_FIXTURE_ADDENDUM_V1.md')]
    files={str(p.relative_to(project)).replace('\\','/'):sha(p.read_bytes()) for p in paths}
    write(HERE/'FINAL_SEAL.json',{'utc':dt.datetime.now(dt.timezone.utc).isoformat(),'files':files,
        'original_hashes_verified':len(originals),'old_case_files_verified':len(old_cases['files']),
        'prior_v2_v4_seals_verified':True,'old_ling_zero_preserved':True,
        'development_requests':24,'corrected_fixture_requests':6,'transfer_requests':len(transfer['rows']),'transfer_cases':12,
        'selected_ling_profile':json.loads((HERE/'SELECTED_LING_PROFILE_EXTENDED.json').read_text())['selected_profile'],
        'ordinary_report_completed':True,'api_key_files_excluded':True,'retries':0})
    for path,expected in files.items():assert sha((project/path).read_bytes())==expected,path
    print(canonical({'sealed_files':len(files),'original_hashes_verified':len(originals),
        'old_case_files_verified':len(old_cases['files']),'development_requests':24,'corrected_fixture_requests':6,'transfer_requests':len(transfer['rows']),
        'ordinary_report_completed':True}))

if __name__=='__main__':main()
