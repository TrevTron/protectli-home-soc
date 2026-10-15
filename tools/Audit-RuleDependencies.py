"""Read an official ET Open archive without extracting or executing its contents.

Produce an advisory category closure. Verify the actual installed rules and
Suricata startup validation before using the resulting plan on the appliance.
"""
import argparse
import collections
import json
import pathlib
import re
import tarfile


def audit(archive, initial):
    rules = []
    with tarfile.open(archive, 'r:gz') as bundle:
        for member in bundle:
            if not member.isfile() or not member.name.endswith('.rules'):
                continue
            if member.size > 20_000_000:
                raise ValueError('Unexpectedly large rule member')
            stream = bundle.extractfile(member)
            text = stream.read().decode('utf-8', errors='replace')
            for line in text.splitlines():
                if not line.startswith(('alert ', 'drop ', 'reject ', 'pass ')):
                    continue
                sid = re.search(r'\bsid\s*:\s*(\d+)\s*;', line)
                if not sid:
                    continue
                checks, sets = set(), set()
                # Suricata warns only for positive isset with no set/toggle.
                # isnotset is a negative condition and must not force a setter.
                for action, expression in re.findall(r'flowbits\s*:\s*(isset|set|toggle)\s*,\s*([^;]+);', line):
                    bits = {v.strip() for v in re.split(r'[&|,]', expression) if v.strip()}
                    (checks if action == 'isset' else sets).update(bits)
                rules.append({'file': pathlib.PurePosixPath(member.name).name,
                              'sid': int(sid[1]), 'checks': checks, 'sets': sets})
    setters = collections.defaultdict(list)
    for rule in rules:
        for bit in rule['sets']:
            setters[bit].append(rule)
    selected = set(initial)
    steps = []
    while True:
        active = [r for r in rules if r['file'] in selected]
        set_bits = set().union(*(r['sets'] for r in active))
        missing = set().union(*(r['checks'] for r in active)) - set_bits
        added = {r['file'] for bit in missing for r in setters[bit]} - selected
        steps.append({'missing': sorted(missing), 'added_categories': sorted(added)})
        if not added:
            break
        selected.update(added)
    return {'initial_categories': sorted(initial), 'category_closure': sorted(selected),
            'enabled_rule_count_in_closure': len(active), 'iterations': steps,
            'unresolved': [{'bit': bit, 'checking_sids': sorted(r['sid'] for r in active if bit in r['checks'])}
                           for bit in sorted(missing)],
            'initial_missing_setters': {bit: [{'sid': r['sid'], 'file': r['file']} for r in setters[bit]]
                                        for bit in steps[0]['missing']},
            'limit': 'Advisory archive analysis; actual enabled overrides and engine validation must be checked.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    initial = {'emerging-dns.rules', 'emerging-malware.rules', 'emerging-phishing.rules',
               'emerging-exploit.rules', 'emerging-attack_response.rules'}
    result = audit(args.archive, initial)
    pathlib.Path(args.output).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('category_closure', 'enabled_rule_count_in_closure', 'unresolved')}))
