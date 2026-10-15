"""Bounded sequential CPU development, admitted SOC endpoint only, no retries."""
import argparse
import concurrent.futures
import ctypes
import datetime as dt
import json
from pathlib import Path
import sys
import time
import urllib.request
from workbench import HERE, BASE, KEYS, compose, grade, canonical, sha

sys.path.insert(0, str(Path('C:/REDACTED_PROJECT/tools')))
import soc_context_guard as context_guard


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(canonical(value) + '\n')


def memory():
    class Status(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [(key, ctypes.c_ulonglong) for key in
                    ('total_phys', 'avail_phys', 'total_page', 'avail_page', 'total_virtual', 'avail_virtual', 'extended')]
    value = Status()
    value.length = ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise RuntimeError('Memory observation unavailable')
    return value.avail_phys


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('Local model redirect refused')


def api(path, payload=None, timeout=5):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    body = None if payload is None else canonical(payload).encode()
    request = urllib.request.Request('http://127.0.0.1:11435' + path, data=body,
                                     headers={'Content-Type': 'application/json'})
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise RuntimeError('Oversize response')
    return json.loads(raw)


def prepare(output, case_ids, skills_only=False, refinement=False, operator=False):
    output.mkdir(exist_ok=False)
    requests = output / 'requests'
    requests.mkdir()
    schedule = []
    for key in KEYS:
        for cid in case_ids:
            for skills in ((True,) if skills_only else (False, True)):
                name = f'{len(schedule)+1:03}-{key}-{cid}-' + ('skills' if skills else 'baseline')
                if operator:
                    from operator_contract import prepare as operator_prepare
                    proposal = operator_prepare(key, cid)
                else:
                    proposal = compose(key, cid, skills)
                if refinement:
                    extra = (HERE / 'skills-refinement-v1.md').read_bytes()
                    proposal['request']['messages'][0]['content'] += '\n\n' + extra.decode()
                    proposal['skill_hashes']['skills-refinement-v1'] = sha(extra)
                    proposal['request_sha256'] = sha(canonical(proposal['request']).encode())
                write(requests / (name + '.json'), proposal)
                schedule.append({'name': name, 'model_key': key, 'case_id': cid, 'skills': skills,
                                 'proposal_sha256': sha((requests / (name + '.json')).read_bytes()),
                                 'request_sha256': proposal['request_sha256']})
    protocol = {'created_utc': now(), 'phase': 'author_known_development', 'requests': schedule,
                'total_requests': len(schedule), 'endpoint': 'http://127.0.0.1:11435',
                'deadline_seconds': 300, 'sequential': True, 'retries': 0,
                'minimum_available_memory_bytes': 16 * 1024**3,
                'temperature_boundaries': 'Native hardware/kernel protections unchanged. No host thermal telemetry or thermal certification claimed.',
                'factors': 'Shared base contract and evidence/schema/options; only appended SOC skill procedures differ within each model/case pair.',
                'output_contract': 'Context/check selections only. Code always displays all groups and binds exact citations.',
                'refinement': refinement, 'skills_only': skills_only, 'operator_contract': operator,
                'limits': 'Development smoke test, not held-out evaluation, human benefit, model family ranking or pure throughput comparison.'}
    write(output / 'protocol.json', protocol)
    files = {p.relative_to(HERE).as_posix(): sha(p.read_bytes()) for p in HERE.glob('*.py')}
    files.update({p.relative_to(output).as_posix(): sha(p.read_bytes()) for p in requests.glob('*.json')})
    files['protocol.json'] = sha((output / 'protocol.json').read_bytes())
    write(output / 'PRE_EXECUTION_SEAL.json', {'created_utc': now(), 'files': files})
    return protocol


def execute(output):
    protocol = json.loads((output / 'protocol.json').read_text())
    if (output / 'complete.json').exists() or (output / 'execution-start.json').exists():
        raise RuntimeError('Execution is immutable; do not restart or retry')
    pause = Path('C:/REDACTED_PROJECT/private/analyst/recovery/paused.flag')
    if not pause.is_file() or pause.read_text() != 'Authorized model-skills-v2 development.':
        raise RuntimeError('Owned development maintenance boundary absent')
    owner = json.loads(Path('C:/REDACTED_PROJECT/private/analyst/model-runtime/owner.json').read_text(encoding='utf-8-sig'))
    if owner['endpoint'] != protocol['endpoint'] or not owner['cloud_disabled']:
        raise RuntimeError('Expected isolated runtime required')
    tags = {m['name']: m for m in api('/api/tags')['models']}
    if api('/api/ps').get('models'):
        raise RuntimeError('Existing CPU work takes priority')
    write(output / 'runtime-preflight.json', {'version': api('/api/version'), 'tags': tags, 'owner': owner, 'utc': now()})
    for row in protocol['requests']:
        proposal_path = output / 'requests' / (row['name'] + '.json')
        if sha(proposal_path.read_bytes()) != row['proposal_sha256']:
            raise RuntimeError('Frozen proposal changed')
        p = json.loads(proposal_path.read_text())
        if tags[p['request']['model']]['digest'] != p['manifest_digest']:
            raise RuntimeError('Installed artifact differs from pin')
    write(output / 'execution-start.json', {'utc': now(), 'planned': len(protocol['requests'])})
    all_rows = []
    for job in protocol['requests']:
        target = output / job['name']
        target.mkdir(exist_ok=False)
        p = json.loads((output / 'requests' / (job['name'] + '.json')).read_text())
        spare = memory()
        if spare < 16 * 1024**3 or api('/api/ps').get('models'):
            raise RuntimeError('Memory guard or existing runtime work stopped development')
        offset = context_guard.start(owner['stderr'])
        observed = []
        start = time.monotonic()
        response = None
        error = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(api, '/api/chat', p['request'], 300)
            while not future.done():
                if time.monotonic() - start > 305:
                    error = 'Wall deadline exceeded; stop subsequent requests'
                    break
                try:
                    observed.append({'utc': now(), 'ps': api('/api/ps'), 'available_memory_bytes': memory()})
                except Exception as exc:
                    observed.append({'utc': now(), 'observation_error': str(exc)})
                time.sleep(1)
            try:
                response = future.result(timeout=1)
            except Exception as exc:
                error = error or str(exc)
        elapsed = time.monotonic() - start
        trace = context_guard.capture(owner['stderr'], offset)
        (target / 'runtime-trace.log').write_bytes(trace)
        write(target / 'runtime-observations.json', observed)
        context = context_guard.assess(trace, context=8192, prompt_tokens=None if response is None else response.get('prompt_eval_count'))
        write(target / 'context-proof.json', context)
        if response is not None:
            write(target / 'response.json', response)
        parsed = None
        if response is not None:
            try:
                parsed = json.loads(response.get('message', {}).get('content', ''))
            except (ValueError, TypeError):
                pass
        if protocol.get('operator_contract'):
            from operator_contract import validate, report
            judgment = validate(job['case_id'], parsed)
            rendered = report(job['case_id'], parsed) if judgment['accepted'] else None
        else:
            judgment = grade(job['case_id'], parsed)
            rendered = None
        natural = response is not None and response.get('done') is True and response.get('done_reason') == 'stop' and not response.get('message', {}).get('thinking')
        actual_cpu = any(m.get('digest') == p['manifest_digest'] and m.get('size_vram') == 0
                         for o in observed for m in o.get('ps', {}).get('models', []))
        result = {**job, 'completed_utc': now(), 'elapsed_s': round(elapsed, 3),
                  'request_sent': True, 'response_retained': response is not None,
                  'natural_complete': natural, 'full_input_verified': context['verified_full_context'],
                  'cpu_residency_observed': actual_cpu, 'available_memory_preflight_bytes': spare,
                  'eval_count': None if response is None else response.get('eval_count'),
                  'prompt_eval_count': None if response is None else response.get('prompt_eval_count'),
                  'thinking_characters': 0 if response is None else len(response.get('message', {}).get('thinking', '')),
                  'selection': parsed, 'grade': judgment, 'transport_error': error}
        result['delivered'] = natural and context['verified_full_context'] and actual_cpu and judgment['accepted']
        if protocol.get('operator_contract'):
            result['contract'] = 'operator_next_check_v1'
            result['model_selection'] = parsed
            result['code_supplied_report'] = rendered
            if rendered:
                result['selection'] = {k: rendered[k] for k in ('contexts', 'next_checks')}
        write(target / 'outcome.json', result)
        all_rows.append(result)
        print(canonical({'request': job['name'], 'delivered': result['delivered'], 'elapsed_s': result['elapsed_s'], 'completed': len(all_rows)}), flush=True)
        deadline = time.monotonic() + 150
        while api('/api/ps').get('models'):
            if time.monotonic() > deadline:
                raise RuntimeError('CPU runner remains loaded; no unload or subsequent request')
            time.sleep(1)
        if error or not natural or not context['verified_full_context'] or not actual_cpu:
            write(output / 'stopped.json', {'utc': now(), 'reason': 'Delivery/runtime guard', 'completed': len(all_rows)})
            raise RuntimeError('Delivery/runtime guard stopped the batch')
    write(output / 'complete.json', {'utc': now(), 'requests': len(all_rows),
                                    'delivered': sum(r['delivered'] for r in all_rows), 'retries': 0})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare', 'execute'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', nargs='+', default=['D01', 'D02', 'D05'])
    parser.add_argument('--skills-only', action='store_true')
    parser.add_argument('--refinement', action='store_true')
    parser.add_argument('--operator', action='store_true')
    args = parser.parse_args()
    if args.output.resolve().parent != HERE:
        raise ValueError('Output must be a new workbench-local directory')
    if args.phase == 'prepare':
        if args.operator and (not args.skills_only or args.refinement):
            raise ValueError('Operator contract uses its own shared skills-only procedure')
        print(canonical({'prepared': prepare(args.output, args.cases, args.skills_only, args.refinement, args.operator)['total_requests']}))
    else:
        execute(args.output)


if __name__ == '__main__':
    main()
