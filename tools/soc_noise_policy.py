"""Offline, scoped expected-context labels. Never hides evidence or changes rules.

Pure preview/activation/rollback functions prepare a later operator workflow.
No model can activate a policy. This module is not imported by live services.
"""
import datetime as dt
import copy
import hashlib
import ipaddress
import json
import re

SCOPE=('sid','rev','source_ip','destination_ip','protocol','destination_port','action','severity')
MAX_GROUPS=5000


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def instant(value):
    time=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if time.tzinfo is None:raise ValueError('Timezone required')
    return time.astimezone(dt.timezone.utc)


def scope(value):
    if not isinstance(value,dict) or set(value)!=set(SCOPE):raise ValueError('Exact scope required')
    for key,limit in (('sid',2**32-1),('rev',2**31-1),('destination_port',65535)):
        if type(value[key]) is not int or not 1<=value[key]<=limit:raise ValueError('Missing or invalid rule/port scope')
    for key in ('source_ip','destination_ip'):
        if str(ipaddress.ip_address(value[key]))!=value[key]:raise ValueError('Canonical endpoint required')
    if value['protocol'] not in ('TCP','UDP') or value['action']!='allowed' or type(value['severity']) is not int or value['severity']!=3:
        raise ValueError('Only allowed severity-three context can be labeled expected')


def validate(policy):
    required={'version','id','revision','scope','reason','supporting_case_sha256','created_utc','expires_utc',
              'window_seconds','max_count'}
    if not isinstance(policy,dict) or set(policy)!=required or policy['version']!=1:raise ValueError('Policy shape changed')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',policy['id']):raise ValueError('Invalid policy identity')
    if type(policy['revision']) is not int or not 1<=policy['revision']<=10000:raise ValueError('Explicit revision required')
    if not isinstance(policy['reason'],str) or not 10<=len(policy['reason'])<=1000:raise ValueError('Review reason required')
    if not re.fullmatch('[a-f0-9]{64}',policy['supporting_case_sha256']):raise ValueError('Supporting case hash required')
    created,expires=instant(policy['created_utc']),instant(policy['expires_utc'])
    if not dt.timedelta(0)<expires-created<=dt.timedelta(days=7):raise ValueError('Expiry within seven days required')
    for key,limit in (('window_seconds',3600),('max_count',100000)):
        if type(policy[key]) is not int or not 1<=policy[key]<=limit:raise ValueError('Explicit bounded count/window required')
    scope(policy['scope']);return policy


def label(group,policy,now):
    # Context and counts are deterministic inputs, never a model's assertions.
    result={'group_id':group.get('id'),'label':'review','reason':'outside_exact_scope',
            'keep_visible':True,'priority_floor':group.get('priority_floor','review'),
            'count':group.get('count'),'evidence_refs':group.get('evidence_refs',[])}
    if group.get('action')=='blocked' or group.get('severity')==1:
        return {**result,'reason':'priority_floor','priority_floor':'review_first'}
    if now<instant(policy['created_utc']) or now>=instant(policy['expires_utc']):return {**result,'reason':'policy_inactive_or_expired'}
    if any(group.get(k)!=v or type(group.get(k)) is not type(v) for k,v in policy['scope'].items()):return result
    if group.get('sources_verified') is not True or group.get('comparison_available') is not True or group.get('scope_complete') is not True:
        return {**result,'reason':'missing_verified_context'}
    count=group.get('count')
    if type(count) is not int or not 1<=count<=policy['max_count']:return {**result,'reason':'count_change_or_burst'}
    if type(group.get('window_seconds')) is not int or group['window_seconds']!=policy['window_seconds']:
        return {**result,'reason':'comparison_window_changed'}
    refs=group.get('evidence_refs')
    if not isinstance(refs,list) or not refs or len(refs)>128 or any(not isinstance(r,str) or not re.fullmatch('E-[a-f0-9]{16}',r) for r in refs):
        return {**result,'reason':'missing_verified_context'}
    return {**result,'label':'expected_context','reason':'reviewed_exact_scope','policy_id':policy['id'],
            'policy_revision':policy['revision']}


def preview(policy,groups,*,now):
    validate(policy);now=instant(now)
    if not isinstance(groups,list) or len(groups)>MAX_GROUPS:raise ValueError('Historical preview bound')
    if any(not isinstance(g,dict) for g in groups):raise ValueError('Group shape required')
    ids=[g.get('id') for g in groups]
    if any(not isinstance(i,str) or not i or len(i)>128 for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError('Distinct group identities required')
    # Refuse duplicate exact scopes: dividing one burst into two groups could
    # otherwise keep each below the allowed count independently.
    seen=[]
    for group in groups:
        key=tuple(group.get(k) for k in SCOPE)
        if key in seen:raise ValueError('Duplicate scope requires combined counts')
        seen.append(key)
    decisions=[label(g,policy,now) for g in groups]
    result={'version':1,'policy_sha256':digest(policy),'dataset_sha256':digest(groups),'created_utc':now.isoformat(),
            'groups':decisions,'input_groups':len(groups),'visible_groups':len(decisions),
            'expected_groups':sum(r['label']=='expected_context' for r in decisions),'suppressed_records':0,
            'scope':'Offline labels only; no live rule, admission, priority or evidence changes'}
    result['preview_sha256']=digest(result);return result


def activate(policy,receipt,*,reviewed_preview_sha256,verified_case_sha256,now,previous=None):
    validate(policy);now=instant(now)
    body={k:v for k,v in receipt.items() if k!='preview_sha256'}
    if receipt.get('preview_sha256')!=reviewed_preview_sha256 or digest(body)!=reviewed_preview_sha256:
        raise ValueError('Reviewed preview changed')
    if receipt.get('policy_sha256')!=digest(policy) or verified_case_sha256!=policy['supporting_case_sha256']:
        raise ValueError('Supporting case or policy differs from review')
    preview_time=instant(receipt['created_utc'])
    if not dt.timedelta(0)<=now-preview_time<=dt.timedelta(hours=1):raise ValueError('Fresh preview required')
    if not instant(policy['created_utc'])<=now<instant(policy['expires_utc']):raise ValueError('Expired policy cannot activate')
    if previous is not None and (previous.get('status')!='active_offline' or previous['policy']['id']!=policy['id'] or
            policy['revision']<=previous['policy']['revision']):raise ValueError('Revision must increase for the same policy')
    # The caller explicitly supplies hashes from operator review. These are not
    # proof of independent human judgement; tests use labeled synthetic cases.
    return {'status':'active_offline','policy':copy.deepcopy(policy),'activated_utc':now.isoformat(),
            'reviewed_preview_sha256':reviewed_preview_sha256,'previous':copy.deepcopy(previous),'live_applied':False}


def rollback(state,*,expected_state_sha256):
    if digest(state)!=expected_state_sha256 or state.get('status')!='active_offline':raise ValueError('Rollback state changed')
    return {'status':'rolled_back_offline','restored':copy.deepcopy(state['previous']),'rolled_back_sha256':expected_state_sha256,
            'live_applied':False}
