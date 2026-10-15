"""Bounded investigation context that accommodates expanded membership.

Investigator context is 8192; live analyst and reviewer remain 4096.
700-token output cap, request deadline and resource floor remain unchanged.
"""
from pathlib import Path
import argparse
import soc_analyst as analyst
import soc_investigation_run as runner
import soc_investigation_v2 as v2
import soc_investigation_v5 as v5

REVISION='fixed-slots-full-investigator-context-8192-v6'


def make_job(pack,scheduled,role,selected,locked,model):
    job,reason=v5.make_job(pack,scheduled,role,selected,locked,model)
    if job and role=='investigator':
        job['payload']['options']['num_ctx']=8192
    return job,reason


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--backend-receipt',type=Path,required=True)
    p.add_argument('--runtime-log',type=Path,required=True,
        help='Owned isolated runtime stderr used to verify every complete input')
    args=p.parse_args()
    runner.run(args.pack,args.output,analyst_model='qwen3.5:4b',investigator_model='qwen3.5:4b',
        reviewer_model='qwen3.5:9b',backend_receipt=args.backend_receipt,job_builder=make_job,
        protocol_revision=REVISION,investigator_decoder=v5.decode,runtime_log=args.runtime_log,
        role_options={'analyst':{'num_ctx':4096,'num_predict':700,'think':False},
                      'investigator':{'num_ctx':8192,'num_predict':700,'think':False},
                      'reviewer':{'num_ctx':4096,'num_predict':700,'think':False}})
    print(analyst.canonical(v2.assess(args.pack,args.output,revision=REVISION)))


if __name__=='__main__':main()
