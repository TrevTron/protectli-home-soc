"""Bounded rolling evidence with monotonic byte offsets and verified cold storage.

Version 2 is explicitly enabled by migration, never by opening a legacy source.
The receiver is the only manifest writer. Readers use a fixed manifest snapshot.
Expired offsets raise EvidenceExpired; new records never reuse those offsets.
"""
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
import uuid

MAX_ENTRIES = 128
MAX_MANIFEST = 256 * 1024
UTC = dt.timezone.utc


class EvidenceExpired(ValueError):
    pass


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            result.update(chunk)
    return result.hexdigest()


def save(path, value):
    data = (json.dumps(value, indent=2)+'\n').encode()
    if len(data) > MAX_MANIFEST:
        raise ValueError('Retention manifest exceeds bound')
    pending = Path(str(path)+'.pending-'+uuid.uuid4().hex)
    with pending.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, path)


def part(base, number):
    return base if number == 0 else base+f'.part{number:06d}'


class ExpiredPrefix:
    name = '[expired-prefix]'
    def open(self, mode):
        raise EvidenceExpired('Original record expired from rolling retention; use a saved case or baseline')


class ColdSegment:
    def __init__(self, path, entry):
        self.path = path
        self.name = entry['name']
        self.entry = entry

    def open(self, mode):
        if mode != 'rb':
            raise ValueError('Cold evidence is read only')
        # The compressed digest binds every byte, including records outside a lookup.
        if sha(self.path) != self.entry['archive_sha256']:
            raise ValueError('Cold archive digest changed; evidence withheld')
        return gzip.open(self.path, 'rb')


def read_layout(path):
    path = Path(path)
    manifest = Path(str(path)+'.segments.json')
    if manifest.is_symlink() or manifest.stat().st_size > MAX_MANIFEST:
        raise ValueError('Unsafe retention manifest')
    value = json.loads(manifest.read_text(encoding='utf-8'))
    if value.get('version') != 2 or value.get('base') != path.name:
        raise ValueError('Invalid rolling evidence manifest')
    for key in ('base_offset', 'first_part', 'active_part', 'max_bytes', 'segment_bytes', 'cold_max_bytes', 'retain_seconds'):
        if type(value.get(key)) is not int or value[key] < 0:
            raise ValueError('Invalid retention boundary')
    if not 0 < value['segment_bytes'] <= value['max_bytes'] or value['retain_seconds'] <= 0 or value['cold_max_bytes'] <= 0:
        raise ValueError('Invalid retention budget')
    closed = value['closed']
    if not isinstance(closed, list) or len(closed) > MAX_ENTRIES or value['active_part']-value['first_part'] != len(closed):
        raise ValueError('Invalid retained segment sequence')
    if value['active'] != part(path.name, value['active_part']):
        raise ValueError('Unsafe active segment name')
    files = [(ExpiredPrefix(), value['base_offset'])] if value['base_offset'] else []
    hot = cold = 0
    for number, entry in enumerate(closed, value['first_part']):
        if entry['name'] != part(path.name, number) or type(entry['bytes']) is not int or entry['bytes'] <= 0:
            raise ValueError('Unsafe sealed segment')
        if not re.fullmatch('[a-f0-9]{64}', entry['sha256']):
            raise ValueError('Invalid sealed digest')
        sealed = dt.datetime.fromisoformat(entry['sealed_utc'])
        if sealed.tzinfo is None:
            raise ValueError('Sealed time requires timezone')
        if entry['storage'] == 'hot':
            source = path.parent/entry['name']
            if source.is_symlink() or source.stat().st_size != entry['bytes']:
                raise ValueError('Sealed evidence length changed')
            hot += entry['bytes']
        elif entry['storage'] == 'cold':
            if entry['archive'] != entry['name']+'.gz' or not re.fullmatch('[a-f0-9]{64}', entry['archive_sha256']):
                raise ValueError('Unsafe cold archive identity')
            archive = path.parent/entry['archive']
            if archive.is_symlink() or archive.stat().st_size != entry['archive_bytes']:
                raise ValueError('Cold archive length changed')
            source = ColdSegment(archive, entry)
            cold += entry['archive_bytes']
        else:
            raise ValueError('Unknown evidence storage state')
        files.append((source, entry['bytes']))
    active = path.parent/value['active']
    if active.is_symlink():
        raise ValueError('Active evidence link refused')
    files.append((active, active.stat().st_size))
    hot += files[-1][1]
    if hot > value['max_bytes'] or cold > value['cold_max_bytes']:
        raise ValueError('Recorded retention budget exceeded')
    return files, value


def migrate(path, *, cold_max_bytes=4*1024**3, retain_seconds=7*86400, now=None):
    """Call only while the legacy receiver is stopped and a baseline is verified."""
    import soc_evidence as legacy
    path = Path(path)
    files, old = legacy.layout(path)
    if not old or old['version'] != 1:
        raise ValueError('Explicit version 1 segmented source required')
    now = now or dt.datetime.now(UTC)
    if now.tzinfo is None or cold_max_bytes <= 0 or retain_seconds <= 0:
        raise ValueError('Valid timezone and retention bounds required')
    closed = []
    for entry, (source, _) in zip(old['closed'], files):
        if sha(source) != entry['sha256']:
            raise ValueError('Original sealed digest changed')
        # Migration begins a conservative review window. No old evidence expires immediately.
        closed.append({**entry, 'sealed_utc': now.isoformat(), 'storage': 'hot'})
    value = {**old, 'version': 2, 'base_offset': 0, 'first_part': 0,
             'active_part': len(closed), 'closed': closed, 'cold_max_bytes': cold_max_bytes,
             'retain_seconds': retain_seconds, 'pending_cleanup': [], 'expired_segments': 0,
             'early_expired_segments': 0, 'migrated_utc': now.isoformat()}
    save(legacy.index_path(path), value)
    return value


class RetainedWriter:
    def __init__(self, path, max_bytes, segment_bytes, *, clock=None):
        self.path = Path(path)
        self.manifest = Path(str(path)+'.segments.json')
        self.clock = clock or (lambda: dt.datetime.now(UTC))
        files, self.value = read_layout(path)
        if self.value['max_bytes'] != max_bytes or self.value['segment_bytes'] != segment_bytes:
            raise ValueError('Recorded budgets differ; no silent change')
        for source, size in files[:-1]:
            if not isinstance(source, ExpiredPrefix) and sha(source) != next(e['sha256'] for e in self.value['closed'] if e['name'] == source.name):
                raise ValueError('Retained sealed digest changed')
        self.active = files[-1][0]
        self.active_size = files[-1][1]
        self.logical_end = sum(size for _, size in files)
        self.last_maintenance = 0
        self.cleanup()
        self.maintain()

    @property
    def total(self):
        return self.active_size+sum(e['bytes'] for e in self.value['closed'] if e['storage'] == 'hot')

    def commit(self):
        save(self.manifest, self.value)

    def cleanup(self):
        # Manifest is committed before reclaim. Exact names and hashes make crash recovery idempotent.
        pending = self.value.get('pending_cleanup', [])
        if not isinstance(pending, list) or len(pending) > 2*MAX_ENTRIES:
            raise ValueError('Cleanup receipt exceeds bound')
        deferred=[]
        for row in pending:
            if not re.fullmatch(re.escape(self.path.name)+r'(?:\.part\d{6,})?(?:\.gz)?', row['name']):
                raise ValueError('Unsafe cleanup name')
            target = self.path.parent/row['name']
            if target.exists():
                if target.is_symlink() or target.stat().st_size != row['bytes'] or sha(target) != row['sha256']:
                    raise ValueError('Cleanup source changed; preserve it')
                try:
                    target.unlink()
                except PermissionError:
                    # Windows readers may briefly hold an original open.
                    # Retain the exact cleanup receipt and retry later.
                    deferred.append(row)
        if pending != deferred:
            self.value['pending_cleanup'] = deferred
            self.commit()

    def reclaim(self, row):
        self.value['pending_cleanup'].append(row)

    def archive(self, entry):
        source = self.path.parent/entry['name']
        if sha(source) != entry['sha256']:
            raise ValueError('Archive source digest changed')
        destination = self.path.parent/(entry['name']+'.gz')
        pending = Path(str(destination)+'.pending')
        candidate = destination if destination.exists() else pending
        if candidate.is_symlink():
            raise ValueError('Archive link refused')
        if not candidate.exists():
            with source.open('rb') as raw, pending.open('xb') as output:
                with gzip.GzipFile(fileobj=output, mode='wb', mtime=0) as compressed:
                    shutil.copyfileobj(raw, compressed, 65536)
                output.flush()
                os.fsync(output.fileno())
        digest = hashlib.sha256()
        restored = 0
        # Recover a crash before or after rename only if the complete restored bytes match.
        with gzip.open(candidate, 'rb') as stream:
            for data in iter(lambda: stream.read(65536), b''):
                restored += len(data)
                if restored > entry['bytes']:
                    raise ValueError('Restored archive exceeds original boundary')
                digest.update(data)
        if restored != entry['bytes'] or digest.hexdigest() != entry['sha256']:
            raise ValueError('Archive restoration did not match original')
        if candidate != destination:
            os.replace(candidate, destination)
        entry.update(storage='cold', archive=destination.name, archive_bytes=destination.stat().st_size,
                     archive_sha256=sha(destination), archived_utc=self.clock().isoformat())
        self.reclaim({'name':source.name,'bytes':entry['bytes'],'sha256':entry['sha256']})
        self.commit()
        self.cleanup()

    def expire_first(self, *, early=False):
        entry = self.value['closed'].pop(0)
        self.value['base_offset'] += entry['bytes']
        self.value['first_part'] += 1
        self.value['expired_segments'] += 1
        self.value['early_expired_segments'] += int(early)
        if entry['storage'] == 'hot':
            row = {'name':entry['name'],'bytes':entry['bytes'],'sha256':entry['sha256']}
        else:
            row = {'name':entry['archive'],'bytes':entry['archive_bytes'],'sha256':entry['archive_sha256']}
        self.reclaim(row)
        self.commit()
        self.cleanup()

    def maintain(self, needed=0):
        self.cleanup()
        now = self.clock()
        if now.tzinfo is None:
            raise ValueError('Retention clock requires timezone')
        cutoff = now-dt.timedelta(seconds=self.value['retain_seconds'])
        while self.value['closed'] and dt.datetime.fromisoformat(self.value['closed'][0]['sealed_utc']) < cutoff:
            self.expire_first()
        # Capacity overflow moves sealed originals to verified cold storage before reclaiming hot files.
        while self.total+needed > self.value['max_bytes']:
            entry = next((e for e in self.value['closed'] if e['storage'] == 'hot'), None)
            if entry is None:
                break
            # Compression worst case is close to raw size. Reserve raw size plus bounded gzip overhead.
            reserve = entry['bytes']+65536
            while self.value['closed'] and sum(e.get('archive_bytes',0) for e in self.value['closed'])+reserve > self.value['cold_max_bytes']:
                self.expire_first(early=True)
                entry = next((e for e in self.value['closed'] if e['storage'] == 'hot'), None)
                if entry is None:
                    break
                reserve = entry['bytes']+65536
            if entry is None:
                break
            if reserve > self.value['cold_max_bytes']:
                raise ValueError('Cold budget cannot hold a sealed segment')
            self.archive(entry)
        self.last_maintenance = time.monotonic()

    def append(self, data):
        if not data.endswith(b'\n') or len(data) > 65536:
            raise ValueError('Only bounded complete records may be appended')
        if self.active_size and self.active_size+len(data) > self.value['segment_bytes']:
            with self.active.open('rb') as source:
                source.seek(-1,2)
                if source.read(1) != b'\n':
                    raise ValueError('Cannot seal an incomplete original record')
            while len(self.value['closed']) >= MAX_ENTRIES:
                self.expire_first(early=True)
            entry = {'name':self.active.name,'bytes':self.active_size,'sha256':sha(self.active),
                     'sealed_utc':self.clock().isoformat(),'storage':'hot'}
            next_part = self.value['active_part']+1
            next_path = self.path.parent/part(self.path.name, next_part)
            if next_path.exists():
                if next_path.is_symlink() or next_path.stat().st_size:
                    raise ValueError('Unexpected rollover part; preserve it')
            else:
                next_path.touch(exist_ok=False)
            self.value['closed'].append(entry)
            self.value.update(active_part=next_part, active=next_path.name)
            self.commit()
            self.active = next_path
            self.active_size = 0
        if self.total+len(data) > self.value['max_bytes'] or time.monotonic()-self.last_maintenance > 300:
            self.maintain(len(data))
        if self.total+len(data) > self.value['max_bytes']:
            return False
        with self.active.open('ab') as stream:
            stream.write(data)
        self.active_size += len(data)
        self.logical_end += len(data)
        return True

    def status(self):
        return {'mode':'rolling-v2','hot_bytes':self.total,
                'cold_bytes':sum(e.get('archive_bytes',0) for e in self.value['closed']),
                'cold_max_bytes':self.value['cold_max_bytes'],'logical_end':self.logical_end,
                'first_retained_offset':self.value['base_offset'],'retention_days':self.value['retain_seconds']/86400,
                'expired_segments':self.value['expired_segments'],
                'early_expired_segments':self.value['early_expired_segments'],
                'deferred_cleanup_bytes':sum(e['bytes'] for e in self.value.get('pending_cleanup',[])),
                'deferred_cleanup_files':len(self.value.get('pending_cleanup',[]))}
