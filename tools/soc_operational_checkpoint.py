"""Five-minute read-only operation receipts and six-hour verified checkpoints."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import urllib.request
from zipfile import BadZipFile

import soc_archive


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def read_state(path):
    if path.stat().st_size>65536:raise ValueError('Operational state exceeds bound')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path,value):
    pending=Path(str(path)+'.pending')
    pending.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    os.replace(pending,path)


def stamp(value):return dt.datetime.fromisoformat(value.replace('Z','+00:00'))


def observe(data,log,archive,*,now=None):
    data=Path(data)
    with soc_archive.evidence.exclusive_lock(data/'observation.lock'):
        return _observe(data,log,archive,now=now)


def _observe(data,log,archive,*,now=None):
    data=Path(data);log=Path(log);archive=Path(archive)
    now=now or dt.datetime.now(dt.timezone.utc)
    path=data/'observation-state.json'
    state=read_state(path) if path.exists() else {
        'started_utc':now.isoformat(),'ends_utc':(now+dt.timedelta(hours=48)).isoformat(),
        'samples':0,'gap_count':0,'max_samples':576,'period_seconds':300,
        'status':'collecting','scope':'User-sign-in observation, not complete traffic delivery or independent model accuracy'}
    if now>=stamp(state['ends_utc']) or state['samples']>=state['max_samples']:
        state['status']='observation_window_finished'
        state['completed_utc']=now.isoformat()
        save(path,state)
        return state
    if state.get('last_sample_utc') and (now-stamp(state['last_sample_utc'])).total_seconds()<240:return state
    if state.get('last_sample_utc') and (now-stamp(state['last_sample_utc'])).total_seconds()>600:state['gap_count']+=1
    sample={'observed_utc':now.isoformat(),'receiver':'unknown','analyst':'unknown','native':'unknown'}
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    for port,route,key in ((8765,'api/events','receiver'),(8766,'api/status','analyst')):
        try:
            with opener.open(f'http://127.0.0.1:{port}/{route}',timeout=3) as response:raw=response.read(4*1024**2+1)
            if len(raw)>4*1024**2:raise ValueError('API response oversized')
            value=json.loads(raw)
            fields=('accepted_this_run','retention_full','storage_error','segment_count','stored_bytes','max_bytes','capacity_warning','growth_bytes_per_second','estimated_hours_remaining','rolling_retention') if key=='receiver' else ('run','status','completed_utc','age_seconds','worker_finished')
            sample[key]={name:value.get(name) for name in fields}
        except (OSError,ValueError) as error:sample[key]={'status':'unavailable','reason':str(error)[:300]}
    try:
        native=read_state(data/'health-snapshot.json')
        age=(now-stamp(native['collected_utc'])).total_seconds()
        sample['native']={'collected_utc':native['collected_utc'],'age_seconds':round(age),'stale':age>600,'vault':native['vault']}
    except (OSError,ValueError,KeyError) as error:sample['native']={'status':'unavailable','reason':str(error)[:300]}
    journal=data/'operational-observations.jsonl'
    line=(json.dumps(sample,separators=(',',':'))+'\n').encode()
    if (journal.stat().st_size if journal.exists() else 0)+len(line)>1024**2:
        state['status']='observation_receipt_limit_reached';save(path,state);return state
    with journal.open('ab') as stream:stream.write(line)
    state['samples']+=1;state['last_sample_utc']=now.isoformat();state['last_sample']=sample;state['status']='collecting'
    archive_due=not state.get('last_archive_attempt_utc') or (now-stamp(state['last_archive_attempt_utc'])).total_seconds()>=21600
    if archive_due:
        state['last_archive_attempt_utc']=now.isoformat();save(path,state)
        try:
            receipt=soc_archive.checkpoint(log,data,archive,now=now)
            archive_state={'status':'verified','checked_utc':now.isoformat(),**receipt}
            state['last_archive_verified_utc']=now.isoformat()
        except (OSError,ValueError,KeyError,BadZipFile) as error:
            archive_state={'status':'error','checked_utc':now.isoformat(),'reason':str(error)[:500]}
        save(data/'archive-state.json',archive_state)
    save(path,state)
    return state


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--archives',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(observe(args.data,args.log,args.archives)))
