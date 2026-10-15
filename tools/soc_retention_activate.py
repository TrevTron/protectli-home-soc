"""Activate bounded retention only after the ownership-checked maintenance preflight."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shutil

import soc_evidence as evidence
import soc_preserved_evidence as preserved
import soc_retained_evidence as rolling


def activate(source,receipt):
    source=Path(source);receipt=Path(receipt)
    preflight=json.loads((receipt/'maintenance-preflight.json').read_text(encoding='utf-8-sig'))
    if not all(preflight.get(k) is True for k in ('receiver_absent','collector_sockets_absent','recovery_paused')):
        raise ValueError('Stopped owned receiver and paused recovery required')
    if Path(preflight['log']).resolve()!=source.resolve() or Path(preflight['receipt']).resolve()!=receipt.resolve():
        raise ValueError('Maintenance preflight belongs to another target')
    age=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(preflight['started_utc'])).total_seconds()
    if not 0<=age<=300:raise ValueError('Maintenance preflight is stale')
    before=evidence.index_path(source).read_bytes()
    if before!=(receipt/'original-segments.json').read_bytes():raise ValueError('Original manifest changed since maintenance preflight')
    files,layout=evidence.layout(source)
    if layout['version']!=1:raise ValueError('Only the recorded legacy source may be migrated')
    if preserved.descriptor(source).exists():
        baseline=preserved.verify_baseline(source)
        if baseline['verified_prefix_bytes']!=sum(size for _,size in files):raise ValueError('Previous baseline does not cover the stopped source')
        with evidence.open_evidence(source) as stream:
            import hashlib
            digest=hashlib.sha256()
            for raw in iter(lambda:stream.read(65536),b''):digest.update(raw)
        _,descriptor=preserved.baseline_layout(source)
        if digest.hexdigest()!=descriptor['prefix_sha256']:raise ValueError('Stopped source differs from saved baseline')
    else:preserved.create_baseline(source)
    baseline=preserved.verify_baseline(source)
    shutil.copy2(preserved.descriptor(source),receipt/'baseline-descriptor.json')
    value=rolling.migrate(source)
    writer=evidence.SegmentWriter(source,value['max_bytes'],value['segment_bytes'])
    result={'activated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'baseline':baseline,'retention':writer.status(),
        'hot_max_bytes':value['max_bytes'],'cold_max_bytes':value['cold_max_bytes'],
        'append_test':'not inserted into live evidence; verify subsequent real Vault receipts',
        'maintenance_gap':'UDP messages during the stopped interval may be lost'}
    (receipt/'activation-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log',type=Path,required=True);parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(activate(args.log,args.receipt)))
