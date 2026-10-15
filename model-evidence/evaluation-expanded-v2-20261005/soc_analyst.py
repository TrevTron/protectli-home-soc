"""Evidence-grounded local SOC analyst. Reads evidence; never edits sensor policy.

Facts and source locators are deterministic. A local model chooses typed findings;
an independent validator rejects unsupported values, references and specificity.
This is claim grounding, not proof that an inference is true or useful.
"""
from __future__ import annotations

import argparse
import base64
import collections
import ctypes
import datetime as dt
import hashlib
import hmac
import html
import ipaddress
import json
import math
import pathlib
import re
import secrets
import time
import urllib.parse
import urllib.request
import soc_evidence

UTC = dt.timezone.utc
DISPLAY_SCRIPT = """document.querySelectorAll('time[data-pacific]').forEach(function(t){var d=new Date(t.dateTime);if(!Number.isNaN(d.getTime())){t.textContent=new Intl.DateTimeFormat('en-US',{timeZone:'America/Los_Angeles',dateStyle:'medium',timeStyle:'long'}).format(d);}});"""
DISPLAY_SCRIPT_HASH = base64.b64encode(hashlib.sha256(DISPLAY_SCRIPT.encode()).digest()).decode()
CONTENT_SECURITY_POLICY = "default-src 'none'; style-src 'unsafe-inline'; script-src 'sha256-"+DISPLAY_SCRIPT_HASH+"'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
MAX_LINE = 65536
MAX_MODEL_RESPONSE = 200_000
OBSERVED_FIELDS = ('count', 'sid', 'action', 'severity', 'protocol', 'prior_count', 'change')
STUN_SIDS = {2016149, 2016150, 2033078}
KNOWN_RULES = {
    2100498: 'UID response text signature. A fixture can trigger this; intent is not established.',
    2016149: 'STUN binding request signature.',
    2016150: 'STUN binding response signature.',
    2033078: 'STUN request on a non-standard high port signature.',
    2031071: 'Microsoft connectivity-test signature.',
    2071648: 'Tailscale control-plane TLS SNI signature. The installed rule was inspected; this is not process attribution.',
}
INFERENCES = {
    'rule_match_not_intrusion_proof': 'A signature match is a starting point for review, not proof of an intrusion.',
    'stun_may_be_normal': 'STUN is used for NAT traversal. Conferencing, games or other applications may explain it; process identity and intent are not established.',
    'uid_fixture_possible': 'This rule can match a harmless UID-response fixture. Verify the exact request against the owned test receipt before treating it as expected.',
    'sensor_reported_block': 'Suricata reported a blocked event. Confirm the associated client outcome; this does not prove every related request failed.',
    'change_needs_context': 'This group appeared or increased in the observed comparison windows. Confirm application activity and collection coverage before interpreting the change.',
    'tailscale_control_possible': 'The inspected rule matches a Tailscale control-plane TLS server name. An owned Tailscale client may explain it; a server-name match does not establish process identity or intent.',
}
UNKNOWN_TOPICS = {
    'intent': 'Intent and whether an intrusion occurred are not established by these alerts.',
    'process_identity': 'The client process responsible is not present in the network alert.',
    'payload': 'Payload content and encrypted application content are not supplied to this analyst.',
    'complete_visibility': 'UDP receipt and a bounded snapshot cannot prove complete traffic or log capture.',
}
NEXT_STEPS = {
    'inspect_event': 'Inspect the cited original event and exact connection.',
    'check_client_process': 'Compare the event time with applications on the owned client.',
    'compare_baseline': 'Review the prior-window comparison and an operator-reviewed baseline.',
    'check_rule': 'Read the installed rule and its metadata before considering a policy change.',
    'check_visibility': 'Check receiver freshness, retention, packet/stream discards and snapshot coverage.',
}


class Rejected(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError('Invalid timestamp')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone required')
    return parsed.astimezone(UTC)


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Rejected('Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Rejected('Nonfinite JSON value')))


def eve_from_record(record):
    if not isinstance(record, dict) or record.get('app') != 'suricata':
        return None
    # The retained original raw message wins over any earlier derived eve cache.
    match = re.search(r'(\{.*\})\s*$', record.get('raw', ''), re.S)
    if not match:
        return None
    value = strict_json(match[1])
    return value if isinstance(value, dict) and value.get('event_type') == 'alert' else None


def alias(address, salt, client):
    address = str(ipaddress.ip_address(address))
    if address == client:
        return 'owned-client'
    return 'endpoint-' + hmac.new(salt, address.encode(), hashlib.sha256).hexdigest()[:10]


def snapshot(path, max_bytes):
    """Read a fixed byte boundary despite append activity; preserve locators."""
    with soc_evidence.open_evidence(path) as stream:
        stream.seek(0, 2)
        end = stream.tell()
        start = max(0, end - max_bytes)
        stream.seek(start)
        if start:
            stream.readline()  # the boundary may be inside a record
        start = stream.tell()
        data = stream.read(end - start)
    if data and not data.endswith(b'\n'):
        # A concurrent partial append is deferred to the next snapshot.
        data = data[:data.rfind(b'\n') + 1] if b'\n' in data else b''
    return start, data, end


def build_brief(path, client, salt, *, now=None, minutes=15, max_bytes=16*1024*1024, max_groups=16):
    client = str(ipaddress.ip_address(client))
    now = now or dt.datetime.now(UTC)
    if now.tzinfo is None or not 1 <= minutes <= 1440 or not 1 <= max_groups <= 32:
        raise ValueError('Bounded window and timezone required')
    current_start = now - dt.timedelta(minutes=minutes)
    previous_start = current_start - dt.timedelta(minutes=minutes)
    offset, data, source_end = snapshot(path, max_bytes)
    initial_offset = offset
    groups = {}
    source_refs = {}
    apps = collections.Counter()
    malformed = invalid_alerts = future_records = current_records = previous_records = out_of_scope = 0
    earliest = latest = None
    for line in data.splitlines(keepends=True):
        position = offset
        offset += len(line)
        if len(line) > MAX_LINE:
            malformed += 1
            continue
        try:
            record = strict_json(line.decode('utf-8'))
            receipt = timestamp(record['received_utc'])
        except (ValueError, KeyError, TypeError, UnicodeError):
            malformed += 1
            continue
        earliest = receipt if earliest is None else min(earliest, receipt)
        latest = receipt if latest is None else max(latest, receipt)
        if receipt > now + dt.timedelta(seconds=2):
            future_records += 1
            continue
        if not previous_start <= receipt <= now:
            continue
        current = receipt >= current_start
        if current:
            current_records += 1
            app = record.get('app', 'unknown')
            apps[app if isinstance(app, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,32}', app) else 'unknown'] += 1
        else:
            previous_records += 1
        try:
            eve = eve_from_record(record)
            if eve is None:
                continue
            alert = eve['alert']
            sid, severity = alert['signature_id'], alert.get('severity')
            action, protocol = alert['action'], eve.get('proto')
            if type(sid) is not int or not 1 <= sid <= 2**32-1:
                raise ValueError('Invalid SID')
            if severity is not None and (type(severity) is not int or severity not in (1, 2, 3)):
                raise ValueError('Invalid severity')
            if action not in ('allowed', 'blocked') or protocol not in ('TCP', 'UDP', 'ICMP', 'ICMPv6'):
                raise ValueError('Unknown action/protocol')
            src, dest = str(ipaddress.ip_address(eve['src_ip'])), str(ipaddress.ip_address(eve['dest_ip']))
            if client not in (src, dest):
                out_of_scope += 1
                continue
            endpoints = (alias(src, salt, client), alias(dest, salt, client))
        except (ValueError, KeyError, TypeError, AttributeError):
            invalid_alerts += 1
            continue
        key = (sid, action, severity, protocol, *endpoints)
        gid = 'G-' + digest(canonical(key).encode())[:12]
        group = groups.setdefault(gid, {'id': gid, 'sid': sid, 'action': action,
                                       'severity': severity, 'protocol': protocol,
                                       'source_alias': endpoints[0], 'destination_alias': endpoints[1],
                                       'count': 0, 'prior_count': 0, 'evidence_refs': [],
                                       'first_received_utc': None, 'last_received_utc': None})
        if not current:
            group['prior_count'] += 1
            continue
        group['count'] += 1
        group['first_received_utc'] = receipt.isoformat() if group['first_received_utc'] is None else min(group['first_received_utc'], receipt.isoformat())
        group['last_received_utc'] = receipt.isoformat() if group['last_received_utc'] is None else max(group['last_received_utc'], receipt.isoformat())
        ref = 'E-' + digest(line)[:16]
        source_refs[ref] = {'byte_offset': position, 'byte_length': len(line), 'sha256': digest(line),
                            'received_utc': receipt.isoformat()}
        if len(group['evidence_refs']) < 2 and ref not in group['evidence_refs']:
            group['evidence_refs'].append(ref)
        elif ref not in group['evidence_refs']:
            group['evidence_refs'] = group['evidence_refs'][:2] + [ref]
    comparison_complete = earliest is not None and earliest <= previous_start
    comparison_complete = comparison_complete and not malformed and not invalid_alerts and not future_records
    selected = [g for g in groups.values() if g['count']]
    for group in selected:
        group['priority_floor'] = 'review_first' if group['action'] == 'blocked' or group['severity'] == 1 else 'review'
        group['change'] = ('comparison_unknown' if not comparison_complete else
                           'new_in_observed_windows' if group['prior_count'] == 0 else
                           'increased' if group['count'] > group['prior_count'] else
                           'decreased' if group['count'] < group['prior_count'] else 'unchanged')
    selected.sort(key=lambda g: (g['priority_floor'] != 'review_first', g['severity'] or 9, -g['count'], g['id']))
    total_groups = len(selected)
    selected = selected[:max_groups]
    kept_refs = {ref for g in selected for ref in g['evidence_refs']}
    brief = {'schema_version': 1, 'generated_utc': now.isoformat(),
             'window': {'minutes': minutes, 'start_utc': current_start.isoformat(), 'end_utc': now.isoformat()},
             'coverage': {'snapshot_start_byte': initial_offset, 'snapshot_end_byte': initial_offset+len(data),
                          'source_size_at_start': source_end, 'snapshot_sha256': digest(data),
                          'tail_clipped': initial_offset > 0, 'comparison_complete_for_retained_records': comparison_complete,
                          'malformed_records': malformed, 'invalid_alerts': invalid_alerts,
                          'future_records': future_records, 'out_of_scope_alerts': out_of_scope,
                          'current_records': current_records, 'prior_records': previous_records,
                          'last_receipt_utc': latest.isoformat() if latest else None,
                          'receiver_age_seconds': max(0, (now-latest).total_seconds()) if latest else None,
                          'total_current_groups': total_groups, 'omitted_groups': total_groups-len(selected),
                          'complete_delivery_proven': False},
             'application_counts': dict(sorted(apps.items())), 'groups': selected}
    # Only numeric/enumerated fields and opaque aliases reach the model. Do not
    # include raw data, signatures, hostnames, URLs, payloads or source paths.
    return brief, {ref: source_refs[ref] for ref in kept_refs}


def eligible(group):
    codes = ['rule_match_not_intrusion_proof']
    if group['sid'] in STUN_SIDS:
        codes.append('stun_may_be_normal')
    if group['sid'] == 2100498:
        codes.append('uid_fixture_possible')
    if group['sid'] == 2071648:
        codes.append('tailscale_control_possible')
    if group['action'] == 'blocked':
        codes.append('sensor_reported_block')
    if group['change'] in ('new_in_observed_windows', 'increased'):
        codes.append('change_needs_context')
    return codes


def schema(brief=None):
    claim = {'type': 'object', 'additionalProperties': False, 'required': ['type', 'group_id', 'field', 'value'],
             'properties': {'type': {'const': 'observed'}, 'group_id': {'type': 'string'},
                            'field': {'enum': list(OBSERVED_FIELDS)}, 'value': {'type': ['integer', 'string', 'null']}}}
    inference = {'type': 'object', 'additionalProperties': False, 'required': ['type', 'code', 'group_id', 'evidence_refs'],
                 'properties': {'type': {'const': 'inferred'}, 'code': {'enum': list(INFERENCES)},
                                'group_id': {'type': 'string'}, 'evidence_refs': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 3}}}
    unknown = {'type': 'object', 'additionalProperties': False, 'required': ['type', 'topic'],
               'properties': {'type': {'const': 'unknown'}, 'topic': {'enum': list(UNKNOWN_TOPICS)}}}
    step = {'type': 'object', 'additionalProperties': False, 'required': ['group_id', 'action'],
            'properties': {'group_id': {'type': 'string'}, 'action': {'enum': list(NEXT_STEPS)}}}
    result = {'type': 'object', 'additionalProperties': False,
            'required': ['observed', 'inferred', 'unknown', 'next_steps'],
            'properties': {'observed': {'type': 'array', 'items': claim, 'maxItems': 12},
                           'inferred': {'type': 'array', 'items': inference, 'maxItems': 6},
                           'unknown': {'type': 'array', 'items': unknown, 'minItems': 2, 'maxItems': 4,
                                       'enum': [[{'type': 'unknown', 'topic': topic} for topic in topics]
                                                for topics in (('intent', 'complete_visibility'),
                                                               ('intent', 'complete_visibility', 'process_identity'),
                                                               ('intent', 'complete_visibility', 'payload'),
                                                               ('intent', 'complete_visibility', 'process_identity', 'payload'))]},
                           'next_steps': {'type': 'array', 'items': step, 'maxItems': 6}}}
    if brief is not None:
        groups = brief['groups']
        if not groups:
            for name in ('observed', 'inferred', 'next_steps'):
                result['properties'][name]['maxItems'] = 0
        else:
            # Bind grammar alternatives to each real group. The independent
            # validator still checks every returned claim, even if a runtime
            # ignores a schema keyword. No repair of fabricated references.
            variants = []
            for group in groups:
                variants.append({'type': 'object', 'additionalProperties': False,
                    'required': ['type', 'code', 'group_id', 'evidence_refs'],
                    'properties': {'type': {'const': 'inferred'}, 'group_id': {'const': group['id']},
                        'code': {'enum': eligible(group)},
                        'evidence_refs': {'type': 'array', 'minItems': 1, 'maxItems': 3,
                                          'items': {'enum': sorted(set(group['evidence_refs']))}}}})
            result['properties']['inferred']['items'] = {'oneOf': variants}
            result['properties']['inferred']['minItems'] = 1
            # Development exposed a numeric SID returned as a string. Bind
            # each complete observation to the exact typed source field;
            # generation grammar never replaces independent validation.
            result['properties']['observed']['items'] = {'enum': [
                {'type': 'observed', 'group_id': group['id'], 'field': field, 'value': group[field]}
                for group in groups for field in OBSERVED_FIELDS]}
            for item in (claim, step):
                item['properties']['group_id'] = {'enum': [group['id'] for group in groups]}
    return result


def model_input(brief):
    groups = [{k: v for k, v in g.items() if k not in ('first_received_utc', 'last_received_utc')} for g in brief['groups']]
    available_codes = sorted({code for g in brief['groups'] for code in eligible(g)})
    return {'window_minutes': brief['window']['minutes'],
            'visibility': {'complete_delivery_proven': False,
                           'comparison_complete': brief['coverage']['comparison_complete_for_retained_records'],
                           'omitted_groups': brief['coverage']['omitted_groups']},
            'groups': groups,
            'eligible_inferences': {g['id']: eligible(g) for g in brief['groups']},
            'interpretation_catalog': {code: INFERENCES[code] for code in available_codes}}


SYSTEM = ('You are a local network evidence analyst. Return only the requested JSON. '
          'Code owns facts; never invent values or citations. An observed claim must exactly copy '
          'a supplied group field. Choose a few helpful inferred codes from eligible_inferences '
          'and cite that group\'s evidence_refs. Always include unknown intent and complete_visibility. '
          'Choose read-only next_steps for the most useful findings. A rule match is not proof of '
          'malice, an allowed event is not proof of safety, and blocked is a sensor action, not a '
          'confirmed client outcome. No diagnoses, country attribution, process names, raw payload '
          'claims, or firewall changes. Output at most 3 observations, 3 inferences and 3 next steps.')
SYSTEM += (' Prioritize a reported block and any specific supplied rule context (STUN, UID fixture, '
           'Tailscale) before general novelty commentary. Do not repeat an inference or citation. '
           'Use interpretation_catalog meanings; they are possibilities, never proof of an application.')
SYSTEM += (' The unknown array must start with {"type":"unknown","topic":"intent"} and '
           '{"type":"unknown","topic":"complete_visibility"}, in that order. '
           'Optionally append process_identity and/or payload. Keep the report concise.')

FREEFORM_SYSTEM = ('You are a local network evidence analyst. Write a concise first-pass report: '
                   'observed facts, possible explanations, unknowns, and read-only next review steps. '
                   'Cite the supplied group IDs and evidence_refs. Do not invent counts, process names, '
                   'payload evidence, attribution, intent or client outcomes. A signature match is not '
                   'proof of intrusion, and allowed is not proof of safety. Blocked is a sensor action, '
                   'not confirmation that every request failed. The supplied eligible_inferences '
                   'describe possible interpretations, not verdicts. Explicitly acknowledge unknown '
                   'intent and incomplete visibility. Do not recommend firewall changes. No JSON is required.')


def available_memory():
    if not hasattr(ctypes, 'windll'):
        return None
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)]+[(name, ctypes.c_ulonglong) for name in
                    ('total_physical', 'available_physical', 'total_pagefile', 'available_pagefile', 'total_virtual', 'available_virtual', 'available_extended')]
    value = Memory()
    value.length = ctypes.sizeof(Memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise OSError('Memory preflight failed')
    return value.available_physical


def validate(report, brief):
    def keys(value, expected):
        if not isinstance(value, dict) or set(value) != set(expected):
            raise Rejected('Unexpected or missing fields')
    keys(report, ('observed', 'inferred', 'unknown', 'next_steps'))
    limits = {'observed': 12, 'inferred': 6, 'unknown': 4, 'next_steps': 6}
    for key, limit in limits.items():
        if not isinstance(report[key], list) or len(report[key]) > limit:
            raise Rejected('Invalid bounded claim list')
    groups = {g['id']: g for g in brief['groups']}
    for claim in report['observed']:
        keys(claim, ('type', 'group_id', 'field', 'value'))
        if claim['type'] != 'observed' or claim['group_id'] not in groups or claim['field'] not in OBSERVED_FIELDS:
            raise Rejected('Unsupported observation')
        expected = groups[claim['group_id']][claim['field']]
        if type(claim['value']) is not type(expected) or claim['value'] != expected:
            raise Rejected('Observed value does not match evidence')
    for claim in report['inferred']:
        keys(claim, ('type', 'code', 'group_id', 'evidence_refs'))
        if claim['type'] != 'inferred' or claim['group_id'] not in groups:
            raise Rejected('Unknown inferred group')
        group = groups[claim['group_id']]
        if claim['code'] not in eligible(group):
            raise Rejected('Inference not supported for this group')
        refs = claim['evidence_refs']
        if not isinstance(refs, list) or not 1 <= len(refs) <= 3 or any(not isinstance(ref, str) or ref not in group['evidence_refs'] for ref in refs):
            raise Rejected('Unsupported evidence reference')
    topics = set()
    for claim in report['unknown']:
        keys(claim, ('type', 'topic'))
        if claim['type'] != 'unknown' or claim['topic'] not in UNKNOWN_TOPICS:
            raise Rejected('Unsupported unknown field')
        topics.add(claim['topic'])
    if not {'intent', 'complete_visibility'} <= topics:
        raise Rejected('Required unknowns absent')
    for step in report['next_steps']:
        keys(step, ('group_id', 'action'))
        if step['group_id'] not in groups or step['action'] not in NEXT_STEPS:
            raise Rejected('Unsupported investigation step')
    if groups and not report['inferred']:
        raise Rejected('No useful inference selected')
    return report


def local_endpoint(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('Use an explicit loopback model endpoint, optionally through a verified SSH forward')
    if parsed.port == 11434:
        raise ValueError('The existing port 11434 model runtime is protected in this project')
    return value.rstrip('/')


EVALUATION_MODELS = frozenset(('qwen3:4b-instruct', 'qwen3.5:4b', 'qwen3.5:9b', 'gemma4:12b-it-qat'))


def request_model(brief, endpoint, model='qwen3:4b-instruct', timeout=120, *, structured=True, evaluation=False):
    endpoint = local_endpoint(endpoint)
    if model != 'qwen3:4b-instruct' and not (evaluation and model in EVALUATION_MODELS):
        raise ValueError('Only the separate tested analyst model is admitted; do not invoke the fine-tuning model')
    memory = available_memory()
    if memory is not None and memory < 16*1024**3:
        raise Rejected('Insufficient spare memory for an isolated analyst run; existing work takes priority')
    system = SYSTEM if structured else FREEFORM_SYSTEM
    payload = {'model': model, 'stream': False, 'think': False, 'keep_alive': 0,
               'options': {'temperature': 0, 'seed': 17, 'num_predict': 700, 'num_ctx': 4096, 'num_thread': 2, 'num_gpu': 0},
               'messages': [{'role': 'system', 'content': system},
                            {'role': 'user', 'content': canonical(model_input(brief))}]}
    output_schema = schema(brief) if structured else None
    if structured:
        payload['format'] = output_schema
    body = canonical(payload).encode()
    request = urllib.request.Request(endpoint+'/api/chat', data=body, headers={'Content-Type': 'application/json'})
    # Disable ambient proxy routing for local evidence. No remote/redirect endpoint.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise Rejected('Model redirect refused')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    started = time.monotonic()
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(MAX_MODEL_RESPONSE+1)
    if len(raw) > MAX_MODEL_RESPONSE:
        raise Rejected('Model response oversized')
    result = strict_json(raw.decode())
    metadata = {'request_sha256': digest(body), 'system_prompt_sha256': digest(system.encode()),
                'schema_sha256': digest(canonical(output_schema).encode()) if structured else None, 'model': model, 'endpoint': endpoint,
                'elapsed_s': time.monotonic()-started, 'structured': structured, 'evaluation': evaluation,
                'thinking_requested': False, 'thinking_characters': len(result.get('message', {}).get('thinking', '')),
                'content_characters': len(result.get('message', {}).get('content', '')),
                'options': payload['options'], 'preflight_available_bytes': memory, 'done': result.get('done'), 'done_reason': result.get('done_reason'),
                'eval_count': result.get('eval_count'), 'prompt_eval_count': result.get('prompt_eval_count'),
                'eval_duration_ns': result.get('eval_duration'), 'total_duration_ns': result.get('total_duration')}
    return result, metadata


def render(brief, report, status, run_name=None):
    esc = lambda value: html.escape(str(value), quote=True)
    if run_name is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', run_name):
        raise ValueError('Invalid run name')
    def evidence_link(ref):
        return '<a href="/evidence/'+(run_name+'/' if run_name else '')+esc(ref)+'">'+esc(ref)+'</a>'
    def pacific(value):
        return '<time data-pacific datetime="'+esc(value)+'">'+esc(value)+' (UTC fallback)</time>'
    rows = []
    for group in brief['groups']:
        label = KNOWN_RULES.get(group['sid'], 'Rule description not vetted by the analyst; inspect the installed signature.')
        rows.append('<tr>'+''.join('<td>'+esc(value)+'</td>' for value in (
            group['id'], group['priority_floor'], group['sid'], label, group['action'],
            group['count'], group['prior_count'], group['change'],
            group['source_alias']+' → '+group['destination_alias']))+
                    '<td>'+', '.join(evidence_link(ref) for ref in group['evidence_refs'])+'</td></tr>')
    findings = []
    if report:
        seen_findings = set()
        for claim in report['inferred']:
            key = (claim['group_id'], claim['code'])
            if key in seen_findings:
                continue
            seen_findings.add(key)
            findings.append('<li><b>Possible interpretation:</b> '+esc(INFERENCES[claim['code']])+' ['+esc(claim['group_id'])+'; '+', '.join(evidence_link(ref) for ref in dict.fromkeys(claim['evidence_refs']))+']</li>')
        for claim in report['unknown']:
            findings.append('<li><b>Unknown</b> '+esc(UNKNOWN_TOPICS[claim['topic']])+'</li>')
        for step in report['next_steps']:
            findings.append('<li><b>Next review</b> '+esc(NEXT_STEPS[step['action']])+' ['+esc(step['group_id'])+']</li>')
    coverage = brief['coverage']
    freshness = 'No received records at snapshot time' if coverage['receiver_age_seconds'] is None else f"At snapshot time: {coverage['receiver_age_seconds']:.1f} seconds since last received log"
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="'+esc(CONTENT_SECURITY_POLICY)+'">'
            '<title>Protectli local analyst</title><style>body{font:16px system-ui;background:#101721;color:#e7eef6;margin:25px auto;padding:0 24px;max-width:1400px}a{color:#8fcaff}table{border-collapse:collapse;width:100%}.table-wrap{overflow-x:auto}td,th{border-bottom:1px solid #4a617b;padding:9px;text-align:left;vertical-align:top}small{color:#b5c5d6}li{margin:12px 0}.status{padding:16px;background:#26364b}code,pre{overflow-wrap:anywhere;white-space:pre-wrap}.cards{display:flex;flex-wrap:wrap;gap:16px}.cards p{background:#1c2938;padding:16px;flex:1;min-width:170px}.cards b{font-size:26px;display:block}</style>'
            '<h1>Protectli local evidence analyst</h1><p class="status">'+esc(status)+'</p>'
            '<p>Generated '+pacific(brief['generated_utc'])+' · Pacific display; original timestamps retained. <a href="http://127.0.0.1:8765/">Original log dashboard</a></p>'
            '<p>Current window: '+pacific(brief['window']['start_utc'])+' to '+pacific(brief['window']['end_utc'])+'. Compared with the preceding '+esc(brief['window']['minutes'])+' minutes.</p>'
            '<div class="cards"><p><b>'+esc(sum(g['count'] for g in brief['groups']))+'</b>Alert events in displayed groups</p><p><b>'+esc(sum(g['priority_floor']=='review_first' for g in brief['groups']))+'</b>Groups to review first</p><p><b>'+esc(coverage['omitted_groups'])+'</b>Groups beyond this report limit</p></div>'
            '<p>'+esc(freshness)+'. Comparison '+('available for retained records' if coverage['comparison_complete_for_retained_records'] else 'incomplete; novelty is unknown')+'. UDP logging cannot prove complete delivery.</p>'
            '<p>Counts and sensor actions are measured facts. Analyst interpretations require human review. No autonomous firewall changes.</p>'
            '<h2>Evidence and changes</h2><div class="table-wrap"><table><thead><tr>'+''.join('<th>'+v+'</th>' for v in ('Group','Review order','SID','Rule context','Sensor action','Count','Prior count','Change','Endpoint aliases','Original evidence refs'))+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
            '<h2>Analyst findings</h2><ul>'+(''.join(findings) or '<li>No accepted model findings for this snapshot. The measured evidence remains available above.</li>')+'</ul><h2>Collection limits</h2><details><summary>Snapshot coverage and source hashes</summary><pre>'+esc(json.dumps(coverage, indent=2))+'</pre></details>'
            '<p><small>Allowed does not prove safety. Blocked does not prove the client outcome. Process identity, payload and intent remain unknown. Evidence links recheck the retained original record hash.</small></p><script>'+DISPLAY_SCRIPT+'</script></html>')


def write_json(path, value):
    pathlib.Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=True)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=pathlib.Path, required=True)
    parser.add_argument('--client', required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True, help='Private new run directory')
    parser.add_argument('--salt-file', type=pathlib.Path, required=True)
    parser.add_argument('--minutes', type=int, default=15)
    parser.add_argument('--as-of', type=timestamp)
    parser.add_argument('--endpoint', default='http://127.0.0.1:11435')
    parser.add_argument('--no-model', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    args.salt_file.parent.mkdir(parents=True, exist_ok=True)
    if not args.salt_file.exists():
        with args.salt_file.open('xb') as stream:
            stream.write(secrets.token_bytes(32))
    salt = args.salt_file.read_bytes()
    if len(salt) != 32:
        raise ValueError('Alias key must contain exactly 32 bytes')
    brief, sources = build_brief(args.log, args.client, salt, now=args.as_of, minutes=args.minutes)
    write_json(args.output/'brief.json', brief)
    write_json(args.output/'sources.json', {'source_path': str(args.log.resolve()), 'sources': sources})
    report = None
    status = 'Deterministic evidence only. No model invoked.'
    success = False
    if not args.no_model:
        try:
            result, metadata = request_model(brief, args.endpoint)
            write_json(args.output/'model-response.json', result)
            write_json(args.output/'model-metadata.json', metadata)
            if result.get('done') is not True or result.get('done_reason') != 'stop':
                raise Rejected('Model did not complete normally; capped output is not delivered')
            message = result.get('message', {})
            report = validate(strict_json(message.get('content', '')), brief)
            write_json(args.output/'accepted-report.json', report)
            status = 'Model claims grounded against this brief. Inferences still require human review.'
            success = True
        except (ValueError, KeyError, TypeError, OSError) as error:
            report = None
            status = 'Model output withheld: '+str(error)
            write_json(args.output/'rejection.json', {'reason': str(error), 'status': 'withheld'})
    (args.output/'report.html').write_text(render(brief, report, status, args.output.name), encoding='utf-8')
    write_json(args.output/'run-status.json', {'status': status, 'model_report_delivered': success,
                                             'current_groups': len(brief['groups']), 'no_sensor_changes': True})
    print(json.dumps({'status': status, 'groups': len(brief['groups']), 'run': str(args.output)}))
    return 0 if success or args.no_model else 2


if __name__ == '__main__':
    raise SystemExit(main())
