"""Bounded private checkpoint archives. All original files remain in place."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import tempfile
import zipfile
import os

import soc_evidence as evidence
import soc_operator as operator

MAX_MEMBERS=16384
MAX_ARCHIVE_INPUT=2*1024**3
MAX_MEMBER=1024**2
MAX_MANIFEST=4*1024**2
DEFAULT_ARCHIVE_BUDGET=4*1024**3
RAW_LIMIT=1024**3
CHUNK=256*1024


def digest(data):return hashlib.sha256(data).hexdigest()


def copy_exact(source,length,destination=None,hasher=None):
    value=hashlib.sha256()
    remaining=length
    while remaining:
        chunk=source.read(min(CHUNK,remaining))
        if not chunk:raise ValueError('Original evidence shortened')
        remaining-=len(chunk);value.update(chunk)
        if hasher is not None:hasher.update(chunk)
        if destination is not None:destination.write(chunk)
    return value.hexdigest()


def source_matches(stream,source,total):
    offset,length=source['byte_offset'],source['byte_length']
    if type(offset) is not int or type(length) is not int or offset<0 or not 1<=length<=MAX_MEMBER or offset+length>total:
        return False
    stream.seek(offset)
    return copy_exact(stream,length)==source['sha256']


def complete_prefix(path,size):
    if not size:return 0
    with path.open('rb') as source:
        source.seek(size-1)
        if source.read(1)==b'\n':return size
        start=max(0,size-MAX_MEMBER)
        source.seek(start);tail=source.read(size-start)
        end=tail.rfind(b'\n')
        if end<0 and start:raise ValueError('Incomplete original record exceeds bound')
        return start+end+1 if end>=0 else 0


def verify_archive(path):
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryFile() as raw:
        names=archive.namelist()
        if len(names)>MAX_MEMBERS+1 or len(set(names))!=len(names):raise ValueError('Archive member count/duplicates')
        if archive.getinfo('archive-manifest.json').file_size>MAX_MANIFEST:raise ValueError('Archive manifest oversized')
        manifest=json.loads(archive.read('archive-manifest.json'))
        expected={item['file'] for item in manifest['files']}|{'archive-manifest.json'}
        if set(names)!=expected:raise ValueError('Unlisted archive member')
        total=0;raw_size=0
        log_names=manifest['logical_log_members']
        if len(set(log_names))!=len(log_names) or any(name not in expected or not name.startswith('logs/') for name in log_names):
            raise ValueError('Invalid logical archive members')
        listed={item['file']:item for item in manifest['files']}
        ordered=[listed[name] for name in log_names]+[item for item in manifest['files'] if item['file'] not in log_names]
        for item in ordered:
            name=item['file']
            if Path(name).is_absolute() or ':' in name or '\\' in name or '..' in Path(name).parts:raise ValueError('Unsafe archive member')
            size=archive.getinfo(name).file_size
            total+=size
            if total>MAX_ARCHIVE_INPUT or size!=item['bytes']:raise ValueError('Archive input budget/length')
            if name not in log_names and size>MAX_MEMBER:raise ValueError('State artifact exceeds bound')
            if name in log_names:
                raw_size+=size
                if raw_size>RAW_LIMIT:raise ValueError('Archive raw budget reached')
            with archive.open(name) as source:
                sha=copy_exact(source,size,raw if name in log_names else None)
                source.read(1)  # Read through EOF/CRC without materializing the raw log.
            if sha!=item['sha256']:raise ValueError('Archive member changed')
        raw.flush()
        if manifest.get('raw_prefix_sha256'):
            raw.seek(0)
            if copy_exact(raw,raw_size)!=manifest['raw_prefix_sha256']:raise ValueError('Restored raw prefix changed')
        references=0
        for name in names:
            if name.startswith('analyst/runs/') and name.endswith('/sources.json'):
                for source in json.loads(archive.read(name))['sources'].values():
                    if not source_matches(raw,source,raw_size):
                        raise ValueError('Restored citation mismatch')
                    references+=1
        notes=[]
        if 'analyst/operator-review.jsonl' in names:
            previous='0'*64
            for line in archive.read('analyst/operator-review.jsonl').splitlines():
                note=json.loads(line);sha=note.pop('entry_sha256')
                if note['previous_sha256']!=previous or sha!=digest(operator.a.canonical(note).encode()) or note['sequence']!=len(notes)+1:
                    raise ValueError('Archived operator note chain changed')
                brief_bytes=archive.read('analyst/runs/'+note['run']+'/brief.json')
                if digest(brief_bytes)!=note['brief_sha256']:raise ValueError('Archived pinned brief changed')
                group=next(g for g in json.loads(brief_bytes)['groups'] if g['id']==note['group_id'])
                if operator.evidence_fingerprint(group)!=note['evidence_fingerprint']:raise ValueError('Archived pinned group changed')
                notes.append(note);previous=sha
        if len(notes)!=manifest['operator_notes_verified']:raise ValueError('Archived note count changed')
        return {'files_verified':len(manifest['files']),'source_references_verified':references,
                'raw_prefix_bytes':raw_size,'saved_report_bundles':len(manifest['saved_runs']),
                'operator_notes_verified':len(notes)}


def checkpoint(log_path,data_dir,archive_dir,*,max_archive_bytes=DEFAULT_ARCHIVE_BUDGET,now=None):
    archive_dir=Path(archive_dir);archive_dir.mkdir(parents=True,exist_ok=True)
    with evidence.exclusive_lock(archive_dir/'archive.lock'):
        return _checkpoint(log_path,data_dir,archive_dir,max_archive_bytes=max_archive_bytes,now=now)


def _checkpoint(log_path,data_dir,archive_dir,*,max_archive_bytes,now):
    log_path=Path(log_path);data_dir=Path(data_dir);archive_dir=Path(archive_dir)
    now=now or dt.datetime.now(dt.timezone.utc)
    archive_dir.mkdir(parents=True,exist_ok=True)
    files,index=evidence.layout(log_path)
    if index and index.get('version')==2:
        return managed_checkpoint(log_path,data_dir,archive_dir,files,index,now)
    existing=[path for path in archive_dir.glob('checkpoint-*') if path.name.endswith(('.zip','.zip.pending'))]
    if len(existing)>=64 or sum(path.stat().st_size for path in existing)>=max_archive_bytes:
        raise ValueError('Private archive budget reached; preserve/export before resuming')
    entries={};log_members=[];raw_size=0
    for position,(path,size) in enumerate(files):
        if size>200*1024**2:raise ValueError('Raw member exceeds receiver bound')
        if position==len(files)-1:size=complete_prefix(path,size)
        name='logs/'+path.name
        entries[name]=(path,size);log_members.append(name);raw_size+=size
    if raw_size>RAW_LIMIT:raise ValueError('Archive raw budget reached')
    if index:entries['logs/'+evidence.index_path(log_path).name]=(json.dumps(index,indent=2)+'\n').encode()
    worker_path=data_dir/'worker-state.json'
    worker=json.loads(worker_path.read_text(encoding='utf-8-sig')) if worker_path.exists() else {}
    saved=[];skipped=[]
    run_root=data_dir/'runs'
    for run in sorted(run_root.iterdir()) if run_root.exists() else []:
        if not run.is_dir():continue
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',run.name):raise ValueError('Invalid saved run name')
        if worker.get('status')=='analyzing' and worker.get('run')==run.name:
            skipped.append(run.name);continue
        if not all((run/name).is_file() for name in ('brief.json','sources.json','report.html')):
            skipped.append(run.name);continue
        source_map=json.loads((run/'sources.json').read_text(encoding='utf-8-sig'))['sources']
        if any(source['byte_offset']+source['byte_length']>raw_size for source in source_map.values()):
            skipped.append(run.name);continue
        with evidence.open_evidence(log_path) as original:
            for source in source_map.values():
                if not source_matches(original,source,raw_size):raise ValueError('Original citation changed; archive withheld')
        for path in sorted(run.iterdir()):
            if path.is_file():
                if path.is_symlink() or path.stat().st_size>MAX_MEMBER:raise ValueError('Saved artifact exceeds bound/link refused')
                entries['analyst/runs/'+run.name+'/'+path.name]=path.read_bytes()
        saved.append(run.name)
    for name in ('operator-review.jsonl','latest.json','health-snapshot.json','worker-state.json','native-health-state.json','startup-state.json','endpoint-context-index.json'):
        path=data_dir/name
        if path.exists():
            if path.is_symlink() or path.stat().st_size>MAX_MEMBER:raise ValueError('State artifact exceeds bound')
            if name=='latest.json' and json.loads(path.read_text(encoding='utf-8-sig')).get('run') not in saved:continue
            entries['analyst/'+name]=path.read_bytes()
    context=data_dir/'endpoint-context-index.json'
    if context.exists():
        for location in json.loads(context.read_text(encoding='utf-8-sig')).values():
            name=location['file']
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}\.json',name):raise ValueError('Invalid endpoint context path')
            path=data_dir/name
            if path.is_symlink() or path.stat().st_size>MAX_MEMBER:raise ValueError('Endpoint context exceeds bound')
            entries['analyst/'+name]=path.read_bytes()
    notes=operator.load_journal(data_dir)
    for note in notes:
        brief_data=entries['analyst/runs/'+note['run']+'/brief.json']
        if digest(brief_data)!=note['brief_sha256']:raise ValueError('Pinned note brief changed')
        group=next(g for g in json.loads(brief_data)['groups'] if g['id']==note['group_id'])
        if operator.evidence_fingerprint(group)!=note['evidence_fingerprint']:raise ValueError('Pinned note group changed')
    if len(entries)>MAX_MEMBERS or sum(value[1] if isinstance(value,tuple) else len(value) for value in entries.values())>MAX_ARCHIVE_INPUT:raise ValueError('Archive input budget reached')
    manifest={'created_utc':now.isoformat(),'logical_log_members':log_members,'saved_runs':saved,'skipped_runs':skipped,
              'operator_notes_verified':len(notes),'original_source_path':str(log_path.resolve()),
              'files':[],
              'scope':'Private point-in-time bytes and restored citation verification; active incomplete runs excluded. No rotation/deletion, model weights, training files or full application disaster-restore claim.'}
    name='checkpoint-'+now.strftime('%Y%m%dT%H%M%S%fZ')+'.zip'
    pending=archive_dir/(name+'.pending')
    raw_hash=hashlib.sha256()
    with zipfile.ZipFile(pending,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for member,data in entries.items():
            if isinstance(data,tuple):
                source_path,size=data
                with source_path.open('rb') as source,archive.open(member,'w',force_zip64=True) as destination:
                    sha=copy_exact(source,size,destination,raw_hash)
            else:
                size=len(data);sha=digest(data);archive.writestr(member,data)
            manifest['files'].append({'file':member,'bytes':size,'sha256':sha})
        manifest['files'].sort(key=lambda item:item['file'])
        manifest['raw_prefix_sha256']=raw_hash.hexdigest()
        archive.writestr('archive-manifest.json',json.dumps(manifest,indent=2)+'\n')
    checked=verify_archive(pending)
    if sum(path.stat().st_size for path in existing)+pending.stat().st_size>max_archive_bytes:
        raise ValueError('Compressed archive budget reached; verified pending file preserved')
    with evidence.open_evidence(log_path) as source:
        if copy_exact(source,raw_size)!=raw_hash.hexdigest():raise ValueError('Original prefix changed during archive')
    journal=data_dir/'operator-review.jsonl'
    if journal.exists() and journal.read_bytes()!=entries['analyst/operator-review.jsonl']:
        raise ValueError('Operator notes changed during archive')
    destination=archive_dir/name
    pending.rename(destination)
    receipt={**checked,'archive':name,'archive_bytes':destination.stat().st_size,'archive_sha256':evidence.sha256_file(destination),
             'checked_utc':now.isoformat(),'original_prefix_unchanged':True,'operator_journal_unchanged':True,
             'archive_budget_bytes':max_archive_bytes,'archive_input_limit_bytes':MAX_ARCHIVE_INPUT,
             'raw_limit_bytes':RAW_LIMIT,'stream_chunk_bytes':CHUNK,
             'skipped_runs':skipped,'originals_deleted_or_rotated':False}
    (archive_dir/(name+'.receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt


def managed_checkpoint(log_path,data_dir,archive_dir,files,index,now):
    """Verify managed cold segments and reviewed pins, without duplicate ZIPs.

    One bounded latest receipt replaces the previous receipt. Historic receipts
    remain in the operating journal; existing legacy ZIPs are never removed.
    """
    import soc_preserved_evidence as preserved
    by_name={path.name:path for path,size in files}
    for row in index['closed']:
        if evidence.sha256_file(by_name[row['name']])!=row['sha256']:
            raise ValueError('Managed sealed original changed; checkpoint withheld')
    references=0;notes=operator.load_journal(data_dir)
    for note in notes:
        brief,brief_hash=operator.read_brief(data_dir,note['run'])
        if brief_hash!=note['brief_sha256']:raise ValueError('Saved note brief changed')
        group=next(g for g in brief['groups'] if g['id']==note['group_id'])
        if operator.evidence_fingerprint(group)!=note['evidence_fingerprint']:
            raise ValueError('Saved note group changed')
        source_map=json.loads((data_dir/'runs'/note['run']/'sources.json').read_text())
        for ref in group['evidence_refs']:
            preserved.read_record(source_map['source_path'],source_map['sources'][ref],pin_root=data_dir)
            references+=1
    baseline=preserved.verify_baseline(log_path) if preserved.descriptor(log_path).exists() else None
    receipt={'mode':'rolling-v2-managed','checked_utc':now.isoformat(),
             'sealed_segments_verified':len(index['closed']),
             'source_references_verified':references,'operator_notes_verified':len(notes),
             'first_retained_offset':index['base_offset'],
             'logical_end':sum(size for path,size in files),
             'hot_bytes':files[-1][1]+sum(e['bytes'] for e in index['closed'] if e['storage']=='hot'),
             'cold_bytes':sum(e.get('archive_bytes',0) for e in index['closed']),
             'baseline':baseline,'expired_segments':index['expired_segments'],
             'early_expired_segments':index['early_expired_segments'],
             'scope':'Managed sealed-original hashes and reviewed source pins. Active appends are not sealed. Unreviewed future reports may lose raw sources after expiry. No additional full-history ZIP or application disaster-restore claim.'}
    raw=(json.dumps(receipt,indent=2)+'\n').encode()
    if len(raw)>65536:raise ValueError('Managed receipt exceeds bound')
    pending=archive_dir/'managed-retention-state.json.pending'
    with pending.open('wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(pending,archive_dir/'managed-retention-state.json')
    return receipt
