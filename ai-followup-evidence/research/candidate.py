"""Disposable, offline candidate. No service, model client or live-project imports.

Candidate record schema uses synthetic attempt IDs and aliases. An adapter for
real EVE/client records is future work; EVE alone cannot supply attempt identity.
"""
import hashlib
import html
import json

FIELDS = ('sid', 'gid', 'rev', 'signature', 'action', 'severity', 'protocol',
          'source_alias', 'source_port', 'destination_alias', 'destination_port')
CONTEXT = {'sensor_action_not_client_result', 'stun_process_unknown',
           'rule_match_not_intrusion_proof', 'coverage_limits', 'comparison_incomplete',
           'possible_fixture_requires_receipt', 'client_receipt_scoped_to_attempt',
           'process_receipt_not_client_result', 'untrusted_log_text'}
CHECKS = {'correlate_client_receipt', 'correlate_process_receipt',
          'inspect_rule', 'inspect_coverage', 'compare_retained_window', 'none'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def freeze_records(records):
    raw = bytearray()
    locators = {}
    for record in records:
        line = (canonical(record) + '\n').encode()
        ref = 'E-' + digest(line)[:16]
        if ref in locators:
            raise ValueError('Repeated physical identity requires distinct receipt envelope')
        locators[ref] = {'offset': len(raw), 'length': len(line), 'sha256': digest(line)}
        raw.extend(line)
    return bytes(raw), locators


def original(raw, locators, ref):
    row = locators[ref]
    start, length = row['offset'], row['length']
    if type(start) is not int or type(length) is not int or start < 0 or length < 1:
        raise ValueError('Invalid locator')
    line = raw[start:start + length]
    if len(line) != length or digest(line) != row['sha256'] or ref != 'E-' + row['sha256'][:16]:
        raise ValueError('Source identity mismatch')
    return json.loads(line)


def groups(raw, locators):
    result = {}
    for ref in sorted(locators, key=lambda r: locators[r]['offset']):
        record = original(raw, locators, ref)
        values = [record.get(key) for key in FIELDS]
        incomplete = any(value is None for value in values)
        # Conservative full identity. No signature truncation or inferred equivalence.
        key = ref if incomplete else digest(canonical(values).encode())
        group = result.setdefault(key, {'id': 'G-' + digest(key.encode())[:12],
                                       'fields': dict(zip(FIELDS, values)), 'members': []})
        group['members'].append({'ref': ref, 'sha256': locators[ref]['sha256'],
                                 'received_utc': record['received_utc']})
    rows = list(result.values())
    for row in rows:
        row['count'] = len(row['members'])
        times = [member['received_utc'] for member in row['members']]
        row['first_receipt_utc'], row['last_receipt_utc'] = min(times), max(times)
    return sorted(rows, key=lambda r: (r['fields']['action'] != 'blocked',
                                     r['fields']['severity'] != 1, r['id']))


def link_receipt(record, receipt):
    """Strict synthetic join. Same attempt/time/full tuple or no join."""
    keys = ('attempt_id', 'event_utc', 'protocol', 'source_alias', 'source_port',
            'destination_alias', 'destination_port')
    if any(record.get(key) is None or record.get(key) != receipt.get(key) for key in keys):
        return None
    return receipt


def score_selection(case, answer):
    """Selections cannot create facts; exact source display stays deterministic."""
    if not isinstance(answer, dict) or set(answer) != {'case', 'contexts', 'next_checks'}:
        return {'accepted': False, 'errors': ['schema']}
    errors = []
    if answer['case'] != case['id']:
        errors.append('case_identity')
    for field, allowed, required in [
            ('contexts', set(case['oracle']['eligible_contexts']), set(case['oracle']['required_contexts'])),
            ('next_checks', set(case['oracle']['useful_checks']), set())]:
        values = answer[field]
        if (not isinstance(values, list) or any(not isinstance(v, str) for v in values)
                or len(values) != len(set(values))):
            errors.append(field + '_schema')
        elif not set(values) <= allowed or not required <= set(values):
            errors.append(field + '_unsupported_or_missing')
        elif field == 'next_checks' and not 1 <= len(values) <= 3:
            errors.append('next_check_schema')
    return {'accepted': not errors, 'errors': errors, 'facts_rewritten_by_model': False}


def score(case, answer, raw, locators):
    """Oracle gate for typed selections. Free prose needs separate source review."""
    errors = []
    required_keys = {'case', 'groups', 'contexts', 'client_outcome', 'client_refs',
                     'intrusion_established', 'delivery_complete', 'next_checks'}
    if not isinstance(answer, dict) or set(answer) != required_keys:
        return {'accepted': False, 'errors': ['schema'], 'free_prose_assessed': False}
    if answer['case'] != case['id']:
        errors.append('case_identity')
    expected = {row['id']: row for row in groups(raw, locators)}
    got = answer['groups']
    if not isinstance(got, list):
        return {'accepted': False, 'errors': ['groups_schema'], 'free_prose_assessed': False}
    identifiers = []
    for row in got:
        if not isinstance(row, dict) or set(row) != {'id', 'count', 'action', 'refs'}:
            errors.append('group_schema')
            continue
        gid = row['id']
        if not isinstance(gid, str):
            errors.append('group_schema')
            continue
        identifiers.append(gid)
        group = expected.get(gid)
        if group is None:
            errors.append('invented_group')
            continue
        if type(row['count']) is not int or row['count'] != group['count']:
            errors.append('wrong_count')
        if row['action'] != group['fields']['action']:
            errors.append('wrong_sensor_action')
        refs = row['refs']
        allowed = {m['ref'] for m in group['members']}
        if (not isinstance(refs, list) or not refs or any(not isinstance(r, str) for r in refs)
                or len(refs) != len(set(refs))):
            errors.append('citation_schema')
        else:
            for ref in refs:
                if ref not in allowed:
                    errors.append('wrong_exact_source')
                else:
                    original(raw, locators, ref)
    if len(identifiers) != len(set(identifiers)):
        errors.append('duplicate_group')
    if set(identifiers) != set(expected):
        errors.append('missing_or_extra_group')
    contexts = answer['contexts']
    if (not isinstance(contexts, list) or any(not isinstance(c, str) for c in contexts)
            or len(contexts) != len(set(contexts)) or not set(contexts) <= CONTEXT):
        errors.append('context_schema')
    elif not set(case['oracle']['required_contexts']) <= set(contexts):
        errors.append('missing_context')
    elif not set(contexts) <= set(case['oracle']['eligible_contexts']):
        errors.append('ineligible_context')
    if answer['client_outcome'] != case['oracle']['client_outcome']:
        errors.append('unsupported_client_outcome')
    if answer['client_refs'] != case['oracle']['client_refs']:
        errors.append('wrong_client_receipt')
    if answer['intrusion_established'] is not False:
        errors.append('unsupported_intrusion')
    if answer['delivery_complete'] is not False:
        errors.append('unsupported_complete_delivery')
    checks = answer['next_checks']
    if (not isinstance(checks, list) or not 1 <= len(checks) <= 3
            or any(not isinstance(c, str) for c in checks)
            or len(checks) != len(set(checks)) or not set(checks) <= CHECKS):
        errors.append('next_check_schema')
    elif not set(checks) <= set(case['oracle']['useful_checks']):
        errors.append('nonresolving_check')
    return {'accepted': not errors, 'errors': sorted(set(errors)), 'free_prose_assessed': False}


def render(case, raw, locators, collapsed):
    """Same deterministic facts, coverage and client panel in both display conditions."""
    esc = lambda v: html.escape(str(v), quote=True)
    rows = groups(raw, locators)
    panel = '<h1>Offline case ' + esc(case['id']) + '</h1>'
    panel += '<p>Sensor action is recorded separately from the client result.</p>'
    panel += '<section data-panel="coverage"><h2>Coverage</h2><pre>' + esc(canonical(case['coverage'])) + '</pre></section>'
    panel += '<section data-panel="client"><h2>Supplied client and process receipts</h2><pre>' + esc(canonical(case['receipts'])) + '</pre></section>'
    panel += '<table><tr><th>Group</th><th>Sensor action</th><th>Records</th><th>Rule and endpoints</th></tr>'
    for row in rows:
        panel += '<tr><td>' + esc(row['id']) + '</td><td>' + esc(row['fields']['action']) + '</td><td>' + str(row['count']) + '</td><td>' + esc(canonical(row['fields'])) + '</td></tr>'
    panel += '</table>'
    for row in rows:
        members = ''
        for member in row['members']:
            record = original(raw, locators, member['ref'])
            members += '<details data-source="' + esc(member['ref']) + '"><summary>' + esc(member['ref']) + '</summary><pre>' + esc(canonical(record)) + '</pre><small>SHA256 ' + member['sha256'] + '</small></details>'
        if collapsed:
            panel += '<details data-group="' + row['id'] + '"><summary>' + str(row['count']) + ' records, ' + esc(row['fields']['action']) + ', ' + esc(row['fields']['signature']) + ', first ' + esc(row['first_receipt_utc']) + ', last ' + esc(row['last_receipt_utc']) + '</summary>' + members + '</details>'
        else:
            panel += members
    # No answer form, saving, fetching, inference or participant claim.
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Disposable offline display</title><style>body{font:16px system-ui;margin:24px;max-width:1100px}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ccc;padding:8px;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:8px 0;padding:8px;border:1px solid #bbb}</style><body>' + panel + '</body></html>'
