"""Write a local review document only after the independent round audit."""
import json
from pathlib import Path
from comparison import HERE, BASE

LABELS={'gemma4-12b':'Gemma4 12B IT QAT','qwen35-4b':'Qwen3.5 4B',
        'qwen3-4b':'Qwen3 4B Instruct 2507','qwen35-9b':'Qwen3.5 9B','ling3-tiny':'Ling-3.0-tiny'}

def main():
    results=json.loads((HERE/'VERIFIED_RESULTS.json').read_text())
    leaders=', '.join(LABELS[k] for k in results['observed_leaders'])
    top=results['scores'][0]['strict_pass']
    text=['# Harder local analyst comparison', '',
          f'{leaders} had the highest observed strict score on this constructed twelve-case test: {top}/12. '
          'The primary score requires all six decisions to be correct in the same answer. '
          'This is a test-set result from one request per artifact and case, not a general model ranking.', '',
          'The previous 15/15 demonstration assigned a smaller job to the models: pick one permitted next check while code supplied the context. '
          'Here every model received complete original synthetic records and unclassified receipts. '
          'It had to choose context and useful checks, decide the client outcome, name the exact matching client receipt, '
          'and avoid unsupported intrusion or complete-delivery claims. The skill package and task/schema were identical across artifacts.', '',
          '| Exact artifact | Strict pass | Alert-bearing pass | Empty-case pass |',
          '| --- | ---: | ---: | ---: |']
    for s in results['scores']:
        text.append(f"| {LABELS[s['model']]} | {s['strict_pass']}/12 | {s['alert_bearing_pass']}/10 | {s['empty_pass']}/2 |")
    text += ['', 'All sixty scheduled requests are included. Completion and full-input validity remain separate from semantic accuracy.', '',
             '| Artifact | Context | Useful check | Client outcome | Exact client receipt | Intrusion boundary | Delivery boundary |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for s in results['scores']:
        d=s['dimensions']
        text.append('| '+LABELS[s['model']]+' | '+' | '.join(f'{d[k]}/12' for k in
                    ('contexts','next_checks','client_outcome','client_refs','intrusion_established','delivery_complete'))+' |')
    text += ['', 'The case-by-case audit and original outputs remain in the '
             '[private verified results](../../private/ai-followup-20261007/model-skills-v4/VERIFIED_RESULTS.json). '
             'Paired pass/fail counts are retained there. A dimension pass is not a full answer pass, '
             'and fluent explanation is not assessed by this structured JSON contract.', '',
             'Every case in this pack leaves intrusion and complete delivery unproved. '
             'Those two dimensions test unsupported positive claims; they do not test recognition of a confirmed intrusion '
             'or proven complete delivery. The strict score also requires the case-dependent context, check, outcome and receipt decisions.', '',
             'The twelve scenario families include wrong-tuple receipts, process-only evidence, a block followed by retry success, '
             'empty windows with different coverage, changed signatures, embedded instructions and unavailable prior evidence. '
             'Evaluation variants had not been sent to these models, but the author knew their labels and paired development families were exposed. '
             'They are constructed transfer cases, not unseen real incidents. No participant session or human-benefit measurement occurred.', '',
             'The four Qwen/Gemma artifacts used the owned isolated Ollama CPU runtime. Current Ling used its pinned official GGUF '
             'and separate CPU-only llama.cpp build. Native templates and installed quantizations differ. '
             'Ling stayed resident within its batch; Ollama released each model between requests. '
             'No runtime-speed winner is inferred from the retained timing observations.', '',
             'Both maintenance batches restored a ready ordinary Qwen3.5 4B/Vulkan reporter. '
             'Collection stayed separate. The default 11434 service, active tool sources, earlier seals and original answers were preserved. '
             'The independent audit verified the prior 508-file workbench closeout and the frozen new proposals/execution sources. '
             'Memory floors, finite deadlines, native monitoring and hardware/kernel protections remain active; '
             'there is no new host thermal certification or broader operating-acceptance claim.', '',
             'The [predeclared protocol](HARDER_COMPARISON_PROTOCOL_V1.md) describes the scoring and execution boundary. '
             'No output was retried, repaired or excluded to improve its score. Live promotion, unrestricted prose, '
             'more varied independent incidents and repeatability on new cases remain separate work.']
    target=BASE.parents[1]/'docs/ai-followup-20261007/HARDER_COMPARISON_RESULTS_V1.md'
    with target.open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(text)+'\n')
    print(str(target))

if __name__=='__main__':main()
