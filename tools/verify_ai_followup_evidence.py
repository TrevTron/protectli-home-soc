"""Verify saved synthetic AI studies offline. Never imports execution wrappers."""
import argparse
import collections
import hashlib
import importlib.util
import json
import re
from pathlib import Path

FIELDS = ('contexts', 'next_checks', 'client_outcome', 'client_refs', 'intrusion_established', 'delivery_complete')
JOIN = ('attempt_id', 'event_utc', 'protocol', 'source_alias', 'source_port', 'destination_alias', 'destination_port')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def require(test, message):
    if not test:
        raise ValueError(message)

def file_manifest(root):
    manifest = load(root / 'PUBLIC_EXPORT_MANIFEST.json')
    for relative, entry in manifest['files'].items():
        path = (root / relative).resolve()
        require(path.is_relative_to(root.resolve()), 'Manifest path escapes evidence root')
        require(path.is_file() and sha(path.read_bytes()) == entry['public_sha256'], 'Public file changed: ' + relative)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    require(actual == set(manifest['files']) | {'PUBLIC_EXPORT_MANIFEST.json'}, 'Export membership changed')
    return manifest

def source_case(base, version, lane, cid):
    if version == 'model-skills-v5' and cid.startswith('N'):
        folder = base / version / ('correction-case' if lane.startswith('correction-') else 'transfer-cases/' + cid)
    else:
        folder = base / 'cases-v3' / ('development' if cid.startswith('D') else 'evaluation') / cid
    case = load(folder / 'case-private.json')
    locators = load(folder / 'locators.json')
    raw = (folder / 'evidence.jsonl').read_bytes()
    records = []
    for ref, locator in sorted(locators.items(), key=lambda item: item[1]['offset']):
        start, length = locator['offset'], locator['length']
        require(type(start) is int and type(length) is int and start >= 0 and length > 0, 'Invalid original locator')
        line = raw[start:start + length]
        require(len(line) == length and sha(line) == locator['sha256'] and ref == 'E-' + sha(line)[:16], 'Original record identity changed')
        records.append(json.loads(line))
    matched = [r for r in case['receipts'] if any(all(record.get(k) is not None and record.get(k) == r.get(k) for k in JOIN) for record in records)]
    refs = {r['receipt_id'] for r in matched if r.get('kind') == 'client_result'}
    require(refs == set(case['oracle']['client_refs']), 'Receipt oracle does not match the source')
    # Derive outcome separately from the supplied label.
    results = [r for r in matched if r.get('kind') == 'client_result']
    outcome = 'unknown'
    if results:
        result = results[0]
        outcome = 'supplied_attempt_' + result['result']
        if result['result'] == 'success' and any(r.get('action') == 'blocked' and r['attempt_id'] != result['attempt_id'] for r in records):
            outcome = 'retry_success_first_attempt_unknown'
    require(outcome == case['oracle']['client_outcome'], 'Client outcome oracle differs from receipts')
    return case, records, locators, matched

def decisions(case, records, matched, answer):
    oracle = case['oracle']
    allowed = set(oracle['eligible_contexts'])
    if any(r.get('sid') == 2016149 for r in records) and not any(r.get('kind') == 'process_socket' for r in matched):
        allowed.add('stun_process_unknown')
    def valid(v):
        return isinstance(v, list) and all(isinstance(x, str) for x in v) and len(v) == len(set(v))
    contexts, checks = answer.get('contexts'), answer.get('next_checks')
    dimensions = {
        'contexts': valid(contexts) and set(oracle['required_contexts']) <= set(contexts) <= allowed,
        'next_checks': valid(checks) and 1 <= len(checks) <= 3 and set(checks) <= set(oracle['useful_checks'])}
    if set(answer) == set(FIELDS):
        refs = answer['client_refs']
        dimensions.update({
            'client_outcome': answer['client_outcome'] == oracle['client_outcome'],
            'client_refs': valid(refs) and set(refs) == set(oracle['client_refs']),
            'intrusion_established': answer['intrusion_established'] is False,
            'delivery_complete': answer['delivery_complete'] is False})
    return dimensions

def verify(root):
    manifest = file_manifest(root)
    base = root / 'research'
    spec = importlib.util.spec_from_file_location('saved_context_guard', root / 'frozen-tools/soc_context_guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    summary, rows = {}, []
    matched_workloads = {}
    for version, expected in [('model-skills-v2', 57), ('model-skills-v4', 60), ('model-skills-v5', 102)]:
        paths = sorted((base / version).rglob('outcome.json'))
        require(len(paths) == expected, 'Missing or extra study request')
        complete_inputs = operator_passes = 0
        for path in paths:
            outcome = load(path)
            folder, lane = path.parent, path.parent.parent.name
            response = load(folder / 'response.json')
            native = 'choices' in response
            if native:
                request = load(folder.parent / (outcome['name'] + '-request.json'))
                message = response['choices'][0]['message']
                stop = response['choices'][0]['finish_reason'] == 'stop'
                prompt_tokens = response['usage']['prompt_tokens']
                schema = request['response_format']['json_schema']['schema']
            else:
                proposal = load(folder.parent / 'requests' / (outcome['name'] + '.json'))
                request, message = proposal['request'], response['message']
                stop = response.get('done') is True and response.get('done_reason') == 'stop'
                prompt_tokens = response['prompt_eval_count']
                schema = request['format']
            require(sha(canonical(request).encode()) == outcome['request_sha256'], 'Actual request identity changed')
            answer = json.loads(message['content'])
            require(answer == outcome.get('model_selection', outcome['selection']), 'Selection differs from raw answer')
            require(stop and outcome['natural_complete'], 'Final completion did not stop normally')
            proof = load(folder / 'context-proof.json')
            trace_path = folder / 'runtime-trace.log'
            trace = trace_path.read_bytes()
            source_hash = manifest['files'][trace_path.relative_to(root).as_posix()]['source_sha256']
            require(proof['trace_sha256'] == source_hash, 'Proof does not bind original trace')
            measured = guard.assess(trace, context=8192, prompt_tokens=prompt_tokens)
            for key in ('trace_sha256', 'trace_bytes'):
                measured.pop(key, None)
            comparison = {k: v for k, v in proof.items() if k not in ('trace_sha256', 'trace_bytes')}
            require(measured == comparison, 'Input trace proof differs')
            require(proof['verified_full_context'] == outcome['full_input_verified'], 'Input validity differs')
            complete_inputs += outcome['full_input_verified']
            case, records, locators, matched = source_case(base, version, lane, outcome['case_id'])
            value = json.loads(request['messages'][1]['content'])
            require('oracle' not in value, 'Answer labels leaked into model input')
            if version != 'model-skills-v2':
                require(sorted(map(canonical, value['original_records'])) == sorted(map(canonical, records)), 'Input records differ from sealed source')
                require(value['receipts'] == case['receipts'], 'Input receipts differ from sealed source')
                dims = decisions(case, records, matched, answer)
                require(dims == outcome['grade']['dimensions'], 'Independent decision grade differs')
                require(all(dims.values()) == outcome['grade']['accepted'], 'Strict grade differs')
            elif outcome.get('contract') == 'operator_next_check_v1':
                require(set(answer) == {'next_check'} and answer['next_check'] in case['oracle']['useful_checks'], 'Operator check unsupported')
                report = outcome['code_supplied_report']
                members = [m for g in report['citation_roster'].values() for m in g['members']]
                require({m['ref'] for m in members} == set(locators) and len(members) == len(locators), 'Operator source membership changed')
                require(all(m['sha256'] == locators[m['ref']]['sha256'] for m in members), 'Operator source hash changed')
                require(report['context_source'] == 'deterministic_code' and report['next_check_source'] == 'validated_model_selection', 'Attribution changed')
                require(outcome['delivered'] and outcome['full_input_verified'], 'Operator request not delivered')
                operator_passes += 1
                dims = {'next_checks': True}
            else:
                dims = decisions(case, records, matched, answer)
                require(all(dims.values()) == outcome['grade']['accepted'], 'Context selection grade differs')
            row = {'version': version, 'lane': lane, 'case': outcome['case_id'], 'model': outcome['model_key'],
                   'profile': outcome.get('profile', ''), 'dimensions': dims, 'accepted': all(dims.values())}
            rows.append(row)
            if version == 'model-skills-v4' or (version == 'model-skills-v5' and lane.startswith('transfer-') and outcome['profile'] == 'clean-off'):
                key = (version, outcome['case_id'])
                workload = {'messages': request['messages'], 'schema': schema}
                if key in matched_workloads:
                    require(matched_workloads[key] == workload, 'Common workload differs between artifacts')
                matched_workloads[key] = workload
            if native and version == 'model-skills-v5':
                reasoning = message.get('reasoning_content') or ''
                require(sha(reasoning.encode()) == outcome['reasoning_sha256'], 'Reasoning channel identity changed')
                require(sha(message['content'].encode()) == outcome['final_sha256'], 'Final channel identity changed')
                require(sha(canonical(message).encode()) == outcome['combined_channels_sha256'], 'Combined channels changed')
                if outcome['profile'].startswith('clean-think') or outcome['profile'].startswith('clean-native'):
                    require(b'common_reaso: budget exhausted, forcing end sequence' in trace, 'Reasoning closure missing')
        summary[version] = {'requests': len(paths), 'full_input_verified': complete_inputs, 'operator_passes': operator_passes}
    require(summary['model-skills-v2']['operator_passes'] == 15, 'Operator demonstration count differs')
    scores = collections.defaultdict(lambda: [0, 0])
    for row in rows:
        if row['version'] == 'model-skills-v4' or (row['version'] == 'model-skills-v5' and row['lane'].startswith('transfer-')):
            key = row['version'] + '/' + row['model'] + '/' + row['profile']
            scores[key][0] += row['accepted']
            scores[key][1] += 1
    expected_F = {'gemma4-12b': 8, 'qwen3-4b': 4, 'qwen35-4b': 4, 'qwen35-9b': 3, 'ling3-tiny': 0}
    expected_N = {'gemma4-12b': 3, 'qwen3-4b': 4, 'qwen35-4b': 0, 'qwen35-9b': 1, 'ling3-tiny': 0}
    for model, passes in expected_F.items():
        require(scores['model-skills-v4/' + model + '/'] == [passes, 12], 'F-pack total differs')
    for model, passes in expected_N.items():
        require(scores['model-skills-v5/' + model + '/clean-off'] == [passes, 12], 'N-pack total differs')
    require(scores['model-skills-v5/ling3-tiny/clean-think-long'] == [3, 12], 'Revised Ling score differs')
    original = load(base / 'model-skills-v5/transfer-ling-long-01/protocol.json')['jobs']
    continuation = load(base / 'model-skills-v5/transfer-ling-long-02/protocol.json')['jobs']
    require(len(original) == 24 and len(continuation) == 5, 'Continuation size differs')
    require({(j['name'], j['request_sha256']) for j in continuation} == {(j['name'], j['request_sha256']) for j in original[19:]}, 'Continuation changed previously unsent requests')
    require('RuntimeError: Memory guard' in (base / 'model-skills-v5/transfer-ling-long-01/console.log').read_text(encoding='utf-8-sig'), 'Guard stop omitted')
    return {'files_verified': len(manifest['files']), 'requests': 219, 'summary': summary, 'strict_scores': dict(scores),
            'boundary': 'Saved synthetic tasks, one draw per case/profile; no model invocation, independent attestation or human-benefit proof.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('ai-followup-evidence'))
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2))
