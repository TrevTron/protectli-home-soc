"""Derived SQLite investigation index. Original JSONL remains authoritative.

One transactional writer, WAL readers, stable logical offsets across rollover.
No evidence deletion, model calls, firewall changes, or network listeners.
"""
import argparse
from contextlib import closing
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3
import time

import soc_analyst as analyst
import soc_evidence

VERSION = 1
GROUP_POLICY = 'exact-flow-repetition-v1'
MAX_BATCH = 8 * 1024 * 1024
MAX_DB = 1024 * 1024 * 1024
FIELDS = ('sid', 'gid', 'rev', 'signature', 'action', 'alert_severity', 'protocol',
          'source_ip', 'source_port', 'destination_ip', 'destination_port')


def connect(path, readonly=False):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Index link refused')
    if readonly:
        db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=2)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path, timeout=2)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        page_size=db.execute('PRAGMA page_size').fetchone()[0]
        db.execute('PRAGMA max_page_count='+str(MAX_DB//page_size))
        db.execute('PRAGMA wal_autocheckpoint=1000')
        db.execute('PRAGMA journal_size_limit=16777216')
    db.row_factory = sqlite3.Row
    return db


def initialize(db, source):
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version not in (0, VERSION):
        raise ValueError('Unsupported index schema; preserve the existing database')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS records (
        offset INTEGER PRIMARY KEY, length INTEGER NOT NULL, sha256 TEXT NOT NULL,
        segment TEXT NOT NULL, segment_offset INTEGER NOT NULL,
        received TEXT, received_epoch REAL, device_timestamp TEXT,
        application TEXT, syslog_severity TEXT, event_type TEXT, parse_error TEXT,
        sid INTEGER, gid INTEGER, rev INTEGER, signature TEXT, action TEXT,
        alert_severity INTEGER, protocol TEXT, source_ip TEXT, source_port INTEGER,
        destination_ip TEXT, destination_port INTEGER, group_key TEXT);
      CREATE INDEX IF NOT EXISTS records_window ON records(received_epoch, offset);
      CREATE INDEX IF NOT EXISTS records_group ON records(group_key, received_epoch, offset);
    ''')
    path = str(Path(source).resolve())
    old = db.execute("SELECT value FROM meta WHERE key='source'").fetchone()
    if old and old[0] != path:
        raise ValueError('Index belongs to another original source')
    with db:
        db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('source', path))
        db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('checkpoint', '0'))
        db.execute('PRAGMA user_version=1')


def metadata(db):
    return {row['key']: row['value'] for row in db.execute('SELECT * FROM meta')}


def parse(line):
    values = dict.fromkeys(('received', 'received_epoch', 'device_timestamp',
                           'application', 'syslog_severity', 'event_type', 'parse_error', *FIELDS, 'group_key'))
    try:
        record = analyst.strict_json(line.decode('utf-8'))
        receipt = analyst.timestamp(record['received_utc'])
        values.update(received=receipt.isoformat(), received_epoch=receipt.timestamp(),
                      device_timestamp=str(record.get('source_timestamp', ''))[:200],
                      application=str(record.get('app', 'unknown'))[:100],
                      syslog_severity=str(record.get('severity', 'unknown'))[:40], event_type='syslog')
        eve = analyst.eve_from_record(record)
        if eve is not None:
            alert = eve['alert']
            values.update(event_type='alert', sid=alert['signature_id'], gid=alert.get('gid'),
                          rev=alert.get('rev'), signature=str(alert.get('signature', ''))[:512],
                          action=alert['action'], alert_severity=alert.get('severity'),
                          protocol=eve.get('proto'), source_ip=eve.get('src_ip'), source_port=eve.get('src_port'),
                          destination_ip=eve.get('dest_ip'), destination_port=eve.get('dest_port'),
                          device_timestamp=str(eve.get('timestamp', ''))[:200])
            if (type(values['sid']) is not int or not 1 <= values['sid'] <= 2**32-1 or
                values['action'] not in ('allowed', 'blocked') or
                values['protocol'] not in ('TCP', 'UDP', 'ICMP', 'ICMPv6') or
                type(values['alert_severity']) is not int or values['alert_severity'] not in (1, 2, 3)):
                raise ValueError('Incomplete or invalid alert context')
            for name in ('gid', 'rev'):
                if values[name] is not None and (type(values[name]) is not int or not 0 <= values[name] <= 2**32-1):
                    raise ValueError('Invalid rule identity')
            import ipaddress
            for name in ('source_ip', 'destination_ip'):
                values[name] = str(ipaddress.ip_address(values[name]))
            for name in ('source_port', 'destination_port'):
                port = values[name]
                if port is not None and (type(port) is not int or not 0 <= port <= 65535):
                    raise ValueError('Invalid port')
            # Missing transport ports or rule revision stay singletons. No inferred equivalence.
            missing = any(values[f] is None for f in ('gid', 'rev')) or (
                values['protocol'] in ('TCP', 'UDP') and any(values[f] is None for f in ('source_port', 'destination_port')))
            if not missing:
                values['group_key'] = hashlib.sha256(analyst.canonical([GROUP_POLICY, *[values[f] for f in FIELDS]]).encode()).hexdigest()
    except (ValueError, KeyError, TypeError, AttributeError, UnicodeError) as error:
        values['parse_error'] = str(error)[:200]
        values['group_key'] = None
    return values


def sync(database, source, max_bytes=MAX_BATCH):
    if not 1 <= max_bytes <= MAX_BATCH:
        raise ValueError('Bounded index batch required')
    files, manifest_value = soc_evidence.layout(source)
    floor = (manifest_value or {}).get('base_offset',0)
    total = sum(size for _, size in files)
    if Path(database).exists() and Path(database).stat().st_size > MAX_DB:
        raise ValueError('Derived index exceeds its independent 1 GiB budget')
    db = connect(database)
    try:
        initialize(db, source)
        # BEGIN IMMEDIATE serializes cooperating writers and rolls back rows + checkpoint together.
        db.execute('BEGIN IMMEDIATE')
        meta = metadata(db)
        start = int(meta['checkpoint'])
        expired_unindexed = max(0,floor-start)
        # Expired records never point to newly appended bytes. Pruning reuses SQLite pages.
        db.execute('DELETE FROM records WHERE offset<?',(floor,))
        start = max(start,floor)
        if total < start:
            raise ValueError('Original evidence shortened; no index rewind')
        with soc_evidence.open_evidence(source) as stream:
            previous = db.execute('SELECT offset,length,sha256 FROM records ORDER BY offset DESC LIMIT 1').fetchone()
            if previous:
                stream.seek(previous['offset'])
                if analyst.digest(stream.read(previous['length'])) != previous['sha256']:
                    raise ValueError('Indexed boundary source changed')
            # Sealed segments are verified once when their manifest identity changes.
            manifest = soc_evidence.index_path(source)
            identity = analyst.digest(manifest.read_bytes()) if manifest.exists() else ''
            if identity != meta.get('manifest_sha256', ''):
                _, layout = soc_evidence.layout(source)
                sources={segment.name:segment for segment,_ in files}
                for closed in (layout or {}).get('closed', []):
                    if soc_evidence.sha256_file(sources[closed['name']]) != closed['sha256']:
                        raise ValueError('Sealed source hash changed')
            stream.seek(start)
            position = start
            rows = 0
            while position < total and position-start < max_bytes:
                line = stream.readline(min(analyst.MAX_LINE+1, total-position))
                if not line.endswith(b'\n'):
                    if len(line) > analyst.MAX_LINE:
                        raise ValueError('Oversized original record; indexing stopped without dropping it')
                    break  # incomplete append, checkpoint does not cross it
                if len(line) > analyst.MAX_LINE:
                    raise ValueError('Oversized original record')
                values = parse(line)
                segment_start = 0
                for segment, size in files:
                    if segment_start <= position < segment_start+size:
                        segment_name, local_offset = segment.name, position-segment_start
                        break
                    segment_start += size
                names = ('offset', 'length', 'sha256', 'segment', 'segment_offset', *values.keys())
                record_values = (position, len(line), analyst.digest(line), segment_name, local_offset, *values.values())
                db.execute('INSERT INTO records ('+','.join(names)+') VALUES ('+','.join('?' for _ in names)+')', record_values)
                position += len(line)
                rows += 1
        for key, value in {'checkpoint': str(position), 'source_bytes': str(total), 'manifest_sha256': identity,
                           'first_retained_offset':str(floor),
                           'expired_unindexed_bytes':str(int(meta.get('expired_unindexed_bytes','0'))+expired_unindexed),
                           'updated_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'group_policy': GROUP_POLICY}.items():
            db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key, value))
        db.commit()
        return {'new_records': rows, 'indexed_bytes': position, 'source_bytes': total,
                'backlog_bytes': total-position, 'caught_up': position == total, 'group_policy': GROUP_POLICY,
                'first_retained_offset':floor,'expired_unindexed_bytes':expired_unindexed}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def status(database):
    with closing(connect(database, True)) as db:
        meta = metadata(db)
        counts = db.execute('SELECT COUNT(*) AS records, SUM(event_type="alert") AS alerts, SUM(parse_error IS NOT NULL) AS malformed FROM records').fetchone()
        return {**meta, **dict(counts)}


def groups(database, minutes=15, limit=100, now=None, client=None, offset=0):
    if not 1 <= minutes <= 1440 or not 1 <= limit <= 200 or not 0<=offset<=10000:
        raise ValueError('Bounded group query required')
    now = now or dt.datetime.now(dt.timezone.utc)
    with closing(connect(database, True)) as db:
        where = 'event_type="alert" AND received_epoch BETWEEN ? AND ?'
        args = [(now-dt.timedelta(minutes=minutes)).timestamp(), now.timestamp()]
        if client:
            where += ' AND (source_ip=? OR destination_ip=?)'
            args += [client, client]
        key = 'COALESCE(group_key, "single-" || offset)'
        columns = ','.join(FIELDS)
        query = f'''SELECT {key} AS group_id, {columns}, MIN(offset) AS first_offset,
          MAX(offset) AS last_offset, MIN(received) AS first_received, MAX(received) AS last_received,
          COUNT(*) AS count, SUM(parse_error IS NOT NULL) AS malformed
          FROM records WHERE {where} GROUP BY {key}
          ORDER BY (action="blocked" OR alert_severity=1) DESC, alert_severity ASC, count DESC, first_offset DESC LIMIT ? OFFSET ?'''
        result = [dict(row) for row in db.execute(query, [*args, limit+1, offset])]
        total = db.execute(f'SELECT COUNT(*) FROM (SELECT 1 FROM records WHERE {where} GROUP BY {key})', args).fetchone()[0]
        return {'groups': result[:limit], 'total_groups': total, 'omitted_groups': max(0,total-len(result[:limit])),
                'offset':offset,'has_more':offset+limit<total,'next_offset':offset+limit if offset+limit<total else None,
                'window_minutes': minutes, 'generated_utc': now.isoformat(), 'policy': GROUP_POLICY,
                'index': metadata(db), 'source_delivery_complete': False}


def members(database, group_id, minutes=15, limit=50, before=None, now=None):
    if not 1 <= limit <= 100 or not 1 <= minutes <= 1440:
        raise ValueError('Bounded member query required')
    now = now or dt.datetime.now(dt.timezone.utc)
    with closing(connect(database, True)) as db:
        where = 'COALESCE(group_key,"single-" || offset)=? AND received_epoch BETWEEN ? AND ?'
        args = [group_id, (now-dt.timedelta(minutes=minutes)).timestamp(), now.timestamp()]
        if before is not None:
            where += ' AND offset<?'
            args.append(int(before))
        rows = [dict(r) for r in db.execute('SELECT * FROM records WHERE '+where+' ORDER BY offset DESC LIMIT ?', [*args,limit+1])]
        return {'records': rows[:limit], 'has_more': len(rows)>limit, 'next_before': rows[limit-1]['offset'] if len(rows)>limit else None}


def original(database, offset):
    with closing(connect(database, True)) as db:
        row = db.execute('SELECT * FROM records WHERE offset=?', (int(offset),)).fetchone()
        if not row:
            source=metadata(db)['source']
            _,layout=soc_evidence.layout(source)
            if 0<=int(offset)<(layout or {}).get('base_offset',0):
                from soc_retained_evidence import EvidenceExpired
                raise EvidenceExpired('Source record expired from the rolling index')
            raise ValueError('Unknown source offset')
        source = metadata(db)['source']
    import soc_preserved_evidence
    line=soc_preserved_evidence.read_record(source,{'byte_offset':row['offset'],
          'byte_length':row['length'],'sha256':row['sha256']},pin_root=Path(database).parent)
    if analyst.digest(line) != row['sha256']:
        raise ValueError('Original source hash mismatch; evidence withheld')
    return line.decode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--follow', action='store_true')
    parser.add_argument('--interval', type=int, default=10)
    args = parser.parse_args()
    if not 5 <= args.interval <= 300:
        parser.error('Interval must be 5-300 seconds')
    while True:
        value = sync(args.database, args.log)
        print(json.dumps(value), flush=True)
        if not args.follow:
            if value['caught_up'] or value['new_records'] == 0:
                break
        else:
            time.sleep(0.1 if value['new_records'] and not value['caught_up'] else args.interval)


if __name__ == '__main__':
    main()
