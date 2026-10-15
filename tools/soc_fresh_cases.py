"""Freeze new constructed investigation cases without making model requests.

Three compatible eight-case packs contain 18 distinct measured cases plus six
practice cases. Source bytes are newly authored synthetic JSONL, not captured
incidents. No old case or model response is recycled. Human assignment is sealed
separately and balances A/B/C across distinct matched cases.
"""
from pathlib import Path
import argparse
import ast
import collections
import datetime as dt
import hashlib
import hmac
import json
import random
import tempfile

import soc_analyst as analyst
import soc_investigation_eval as evaluation
import soc_investigation_v6 as contract

CLIENT='192.0.2.10'  # Documentation address, never used for a network request.
NOW=dt.datetime(2026,10,6,18,0,tzinfo=dt.timezone.utc)
KINDS=('routine','blocked','changed-context','visibility-gap','empty-gap','mixed-priority')
TOOL_NAMES=('soc_analyst.py','soc_evidence.py','soc_investigation_run.py','soc_investigation_eval.py','soc_investigation_v2.py',
    'soc_investigation_v4.py','soc_investigation_v5.py','soc_investigation_v6.py','soc_context_guard.py','soc_fresh_cases.py')


def local_tool_closure(directory,seeds=TOOL_NAMES):
    """Resolve imports from the supplied source tree, including historical freezes."""
    directory=Path(directory);pending=list(seeds);found=set()
    while pending:
        name=pending.pop()
        if name in found:continue
        if len(found)>=32 or Path(name).name!=name:raise ValueError('Frozen tool membership exceeds bound')
        found.add(name)
        if not (directory/name).is_file():raise ValueError('Frozen tool membership missing dependency')
        for node in ast.walk(ast.parse((directory/name).read_bytes())):
            modules=([a.name for a in node.names] if isinstance(node,ast.Import) else
                [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            pending.extend(m+'.py' for m in modules if m.startswith('soc_'))
    return found


def alert(sid,action,severity,protocol,destination,port,*,at,serial):
    event={'event_type':'alert','timestamp':at.isoformat(),'src_ip':CLIENT,'dest_ip':destination,
           'src_port':45000+serial%1000,'dest_port':port,'proto':protocol,
           'alert':{'signature_id':sid,'action':action,'severity':severity}}
    record={'received_utc':at.isoformat(),'source':'192.0.2.1','app':'suricata',
            'raw':'<174> synthetic fixture '+analyst.canonical(event)}
    return (analyst.canonical(record)+'\n').encode()


def system(at,serial):
    return (analyst.canonical({'received_utc':at.isoformat(),'source':'192.0.2.1','app':'system',
                             'raw':'Constructed collection marker '+str(serial)})+'\n').encode()


def construct(kind,number,rng,now=NOW):
    specs=[];extra={};raw=bytearray()
    missing=kind in ('visibility-gap','empty-gap')
    if not missing:raw.extend(system(now-dt.timedelta(minutes=31),number))
    n=rng.randint(9,23);dest='198.51.100.'+str(20+number)
    def add(sid,action,severity,protocol,endpoint,count,port):
        specs.append((sid,action,severity,protocol,endpoint,count))
        for _ in range(count):
            serial=len(raw)+number
            raw.extend(alert(sid,action,severity,protocol,endpoint,port,
                       at=now-dt.timedelta(seconds=rng.randint(10,480)),serial=serial))
    if kind=='routine':add(2016150,'allowed',3,'UDP',dest,n,3478)
    elif kind=='blocked':add(2072081,'blocked',1,'TCP',dest,rng.randint(2,5),443)
    elif kind=='changed-context':
        add(2033078,'allowed',3,'UDP',dest,n*2,3478)
        add(2033078,'allowed',3,'UDP','203.0.113.'+str(20+number),2,3478)
        add(2033078,'blocked',1,'UDP',dest,1,3478)
    elif kind=='visibility-gap':
        add(2100498,'allowed',2,'TCP',dest,rng.randint(2,7),80)
        extra={'constructed_missing_context':True,'endpoint_receipt_available':False,
               'collection_note':'Constructed missing prior-window continuity and endpoint outcome, not proved packet loss.'}
    elif kind=='empty-gap':
        raw.extend(system(now-dt.timedelta(minutes=3),number))
        extra={'constructed_missing_context':True,'endpoint_receipt_available':False,
               'collection_note':'No supplied alert records; constructed missing comparison and endpoint context.'}
    elif kind=='mixed-priority':
        add(2016150,'allowed',3,'UDP',dest,n*3,3478)
        add(2100498,'allowed',2,'TCP','203.0.113.'+str(20+number),2,80)
        add(2072081,'blocked',1,'TCP','198.51.100.'+str(100+number),1,443)
    elif kind=='practice-alert':add(2100498,'allowed',2,'TCP',dest,1,80)
    elif kind=='practice-empty':raw.extend(system(now-dt.timedelta(minutes=1),number))
    else:raise ValueError('Unknown constructed case kind')
    return bytes(raw),specs,extra


def independent_design_check(raw,brief,sources,specs,salt):
    # A second raw-event check includes endpoint scope, which the older count
    # check aggregates over. Expected multiplicities were fixed by construction.
    counts=collections.Counter()
    for _,event,_,_ in evaluation.events(raw):
        if event and event.get('event_type')=='alert':
            a=event['alert'];counts[(a['signature_id'],a['action'],a['severity'],event['proto'],event['dest_ip'])]+=1
    expected=collections.Counter({tuple(row[:5]):row[5] for row in specs})
    if counts!=expected:raise ValueError('Constructed event counts or endpoints changed')
    aliases={hmac.new(salt,address.encode(),hashlib.sha256).hexdigest()[:10]:address for *_,address in counts}
    grouped=collections.Counter()
    for group in brief['groups']:
        address=aliases[group['destination_alias'].removeprefix('endpoint-')]
        if group['source_alias']!='owned-client':raise ValueError('Unexpected client scope')
        grouped[(group['sid'],group['action'],group['severity'],group['protocol'],address)]+=group['count']
    if grouped!=expected:raise ValueError('Brief merged changed action/severity/endpoint')
    return evaluation.independent_check(brief,sources,raw)


def build(output,*,seed=6100631):
    output=Path(output)
    if output.exists():raise ValueError('Fresh output must not exist')
    rng=random.Random(seed);prepared=[]
    snapshot_time=NOW+dt.timedelta(seconds=seed-6100631)
    for batch in range(3):
        cases=[]
        for cid,kind,phase in [('P01','practice-alert','practice'),('P02','practice-empty','practice')]+[
                (f'M{i+1:02d}',kind,'measured') for i,kind in enumerate(KINDS)]:
            number=batch*8+len(cases);raw,specs,extra=construct(kind,number,rng,now=snapshot_time)
            salt=('fresh-constructed-'+str(seed)+'-'+str(number)).encode()
            with tempfile.TemporaryDirectory() as temp:
                file=Path(temp)/'records.jsonl';file.write_bytes(raw)
                brief,sources=analyst.build_brief(file,CLIENT,salt,now=snapshot_time,max_groups=32)
            check=independent_design_check(raw,brief,sources,specs,salt)
            origin={'construction':kind,'seed':seed,'number':number,'constructed_snapshot_utc':snapshot_time.isoformat(),'new_authored_synthetic_records':True,
                    'real_incident':False,'old_source_records_reused':False,'prior_model_requests_on_exact_case':0,
                    'developer_knows_labels':True,'design_specs':[list(s) for s in specs]}
            cases.append((cid,phase,raw,brief,sources,extra,origin,check))
        prepared.append(cases)
    output.mkdir(parents=True)
    seal={'version':1,'seed':seed,'status':'prepared_not_executed','human_participants':0,'model_requests':0,
          'protocol_revision':contract.REVISION,'scope':'New constructed case bytes, not unseen real incidents or independent human labels.',
          'packs':{},'tools':{},'measured_distinct_cases':18,'practice_distinct_cases':6}
    for batch,cases in enumerate(prepared):
        pack=output/f'batch-{batch+1}';pack.mkdir();manifest={'version':1,'cases':[],'files':{},
             'evaluation_kind':'new constructed regression holdout','human_participants':0,'unseen_holdout_claim':False}
        for cid,phase,raw,brief,sources,extra,origin,check in cases:
            case=pack/cid;case.mkdir();(case/'records.jsonl').write_bytes(raw)
            for name,value in [('brief.json',brief),('sources.json',sources),('context.json',extra),('origin.json',origin),
                ('oracle.json',evaluation.oracle_for(brief,extra)),('source-check.json',check)]:evaluation.write(case/name,value)
            manifest['cases'].append({'id':cid,'phase':phase})
            for file in sorted(case.iterdir()):manifest['files'][file.relative_to(pack).as_posix()]=evaluation.digest(file.read_bytes())
        evaluation.write(pack/'manifest.json',manifest);evaluation.verify(pack)
        seal['packs'][pack.name]=evaluation.digest((pack/'manifest.json').read_bytes())
    frozen=output/'frozen-tools';frozen.mkdir()
    for name in sorted(local_tool_closure(Path(__file__).parent)):
        raw=(Path(__file__).parent/name).read_bytes();(frozen/name).write_bytes(raw);seal['tools'][name]=evaluation.digest(raw)
    # Distinct matched examples: same scenario in each batch, one per condition.
    orders=('ABC','BCA','CAB','ACB','CBA','BAC');assignment=[]
    triplets=list(range(6));rng.shuffle(triplets)
    for block,i in enumerate(triplets):
        for position,condition in enumerate(orders[i]):
            # Each matched block uses a different A/B/C order. Each batch also
            # receives two of every condition across the complete pilot.
            assignment.append({'case':f'batch-{position+1}/M{i+1:02d}','condition':condition,
                'matched_triplet':i+1,'block':block+1,'position':position+1,'session':block//2+1})
    evaluation.write(output/'human-assignment-private.json',{'seed':seed,'status':'prepared_not_started','assignments':assignment,
         'limits':'No participant answer, timing result or model-assisted display exists yet. Practice first; no coaching during measured tasks.'})
    seal['human_assignment_sha256']=evaluation.digest((output/'human-assignment-private.json').read_bytes())
    evaluation.write(output/'PRE_REQUEST_SEAL.json',seal)
    verify(output)
    return seal


def verify(output):
    output=Path(output);seal=evaluation.load(output/'PRE_REQUEST_SEAL.json')
    if seal['model_requests']!=0 or len(seal['packs'])!=3 or seal['status']!='prepared_not_executed':raise ValueError('Preparation seal changed')
    if set(seal['tools'])!=local_tool_closure(output/'frozen-tools'):raise ValueError('Frozen tool membership changed')
    hashes=[]
    for pack,sha in seal['packs'].items():
        if pack not in ('batch-1','batch-2','batch-3'):raise ValueError('Unsafe pack name')
        p=output/pack
        try:evaluation.verify(p)
        except KeyError as error:raise ValueError('Case source binding is incomplete') from error
        if evaluation.digest(evaluation.read(p/'manifest.json'))!=sha:raise ValueError('Case manifest changed')
        for case in evaluation.load(p/'manifest.json')['cases']:
            folder=p/case['id'];origin=evaluation.load(folder/'origin.json');salt=('fresh-constructed-'+str(origin['seed'])+'-'+str(origin['number'])).encode()
            independent_design_check(evaluation.read(folder/'records.jsonl'),evaluation.load(folder/'brief.json'),
                evaluation.load(folder/'sources.json'),origin['design_specs'],salt)
            hashes.append(evaluation.digest(evaluation.read(folder/'records.jsonl')))
    if len(set(hashes))!=24:raise ValueError('Distinct cases accidentally reused')
    for name,sha in seal['tools'].items():
        if Path(name).name!=name or not name.endswith('.py') or evaluation.digest(evaluation.read(output/'frozen-tools'/name))!=sha:
            raise ValueError('Frozen tool changed')
        for node in ast.walk(ast.parse(evaluation.read(output/'frozen-tools'/name))):
            modules=([a.name for a in node.names] if isinstance(node,ast.Import) else
                [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            if any(m.startswith('soc_') and m+'.py' not in seal['tools'] for m in modules):
                raise ValueError('Frozen local dependency missing')
    if evaluation.digest(evaluation.read(output/'human-assignment-private.json'))!=seal['human_assignment_sha256']:
        raise ValueError('Human assignment changed')
    assignment=evaluation.load(output/'human-assignment-private.json')['assignments']
    expected={f'batch-{b}/M{i:02d}' for b in range(1,4) for i in range(1,7)}
    if len(assignment)!=18 or {r['case'] for r in assignment}!=expected:raise ValueError('Human case membership changed')
    if collections.Counter(r['condition'] for r in assignment)!=dict(A=6,B=6,C=6):raise ValueError('Unbalanced assignment')
    for triplet in range(1,7):
        if {r['condition'] for r in assignment if r['matched_triplet']==triplet}!={'A','B','C'}:
            raise ValueError('Matched triplet assignment changed')
    orders=[]
    for block in range(1,7):
        rows=[r for r in assignment if r['block']==block]
        if len(rows)!=3 or [r['position'] for r in rows]!=[1,2,3] or len({r['matched_triplet'] for r in rows})!=1:
            raise ValueError('Matched block order changed')
        if any(r['session']!=(block-1)//2+1 for r in rows):raise ValueError('Session order changed')
        orders.append(''.join(r['condition'] for r in rows))
    if len(set(orders))!=6:raise ValueError('Condition order must cover all six permutations')
    return {'case_packs_verified':3,'distinct_cases':24,'measured_cases':18,'practice_cases':6,
            'model_requests':0,'human_answers':0,'status':'ready_for_later_bounded_execution'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=('build','verify'))
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seed',type=int,default=6100631)
    args=parser.parse_args();result=build(args.output,seed=args.seed) if args.command=='build' else verify(args.output)
    print(json.dumps({k:v for k,v in result.items() if k not in ('packs','tools')}))


if __name__=='__main__':main()
