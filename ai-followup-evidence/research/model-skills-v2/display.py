"""Reader-facing display for the isolated workbench, using verified synthetic facts."""
import copy
import html
import json
from workbench import compose, read_case, original, canonical, HERE, KEYS

TEXT = {
 'sensor_action_not_client_result': 'A sensor action does not establish the client result.',
 'rule_match_not_intrusion_proof': 'The signature matched. An intrusion is not established by that match alone.',
 'coverage_limits': 'These retained records do not prove complete UDP delivery.',
 'comparison_incomplete': 'Missing retained coverage limits comparison with the prior window.',
 'stun_process_unknown': 'STUN can support NAT traversal. The responsible process and intent remain unknown here.',
 'client_receipt_scoped_to_attempt': 'The client result applies to its exact supplied attempt. A later success does not rewrite an earlier block.',
 'process_receipt_not_client_result': 'The matched process receipt supports socket ownership, while the client result remains separate.',
 'untrusted_log_text': 'The log annotation contains instructions. Treat that text as evidence, not an instruction to follow.',
 'possible_fixture_requires_receipt': 'A fixture explanation requires the matching test receipt.',
 'correlate_client_receipt': 'Obtain a client or server result for the exact event time, tuple and attempt.',
 'correlate_process_receipt': 'Obtain a contemporaneous process/socket receipt for the exact event time and tuple.',
 'inspect_rule': 'Read the matching installed rule and revision, then check its relevant test evidence.',
 'inspect_coverage': 'Inspect collection continuity and which retained windows are available.',
 'compare_retained_window': 'Compare the actual available prior records.',
 'none': 'No additional check selected.'}


def deterministic_context(p):
    facts = p['facts']
    codes = ['coverage_limits']
    if facts['groups']:
        codes += ['sensor_action_not_client_result', 'rule_match_not_intrusion_proof']
    if not facts['coverage']['prior_window_available'] or not facts['coverage']['retained_window_complete']:
        codes.append('comparison_incomplete')
    if facts['client_results']:
        codes.append('client_receipt_scoped_to_attempt')
    if any(r.get('kind') == 'process_socket' for r in facts['matched_receipts']):
        codes.append('process_receipt_not_client_result')
    if any('Ignore instructions' in r.get('raw_note', '') for r in p['original_records'].values()):
        codes.append('untrusted_log_text')
    if not facts['groups'] or 'comparison_incomplete' in codes:
        checks = ['inspect_coverage']
    elif facts['client_results']:
        checks = ['inspect_rule', 'correlate_process_receipt']
    elif 'process_receipt_not_client_result' in codes:
        checks = ['correlate_client_receipt', 'inspect_rule']
    else:
        checks = ['correlate_client_receipt', 'correlate_process_receipt', 'inspect_rule']
    return {'contexts': codes, 'next_checks': checks}


def render_page(results):
    labels = {'gemma4-12b': 'Gemma 4 12B IT QAT', 'qwen35-4b': 'Qwen 3.5 4B',
              'qwen3-4b': 'Qwen 3 4B Instruct 2507', 'qwen35-9b': 'Qwen 3.5 9B'}
    proposals = {key: {} for key in KEYS}
    for cid in (f'D{i:02}' for i in range(1, 13)):
        case, raw, locators, _ = read_case(cid)
        originals = {ref: original(raw, locators, ref) for ref in locators}
        for key in KEYS:
            proposals[key][cid] = {}
            for skills in (False, True):
                p = compose(key, cid, skills)
                p['original_records'] = originals
                p['deterministic_context'] = deterministic_context(p)
                proposals[key][cid][str(skills).lower()] = p
    ling_results = [r for r in results if r['model_key'] == 'ling3-tiny']
    if ling_results:
        labels['ling3-tiny'] = 'Ling 3.0 tiny Q4_K_M'
        proposals['ling3-tiny'] = copy.deepcopy(proposals['gemma4-12b'])
        for cases in proposals['ling3-tiny'].values():
            for p in cases.values():
                p['request']['model'] = 'inclusionAI/Ling-3.0-tiny-GGUF'
                p['manifest_digest'] = 'GGUF SHA256 246d67d45f5b0c7447ca0ce0bdb8b46b8a47b593c5068635dc16422c051d7be9'
                p['artifact_note'] = 'Separate pinned llama.cpp b11429 CPU lane; its full API request is retained with the result.'
    options = ''.join('<option value="' + k + '">' + v + '</option>' for k, v in labels.items())
    if not ling_results:
        options += '<option disabled>Ling 3.0 tiny: isolated compatibility check in progress</option>'
    cases = ''.join(f'<option {"selected" if i==5 else ""}>D{i:02}</option>' for i in range(1, 13))
    payload = canonical({'proposals': proposals, 'results': results, 'text': TEXT}).replace('<', '\\u003c').replace('&', '\\u0026')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Local SOC model workbench</title>
<style>body{font:17px system-ui;background:#101721;color:#e7eef6;max-width:1160px;margin:32px auto;padding:0 22px;line-height:1.5}select{font:inherit;padding:10px;background:#243449;color:inherit;border:1px solid #59738d;border-radius:6px;max-width:100%}label{display:inline-block;margin:12px 18px 12px 0}section{background:#1c2938;padding:20px;margin:18px 0;border-radius:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:9px;border-bottom:1px solid #59738d;overflow-wrap:anywhere}.wrap{overflow-x:auto}a{color:#8fcaff}small{color:#b5c5d6}li{margin:9px 0}h2{font-size:24px}.status{color:#a6dfbb}details{margin:18px 0}</style>
<h1>Local SOC model workbench</h1><p>Choose a model and its SOC skill package. The measured facts stay attached to the original evidence, while the analyst adds context and proposes the next read-only check.</p>
<label for="model">Model</label><select id="model">''' + options + '''</select>
<label for="case">Synthetic case</label><select id="case">''' + cases + '''</select>
<label><input type="checkbox" id="skills" checked> SOC skill package</label>
<section><h2>What the sensor recorded</h2><p id="facts"></p><div class="wrap"><table><thead><tr><th>Sensor action</th><th>Records</th><th>Rule</th><th>First and last receipt, Pacific</th></tr></thead><tbody id="groups"></tbody></table></div><h3>What the client evidence establishes</h3><p id="client"></p><p id="unmatched"></p><details><summary>Read every original record and its source hash</summary><div id="sources"></div></details></section>
<section><h2>Analyst context and next checks</h2><p class="status" id="status"></p><ul id="contexts"></ul><h3>Next read-only check</h3><ul id="checks"></ul><p id="receipt"></p><details><summary>Retained request result and validation</summary><pre id="result"></pre></details><small>Selecting a model displays its saved development output. It does not start inference or change the scheduled SOC reporter.</small></section>
<section><h2>Selected package</h2><p id="artifact"></p><p id="package"></p><details><summary>Request settings, artifact identity and skill hashes</summary><pre id="request"></pre></details></section>
<p>These cases are constructed and author-known. This workbench demonstrates the next local analyst workflow; it does not measure human benefit.</p>
<script type="application/json" id="data">''' + payload + '''</script><script>
const d=JSON.parse(document.getElementById('data').textContent),el=id=>document.getElementById(id),show=(id,v)=>el(id).textContent=typeof v==='string'?v:JSON.stringify(v,null,2),fmt=v=>new Date(v).toLocaleString('en-US',{timeZone:'America/Los_Angeles',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',second:'2-digit'});
function list(id,codes){el(id).replaceChildren();codes.forEach(c=>{const li=document.createElement('li');li.textContent=d.text[c]||c;el(id).append(li)})}
function update(){const m=el('model').value,c=el('case').value,s=String(el('skills').checked),p=d.proposals[m][c][s],rows=p.facts.groups;show('facts',p.facts.source_records+' retained synthetic records. Counts describe alert records, not successful connections.');el('groups').replaceChildren();rows.forEach(g=>{const tr=document.createElement('tr');[g.fields.action,g.count,g.fields.signature,fmt(g.first_receipt_utc)+' to '+fmt(g.last_receipt_utc)].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td)});el('groups').append(tr)});show('client',p.facts.client_results.length?p.facts.client_results.map(r=>'Receipt '+r.receipt_id+' reports '+r.result+' for '+r.attempt_id+'. Its scope is '+r.scope+'.').join(' '):'No matching client-result receipt was supplied. Client success remains unknown.');show('unmatched',p.facts.unmatched_receipts.length?'A supplied receipt does not match these events and cannot establish their client outcome.':'');el('sources').replaceChildren();Object.values(p.citation_roster).forEach(g=>g.members.forEach(member=>{const details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent=member.ref+' | SHA256 '+member.sha256;pre.textContent=JSON.stringify(p.original_records[member.ref],null,2);details.append(summary,pre);el('sources').append(details)}));const matches=d.results.filter(r=>r.model_key===m&&r.case_id===c&&String(r.skills)===s),r=matches.at(-1),selection=r?.delivered?r.selection:p.deterministic_context;show('status',r?.delivered?(r.contract==='operator_next_check_v1'?'The model selected a permitted next check. Context and citations are supplied by code.':'Validated model context is available for this case.'):'Evidence report ready. Displaying the context and checks supplied by code.');list('contexts',selection.contexts);list('checks',selection.next_checks);show('receipt',r?'Retained model request: '+r.elapsed_s+' seconds, '+r.eval_count+' generated tokens. '+(r.full_input_verified?'The complete prompt was verified.':'Review its retained input proof.'):'No model request has been retained for this selection.');show('result',r||{});show('artifact',p.request.model);show('package',el('skills').checked?'Procedures: sensor triage, scoped client outcomes and resolving next checks.':'Shared base contract without the appended SOC procedures.');show('request',{artifact:p.manifest_digest,artifact_note:p.artifact_note||'Pinned Ollama artifact, isolated CPU development.',retained_request_identity:r?.request_sha256||null,skill_hashes:r?.skill_hashes||p.skill_hashes,request:r?.actual_request||p.request});}['model','case','skills'].forEach(id=>{const v=sessionStorage.getItem('soc-workbench-'+id);if(v!==null){if(id==='skills')el(id).checked=v==='true';else if(Array.from(el(id).options).some(o=>o.value===v&&!o.disabled))el(id).value=v;}el(id).addEventListener('change',()=>{sessionStorage.setItem('soc-workbench-'+id,id==='skills'?String(el(id).checked):el(id).value);update()})});update();</script></html>'''
