"""Exercise rollover, immutable citations, restart, aggregate bounds and tampering."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import soc_analyst as analyst
import soc_analyst_server as server
import soc_evidence as evidence
from soc_receiver import Store


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'syslog.jsonl'

    def test_rollover_keeps_exact_old_and_new_locators_across_restart(self):
        old=b'{"raw":"original"}\n'
        self.path.write_bytes(old)
        writer=evidence.SegmentWriter(self.path,200,24)
        newer=b'{"raw":"second"}\n'
        self.assertTrue(writer.append(newer))
        self.assertEqual(self.path.read_bytes(),old)
        with evidence.open_evidence(self.path) as stream:
            self.assertEqual(stream.read(),old+newer)
            stream.seek(len(old))
            self.assertEqual(stream.read(len(newer)),newer)
            stream.seek(-len(newer),2)
            self.assertEqual(stream.readline(),newer)
        restarted=evidence.SegmentWriter(self.path,200,24)
        last=b'{"raw":"third"}\n'
        restarted.append(last)
        self.assertEqual(analyst.snapshot(self.path,1024)[1],old+newer+last)
        run=Path(self.temp.name)/'run'
        run.mkdir()
        for number,(offset,data) in enumerate(((0,old),(len(old),newer))):
            sha=hashlib.sha256(data).hexdigest();ref='E-'+sha[:16]
            (run/'sources.json').write_text(json.dumps({'source_path':str(self.path),'sources':{ref:{'byte_offset':offset,'byte_length':len(data),'sha256':sha}}}))
            self.assertEqual(server.original_event(run,ref),data.decode())

    def test_aggregate_limit_does_not_reset_when_segment_rolls(self):
        writer=evidence.SegmentWriter(self.path,30,10)
        for _ in range(3):self.assertTrue(writer.append(b'123456789\n'))
        files,_=evidence.layout(self.path)
        before={path.name:path.read_bytes() for path,_ in files}
        self.assertFalse(writer.append(b'x\n'))
        self.assertEqual(writer.total,30)
        self.assertEqual({path.name:path.read_bytes() for path,_ in evidence.layout(self.path)[0]},before)

    def test_partial_final_original_line_refuses_rollover_without_touching_evidence(self):
        self.path.write_bytes(b'partial')
        writer=evidence.SegmentWriter(self.path,200,8)
        with self.assertRaisesRegex(ValueError,'incomplete'):writer.append(b'another\n')
        self.assertEqual(self.path.read_bytes(),b'partial')

    def test_unsafe_index_paths_and_changed_sealed_lengths_fail_closed(self):
        writer=evidence.SegmentWriter(self.path,200,8)
        writer.append(b'1234567\n');writer.append(b'next\n')
        index=evidence.index_path(self.path)
        original=index.read_text()
        data=json.loads(original);data['closed'][0]['name']='../outside'
        index.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'unsafe'):evidence.open_evidence(self.path)
        index.write_text(original)
        self.path.write_bytes(b'short\n')
        with self.assertRaisesRegex(ValueError,'length'):evidence.open_evidence(self.path)

    def test_same_size_tampering_and_budget_change_are_refused_on_restart(self):
        writer=evidence.SegmentWriter(self.path,200,8)
        writer.append(b'1234567\n');writer.append(b'next\n')
        with self.assertRaisesRegex(ValueError,'budgets'):evidence.SegmentWriter(self.path,300,8)
        self.path.write_bytes(b'7654321\n')
        with self.assertRaisesRegex(ValueError,'digest'):evidence.SegmentWriter(self.path,200,8)

    def test_bounded_tail_and_partial_active_line_survive_segment_boundary(self):
        writer=evidence.SegmentWriter(self.path,200,6)
        writer.append(b'first\n');writer.append(b'second\n');writer.append(b'third\n')
        with writer.active.open('ab') as stream:stream.write(b'partial')
        offset,data,end=analyst.snapshot(self.path,18)
        self.assertEqual(data,b'third\n')
        self.assertEqual(offset,13)
        self.assertEqual(end,26)

    def test_receiver_restart_restores_alerts_from_later_segment_and_exposes_total_cap(self):
        store=Store(self.path,1000,100)
        store.add({'app':'system','raw':'x'*80})
        alert={'app':'suricata','raw':'{"event_type":"alert","alert":{"signature_id":2100498}}'}
        store.add(alert)
        initial=self.path.read_bytes()
        restarted=Store(self.path,1000,100)
        self.assertEqual(restarted.snapshot()['security_events'][0]['eve']['alert']['signature_id'],2100498)
        restarted.add({'raw':'x'*1001})
        self.assertTrue(restarted.snapshot()['retention_full'])
        self.assertEqual(restarted.snapshot()['max_bytes'],1000)
        self.assertEqual(self.path.read_bytes(),initial)


if __name__=='__main__':unittest.main(verbosity=2)
