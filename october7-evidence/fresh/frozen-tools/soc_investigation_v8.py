"""New synthetic cases with a recorded larger resource budget, not a human pilot."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shutil

import soc_analyst as analyst
import soc_fresh_cases as fresh
import soc_investigation_eval as evaluation
import soc_investigation_run as runner
import soc_investigation_v2 as v2
import soc_investigation_v5 as v5

REVISION='fresh-constructed-larger-resource-budget-v8'
OPTIONS={'num_ctx':8192,'num_predict':2048,'num_thread':16,'num_gpu':99}


def make_job(pack,scheduled,role,selected,locked,model):
    job,reason=v5.make_job(pack,scheduled,role,selected,locked,model)
    if job:job['payload']['options'].update(OPTIONS)
    return job,reason


def prepare(cases,output):
    fresh.verify(cases)
    output=Path(output)
    if output.exists():raise ValueError('New execution root required; earlier outcomes are not rerun')
    output.mkdir(parents=True)
    frozen=output/'frozen-tools';frozen.mkdir()
    names=fresh.local_tool_closure(Path(__file__).parent,seeds=(*fresh.TOOL_NAMES,'soc_investigation_v8.py'))
    tool_hashes={}
    for name in sorted(names):
        raw=(Path(__file__).parent/name).read_bytes();(frozen/name).write_bytes(raw)
        tool_hashes[name]=evaluation.digest(raw)
    seal={'revision':REVISION,'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'case_pre_request_seal_sha256':evaluation.digest((Path(cases)/'PRE_REQUEST_SEAL.json').read_bytes()),
        'tools':tool_hashes,'options':OPTIONS,'timeout_seconds':300,'thinking':False,
        'actual_requests':0,'human_participants':0,
        'case_exposure':'New constructed source bytes, sealed before first request. The case author knows the labels. Not unseen real incidents.',
        'conditions':'A evidence/catalogue; B same plus model-selected assistance; C assistance with exact repeats collapsed',
        'total_scheduled_jobs':168,'roles':{'analyst':'qwen3.5:4b','investigator':'qwen3.5:4b','reviewer':'qwen3.5:9b'},
        'grading':'Deterministic source-backed oracle; model reviewer is supplementary and cannot override it.'}
    evaluation.write(output/'EXECUTION_PRE_REQUEST_SEAL.json',seal)
    return seal


def execute(cases,output,backend,runtime_log):
    cases=Path(cases);output=Path(output)
    seal=evaluation.load(output/'EXECUTION_PRE_REQUEST_SEAL.json')
    if seal['revision']!=REVISION or seal['options']!=OPTIONS or seal['timeout_seconds']!=300:
        raise ValueError('Execution budget seal changed')
    if evaluation.digest((cases/'PRE_REQUEST_SEAL.json').read_bytes())!=seal['case_pre_request_seal_sha256']:
        raise ValueError('Execution case seal changed')
    for name,digest in seal['tools'].items():
        if Path(name).name!=name or evaluation.digest((Path(__file__).parent/name).read_bytes())!=digest:
            raise ValueError('Execute the frozen tool tree, not changed project code')
    old_timeout=runner.HTTP_TIMEOUT;runner.HTTP_TIMEOUT=300
    try:
        results=[]
        for number in (1,2,3):
            fresh.verify(cases)
            pack=cases/f'batch-{number}';target=output/f'batch-{number}'
            completion=runner.run(pack,target,analyst_model='qwen3.5:4b',investigator_model='qwen3.5:4b',
                reviewer_model='qwen3.5:9b',backend_receipt=backend,job_builder=make_job,
                protocol_revision=REVISION,investigator_decoder=v5.decode,runtime_log=runtime_log,
                role_options={role:{**OPTIONS,'think':False} for role in ('analyst','investigator','reviewer')},
                case_exposure=seal['case_exposure'])
            result=v2.assess(pack,target,revision=REVISION);results.append(result)
            evaluation.write(output/'progress.json',results)
            if completion['halt_reason']:raise ValueError('Execution halted; preserve outcomes and do not retry')
        evaluation.write(output/'complete.json',results)
        return results
    finally:runner.HTTP_TIMEOUT=old_timeout


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','execute'))
    parser.add_argument('--cases',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--backend-receipt',type=Path);parser.add_argument('--runtime-log',type=Path)
    args=parser.parse_args()
    if args.command=='execute' and (not args.backend_receipt or not args.runtime_log):parser.error('Execution requires backend and runtime receipts')
    result=prepare(args.cases,args.output) if args.command=='prepare' else execute(args.cases,args.output,args.backend_receipt,args.runtime_log)
    print(analyst.canonical(result))
