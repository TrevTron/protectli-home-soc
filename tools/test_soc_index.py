import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

import soc_index as index
import soc_evidence

NOW=dt.datetime(2026,10,6,15,0,tzinfo=dt.timezone.utc)


def event(action='allowed', severity=3, port=443, destination='203.0.113.9'):
    return {'received_utc':NOW.isoformat(),'app':'suricata','severity':'info','eve':{
        'event_type':'alert','timestamp':NOW.isoformat(),'proto':'TCP',
        'src_ip':'192.0.2.10','src_port':32100,'dest_ip':destination,'dest_port':port,
        'alert':{'signature_id':2016149,'gid':1,'rev':7,'signature':'Fixture <script>','action':action,'severity':severity}}}


def line(value):
    value=copy.deepcopy(value)
    value['raw']='<174>1 source suricata - - - '+json.dumps(value.pop('eve'))
    return (json.dumps(value)+'\n').encode()


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/'source.jsonl'
        self.database=self.root/'index.sqlite'

    def test_restart_partial_append_and_idempotence(self):
        raw=line(event())
        self.source.write_bytes(raw+raw[:30])
        first=index.sync(self.database,self.source)
        self.assertEqual(first['indexed_bytes'],len(raw))
        self.assertFalse(first['caught_up'])
        self.assertEqual(index.sync(self.database,self.source)['new_records'],0)
        with self.source.open('ab') as f:f.write(raw[30:])
        self.assertEqual(index.sync(self.database,self.source)['new_records'],1)
        self.assertEqual(index.status(self.database)['records'],2)
        self.assertEqual(index.original(self.database,len(raw)),raw.decode())

    def test_grouping_preserves_action_severity_endpoint_port_and_revision(self):
        values=[event(),event(),event('blocked'),event(severity=1),event(port=444),event(destination='203.0.113.8')]
        modified=event();modified['eve']['alert']['rev']=8;values.append(modified)
        self.source.write_bytes(b''.join(map(line,values)))
        original=self.source.read_bytes()
        index.sync(self.database,self.source)
        groups=index.groups(self.database,now=NOW)
        self.assertEqual(sorted(g['count'] for g in groups['groups']),[1,1,1,1,1,2])
        self.assertIn(groups['groups'][0]['action'],('blocked','allowed'))
        self.assertTrue(groups['groups'][0]['action']=='blocked' or groups['groups'][0]['alert_severity']==1)
        repeated=next(g for g in groups['groups'] if g['count']==2)
        rows=index.members(self.database,repeated['group_id'],now=NOW,limit=1)
        self.assertTrue(rows['has_more'])
        self.assertEqual(len(rows['records']),1)
        self.assertEqual(len(index.members(self.database,repeated['group_id'],now=NOW,before=rows['next_before'])['records']),1)
        self.assertEqual(self.source.read_bytes(),original)

    def test_missing_context_stays_visible_singleton_and_bad_line_counted(self):
        incomplete=event();incomplete['eve']['alert'].pop('severity')
        missing=event();missing['eve'].pop('dest_port')
        self.source.write_bytes(line(incomplete)*2+line(missing)*2+b'{broken}\n')
        index.sync(self.database,self.source)
        result=index.groups(self.database,now=NOW)
        self.assertEqual(len(result['groups']),4)
        self.assertEqual(index.status(self.database)['malformed'],3)

    def test_group_pages_preserve_membership_in_fixed_window(self):
        self.source.write_bytes(b''.join(line(event(port=400+i)) for i in range(26)))
        index.sync(self.database,self.source)
        first=index.groups(self.database,now=NOW,limit=25)
        second=index.groups(self.database,now=NOW,limit=25,offset=first['next_offset'])
        self.assertEqual(len(first['groups']),25)
        self.assertEqual(len(second['groups']),1)
        self.assertFalse(second['has_more'])
        self.assertEqual(len({g['group_id'] for g in first['groups']+second['groups']}),26)
        later=event();later['received_utc']=(NOW+dt.timedelta(seconds=1)).isoformat()
        with self.source.open('ab') as f:f.write(line(later))
        index.sync(self.database,self.source)
        self.assertEqual(index.groups(self.database,now=NOW)['total_groups'],26)

    def test_rollover_offsets_and_rebuild_are_source_preserving(self):
        writer=soc_evidence.SegmentWriter(self.source,100000,700)
        raw=line(event())
        for _ in range(5):writer.append(raw)
        while not index.sync(self.database,self.source,max_bytes=500)['caught_up']:pass
        for offset in range(0,len(raw)*5,len(raw)):
            self.assertEqual(index.original(self.database,offset),raw.decode())
        other=self.root/'rebuilt.sqlite'
        index.sync(other,self.source)
        self.assertEqual(index.status(other)['records'],5)

    def test_source_mismatch_and_truncation_refused_without_checkpoint_loss(self):
        raw=line(event());self.source.write_bytes(raw)
        index.sync(self.database,self.source)
        self.source.write_bytes(b'X'+raw[1:])
        with self.assertRaisesRegex(ValueError,'changed'):index.sync(self.database,self.source)
        with self.assertRaisesRegex(ValueError,'hash mismatch'):index.original(self.database,0)
        self.assertEqual(index.status(self.database)['checkpoint'],str(len(raw)))
        self.source.write_bytes(b'')
        with self.assertRaisesRegex(ValueError,'shortened'):index.sync(self.database,self.source)
        other=self.root/'other.jsonl';other.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'another'):index.sync(self.database,other)

    def test_limits_and_oversized_record_do_not_advance_checkpoint(self):
        self.source.write_bytes(b'x'*(index.analyst.MAX_LINE+2))
        with self.assertRaisesRegex(ValueError,'Oversized'):index.sync(self.database,self.source)
        self.assertEqual(index.status(self.database)['checkpoint'],'0')
        with self.assertRaises(ValueError):index.groups(self.database,limit=1000)


if __name__=='__main__':unittest.main(verbosity=2)
