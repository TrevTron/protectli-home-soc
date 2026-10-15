"""Fixed decision slots prevent duplicate choices, without computing their values.

All supplied facts and model-returned observations remain separately checked.
Boolean maps are reversibly decoded into the original grading representation.
"""
from pathlib import Path
import argparse
import copy
import soc_analyst as analyst
import soc_investigation_eval as evaluation
import soc_investigation_run as runner
import soc_investigation_v2 as v2
import soc_investigation_v4 as v4

REVISION='trusted-contract-fixed-decision-slots-v5'
MAPS={'decisions':evaluation.DECISIONS,'context_codes':sorted(analyst.INFERENCES),'next_steps':sorted(analyst.NEXT_STEPS)}


def schema():
    result=copy.deepcopy(evaluation.decision_schema())
    for field,names in MAPS.items():
        result['properties'][field]={'type':'object','additionalProperties':False,
                                    'required':names,'properties':{k:{'type':'boolean'} for k in names}}
    return result


def decode(answer):
    if not isinstance(answer,dict) or set(answer)!=set(schema()['required']):raise ValueError('Missing or extra decision fields')
    decoded=copy.deepcopy(answer)
    for field,names in MAPS.items():
        values=answer[field]
        if not isinstance(values,dict) or set(values)!=set(names) or any(type(v) is not bool for v in values.values()):
            raise ValueError('Decision slots must all be explicit boolean values')
        decoded[field]=[name for name in names if values[name]]
    return decoded


def make_job(pack,scheduled,role,selected,locked,model):
    job,reason=v4.make_job(pack,scheduled,role,selected,locked,model)
    if job and role=='investigator':
        payload=job['payload'];payload['format']=schema()
        semantics=copy.deepcopy(v2.CONTRACT)
        semantics['context_codes']='For each named context code return true only when it appears in an eligible_inferences list for a supplied group. Otherwise false.'
        semantics['next_steps']='Return true for inspect_event when groups exist. Return true for check_visibility when groups is empty or context.constructed_missing_context is true. Other listed read-only checks can be true if useful. Never execute checks.'
        semantics['arrays']='observations is an array with each supplied group once, or [] if none. decisions, context_codes and next_steps are objects with every named slot once, true if selected and false otherwise. No omitted boolean slots.'
        payload['messages'][0]['content']=(evaluation.INVESTIGATOR_SYSTEM+
            ' Return exactly the JSON object defined by this schema. Each decision/context/check has its own boolean slot. '
            'Apply each condition independently to the user evidence. No group entries means zero alerts; action allowed does not mean zero alerts. '
            'A missing comparison may coexist with observed alerts. '
            '\nOutput schema: '+analyst.canonical(schema())+'\nTrusted field meanings: '+analyst.canonical(semantics))
    return job,reason


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--backend-receipt',type=Path,required=True)
    args=p.parse_args()
    runner.run(args.pack,args.output,analyst_model='qwen3.5:4b',investigator_model='qwen3.5:4b',
        reviewer_model='qwen3.5:9b',backend_receipt=args.backend_receipt,job_builder=make_job,
        protocol_revision=REVISION,investigator_decoder=decode)
    print(analyst.canonical(v2.assess(args.pack,args.output,revision=REVISION)))


if __name__=='__main__':main()
