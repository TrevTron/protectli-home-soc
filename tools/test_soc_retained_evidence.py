"""Exercise real rolling reclaim, exact citations, corruption and restart recovery."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import soc_analyst as analyst
import soc_evidence as evidence
import soc_index as index
import soc_retained_evidence as rolling
from soc_receiver import Store


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'syslog.jsonl'
        self.now = dt.datetime(2026,10,7,tzinfo=dt.timezone.utc)

    def writer(self, max_bytes=60, segment_bytes=20, cold_max=70000):
        evidence.SegmentWriter(self.path,max_bytes,segment_bytes)
        rolling.migrate(self.path,cold_max_bytes=cold_max,now=self.now)
        return rolling.RetainedWriter(self.path,max_bytes,segment_bytes,clock=lambda:self.now)

    def test_live_reclaim_allows_collection_past_hot_cap_without_reusing_offsets(self):
        writer=self.writer()
        rows=[(f'{n:019d}\n').encode() for n in range(12)]
        for row in rows:self.assertTrue(writer.append(row))
        self.assertLessEqual(writer.total,60)
        self.assertEqual(writer.logical_end,240)
        self.assertGreater(writer.status()['cold_bytes'],0)
        with evidence.open_evidence(self.path) as stream:
            self.assertEqual(stream.read(),b''.join(rows))
            stream.seek(80)
            self.assertEqual(stream.read(20),rows[4])
        restarted=evidence.SegmentWriter(self.path,60,20)
        self.assertEqual(restarted.logical_end,240)
        self.assertTrue(restarted.append(b'new-record\n'))
        self.assertEqual(restarted.logical_end,251)

    def test_age_expiry_frees_both_stores_and_snapshot_reads_surviving_tail(self):
        writer=self.writer()
        for row in (b'first-closed-record!\n',b'second-closed-rec!!\n',b'current-active-rec!\n'):
            self.assertTrue(writer.append(row))
        end=writer.logical_end
        self.now+=dt.timedelta(days=8)
        writer.maintain()
        self.assertGreater(writer.value['base_offset'],0)
        self.assertEqual(writer.logical_end,end)
        with evidence.open_evidence(self.path) as stream:
            with self.assertRaises(rolling.EvidenceExpired):stream.read(1)
            stream.seek(writer.value['base_offset'])
            self.assertEqual(stream.read(),b'current-active-rec!\n')
        self.assertEqual(analyst.snapshot(self.path,1024)[1],b'current-active-rec!\n')
        self.assertTrue(writer.append(b'after-expiry\n'))
        self.assertGreater(writer.logical_end,end)
        self.assertEqual(rolling.read_layout(self.path)[1]['active_part'],3)

    def test_same_size_cold_tamper_refuses_lookup_and_restart(self):
        writer=self.writer()
        for _ in range(5):writer.append(b'x'*19+b'\n')
        entry=next(e for e in writer.value['closed'] if e['storage']=='cold')
        archive=self.path.parent/entry['archive']
        raw=bytearray(archive.read_bytes());raw[-1]^=1;archive.write_bytes(raw)
        with evidence.open_evidence(self.path) as stream:
            with self.assertRaisesRegex(ValueError,'digest'):stream.read(20)
        with self.assertRaisesRegex(ValueError,'digest'):evidence.SegmentWriter(self.path,60,20)

    def test_manifest_commit_before_cleanup_recovers_crash_without_duplicate_archive(self):
        writer=self.writer()
        for _ in range(3):writer.append(b'x'*19+b'\n')
        original_cleanup=writer.cleanup
        def fail_after_commit():
            if writer.value['pending_cleanup']:raise OSError('simulated crash')
            original_cleanup()
        with mock.patch.object(writer,'cleanup',side_effect=fail_after_commit):
            with self.assertRaisesRegex(OSError,'simulated'):writer.append(b'y'*19+b'\n')
        value=json.loads(evidence.index_path(self.path).read_text())
        self.assertTrue(value['pending_cleanup'])
        restarted=evidence.SegmentWriter(self.path,60,20)
        self.assertFalse(restarted.value['pending_cleanup'])
        self.assertTrue(restarted.append(b'y'*19+b'\n'))
        self.assertEqual(restarted.logical_end,80)

    def test_archive_rename_before_manifest_commit_is_recovered_only_by_exact_bytes(self):
        writer=self.writer()
        for _ in range(3):writer.append(b'x'*19+b'\n')
        original=writer.commit
        def interrupted():
            if writer.value['pending_cleanup']:raise OSError('manifest interrupted')
            original()
        with mock.patch.object(writer,'commit',side_effect=interrupted):
            with self.assertRaisesRegex(OSError,'interrupted'):writer.append(b'y'*19+b'\n')
        restarted=evidence.SegmentWriter(self.path,60,20)
        self.assertTrue(restarted.append(b'y'*19+b'\n'))
        self.assertEqual(restarted.logical_end,80)

    def test_derived_index_prunes_expired_rows_but_keeps_new_offsets_and_cold_sources(self):
        writer=self.writer(max_bytes=500,segment_bytes=150)
        rows=[]
        for n in range(12):
            row=(json.dumps({'received_utc':self.now.isoformat(),'app':'test','raw':str(n)})+'\n').encode()
            rows.append(row);writer.append(row)
        database=self.path.parent/'events.sqlite3'
        while not index.sync(database,self.path)['caught_up']:pass
        self.assertEqual(index.original(database,0),rows[0].decode())
        self.now+=dt.timedelta(days=8);writer.maintain()
        status=index.sync(database,self.path)
        self.assertGreater(status['first_retained_offset'],0)
        with self.assertRaises(rolling.EvidenceExpired):index.original(database,0)
        new=(json.dumps({'received_utc':self.now.isoformat(),'app':'test','raw':'new'})+'\n').encode()
        offset=writer.logical_end;writer.append(new)
        index.sync(database,self.path)
        self.assertEqual(index.original(database,offset),new.decode())

    def test_metadata_count_bound_does_not_stop_collection_and_expiry_is_explicit(self):
        writer=self.writer(max_bytes=5000,segment_bytes=20)
        for n in range(300):self.assertTrue(writer.append((f'{n:019d}\n').encode()))
        self.assertEqual(writer.logical_end,6000)
        self.assertLessEqual(len(writer.value['closed']),rolling.MAX_ENTRIES)
        self.assertGreater(writer.status()['early_expired_segments'],0)

    def test_receiver_restarts_after_base_file_expires_and_reports_hot_cold_separately(self):
        writer=self.writer(max_bytes=500,segment_bytes=100)
        writer.append(b'{"app":"test","raw":"one"}\n')
        writer.append(b'{"app":"test","raw":"'+b'x'*80+b'"}\n')
        self.now+=dt.timedelta(days=8);writer.maintain()
        self.assertFalse(self.path.exists())
        store=Store(self.path,500,100)
        self.assertEqual(store.snapshot()['events'][0]['app'],'test')
        self.assertEqual(store.snapshot()['rolling_retention']['mode'],'rolling-v2')

    def test_idle_receiver_maintains_expiry_and_does_not_forecast_hot_cap_failure(self):
        writer=self.writer(max_bytes=500,segment_bytes=100)
        writer.append(b'{"app":"test","raw":"first"}\n')
        writer.append(b'{"app":"test","raw":"'+b'x'*80+b'"}\n')
        store=Store(self.path,500,100)
        store.segment_writer.clock=lambda:self.now
        self.now+=dt.timedelta(days=8)
        store.segment_writer.last_maintenance=0
        store.maintenance()
        snapshot=store.snapshot()
        self.assertGreater(snapshot['rolling_retention']['expired_segments'],0)
        self.assertIsNone(snapshot['estimated_hours_remaining'])
        self.assertFalse(snapshot['retention_full'])



if __name__=='__main__':unittest.main(verbosity=2)
