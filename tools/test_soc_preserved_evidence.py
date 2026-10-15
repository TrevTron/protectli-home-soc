"""Migration originals, post-migration case pins and honest expiry end to end."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest import mock

import soc_archive as archive
import soc_evidence as evidence
import soc_operator as operator
import soc_preserved_evidence as preserved
import soc_retained_evidence as rolling
import test_soc_analyst_server as fixtures


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'syslog.jsonl'
        self.now=dt.datetime(2026,10,7,tzinfo=dt.timezone.utc)
        self.first=b'{"original":"first"}\n';self.second=b'{"original":"second"}\n'
        writer=evidence.SegmentWriter(self.source,200,25)
        writer.append(self.first);writer.append(self.second)
        self.location={'byte_offset':0,'byte_length':len(self.first),'sha256':preserved.digest(self.first)}

    def rolling_writer(self):
        rolling.migrate(self.source,now=self.now)
        return rolling.RetainedWriter(self.source,200,25,clock=lambda:self.now)

    def test_baseline_preserves_exact_offsets_after_original_expires(self):
        before=evidence.sha256_file(self.source)
        result=preserved.create_baseline(self.source)
        self.assertEqual(result['prefix_bytes'],len(self.first)+len(self.second))
        self.assertEqual(evidence.sha256_file(self.source),before)
        writer=self.rolling_writer();self.now+=dt.timedelta(days=8);writer.maintain()
        self.assertFalse(self.source.exists())
        self.assertEqual(preserved.read_record(self.source,self.location),self.first)
        with self.assertRaisesRegex(ValueError,'already exists'):preserved.create_baseline(self.source)

    def test_wrong_full_digest_and_changed_baseline_are_withheld(self):
        value=preserved.create_baseline(self.source);writer=self.rolling_writer()
        self.now+=dt.timedelta(days=8);writer.maintain()
        with self.assertRaisesRegex(ValueError,'changed'):
            preserved.read_record(self.source,{**self.location,'sha256':'0'*64})
        saved=self.source.parent/value['directory']/self.source.name
        saved.write_bytes(b'X'+saved.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError,'member changed'):preserved.read_record(self.source,self.location)

    def test_pinned_future_record_survives_without_baseline_and_tamper_is_withheld(self):
        writer=self.rolling_writer()
        preserved.pin_records(self.root,[self.first])
        self.now+=dt.timedelta(days=8);writer.maintain()
        self.assertEqual(preserved.read_record(self.source,self.location,pin_root=self.root),self.first)
        path=self.root/'preserved-records'/(self.location['sha256']+'.jsonl')
        path.write_bytes(b'X'+self.first[1:])
        with self.assertRaisesRegex(ValueError,'hash mismatch'):preserved.read_record(self.source,self.location,pin_root=self.root)

    def test_unpinned_expired_record_is_explicit_and_offsets_are_not_reused(self):
        writer=self.rolling_writer();self.now+=dt.timedelta(days=8);writer.maintain()
        end=writer.logical_end;writer.append(b'{"next":"new"}\n')
        self.assertGreater(writer.logical_end,end)
        with self.assertRaises(rolling.EvidenceExpired):preserved.read_record(self.source,self.location)

    def test_pin_budget_refuses_new_review_without_mutating_existing_pins(self):
        preserved.pin_records(self.root,[self.first])
        with mock.patch.object(preserved,'MAX_PINS',1):
            with self.assertRaisesRegex(ValueError,'budget reached'):preserved.pin_records(self.root,[self.second])
        self.assertEqual(len(list((self.root/'preserved-records').glob('*.jsonl'))),1)

    def test_managed_checkpoints_do_not_repeat_full_history_archives(self):
        preserved.create_baseline(self.source);writer=self.rolling_writer()
        data=self.root/'analyst';data.mkdir();archives=self.root/'archives'
        for n in range(70):
            receipt=archive.checkpoint(self.source,data,archives,now=self.now+dt.timedelta(hours=n*6))
            self.assertEqual(receipt['mode'],'rolling-v2-managed')
        self.assertEqual(len(list(archives.glob('managed-*.json'))),1)
        self.assertEqual(len(list(archives.glob('checkpoint-*.zip'))),0)
        self.assertEqual(receipt['baseline']['verified_prefix_bytes'],len(self.first)+len(self.second))

    def test_deferred_windows_cleanup_retries_without_stopping_append(self):
        writer=self.rolling_writer()
        for _ in range(6):writer.append(b'x'*24+b'\n')
        original=Path.unlink
        def busy(path,*args,**kwargs):
            if path.name==self.source.name:raise PermissionError('Reader still owns the original')
            return original(path,*args,**kwargs)
        with mock.patch.object(Path,'unlink',busy):
            self.assertTrue(writer.append(b'y'*24+b'\n'))
            self.assertGreater(writer.status()['deferred_cleanup_bytes'],0)
        writer.cleanup()
        self.assertEqual(writer.status()['deferred_cleanup_files'],0)

    def test_cold_sequential_reader_opens_each_segment_once_and_closes_handle(self):
        temp=self.root/'sequential.jsonl';legacy=evidence.SegmentWriter(temp,200000,100000)
        rolling.migrate(temp,now=self.now);writer=evidence.SegmentWriter(temp,200000,100000)
        row=b'x'*999+b'\n'
        for _ in range(300):writer.append(row)
        opened=[];real=rolling.ColdSegment.open
        def tracked(segment,mode):
            stream=real(segment,mode);opened.append(stream);return stream
        with mock.patch.object(rolling.ColdSegment,'open',tracked):
            with evidence.open_evidence(temp) as stream:
                for _ in range(100):self.assertEqual(stream.read(1000),row)
            self.assertEqual(len(opened),1)
            self.assertTrue(opened[0].closed)


class ExpiryHttpTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ViewerTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.now=dt.datetime(2026,10,7,tzinfo=dt.timezone.utc)
        self.size=self.fixture.raw.stat().st_size
        evidence.SegmentWriter(self.fixture.raw,10000,self.size)
        rolling.migrate(self.fixture.raw,now=self.now)
        self.writer=rolling.RetainedWriter(self.fixture.raw,10000,self.size,clock=lambda:self.now)

    def expire(self):
        self.writer.append(b'{"next":"new"}\n')
        self.now+=dt.timedelta(days=8);self.writer.maintain()

    def test_http_expired_source_returns_410_without_writing_a_pin(self):
        self.expire()
        with self.assertRaises(urllib.error.HTTPError) as raised:self.fixture.get('/evidence/fixture/'+self.fixture.ref)
        self.assertEqual(raised.exception.code,410)
        self.assertIn(b'never reused',raised.exception.read())
        self.assertFalse((self.fixture.root/'preserved-records').exists())

    def test_operator_review_pins_source_and_remains_readable_after_expiry(self):
        brief,sha=operator.read_brief(self.fixture.root,'fixture');group=brief['groups'][0]
        entry=operator.append_review(self.fixture.root,'fixture',group['id'],sha,'investigate','Needs a client result.',fixtures.viewer.original_event)
        self.assertTrue(entry['preserved_sources'])
        self.expire()
        with self.fixture.get('/evidence/fixture/'+self.fixture.ref) as response:
            self.assertEqual(response.status,200)
            self.assertIn(b'Hash-checked private evidence',response.read())
        self.assertEqual(operator.load_journal(self.fixture.root)[0],entry)


if __name__=='__main__':unittest.main(verbosity=2)
