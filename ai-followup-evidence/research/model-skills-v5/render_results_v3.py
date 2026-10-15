"""Render observed scores without replacing historical evidence or claiming family rankings."""
import json
from bench import HERE,BASE,DIMENSIONS

LABELS={'gemma4-12b':'Gemma 4 12B IT QAT','qwen35-4b':'Qwen 3.5 4B',
        'qwen3-4b':'Qwen 3 4B Instruct 2507','qwen35-9b':'Qwen 3.5 9B','ling3-tiny':'Ling 3.0 tiny Q4_K_M'}

def main():
    result=json.loads((HERE/'TRANSFER_VERIFIED_RESULTS.json').read_text())
    selected=json.loads((HERE/'SELECTED_LING_PROFILE_EXTENDED.json').read_text())
    old=json.loads((BASE/'model-skills-v4/VERIFIED_RESULTS.json').read_text())
    recovery=json.loads((HERE/'recovery-final.json').read_text(encoding='utf-8-sig'))
    assert recovery['fresh_report_completed'] and recovery['socket_owner_verified']
    totals=result['totals'];profile=selected['selected_profile'];ling=totals['ling3-tiny/'+profile]
    common=[(key,totals[key+'/clean-off']) for key in LABELS]
    leaders=[LABELS[k] for k,v in common if v['full_passes']==max(x['full_passes'] for _,x in common)]
    lines=['# Ling revision and fresh comparison results','',
        f"The historical Ling score remains **0/12**. On the fresh twelve-case pack, the frozen revised Ling profile `{profile}` passed **{ling['full_passes']}/12** strict six-dimension cases. All {len(result['rows'])} new comparison requests returned complete, input-verified final JSON. A complete answer and a correct answer are counted separately.",'',
        '## Matched common profile','',
        'All five artifacts received identical revised skill text, original records, unclassified receipts and answer schema. This table uses greedy sampling with thinking disabled.','',
        '| Artifact | Strict full passes | Complete answers |','|---|---:|---:|']
    for k,v in sorted(common,key=lambda kv:-kv[1]['full_passes']):
        lines.append(f"| {LABELS[k]} | {v['full_passes']}/12 | {v['complete_final_json']}/12 |")
    lines+=['',f"Observed common-profile leader: {', '.join(leaders)}. This is a task/configuration result from one draw per constructed case, not a model-family ranking.",'',
        '## Frozen Ling revision','',
        f"Selected on development evidence before creating the transfer pack: `{profile}`. Temperature {selected['profile']['temperature']}, top-p {selected['profile']['top_p']}, top-k 20, seed 17, native Bailing template, thinking {'enabled' if selected['profile']['thinking'] else 'disabled'}. The enabled reasoning cap is {selected['profile'].get('thinking_budget',1024):,} tokens, inside a 4,096-token overall completion ceiling and 8,192-token context. CPU-only, sixteen threads, finite 300-second requests.",'',
        f"On the same fresh cases, common non-thinking Ling passed {totals['ling3-tiny/clean-off']['full_passes']}/12 and the selected profile passed {ling['full_passes']}/12. Its enabled reasoning was forcibly closed by the budget on {ling['reasoning_budget_closures']}/12 requests. Every final JSON stopped normally; that does not mean every reasoning trace ended naturally.",'',
        '| Development profile | Strict full passes | Reasoning-budget closures |','|---|---:|---:|']
    for p in ('legacy-off','clean-off','clean-think','clean-native','clean-think-long','clean-native-long'):
        v=selected['scores']['ling3-tiny/'+p]
        lines.append(f"| {p} | {v['full_passes']}/4 | {v['reasoning_budget_closures']}/4 |")
    lines+=['','The consistent prompt corrected development success/failure classifications. A larger bounded reasoning budget was tested because all initial thinking traces reached their cap. Selection uses strict full-case passes and the predeclared tie order. The publisher sampling recipe was tested; it is not assumed to win locally.','',
        '## Decision dimensions on the fresh pack','',
        '| Artifact/profile | Contexts | Checks | Client outcome | Client refs | Intrusion boundary | Delivery boundary |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for key,v in totals.items():
        artifact,p=key.split('/');ds=v['dimensions']
        lines.append('| '+LABELS[artifact]+' / '+p+' | '+' | '.join(f'{ds[d]}/12' for d in DIMENSIONS)+' |')
    lines+=['','Both boundary dimensions only test unsupported positive claims. No fixture proves an intrusion or complete UDP delivery. This evaluation does not establish positive intrusion-detection ability.','',
        '## Preserved earlier result','',
        '| Artifact | Original F-pack strict passes |','|---|---:|']
    for row in old['scores']:lines.append(f"| {LABELS[row['model']]} | {row['strict_pass']}/12 |")
    lines+=['','The original prompt, cases, answers, grades and seals remain. The original Ling failure pattern included an unsupported comparison check on every case. The fresh pack changes source windows and near-match receipt distractors, so its scores cannot be used as a controlled old-to-new accuracy delta. The development contrasts and the two Ling lanes provide the matched comparisons.','',
        '## Evidence and limits','',
        'The twelve new cases are author-known synthetic variants of the same development families. They change attempt identifiers, timestamps, tuples, counts/order and near-match receipts. Even empty cases carry fresh window metadata. No real unseen incidents or human-benefit test is claimed. Artifact sizes, quantization and runtimes differ; timings are not pooled into a speed ranking. One stochastic seed cannot establish repeatability.','',
        'Raw response bytes were independently parsed and regraded against the sealed source cases. The audit checked identical common prompts/inputs/schemas, native thinking prefixes and returned channels, complete-input traces, CPU residency for the Ollama lane, runtime/model identities and owned-child cleanup. No answers were repaired or retried. The original log-phrase detector and the initial audit parser were preserved; an additive auditor uses the actual native generation-prefix and budget-exhaustion lines. A future-case generator briefly changed during calibration and was restored to exact sealed bytes before a separate version was created. It was not read by the calibration executor.','',
        f"The ordinary Qwen 3.5 4B Vulkan reporter completed a fresh report at {recovery['worker']['result']['completed_utc']}. Current viewer socket/process ownership was verified. The maintenance pause is absent and the temporary Ling listener is gone. The collector and existing native health monitoring remain separate; the protected default model endpoint was not invoked. No new host thermal certification is claimed.",'',
        'Research: [official Ling card](https://huggingface.co/inclusionAI/Ling-3.0-tiny), [community observations](https://www.reddit.com/r/LocalLLaMA/comments/1w7y3sa/aa_update_heres_how_the_small_models_score/), and the local research/protocol documents.','',
        'Reproduction files: `soc-decision-skill-v2.md`, `SELECTED_LING_PROFILE_EXTENDED.json`, `TRANSFER_PROTOCOL.json`, `TRANSFER_PRE_EXECUTION_SEAL.json`, `TRANSFER_VERIFIED_RESULTS.json`, the two calibration result files and immutable per-request source/response/trace receipts.']
    correction=json.loads((HERE/'CORRECTION_VERIFIED_RESULTS.json').read_text())
    lines+=['','## Retry timestamp correction addendum','',
        'The authored N05 retry fixture had one collection timestamp earlier than its event. The original twelve-case pack and all scores remain intact. A separately sealed variant changes only that collection time to two seconds after the event. Its receipt join fields and source-derived oracle are unchanged. Each artifact and both Ling profiles received this corrected case as six additional requests with identical recipes.','',
        '| Artifact/profile | Original N05 pass | Corrected N05 pass | Twelve-case sensitivity total |',
        '|---|---:|---:|---:|']
    for pair in correction['pairs']:
        key=pair['model_key']+'/'+pair['profile']
        lines.append(f"| {LABELS[pair['model_key']]} / {pair['profile']} | {pair['original_case_pass']} | {pair['corrected_case_pass']} | {correction['sensitivity_full_passes'][key]}/12 |")
    lines+=['','Sensitivity totals replace only N05 with the corrected-case result. They are supplemental and do not overwrite the predeclared primary scores. Read the new set as authored synthetic tasks rather than a real-world clock-validation benchmark. The corrected fixture is internally time-consistent.']
    lines+=['','## Native resource guard and continuation','',
        'The original native transfer batch completed nineteen requests, then stopped at its pre-request 16 GiB spare-memory guard. The next five requests were never sent. Its completed outcomes, raw logs, nonzero execution receipt, owned-child cleanup and ordinary recovery remain intact. A separately sealed continuation sent only those five unchanged request bodies with server RAM prompt caching disabled. It also monitored spare memory during each answer and kept the same floor. All five completed without a threshold breach. Inputs, weights, skill, schema, sampling, seed, context, output/reasoning budgets and deadlines remain as declared. Runtime resource conditions differ, so these results are not a pure resource-uncontrolled causal or pooled throughput comparison. No completed request was repeated.']
    target=BASE.parents[1]/'docs/ai-followup-20261007/LING_REVISION_RESULTS_V3.md'
    with target.open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    print(str(target))

if __name__=='__main__':main()
