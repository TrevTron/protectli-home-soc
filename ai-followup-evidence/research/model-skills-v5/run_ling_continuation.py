"""Pinned Ling 3.0 tiny in a private CPU-only child, separate from Ollama."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import socket
import secrets
import subprocess
import sys
import time
import urllib.request
from bench_long import HERE, BASE, V2, compose, grade, canonical, sha
from run_development import memory, NoRedirect, write

sys.path.insert(0, 'C:/REDACTED_PROJECT/tools')
import soc_context_guard as guard
sys.path.insert(0, str(BASE))
from audit_evidence import gguf_metadata

ROOT = V2 / 'ling-isolated'
EXPECTED = '246d67d45f5b0c7447ca0ce0bdb8b46b8a47b593c5068635dc16422c051d7be9'
TOKEN_FILE = None


def api(path, payload=None, timeout=5):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    body = None if payload is None else canonical(payload).encode()
    headers = {'Content-Type': 'application/json'}
    if TOKEN_FILE is not None:
        headers['Authorization'] = 'Bearer ' + TOKEN_FILE.read_text().strip()
    request = urllib.request.Request('http://127.0.0.1:11437' + path, data=body, headers=headers)
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise RuntimeError('Oversized Ling response')
    return json.loads(raw)


def payload(cid, skills):
    p = compose('gemma4-12b', cid, skills)
    return {'model': 'ling3-tiny', 'messages': p['request']['messages'],
            'response_format': {'type': 'json_schema', 'json_schema': {'name': 'soc_selection', 'strict': True, 'schema': p['request']['format']}},
            'max_tokens': 2048, 'temperature': 0, 'seed': 17, 'top_k': 20, 'top_p': 1,
            'min_p': 0, 'repeat_penalty': 1, 'presence_penalty': 0, 'frequency_penalty': 0,
            'cache_prompt': False, 'stream': False, 'chat_template_kwargs': {'enable_thinking': False}}


def prepare(output, continuation=False, operator=False):
    output.mkdir(exist_ok=False)
    jobs = []
    for cid in ('D01', 'D02', 'D05'):
        for skills in (False, True):
            request = payload(cid, skills)
            name = f'{len(jobs)+1:03}-ling3-tiny-{cid}-' + ('skills' if skills else 'baseline')
            write(output / (name + '-request.json'), request)
            jobs.append({'name': name, 'model_key': 'ling3-tiny', 'case_id': cid, 'skills': skills,
                         'request_sha256': sha(canonical(request).encode())})
    protocol = {'jobs': jobs, 'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                'model_file_sha256': EXPECTED, 'runtime': 'llama.cpp b11429 official Windows CPU build',
                'endpoint': 'http://127.0.0.1:11437', 'sequential': True, 'retries': 0,
                'request_deadline_seconds': 300, 'load_deadline_seconds': 120,
                'context': 8192, 'threads': 16, 'minimum_available_memory_bytes': 16*1024**3,
                'thinking': False, 'native_chat_template': True,
                'boundary': 'Separate compatibility/development lane with a different runtime. Resident Ling server; not pooled as a matched Ollama throughput comparison.'}
    if continuation:
        parent = ROOT / 'soc-development-01'
        first = json.loads((parent / '001-ling3-tiny-D01-baseline' / 'outcome.json').read_text())
        if first['natural_complete'] is not True or first['full_input_verified'] is not False:
            raise ValueError('Expected the original trace-instrumentation stop')
        protocol['jobs'] = jobs[1:]
        protocol['continuation'] = {'parent': 'soc-development-01', 'original_first_request_preserved': True,
                                    'only_never_requested_jobs': True, 'change': 'verbosity 5 for complete-input trace; local API authentication',
                                    'original_first_outcome_sha256': sha((parent / '001-ling3-tiny-D01-baseline' / 'outcome.json').read_bytes())}
        for job in protocol['jobs']:
            original = parent / (job['name'] + '-request.json')
            if json.loads(original.read_text()) != json.loads((output / (job['name'] + '-request.json')).read_text()):
                raise ValueError('Continuation request differs from original sealed proposal')
    if operator:
        from operator_contract import prepare as operator_prepare
        protocol['jobs'] = []
        for cid in ('D01', 'D02', 'D05'):
            p = operator_prepare('gemma4-12b', cid)
            request = payload(cid, True)
            request['messages'] = p['request']['messages']
            request['response_format']['json_schema']['schema'] = p['request']['format']
            name = f'{len(protocol["jobs"])+1:03}-ling3-tiny-{cid}-operator'
            write(output / (name + '-request.json'), request)
            protocol['jobs'].append({'name': name, 'model_key': 'ling3-tiny', 'case_id': cid, 'skills': True,
                                     'request_sha256': sha(canonical(request).encode())})
        protocol['operator_contract'] = True
        protocol['boundary'] += ' Product next-check menu contract; distinct from open context selection.'
    write(output / 'protocol.json', protocol)
    files = {p.name: sha(p.read_bytes()) for p in output.glob('*.json')}
    write(output / 'PRE_EXECUTION_SEAL.json', {'files': files, 'script_sha256': sha(Path(__file__).read_bytes())})
    return protocol


def execute(output):
    global TOKEN_FILE
    if (output / 'execution-start.json').exists():
        raise ValueError('No retries or resuming immutable requests')
    pause = Path('C:/REDACTED_PROJECT/private/analyst/recovery/paused.flag')
    if not pause.is_file() or pause.read_text() != 'Authorized model-skills-v2 development.':
        raise RuntimeError('Owned maintenance boundary required')
    if memory() < 16 * 1024**3:
        raise RuntimeError('Spare memory guard')
    verified = json.loads((ROOT / 'download-verified.json').read_text())
    model = ROOT / 'Ling-3.0-tiny-Q4_K_M.gguf'
    with model.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != EXPECTED:
            raise RuntimeError('Ling artifact identity changed')
    runtime = ROOT / 'runtime'
    for relative, expected in verified['runtime_files'].items():
        if sha((ROOT / relative).read_bytes()) != expected:
            raise RuntimeError('Runtime byte identity changed')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 11437))
    write(output / 'gguf-metadata.json', gguf_metadata(model))
    TOKEN_FILE = output / 'api-key.txt'
    with TOKEN_FILE.open('x') as stream:
        stream.write(secrets.token_urlsafe(32) + '\n')
    args = [str(runtime / 'llama-server.exe'), '-m', str(model), '--alias', 'ling3-tiny',
            '--host', '127.0.0.1', '--port', '11437', '-c', '8192', '-t', '16', '-tb', '16',
            '-ngl', '0', '--device', 'none', '--no-op-offload', '--fit', 'off', '-np', '1',
            '--cache-ram', '0', '--batch-size', '512', '--ubatch-size', '128', '--jinja', '--reasoning', 'auto', '--reasoning-format', 'deepseek',
            '--reasoning-budget', '3072', '--chat-template-kwargs', '{"enable_thinking":true}',
            '--timeout', '300', '--no-webui', '--no-webui-mcp-proxy', '--verbosity', '5',
            '--api-key-file', str(TOKEN_FILE), '--cors-origins', 'http://127.0.0.1:11437', '--no-cors-credentials']
    log_path = output / 'server.stderr.log'
    with (output / 'server.stdout.log').open('xb') as stdout, log_path.open('xb') as stderr:
        child = subprocess.Popen(args, cwd=runtime, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        write(output / 'execution-start.json', {'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'owned_child_pid': child.pid,
                                               'arguments': args, 'spare_memory_bytes': memory(), 'protected_11434_invoked': False})
        try:
            deadline = time.monotonic() + 120
            while True:
                if child.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Ling load did not reach ready within its bound')
                try:
                    if api('/health').get('status') == 'ok':
                        break
                except Exception:
                    pass
                time.sleep(1)
            write(output / 'native-runtime-properties.json', api('/props'))
            protocol = json.loads((output / 'protocol.json').read_text())
            completed = []
            for job in protocol['jobs']:
                if memory() < 16 * 1024**3:
                    raise RuntimeError('Memory guard')
                request = json.loads((output / (job['name'] + '-request.json')).read_text())
                if sha(canonical(request).encode()) != job['request_sha256']:
                    raise RuntimeError('Frozen request changed')
                target = output / job['name']
                target.mkdir()
                offset = guard.start(log_path)
                start = time.monotonic()
                import concurrent.futures
                available_before=memory();observed=[]
                write(target/'memory-preflight.json',{'available_memory_bytes':available_before,'minimum_bytes':16*1024**3})
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future=pool.submit(api,'/v1/chat/completions',request,300)
                    while not future.done():
                        spare=memory();observed.append({'monotonic_elapsed_s':time.monotonic()-start,'available_memory_bytes':spare})
                        if spare<16*1024**3:
                            child.terminate()
                            write(target/'memory-observations.json',observed)
                            raise RuntimeError('During-request memory guard stopped only owned Ling child; retain sent request, no retry')
                        time.sleep(1)
                    response=future.result()
                write(target/'memory-observations.json',observed)
                elapsed = time.monotonic() - start
                write(target / 'response.json', response)
                trace = guard.capture(log_path, offset)
                (target / 'runtime-trace.log').write_bytes(trace)
                prompt_tokens = response.get('usage', {}).get('prompt_tokens')
                proof = guard.assess(trace, context=8192, prompt_tokens=prompt_tokens)
                write(target / 'context-proof.json', proof)
                choice = response.get('choices', [{}])[0]
                message = choice.get('message', {})
                try:
                    answer = json.loads(message.get('content', ''))
                except (ValueError, TypeError):
                    answer = None
                natural = choice.get('finish_reason') == 'stop'
                if protocol.get('operator_contract'):
                    from operator_contract import validate, report
                    judgment = validate(job['case_id'], answer)
                    rendered = report(job['case_id'], answer) if judgment['accepted'] else None
                else:
                    judgment = grade(job['case_id'], answer)
                    rendered = None
                result = {**job, 'elapsed_s': round(elapsed, 3), 'selection': answer, 'grade': judgment,
                          'eval_count': response.get('usage', {}).get('completion_tokens'), 'prompt_eval_count': prompt_tokens,
                          'natural_complete': natural, 'full_input_verified': proof['verified_full_context'],
                          'cpu_only_configuration': True, 'thinking_characters': len(message.get('reasoning_content', '') or ''),
                          'reasoning_sha256': sha((message.get('reasoning_content', '') or '').encode()),
                          'final_sha256': sha((message.get('content', '') or '').encode()),
                          'combined_channels_sha256': sha(canonical(message).encode()),
                          'reasoning_requested': request['chat_template_kwargs']['enable_thinking'],
                          'reasoning_budget_exhaustion_observed': b'reasoning budget exhausted' in trace.lower(),
                          'model_file_sha256': EXPECTED, 'runtime': 'llama.cpp b11429 Windows CPU',
                          'actual_request': request, 'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
                result['delivered'] = natural and proof['verified_full_context'] and judgment['accepted']
                if protocol.get('operator_contract'):
                    result['contract'] = 'operator_next_check_v1'
                    result['model_selection'] = answer
                    result['code_supplied_report'] = rendered
                    if rendered:
                        result['selection'] = {k: rendered[k] for k in ('contexts', 'next_checks')}
                write(target / 'outcome.json', result)
                completed.append(result)
                print(canonical({'request': job['name'], 'delivered': result['delivered'], 'natural': natural,
                                 'full_input': proof['verified_full_context'], 'elapsed_s': result['elapsed_s']}), flush=True)
                if not natural or not proof['verified_full_context']:
                    raise RuntimeError('Ling delivery/input guard; retain original and stop subsequent requests')
            write(output / 'complete.json', {'requests': len(completed), 'delivered': sum(r['delivered'] for r in completed), 'retries': 0})
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=10)
            write(output / 'owned-child-cleanup.json', {'pid': child.pid, 'exit_code': child.returncode, 'only_owned_child_stopped': True})


if __name__ == '__main__':
    
    name = sys.argv[1]
    if name not in ('transfer-ling-long-02',):
        raise ValueError('Explicit new lane required')
    execute(HERE / name)
