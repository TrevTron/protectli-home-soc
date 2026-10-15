"""V3 development: natural JSON, same explicit V2 contract and resource bounds.

No schema-constrained token decoding. Strict parsing and the independent oracle
still reject wrong outputs. Retain V1/V2 failures separately.
"""
from pathlib import Path
import argparse
import soc_analyst as analyst
import soc_investigation_eval as evaluation
import soc_investigation_run as runner
import soc_investigation_v2 as v2

REVISION='explicit-contract-natural-json-v3'


def make_job(pack, scheduled, role, selected, locked, model):
    job,reason=v2.make_job(pack,scheduled,role,selected,locked,model)
    if job and role in ('investigator','reviewer'):
        job['payload'].pop('format',None)
        job['structured_content']=True
    return job,reason


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--backend-receipt',type=Path,required=True)
    args=p.parse_args()
    runner.run(args.pack,args.output,analyst_model='qwen3.5:4b',investigator_model='qwen3.5:4b',
        reviewer_model='qwen3.5:9b',backend_receipt=args.backend_receipt,job_builder=make_job,protocol_revision=REVISION)
    result=v2.assess(args.pack,args.output)
    print(analyst.canonical(result))


if __name__=='__main__':main()
