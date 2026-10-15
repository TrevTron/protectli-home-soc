"""Research reviewer reasoning mode, separately bounded and never an oracle.

Investigator uses full 8192 context and 700 output tokens. Reviewer uses 4096
context and a 2048 token generation ceiling that includes its thinking channel.
Both channels are retained; only naturally completed strict JSON is assessed.
"""
import soc_investigation_v6 as v6

REVISION='full-input-context-and-reasoning-review-v7'


def make_job(pack,scheduled,role,selected,locked,model):
    job,reason=v6.make_job(pack,scheduled,role,selected,locked,model)
    if job and role=='reviewer':
        job['payload']['think']=True
        job['payload']['options']['num_predict']=2048
        job['allow_thinking']=True
    return job,reason
