"""Offline verification of retained requests, answers, original sources and scopes."""
import collections
import hashlib
import json
from pathlib import Path
from workbench import HERE, BASE, canonical, sha, read_case

PROJECT = Path('C:/REDACTED_PROJECT')


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def verify():
    old = load(BASE / 'source-hashes-before.json')
    changed = [name for name, expected in old.items() if sha(Path(name).read_bytes()) != expected]
    if changed:
        raise ValueError('Original inspected evidence changed: ' + str(changed))
    prior_seal = load(BASE / 'READY_FOR_REVIEW_SEAL.json')
    for relative, expected in prior_seal['files'].items():
        if sha((PROJECT / relative).read_bytes()) != expected:
            raise ValueError('Prior sealed work changed: ' + relative)
    case_seal = load(BASE / 'cases-v3' / 'PRE_EVALUATION_SEAL.json')
    for relative, expected in case_seal['files'].items():
        if sha((BASE / 'cases-v3' / relative).read_bytes()) != expected:
            raise ValueError('Sealed synthetic case changed')
    ledger = []
    totals = collections.defaultdict(lambda: {'requests': 0, 'natural_complete': 0, 'full_input_verified': 0, 'delivered': 0})
    paths = list(HERE.glob('development-*/[0-9]*-*/outcome.json'))
    paths += list((HERE / 'ling-isolated').glob('soc-development-*/[0-9]*-*/outcome.json'))
    for path in sorted(paths):
        row = load(path)
        case, _, _, _ = read_case(row['case_id'])
        response = load(path.parent / 'response.json')
        ollama = 'choices' not in response
        if ollama:
            proposal_path = path.parent.parent / 'requests' / (row['name'] + '.json')
            proposal = load(proposal_path)
            request = proposal['request']
            if sha(proposal_path.read_bytes()) != row['proposal_sha256']:
                raise ValueError('Proposal file differs')
            returned = json.loads(response['message']['content'])
        else:
            request = load(path.parent.parent / (row['name'] + '-request.json'))
            returned = json.loads(response['choices'][0]['message']['content'])
        if sha(canonical(request).encode()) != row['request_sha256']:
            raise ValueError('Request identity differs')
        if returned != row.get('model_selection', row['selection']):
            raise ValueError('Displayed model selection differs from original response')
        proof = load(path.parent / 'context-proof.json')
        raw_trace = (path.parent / 'runtime-trace.log').read_bytes()
        if sha(raw_trace) != proof['trace_sha256'] or row['full_input_verified'] != proof['verified_full_context']:
            raise ValueError('Runtime proof differs')
        if row.get('contract') == 'operator_next_check_v1':
            # Independent source oracle, rather than trusting the menu producer.
            if set(returned) != {'next_check'} or returned['next_check'] not in case['oracle']['useful_checks']:
                raise ValueError('Next check cannot resolve the source case')
            rendered = row['code_supplied_report']
            if rendered['context_source'] != 'deterministic_code' or rendered['next_check_source'] != 'validated_model_selection':
                raise ValueError('Model/code attribution changed')
            if not set(case['oracle']['required_contexts']) <= set(rendered['contexts']):
                raise ValueError('Mandatory evidence warning lost')
            records = load(BASE / 'cases-v3' / 'development' / row['case_id'] / 'locators.json')
            raw = (BASE / 'cases-v3' / 'development' / row['case_id'] / 'evidence.jsonl').read_bytes()
            refs = [m for g in rendered['citation_roster'].values() for m in g['members']]
            if {m['ref'] for m in refs} != set(records) or len(refs) != len(records):
                raise ValueError('Original membership lost or duplicated')
            for member in refs:
                source = records[member['ref']]
                line = raw[source['offset']:source['offset'] + source['length']]
                if sha(line) != member['sha256'] or member['ref'] != 'E-' + sha(line)[:16]:
                    raise ValueError('Exact original source changed')
        group = path.parent.parent.relative_to(HERE).as_posix()
        for field in totals[group]:
            totals[group][field] += 1 if field == 'requests' else int(row[field])
        ledger.append({'run': group, 'request': row['name'], 'model': row['model_key'], 'case': row['case_id'],
                       'skills': row['skills'], 'contract': row.get('contract', 'context_selection'),
                       'natural_complete': row['natural_complete'], 'full_input_verified': row['full_input_verified'],
                       'delivered': row['delivered'], 'grade': row['grade'],
                       'response_sha256': sha((path.parent / 'response.json').read_bytes()),
                       'request_sha256': row['request_sha256'], 'outcome_sha256': sha(path.read_bytes())})
    operator_rows = [r for r in ledger if r['contract'] == 'operator_next_check_v1']
    if len(operator_rows) != 15 or not all(r['delivered'] for r in operator_rows):
        raise ValueError('Expected all fifteen bounded operator demonstrations')
    if len(ledger) != 57:
        raise ValueError('Request count changed')
    artifact = load(HERE / 'ling-isolated' / 'download-verified.json')
    summary = {'requests_retained': len(ledger), 'operator_demonstrations': len(operator_rows),
               'operator_delivered': sum(r['delivered'] for r in operator_rows),
               'operator_models': sorted({r['model'] for r in operator_rows}),
               'operator_cases': sorted({r['case'] for r in operator_rows}),
               'original_evidence_hashes_unchanged': len(old), 'prior_sealed_files_unchanged': len(prior_seal['files']),
               'sealed_case_files_unchanged': len(case_seal['files']), 'totals_by_contract_run': dict(totals),
               'ling_artifact_sha256': next(r['sha256'] for r in artifact['artifacts'] if r['file'].endswith('.gguf')),
               'human_sessions': 0, 'live_tools_integrated': False, 'default_11434_invoked': False,
               'boundary': 'Three author-known source cases and permitted-menu next-check selection; no open-ended quality or human-benefit winner claim.'}
    (HERE / 'VERIFIED_LEDGER.json').write_text(canonical({'summary': summary, 'requests': ledger}) + '\n')
    print(canonical(summary))


if __name__ == '__main__':
    verify()
