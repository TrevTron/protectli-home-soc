"""Verified private archive reads and retention previews. Never deletes evidence.

This offline module is not wired into the running receiver or dashboard.
Checkpoint archives stay bounded by soc_archive's existing verification limits.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import re
import zipfile

import soc_archive as archives
import soc_evidence as evidence

MAX_CATALOG = 1024 * 1024
MAX_ARCHIVES = 64
MAX_PINS = 128
MAX_RECORD = 1024 * 1024


def digest(raw):return hashlib.sha256(raw).hexdigest()


def regular(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents):
        raise ValueError('Regular private file required; links refused')
    return path


def timestamp(value):
    value=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if value.tzinfo is None:raise ValueError('Timezone required')
    return value.astimezone(dt.timezone.utc)


def locator(value):
    if not isinstance(value,dict):raise ValueError('Invalid source locator')
    offset,length=value.get('byte_offset'),value.get('byte_length')
    if type(offset) is not int or type(length) is not int or offset<0 or not 1<=length<=MAX_RECORD:
        raise ValueError('Source locator outside bounds')
    if not re.fullmatch('[a-f0-9]{64}',value.get('sha256','')):raise ValueError('Full record digest required')
    return offset,length


def archive_entry(path):
    path=regular(path)
    if path.stat().st_size>archives.DEFAULT_ARCHIVE_BUDGET:raise ValueError('Archive byte bound')
    checked=archives.verify_archive(path)
    with zipfile.ZipFile(path) as saved:
        manifest=json.loads(saved.read('archive-manifest.json'))
    listed={row['file']:row for row in manifest['files']};members=[];offset=0
    for name in manifest['logical_log_members']:
        row=listed[name]
        members.append({'member':name,'start':offset,'bytes':row['bytes'],'sha256':row['sha256']})
        offset+=row['bytes']
    return {'archive':path.name,'bytes':path.stat().st_size,'sha256':evidence.sha256_file(path),
            'raw_prefix_bytes':offset,'raw_prefix_sha256':manifest.get('raw_prefix_sha256'),
            'members':members,'verification':checked}


def write_catalog(archive_directory,output):
    archive_directory=Path(archive_directory)
    if archive_directory.is_symlink():raise ValueError('Archive directory link refused')
    paths=sorted(archive_directory.glob('checkpoint-*.zip'))
    if not 1<=len(paths)<=MAX_ARCHIVES:raise ValueError('Archive count bound')
    rows=[archive_entry(p) for p in paths]
    value={'version':1,'archives':rows,'scope':'Verified archived prefixes; no deletion or live migration'}
    raw=(json.dumps(value,indent=2)+'\n').encode()
    if len(raw)>MAX_CATALOG:raise ValueError('Catalog byte bound')
    with Path(output).open('xb') as stream:stream.write(raw)
    return value


def load_catalog(path):
    path=regular(path)
    if path.stat().st_size>MAX_CATALOG:raise ValueError('Catalog byte bound')
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('version')!=1 or not isinstance(value.get('archives'),list) or not 1<=len(value['archives'])<=MAX_ARCHIVES:
        raise ValueError('Catalog shape/count bound')
    names=[]
    for row in value['archives']:
        name=row.get('archive','')
        if not re.fullmatch(r'checkpoint-[A-Za-z0-9_-]+\.zip',name):raise ValueError('Unsafe archive filename')
        names.append(name)
        if type(row.get('raw_prefix_bytes')) is not int or not 0<=row['raw_prefix_bytes']<=archives.RAW_LIMIT:
            raise ValueError('Catalog prefix bound')
    if len(set(names))!=len(names):raise ValueError('Duplicate archive identity')
    return value


def verified_entry(directory,row):
    path=regular(Path(directory)/row['archive'])
    if path.stat().st_size!=row['bytes'] or evidence.sha256_file(path)!=row['sha256']:
        raise ValueError('Archived file changed; source withheld')
    actual=archive_entry(path)
    if actual!=row:raise ValueError('Catalog does not match verified archive')
    return path


def archived_record(catalog_path,archive_directory,source):
    """Resolve the original logical locator, even with no hot files present."""
    start,length=locator(source);end=start+length
    rows=load_catalog(catalog_path)['archives']
    eligible=sorted((r for r in rows if r['raw_prefix_bytes']>=end),key=lambda r:(r['raw_prefix_bytes'],r['archive']))
    if not eligible:raise ValueError('No verified archive covers the complete source')
    row=eligible[0];path=verified_entry(archive_directory,row);parts=[]
    with zipfile.ZipFile(path) as saved:
        for member in row['members']:
            low=max(start,member['start']);high=min(end,member['start']+member['bytes'])
            if high<=low:continue
            with saved.open(member['member']) as stream:
                stream.seek(low-member['start']);part=stream.read(high-low)
            if len(part)!=high-low:raise ValueError('Archived source shortened')
            parts.append(part)
    raw=b''.join(parts)
    if len(raw)!=length or digest(raw)!=source['sha256']:raise ValueError('Archived record digest mismatch')
    return raw


def pin_case(catalog_path,archive_directory,sources,output,*,context):
    """Save an immutable source/context bundle outside proposed hot retention."""
    if not isinstance(sources,dict) or not 1<=len(sources)<=MAX_PINS:raise ValueError('Pinned source count bound')
    if not isinstance(context,dict):raise ValueError('Pinned context must be explicit')
    if len(json.dumps(context).encode())>MAX_RECORD:raise ValueError('Pinned context byte bound')
    output=Path(output)
    if output.exists():raise ValueError('Pinned destination must be new')
    # Verify everything before creating the destination; do not leave a partial pin.
    records={}
    for ref,source in sources.items():
        if not re.fullmatch(r'E-[a-f0-9]{16}',ref) or ref!='E-'+source.get('sha256','')[:16]:raise ValueError('Invalid evidence reference')
        records[ref]=archived_record(catalog_path,archive_directory,source)
    manifest={'version':1,'context':context,'sources':sources,'records':{}}
    for ref,raw in records.items():
        name=ref+'.jsonl'
        manifest['records'][ref]={'file':name,'bytes':len(raw),'sha256':digest(raw)}
    encoded=(json.dumps(manifest,indent=2)+'\n').encode()
    if len(encoded)>MAX_CATALOG:raise ValueError('Pinned manifest byte bound')
    output.mkdir(parents=True)
    for ref,raw in records.items():(output/(ref+'.jsonl')).write_bytes(raw)
    (output/'case.json').write_bytes(encoded)
    return verify_pin(output)


def verify_pin(folder,expected_sha256=None):
    folder=Path(folder);path=regular(folder/'case.json')
    if path.stat().st_size>MAX_CATALOG:raise ValueError('Pinned manifest byte bound')
    if expected_sha256 is not None and evidence.sha256_file(path)!=expected_sha256:
        raise ValueError('Pinned context/manifest changed from receipt')
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('version')!=1 or not 1<=len(value.get('records',{}))<=MAX_PINS or set(value['records'])!=set(value['sources']):
        raise ValueError('Pinned manifest membership changed')
    for ref,row in value['records'].items():
        if not re.fullmatch(r'E-[a-f0-9]{16}',ref) or row['file']!=ref+'.jsonl':raise ValueError('Unsafe pinned filename')
        raw=regular(folder/row['file']).read_bytes();locator(value['sources'][ref])
        if ref!='E-'+value['sources'][ref]['sha256'][:16]:raise ValueError('Pinned reference does not match full digest')
        if len(raw)>MAX_RECORD or len(raw)!=row['bytes'] or digest(raw)!=row['sha256'] or digest(raw)!=value['sources'][ref]['sha256']:
            raise ValueError('Pinned source changed')
    return {'pinned_sources_verified':len(value['records']),'case_sha256':evidence.sha256_file(path)}


def retention_preview(log_path,catalog_path,archive_directory,*,now,days=7,pinned_sources=()):
    """List old sealed segments eligible for cold storage. Never deletes/moves.

    Missing timestamps, future dates, active records, unresolved pins, archive
    conflicts and missing archive coverage keep a segment in hot storage.
    """
    if now.tzinfo is None or type(days) is not int or not 1<=days<=365:raise ValueError('Explicit retention window required')
    files,index=evidence.layout(log_path)
    if not index:raise ValueError('An explicit segmented layout is required')
    rows=load_catalog(catalog_path)['archives'];valid=[];failures=[]
    for row in rows:
        try:verified_entry(archive_directory,row);valid.append(row)
        except (OSError,ValueError,zipfile.BadZipFile,KeyError) as error:failures.append(str(error))
    cutoff=now-dt.timedelta(days=days);offset=0;segments=[]
    pins=[locator(p) for p in pinned_sources]
    for position,(path,size) in enumerate(files):
        item={'segment':path.name,'start':offset,'bytes':size,'eligible_for_cold':False,'reason':'active_segment'}
        if position<len(files)-1:
            sha=evidence.sha256_file(path)
            if sha!=index['closed'][position]['sha256']:raise ValueError('Sealed source digest changed')
            covered=any(m['start']==offset and m['bytes']==size and m['sha256']==sha and m['member']=='logs/'+path.name
                        for row in valid for m in row['members'])
            pinned=any(start<offset+size and start+length>offset for start,length in pins)
            latest=None;bad=False
            with path.open('rb') as stream:
                while line:=stream.readline(MAX_RECORD+1):
                    if len(line)>MAX_RECORD or not line.endswith(b'\n'):bad=True;break
                    try:receipt=timestamp(json.loads(line)['received_utc'])
                    except (ValueError,KeyError,TypeError,UnicodeError):bad=True;break
                    latest=receipt if latest is None else max(latest,receipt)
            if pinned:item['reason']='pinned_source_retained_hot'
            elif not covered:item['reason']='no_matching_verified_archive'
            elif bad or latest is None:item['reason']='unknown_record_age'
            elif latest>now:item['reason']='future_timestamp'
            elif latest>=cutoff:item['reason']='within_hot_window'
            else:item.update(eligible_for_cold=True,reason='old_sealed_bytes_verified_in_archive')
            item['latest_received_utc']=latest.isoformat() if latest else None
        segments.append(item);offset+=size
    return {'version':1,'created_utc':now.isoformat(),'hot_days':days,'segments':segments,
            'eligible_bytes':sum(r['bytes'] for r in segments if r['eligible_for_cold']),
            'archive_failures':failures,'deletion_enabled':False,
            'scope':'Offline eligibility preview. Current live consumers still require all hot segments.'}
