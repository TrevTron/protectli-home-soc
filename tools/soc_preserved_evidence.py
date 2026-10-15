"""Explicit immutable migration baseline and source pins for reviewed cases.

Rolling retention is separate. Reads never create pins or infer missing data.
The baseline preserves the original prefix once, without repeated full copies.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

import soc_evidence as evidence
from soc_retained_evidence import EvidenceExpired

MAX_RECORD = 1024 * 1024
MAX_BASELINE = 1024**3
MAX_DESCRIPTOR = 256 * 1024
MAX_PINS = 4096
MAX_PIN_BYTES = 64 * 1024**2


def digest(raw):return hashlib.sha256(raw).hexdigest()


def regular(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents):
        raise ValueError('Preserved evidence links refused')
    return path


def locator(source):
    start,length=source.get('byte_offset'),source.get('byte_length')
    if type(start) is not int or type(length) is not int or start<0 or not 1<=length<=MAX_RECORD:
        raise ValueError('Invalid original source locator')
    if not re.fullmatch('[a-f0-9]{64}',source.get('sha256','')):
        raise ValueError('Full original source digest required')
    return start,length


def descriptor(path):return Path(str(path)+'.preserved.json')


def create_baseline(source):
    """Explicit migration preparation; stop the writer before the final copy."""
    source=Path(source)
    if descriptor(source).exists():raise ValueError('Baseline already exists; preserve it')
    files,layout=evidence.layout(source)
    if not layout or layout.get('version')!=1:
        raise ValueError('Baseline preparation requires the original version 1 source')
    total=sum(size for _,size in files)
    if total>MAX_BASELINE:raise ValueError('Baseline exceeds its independent 1 GiB bound')
    folder=source.parent/(source.name+'.baseline-'+uuid.uuid4().hex[:12])
    folder.mkdir()
    members=[];start=0;whole=hashlib.sha256()
    for path,size in files:
        target=folder/path.name
        remaining=size;hashed=hashlib.sha256()
        with regular(path).open('rb') as original,target.open('xb') as saved:
            while remaining:
                raw=original.read(min(65536,remaining))
                if not raw:raise ValueError('Original baseline source shortened')
                saved.write(raw);hashed.update(raw);whole.update(raw);remaining-=len(raw)
            saved.flush();os.fsync(saved.fileno())
        if evidence.sha256_file(target)!=hashed.hexdigest():raise ValueError('Baseline copy did not verify')
        members.append({'name':path.name,'start':start,'bytes':size,'sha256':hashed.hexdigest()})
        start+=size
    # Refuse a concurrent append or rollover. A failed copy remains private evidence.
    current,current_layout=evidence.layout(source)
    if current_layout!=layout or [(p.name,n) for p,n in current]!=[(p.name,n) for p,n in files]:
        raise ValueError('Original source advanced during baseline; stop the receiver and try a new copy')
    with evidence.open_evidence(source) as stream:
        actual=hashlib.sha256()
        for raw in iter(lambda:stream.read(65536),b''):actual.update(raw)
    if actual.hexdigest()!=whole.hexdigest():raise ValueError('Original baseline prefix changed')
    value={'version':1,'source_name':source.name,'directory':folder.name,
           'prefix_bytes':total,'prefix_sha256':whole.hexdigest(),'members':members}
    raw=(json.dumps(value,indent=2)+'\n').encode()
    if len(raw)>MAX_DESCRIPTOR:raise ValueError('Baseline descriptor exceeds bound')
    with descriptor(source).open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    verify_baseline(source)
    return value


def baseline_layout(source):
    source=Path(source);path=regular(descriptor(source))
    if path.stat().st_size>MAX_DESCRIPTOR:raise ValueError('Baseline descriptor exceeds bound')
    value=json.loads(path.read_text())
    if value.get('version')!=1 or value.get('source_name')!=source.name:
        raise ValueError('Baseline belongs to another source')
    if not re.fullmatch(re.escape(source.name)+r'\.baseline-[a-f0-9]{12}',value.get('directory','')):
        raise ValueError('Unsafe baseline directory')
    members=value.get('members',[])
    if not 1<=len(members)<=65:raise ValueError('Baseline member count bound')
    position=0;files=[]
    for number,row in enumerate(members):
        expected=source.name if number==0 else source.name+f'.part{number:06d}'
        if row['name']!=expected or type(row['start']) is not int or row['start']!=position or type(row['bytes']) is not int or row['bytes']<0:
            raise ValueError('Unsafe baseline sequence')
        if not re.fullmatch('[a-f0-9]{64}',row['sha256']):raise ValueError('Invalid baseline digest')
        path=regular(source.parent/value['directory']/row['name'])
        if path.stat().st_size!=row['bytes']:raise ValueError('Baseline length changed')
        files.append((path,row));position+=row['bytes']
    if position!=value['prefix_bytes'] or not 0<=position<=MAX_BASELINE:
        raise ValueError('Invalid baseline prefix')
    return files,value


def verify_baseline(source):
    files,value=baseline_layout(source);whole=hashlib.sha256()
    for path,row in files:
        hashed=hashlib.sha256()
        with path.open('rb') as stream:
            for raw in iter(lambda:stream.read(65536),b''):hashed.update(raw);whole.update(raw)
        if hashed.hexdigest()!=row['sha256']:raise ValueError('Baseline member changed')
    if whole.hexdigest()!=value['prefix_sha256']:raise ValueError('Baseline prefix changed')
    return {'verified_prefix_bytes':value['prefix_bytes'],'members_verified':len(files),
            'descriptor_sha256':evidence.sha256_file(descriptor(source))}


def baseline_record(source,location):
    start,length=locator(location);files,value=baseline_layout(source)
    if start+length>value['prefix_bytes']:raise EvidenceExpired('Record is outside the preserved migration baseline')
    result=[]
    for path,row in files:
        low=max(start,row['start']);high=min(start+length,row['start']+row['bytes'])
        if low>=high:continue
        if evidence.sha256_file(path)!=row['sha256']:raise ValueError('Baseline member changed; evidence withheld')
        with path.open('rb') as stream:stream.seek(low-row['start']);result.append(stream.read(high-low))
    raw=b''.join(result)
    if len(raw)!=length or digest(raw)!=location['sha256']:raise ValueError('Preserved original record changed')
    return raw


def read_record(source,location,*,pin_root=None):
    start,length=locator(location)
    try:
        with evidence.open_evidence(source) as stream:stream.seek(start);raw=stream.read(length)
    except EvidenceExpired:
        if pin_root is not None:
            pin=Path(pin_root)/'preserved-records'/(location['sha256']+'.jsonl')
            if pin.exists():
                if regular(pin).stat().st_size!=length:raise ValueError('Saved source length changed')
                raw=pin.read_bytes()
            elif descriptor(source).exists():raw=baseline_record(source,location)
            else:raise
        elif descriptor(source).exists():raw=baseline_record(source,location)
        else:raise
    if len(raw)!=length or digest(raw)!=location['sha256']:
        raise ValueError('Original source hash mismatch; evidence withheld')
    return raw


def pin_records(root,records):
    """Called only by an explicit review POST, never by a GET or model output."""
    root=Path(root);folder=root/'preserved-records';folder.mkdir(exist_ok=True)
    if folder.is_symlink() or any(p.is_symlink() for p in folder.parents):
        raise ValueError('Saved-case directory links refused')
    with evidence.exclusive_lock(folder/'pins.lock'):
        existing=list(folder.glob('*.jsonl'))
        if len(existing)>MAX_PINS or sum(regular(p).stat().st_size for p in existing)>MAX_PIN_BYTES:
            raise ValueError('Saved-case record budget exceeded; preserve/export cases')
        values={digest(raw):raw for raw in records}
        if any(not 1<=len(raw)<=MAX_RECORD for raw in values.values()):raise ValueError('Pinned record byte bound')
        new={sha:raw for sha,raw in values.items() if not (folder/(sha+'.jsonl')).exists()}
        if len(existing)+len(new)>MAX_PINS or sum(p.stat().st_size for p in existing)+sum(map(len,new.values()))>MAX_PIN_BYTES:
            raise ValueError('Saved-case record budget reached; review was not recorded')
        for sha,raw in values.items():
            target=folder/(sha+'.jsonl')
            if target.exists():
                if regular(target).read_bytes()!=raw:raise ValueError('Existing saved source changed')
            else:
                with target.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        return [{'sha256':sha,'byte_length':len(raw)} for sha,raw in sorted(values.items())]
