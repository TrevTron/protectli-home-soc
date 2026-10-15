"""Bind an operator-captured Windows connection receipt to one original alert.

Read-only historical context, outside the model. An exact current tuple alone
cannot identify an old flow: connection creation must also match EVE flow start.
No automatic benign verdict, process execution or endpoint collection occurs.
"""
import pathlib
import re
import datetime as dt

import soc_analyst as a
import soc_flow_review as f


def verify(proof, record, client):
    eve=a.eve_from_record(record)
    anchor=f.eve_event(record)
    if anchor is None or client not in (anchor['key'][1],anchor['key'][3]):
        raise ValueError('Context anchor is outside the owned client')
    event_time=a.timestamp(record['received_utc'])
    captured=a.timestamp(proof['captured_utc'])
    if captured<event_time or captured-event_time>dt.timedelta(hours=1):
        raise ValueError('Endpoint observation is outside the bounded historical window')
    saved=proof['exact_tuple']
    if f.tuple_key(saved['proto'],saved['src_ip'],saved['src_port'],saved['dest_ip'],saved['dest_port'])!=anchor['key']:
        raise ValueError('Endpoint receipt tuple differs from the alert')
    connections=proof['active_connection']
    if len(connections)!=1 or saved['proto']!='TCP':
        raise ValueError('Require one observed TCP connection; UDP identity is not inferred')
    connection=connections[0]
    if f.tuple_key('TCP',connection['LocalAddress'],connection['LocalPort'],connection['RemoteAddress'],connection['RemotePort'])!=anchor['key'] or connection['LocalAddress']!=client:
        raise ValueError('Active owned-client connection differs')
    start=a.timestamp(eve['flow']['start'])
    created=a.timestamp(connection['CreationTime'])
    if abs((created-start).total_seconds())>3:
        raise ValueError('Connection creation differs from EVE flow start; possible tuple reuse')
    process=proof['process']
    service=proof['service']
    pids=(process['ProcessId'],connection['OwningProcess'],process['ParentProcessId'],service['ProcessId'])
    if any(type(pid) is not int or pid<=0 for pid in pids) or pids[0]!=pids[1] or pids[2]!=pids[3]:
        raise ValueError('Process ownership/service lineage does not match')
    if a.timestamp(process['CreationDate'])>created or service['State']!='Running':
        raise ValueError('Process lifetime or service state does not match')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',process['Name']) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}',service['Name']):
        raise ValueError('Unexpected process/service name')
    return {'status':'historical_exact_flow_observation','captured_utc':captured.isoformat(),
        'process_name':process['Name'],'service_name':service['Name'],
        'connection_creation_delta_seconds':(created-start).total_seconds(),
        'meaning':'At the recorded observation time, this exact TCP tuple was owned by the named Windows process, with creation time matching EVE flow start and parent matching the running service. This does not establish benign intent or current connection state.',
        'installed_service_binary_signature_status':proof.get('signature_status','Unknown'),
        'signature_limit':'The installed service binary signature is a separate observation; it does not prove the running executable path or traffic intent.'}


def load(root, original, client):
    index=root/'endpoint-context-index.json'
    if not index.is_file():
        return None
    location=a.strict_json(index.read_text(encoding='utf-8-sig')).get(a.digest(original.encode()))
    if location is None:
        return None
    filename=location['file']
    if not isinstance(filename,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}\.json',filename):
        raise ValueError('Invalid endpoint receipt locator')
    path=root/filename
    if path.stat().st_size>64*1024:
        raise ValueError('Endpoint receipt exceeds bound')
    data=path.read_bytes()
    if a.digest(data)!=location['sha256']:
        raise ValueError('Endpoint receipt changed; context withheld')
    result=verify(a.strict_json(data.decode('utf-8-sig')),a.strict_json(original),client)
    result['receipt_sha256']=location['sha256']
    return result
