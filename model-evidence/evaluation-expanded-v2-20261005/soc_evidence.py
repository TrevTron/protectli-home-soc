"""Append-only log segments with stable logical byte offsets. No deletion."""
import hashlib
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import re
import uuid


@contextmanager
def exclusive_lock(path):
    """An OS-released advisory lock for cooperating checkpoint callers."""
    path=Path(path)
    if path.is_symlink():raise ValueError('Lock link refused')
    with path.open('a+b') as stream:
        stream.seek(0,2)
        if stream.tell()==0:stream.write(b'1');stream.flush()
        stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as error:raise ValueError('Another checkpoint owns the lock') from error
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)


def index_path(path):
    return Path(str(path)+'.segments.json')


def layout(path):
    path=Path(path)
    index=index_path(path)
    if not index.exists():
        return [(path,path.stat().st_size)],None
    if index.stat().st_size>65536:raise ValueError('Evidence segment index exceeds bound')
    value=json.loads(index.read_text(encoding='utf-8'))
    if value.get('version')!=1 or value.get('base')!=path.name:raise ValueError('Invalid evidence segment index')
    closed=value['closed']
    if not isinstance(closed,list) or len(closed)>64:raise ValueError('Segment count exceeds bound')
    names=[entry['name'] for entry in closed]+[value['active']]
    expected=[path.name]+[path.name+f'.part{i:06d}' for i in range(1,len(names))]
    if names!=expected:raise ValueError('Non-contiguous or unsafe segment paths')
    files=[]
    for item,name in zip(closed,names):
        source=path.parent/name
        if source.is_symlink() or source.stat().st_size!=item['bytes'] or type(item['bytes']) is not int or item['bytes']<0:
            raise ValueError('Sealed evidence length changed')
        if not re.fullmatch('[a-f0-9]{64}',item['sha256']):raise ValueError('Invalid sealed digest')
        files.append((source,item['bytes']))
    active=path.parent/value['active']
    if active.is_symlink():raise ValueError('Evidence link refused')
    files.append((active,active.stat().st_size))
    if not (type(value['max_bytes']) is int and type(value['segment_bytes']) is int and 0<value['segment_bytes']<=value['max_bytes']):
        raise ValueError('Invalid evidence budget')
    if sum(size for _,size in files)>value['max_bytes']:raise ValueError('Aggregate evidence budget exceeded')
    return files,value


class _LogicalRaw(io.RawIOBase):
    def __init__(self,files):
        super().__init__()
        self.files=files
        self.length=sum(size for _,size in files)
        self.position=0

    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.position
    def seek(self,offset,whence=0):
        position=offset if whence==0 else self.position+offset if whence==1 else self.length+offset if whence==2 else -1
        if position<0:raise ValueError('Invalid evidence offset')
        self.position=position
        return position

    def readinto(self,buffer):
        wanted=min(len(buffer),max(0,self.length-self.position))
        copied=0
        start=0
        for source,size in self.files:
            if copied==wanted:break
            local=self.position-start
            if 0<=local<size:
                length=min(wanted-copied,size-local)
                with source.open('rb') as stream:
                    stream.seek(local)
                    data=stream.read(length)
                if len(data)!=length:raise ValueError('Evidence segment shortened during read')
                buffer[copied:copied+length]=data
                copied+=length
                self.position+=length
            start+=size
        return copied


def open_evidence(path):
    path=Path(path)
    if not index_path(path).exists():return path.open('rb')
    files,_=layout(path)
    return io.BufferedReader(_LogicalRaw(files))


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(65536),b''):digest.update(chunk)
    return digest.hexdigest()


class SegmentWriter:
    def __init__(self,path,max_bytes,segment_bytes):
        self.path=Path(path)
        if self.path.is_symlink():raise ValueError('Evidence link refused')
        if not self.path.exists():self.path.touch(exist_ok=False)
        files,value=layout(self.path)
        self.value=value or {'version':1,'base':self.path.name,'closed':[],'active':self.path.name,
                             'max_bytes':max_bytes,'segment_bytes':segment_bytes}
        if not 0<segment_bytes<=max_bytes:raise ValueError('Invalid segment budget')
        if value and (value['max_bytes']!=max_bytes or value['segment_bytes']!=segment_bytes):
            raise ValueError('Recorded evidence budgets differ; no silent change')
        if sum(size for _,size in files)>max_bytes:raise ValueError('Existing evidence exceeds budget')
        for entry in self.value['closed']:
            if sha256_file(self.path.parent/entry['name'])!=entry['sha256']:raise ValueError('Sealed evidence digest changed')
        self.total=sum(size for _,size in files)
        self.active_size=files[-1][1]
        self.active=files[-1][0]
        if not value:self.commit()

    def commit(self):
        destination=index_path(self.path)
        pending=Path(str(destination)+'.pending-'+uuid.uuid4().hex)
        with pending.open('x',encoding='utf-8') as stream:
            json.dump(self.value,stream,indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending,destination)

    def append(self,data):
        if not data.endswith(b'\n'):raise ValueError('Only complete records may be appended')
        if self.total+len(data)>self.value['max_bytes']:return False
        if self.active_size and self.active_size+len(data)>self.value['segment_bytes']:
            if len(self.value['closed'])>=64:raise ValueError('Segment count exceeds bound')
            with self.active.open('rb') as source:
                source.seek(-1,2)
                if source.read(1)!=b'\n':raise ValueError('Cannot seal an incomplete original record')
            sealed={'name':self.active.name,'bytes':self.active_size,'sha256':sha256_file(self.active)}
            next_path=self.path.parent/(self.path.name+f'.part{len(self.value["closed"])+1:06d}')
            # A crash before index replacement may leave an empty unused part.
            # Reuse only that exact empty path; preserve unexpected nonempty files.
            if next_path.exists():
                if next_path.is_symlink() or next_path.stat().st_size:raise ValueError('Unexpected rollover part exists')
            else:next_path.touch(exist_ok=False)
            self.value['closed'].append(sealed)
            self.value['active']=next_path.name
            self.commit()
            self.active=next_path
            self.active_size=0
        with self.active.open('ab') as stream:stream.write(data)
        self.total+=len(data)
        self.active_size+=len(data)
        return True
