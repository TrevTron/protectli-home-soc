"""Verify saved expanded-study receipts offline. Never executes study code or inference.

Hashes establish consistency within the supplied package, not trusted authorship.
Written answers require the separately recorded semantic review.
"""
import argparse
import ast
from collections import defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import soc_analyst as analyst

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_FROZEN_ASSET_BYTES = 64 * 1024 * 1024
BASE_OPTIONS = {'temperature': 0, 'seed': 17, 'num_predict': 700, 'num_ctx': 4096,
                'num_thread': 2, 'num_gpu': 0}
COMMON_OPTIONS = dict(BASE_OPTIONS, top_k=20, top_p=1, min_p=0,
                      repeat_penalty=1, presence_penalty=0, frequency_penalty=0)

def check(condition, message):
    if not condition:
        raise ValueError(message)

def digest(value):
    return hashlib.sha256(value).hexdigest()

def bounded_bytes(path):
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    check(len(raw) <= MAX_FILE_BYTES, 'Study file exceeds verification bound')
    return raw

def read(path):
    return analyst.strict_json(bounded_bytes(path).decode('utf-8-sig'))

def asset_digest(path):
    checksum = hashlib.sha256()
    total = 0
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            check(total <= MAX_FROZEN_ASSET_BYTES, 'Frozen asset exceeds verification bound')
            checksum.update(chunk)
    return checksum.hexdigest()

def inside(root, relative):
    check(isinstance(relative, str) and '\\' not in relative and ':' not in relative,
          'Manifest path must be a relative portable path')
    parts = PurePosixPath(relative)
    check(not parts.is_absolute() and all(p not in ('', '.', '..') for p in relative.split('/')),
          'Manifest path escapes study root')
    target = (root / relative).resolve()
    check(target.is_relative_to(root), 'Resolved manifest path escapes study root')
    return target

def quality(report, expected):
    matched = [r['code'] for r in expected['required_contexts']
               if any(c['code'] == r['code'] and c['group_id'] in r['any_group_ids']
                      for c in report['inferred'])]
    problems = []
    if len(matched) != len(expected['required_contexts']): problems.append('Missing required contexts')
    if any(len(report[k]) > 3 for k in ('observed', 'inferred', 'next_steps')):
        problems.append('Exceeded requested three-item list')
    claims = [analyst.canonical(c) for c in report['inferred']]
    if len(claims) != len(set(claims)): problems.append('Repeated inference')
    if any(len(c['evidence_refs']) != len(set(c['evidence_refs'])) for c in report['inferred']):
        problems.append('Repeated citation within inference')
    if not expected['empty_report'] and not report['next_steps']: problems.append('No investigation step')
    attended = {c['group_id'] for c in report['inferred'] + report['next_steps']}
    if expected['review_first_any_groups'] and not attended.intersection(expected['review_first_any_groups']):
        problems.append('Missed all review-first groups')
    return {'matched_contexts': matched,
            'required_contexts': [r['code'] for r in expected['required_contexts']],
            'complete': not problems, 'problems': problems}

def verify(root, require_complete=False):
    root = Path(root).resolve()
    manifest = read(root / 'frozen-manifest.json')
    check(isinstance(manifest, list) and 1 <= len(manifest) <= 1000, 'Invalid frozen manifest')
    frozen = set()
    for row in manifest:
        check(row['file'] not in frozen, 'Duplicate manifest entry')
        frozen.add(row['file'])
        check(asset_digest(inside(root, row['file'])) == row['sha256'],
              'Frozen file hash differs: ' + row['file'])
    check({'protocol.json', 'schedule.json'}.issubset(frozen), 'Unfrozen protocol or schedule')
    protocol = read(root / 'protocol.json')
    schedule = read(root / 'schedule.json')
    check(isinstance(schedule, list) and 1 <= len(schedule) <= 416, 'Invalid schedule bound')
    options = protocol.get('options', BASE_OPTIONS)
    check(analyst.canonical(options) in (analyst.canonical(BASE_OPTIONS), analyst.canonical(COMMON_OPTIONS)),
          'Unrecognized shared option contract')
    if 'prompts' in protocol:
        prompts = protocol['prompts']
    else:
        check('soc_analyst.py' in frozen, 'Missing frozen prompt source')
        # Extract only literal assignments. Never import or execute study code.
        assignments = ast.parse(bounded_bytes(root / 'soc_analyst.py').decode('utf-8-sig')).body
        literals = {}
        for node in assignments:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('SYSTEM', 'FREEFORM_SYSTEM'):
                value = ast.literal_eval(node.value)
                check(isinstance(value, str), 'Frozen prompt assignment must be a literal string')
                literals[node.targets[0].id] = value
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id in ('SYSTEM', 'FREEFORM_SYSTEM'):
                value = ast.literal_eval(node.value)
                check(isinstance(node.op, ast.Add) and isinstance(value, str) and node.target.id in literals,
                      'Frozen prompt extension must append a literal string')
                literals[node.target.id] += value
        prompts = {'structured': literals['SYSTEM'], 'written_analysis': literals['FREEFORM_SYSTEM']}
    check(prompts['structured'] == analyst.SYSTEM and prompts['written_analysis'] == analyst.FREEFORM_SYSTEM,
          'Prompt differs from this verifier version')
    unique_inputs = defaultdict(list)
    for case in sorted({s['case'] for s in schedule if s['phase'] != 'development'}):
        check(re.fullmatch(r'[A-Za-z0-9_-]{1,100}', case) is not None, 'Invalid case name')
        relative = 'cases/' + case + '/brief.json'
        check(relative in frozen, 'Case brief is not frozen')
        brief = read(inside(root, relative))
        model_input = analyst.model_input(brief)
        check({'cases/' + case + '/model-input.json', 'cases/' + case + '/schema.json'}.issubset(frozen),
              'Case input or schema is not frozen')
        check(model_input == read(inside(root, 'cases/' + case + '/model-input.json')),
              'Saved model input differs from brief')
        check(analyst.schema(brief) == read(inside(root, 'cases/' + case + '/schema.json')),
              'Saved schema differs from brief')
        unique_inputs[digest(analyst.canonical(model_input).encode())].append(case)
    rows = []
    returned = 0
    written_storage = []
    for number, item in enumerate(schedule, 1):
        check(item['model'] in analyst.EVALUATION_MODELS, 'Unadmitted model')
        check(type(item['structured']) is bool and item['deadline_seconds'] in (120, 300),
              'Invalid request contract')
        check(item['deadline_seconds'] == (120 if item['structured'] else 300),
              'Deadline differs from structured/written lane')
        check(item['phase'] in ('development', 'production_contract', 'written_analysis',
                               'simulation_holdout', 'normalized_control'), 'Invalid phase')
        check(re.fullmatch(r'[A-Za-z0-9_-]{1,100}', item['case']) is not None, 'Invalid case name')
        target = inside(root, f'execution/{number:03d}')
        if not (target / 'outcome.json').exists():
            continue
        outcome = read(target / 'outcome.json')
        check(outcome['number'] == number and all(outcome[k] == v for k, v in item.items()),
              'Outcome differs from scheduled request')
        folder = ('development' if item['phase'] == 'development' else 'cases') + '/' + item['case']
        brief_relative = folder + '/brief.json'
        check(brief_relative in frozen, 'Completed brief is not frozen')
        raw_brief = bounded_bytes(inside(root, brief_relative))
        check(digest(raw_brief) == outcome['brief_sha256'], 'Outcome brief hash differs')
        brief = analyst.strict_json(raw_brief.decode('utf-8-sig'))
        check(outcome['status'] in ('delivered', 'withheld'), 'Invalid outcome status')
        if (target / 'metadata.json').exists():
            metadata = read(target / 'metadata.json')
            response = read(target / 'response.json')
            check(metadata['model'] == response['model'] == item['model'], 'Model identity differs')
            check(metadata['endpoint'] == 'http://127.0.0.1:11435', 'Unexpected inference endpoint')
            check(analyst.canonical(metadata['options']) == analyst.canonical(options),
                  'Recorded options differ from shared contract')
            system = analyst.SYSTEM if item['structured'] else analyst.FREEFORM_SYSTEM
            schema = analyst.schema(brief) if item['structured'] else None
            payload = {'model': item['model'], 'stream': False, 'think': False, 'keep_alive': 0,
                       'options': options, 'messages': [{'role': 'system', 'content': system},
                       {'role': 'user', 'content': analyst.canonical(analyst.model_input(brief))}]}
            if item['structured']: payload['format'] = schema
            check(digest(analyst.canonical(payload).encode()) == metadata['request_sha256'],
                  'Reconstructed request hash differs')
            check(digest(system.encode()) == metadata['system_prompt_sha256'], 'System hash differs')
            check(metadata['schema_sha256'] == (digest(analyst.canonical(schema).encode()) if schema else None),
                  'Schema hash differs')
            content = response.get('message', {}).get('content', '')
            thinking = response.get('message', {}).get('thinking', '')
            check(digest(content.encode()) == outcome['content_sha256'], 'Response content hash differs')
            check(metadata['content_characters'] == len(content) and
                  metadata['thinking_characters'] == len(thinking), 'Response channel length differs')
            check(type(metadata['eval_count']) is int and 0 <= metadata['eval_count'] <= 700 and
                  metadata['eval_count'] == response['eval_count'] == outcome['eval_count'],
                  'Generated token count differs or exceeds bound')
            check(metadata['prompt_eval_count'] == response['prompt_eval_count'] == outcome['prompt_eval_count'],
                  'Prompt token count differs')
            check(metadata['done_reason'] == response['done_reason'] == outcome['done_reason'],
                  'Stop reason differs')
            if outcome['status'] == 'delivered':
                check(response['done'] is True and response['done_reason'] == 'stop' and not thinking,
                      'Delivered response incomplete, capped or has thinking content')
                if item['structured']:
                    report = analyst.validate(analyst.strict_json(content), brief)
                    check(report == read(target / 'accepted-report.json'), 'Accepted report differs')
                    if item['phase'] != 'development':
                        expected_relative = folder + '/expected.json'
                        check(expected_relative in frozen, 'Utility oracle is not frozen')
                        check(quality(report, read(inside(root, expected_relative))) == outcome['quality'],
                              'Frozen utility score differs')
                else:
                    saved = bounded_bytes(target / 'analysis.txt')
                    # Python's default text writer expands LF to CRLF on Windows.
                    # Admit only the literal response or that exact whole-file
                    # translation, never arbitrary whitespace/word normalization.
                    storage = ('literal' if saved == content.encode('utf-8') else
                               'windows_text' if saved == content.replace('\n', '\r\n').encode('utf-8') else None)
                    check(storage is not None,
                          'Saved written analysis differs')
                    written_storage.append({'number': number, 'file_sha256': digest(saved),
                                            'newline_storage': storage})
            returned += 1
        else:
            check(outcome['status'] == 'withheld' and (target / 'error.json').exists(),
                  'Missing response/error receipt')
        rows.append(outcome)
    check(not require_complete or len(rows) == len(schedule), 'Study is incomplete')
    return {'status': 'complete_receipts_verified' if len(rows) == len(schedule) else 'partial_receipts_verified',
            'planned': len(schedule), 'completed': len(rows), 'returned_request_hashes_verified': returned,
            'frozen_files_verified': len(frozen), 'source_cases': sum(map(len, unique_inputs.values())),
            'unique_model_inputs': len(unique_inputs),
            'duplicate_input_groups': [v for v in unique_inputs.values() if len(v) > 1],
            'delivered': sum(r['status'] == 'delivered' for r in rows),
            'withheld': sum(r['status'] == 'withheld' for r in rows),
            'written_returned_needing_semantic_review': sum(r['status'] == 'delivered' and not r['structured'] for r in rows),
            'written_analysis_storage': written_storage,
            'boundary': 'Offline consistency and frozen utility verification; not trusted provenance, independent semantic accuracy or a model recommendation.'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--require-complete', action='store_true')
    parser.add_argument('--output', type=Path, help='New audit file; never replaces an existing result')
    args = parser.parse_args()
    result = verify(args.study, args.require_complete)
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
