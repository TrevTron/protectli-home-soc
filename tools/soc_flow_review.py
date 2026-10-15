"""Read-only, exact-tuple PF/Suricata evidence review for one owned client.

Only the observed IPv4 TCP/UDP filterlog format is supported. A PF pass and a
Suricata block are independent sensor actions, not conflicting verdicts. NAT
tuples, missing logs and client outcomes are never inferred from a port match.
"""
import csv
import datetime as dt
import ipaddress
import json
import pathlib
import re

import soc_analyst as a


def tuple_key(protocol, src, sport, dst, dport):
    protocol = protocol.upper()
    if protocol not in ('TCP', 'UDP'):
        raise ValueError('Only TCP/UDP exact tuples supported')
    if any(type(p) is not int or not 0 <= p <= 65535 for p in (sport, dport)):
        raise ValueError('Invalid port')
    ends = sorted([(str(ipaddress.ip_address(src)), sport), (str(ipaddress.ip_address(dst)), dport)])
    return (protocol, *ends[0], *ends[1])


def pf_event(record):
    if record.get('app') != 'filterlog':
        return None
    # Match only the terminal CSV payload from the actual RFC5424 receipts.
    match = re.search(r'(?:\] | - )(\d+,[^\r\n]+)$', record.get('raw', ''))
    if not match:
        raise ValueError('Unrecognized filterlog envelope')
    fields = next(csv.reader([match[1]]))
    if len(fields) < 22 or fields[8] != '4' or fields[13] != '0':
        raise ValueError('Unsupported IP version/fragment or short payload')
    if fields[6] not in ('pass', 'block') or fields[7] not in ('in', 'out'):
        raise ValueError('Unknown PF action/direction')
    proto = fields[16].upper()
    if fields[15] != {'TCP':'6','UDP':'17'}.get(proto):
        raise ValueError('Unknown or contradictory protocol')
    key = tuple_key(proto, fields[18], int(fields[20]), fields[19], int(fields[21]))
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,32}', fields[4]):
        raise ValueError('Invalid interface')
    return {'key':key, 'sensor':'pf', 'action':fields[6], 'interface':fields[4],
            'direction':fields[7], 'rule_number':int(fields[0])}


def eve_event(record):
    eve = a.eve_from_record(record)
    if eve is None:
        return None
    action = eve['alert']['action']
    sid = eve['alert']['signature_id']
    if action not in ('allowed','blocked') or type(sid) is not int:
        raise ValueError('Invalid alert action/SID')
    return {'key':tuple_key(eve['proto'],eve['src_ip'],eve['src_port'],eve['dest_ip'],eve['dest_port']),
            'sensor':'suricata','action':action,'sid':sid}


def investigate(path, anchor_record, client, *, seconds=60, max_bytes=16*1024**2):
    client = str(ipaddress.ip_address(client))
    anchor = eve_event(anchor_record)
    if anchor is None or client not in (anchor['key'][1],anchor['key'][3]):
        raise ValueError('Anchor must be an alert involving the owned client')
    if not 1 <= seconds <= 300:
        raise ValueError('Use a bounded correlation window')
    when = a.timestamp(anchor_record['received_utc'])
    start, data, end = a.snapshot(path,max_bytes)
    offset = start
    matches=[]
    earliest=latest=None
    malformed=unsupported=0
    for line in data.splitlines(keepends=True):
        position=offset
        offset+=len(line)
        try:
            if len(line)>a.MAX_LINE:
                raise ValueError('Oversized source record')
            record=a.strict_json(line.decode('utf-8'))
            receipt=a.timestamp(record['received_utc'])
            earliest=receipt if earliest is None else min(earliest,receipt)
            latest=receipt if latest is None else max(latest,receipt)
        except (ValueError,KeyError,TypeError,UnicodeError):
            malformed+=1
            continue
        if abs((receipt-when).total_seconds())>seconds:
            continue
        try:
            sensor=pf_event(record) if record.get('app')=='filterlog' else eve_event(record)
        except (ValueError,KeyError,TypeError,AttributeError):
            unsupported+=1
            continue
        if sensor is None or sensor['key'] != anchor['key']:
            continue
        sensor.pop('key')
        sensor.update(received_utc=receipt.isoformat(),ref='E-'+a.digest(line)[:16],
                      byte_offset=position,byte_length=len(line),sha256=a.digest(line))
        matches.append(sensor)
    pf={v['action'] for v in matches if v['sensor']=='pf'}
    ids={v['action'] for v in matches if v['sensor']=='suricata'}
    notes=[]
    if 'pass' in pf and 'blocked' in ids:
        notes.append('PF logged a pass and Suricata reported a block for this exact tuple in the selected time window. Different inspection layers can make different decisions.')
    if 'block' in pf:
        notes.append('PF logged a block for this exact tuple in the selected time window. The rule number is an observed log field, not a decoded policy explanation.')
    if not pf:
        notes.append('No exact pre-NAT PF match is present in the retained snapshot. This does not prove that PF allowed or blocked it. Post-NAT address translation is not guessed.')
    if 'blocked' in ids:
        notes.append('Suricata reported a blocked alert for this exact tuple. This is a sensor action; verify the separate client result before claiming that its request failed.')
    if 'allowed' in ids:
        notes.append('Suricata reported an allowed alert. This does not prove that the connection completed or that another inspection layer allowed it.')
    notes.append('Client success/failure and process identity require separate owned-client evidence. A time/tuple match does not establish identical packets or malicious intent.')
    return {'anchor_received_utc':when.isoformat(),'window_seconds_each_side':seconds,
            'tuple_match':'full bidirectional protocol/IP/port tuple; no NAT guessing',
            'matches':matches[:100], 'total_matches':len(matches),'omitted_matches':max(0,len(matches)-100),
            'interpretation':notes,'coverage':{'start_byte':start,'end_byte':start+len(data),'source_size':end,
                'snapshot_sha256':a.digest(data),'tail_clipped':start>0,'malformed_records':malformed,
                'unsupported_sensor_records_in_window':unsupported,
                'window_covered_by_retained_receipts':bool(earliest is not None and earliest<=when-dt.timedelta(seconds=seconds) and latest>=when+dt.timedelta(seconds=seconds)),
                'complete_delivery_proven':False}}
