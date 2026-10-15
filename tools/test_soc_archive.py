"""Real segmented archives, restored source hashes, notes and bounded scheduling."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import soc_archive as archive
import soc_evidence as evidence
import soc_operational_checkpoint as operation
import soc_operator as operator
import soc_analyst_server as viewer
import test_soc_analyst_server as fixtures


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ViewerTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.raw=self.fixture.raw
        self.destination=self.root/'archives'
        self.now=dt.datetime(2026,10,6,2,0,tzinfo=dt.timezone.utc)

    def test_rollover_restore_hashes_notes_and_originals_unchanged(self):
        original=self.raw.read_bytes()
        brief,sha=operator.read_brief(self.root,'fixture')
        operator.append_review(self.root,'fixture',brief['groups'][0]['id'],sha,'reviewed','Exact receipt checked',viewer.original_event)
        journal=(self.root/'operator-review.jsonl').read_bytes()
        writer=evidence.SegmentWriter(self.raw,10000,len(original))
        writer.append(b'{"raw":"next segment"}\n')
        receipt=archive.checkpoint(self.raw,self.root,self.destination,now=self.now)
        self.assertEqual(receipt['source_references_verified'],1)
        self.assertEqual(receipt['operator_notes_verified'],1)
        self.assertEqual(self.raw.read_bytes(),original)
        self.assertEqual((self.root/'operator-review.jsonl').read_bytes(),journal)
        restored=archive.verify_archive(self.destination/receipt['archive'])
        self.assertEqual(restored['raw_prefix_bytes'],len(original)+len(b'{"raw":"next segment"}\n'))
        with zipfile.ZipFile(self.destination/receipt['archive']) as saved:
            self.assertIn('logs/syslog.jsonl.part000001',saved.namelist())
        # Alter one restored byte without updating the archive manifest.
        broken=self.destination/'broken.zip'
        with zipfile.ZipFile(self.destination/receipt['archive']) as saved,zipfile.ZipFile(broken,'w') as changed:
            for name in saved.namelist():
                data=saved.read(name)
                if name=='logs/syslog.jsonl':data=b'X'+data[1:]
                changed.writestr(name,data)
        with self.assertRaisesRegex(ValueError,'member changed'):archive.verify_archive(broken)

    def test_changed_original_citation_withholds_archive(self):
        self.raw.write_bytes(b'X'+self.raw.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError,'citation changed'):archive.checkpoint(self.raw,self.root,self.destination)
        self.assertFalse(list(self.destination.glob('*.zip')))

    def test_active_bundle_excluded_and_latest_pointer_not_left_dangling(self):
        (self.root/'worker-state.json').write_text(json.dumps({'status':'analyzing','run':'fixture'}))
        receipt=archive.checkpoint(self.raw,self.root,self.destination)
        self.assertEqual(receipt['saved_report_bundles'],0)
        self.assertEqual(receipt['skipped_runs'],['fixture'])
        with zipfile.ZipFile(self.destination/receipt['archive']) as saved:self.assertNotIn('analyst/latest.json',saved.namelist())

    def test_pinned_active_bundle_is_not_silently_lost(self):
        brief,sha=operator.read_brief(self.root,'fixture')
        operator.append_review(self.root,'fixture',brief['groups'][0]['id'],sha,'reviewed','Keep pinned evidence',viewer.original_event)
        (self.root/'worker-state.json').write_text(json.dumps({'status':'analyzing','run':'fixture'}))
        with self.assertRaises(KeyError):archive.checkpoint(self.raw,self.root,self.destination)

    def test_archive_budget_preserves_verified_pending_and_originals(self):
        original=self.raw.read_bytes()
        with self.assertRaisesRegex(ValueError,'Compressed archive budget'):archive.checkpoint(self.raw,self.root,self.destination,max_archive_bytes=1)
        self.assertEqual(len(list(self.destination.glob('*.zip.pending'))),1)
        with self.assertRaisesRegex(ValueError,'Private archive budget'):archive.checkpoint(self.raw,self.root,self.destination,max_archive_bytes=1)
        self.assertEqual(self.raw.read_bytes(),original)

    def test_concurrent_archive_and_observation_callers_refused(self):
        self.destination.mkdir()
        with evidence.exclusive_lock(self.destination/'archive.lock'):
            with self.assertRaisesRegex(ValueError,'owns the lock'):archive.checkpoint(self.raw,self.root,self.destination)
        with evidence.exclusive_lock(self.root/'observation.lock'):
            with self.assertRaisesRegex(ValueError,'owns the lock'):operation.observe(self.root,self.raw,self.destination)
        receipt=archive.checkpoint(self.raw,self.root,self.destination)
        self.assertEqual(receipt['source_references_verified'],1)

    def test_checkpoint_above_old_256_mib_bound_streams_and_preserves_citation(self):
        original=self.raw.read_bytes()
        writer=evidence.SegmentWriter(self.raw,archive.RAW_LIMIT,32*1024**2)
        record=b'X'*(1024**2-1)+b'\n'
        for _ in range(260):writer.append(record)
        before={path.name:evidence.sha256_file(path) for path,_ in evidence.layout(self.raw)[0]}
        old_read=zipfile.ZipFile.read
        def guarded_read(saved,name,*args,**kwargs):
            if str(name).startswith('logs/') and not str(name).endswith('.segments.json'):
                raise AssertionError('Raw archive must be streamed, not read whole')
            return old_read(saved,name,*args,**kwargs)
        with mock.patch.object(zipfile.ZipFile,'read',guarded_read):
            receipt=archive.checkpoint(self.raw,self.root,self.destination,now=self.now)
            checked=archive.verify_archive(self.destination/receipt['archive'])
        self.assertGreater(checked['raw_prefix_bytes'],256*1024**2)
        self.assertEqual(checked['source_references_verified'],1)
        with self.raw.open('rb') as raw:self.assertEqual(raw.read(len(original)),original)
        self.assertEqual({path.name:evidence.sha256_file(path) for path,_ in evidence.layout(self.raw)[0]},before)
        self.assertEqual(receipt['stream_chunk_bytes'],256*1024)

    def test_incomplete_active_record_excluded_without_changing_original(self):
        original=self.raw.read_bytes()+b'{"partial":'
        self.raw.write_bytes(original)
        receipt=archive.checkpoint(self.raw,self.root,self.destination,now=self.now)
        self.assertEqual(receipt['raw_prefix_bytes'],len(original)-len(b'{"partial":'))
        self.assertEqual(self.raw.read_bytes(),original)

    def test_larger_report_manifest_within_new_bound(self):
        self.destination.mkdir()
        path=self.destination/'many-artifacts.zip'
        rows=[{'file':'analyst/runs/fixture/'+('artifact-'+'x'*50+str(number)+'.txt'),
               'bytes':1,'sha256':archive.digest(b'x')} for number in range(5000)]
        manifest={'files':rows,'logical_log_members':[],'saved_runs':[], 'operator_notes_verified':0}
        encoded=json.dumps(manifest,indent=2).encode()
        self.assertGreater(len(encoded),archive.MAX_MEMBER)
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as saved:
            for row in rows:saved.writestr(row['file'],b'x')
            saved.writestr('archive-manifest.json',encoded)
        self.assertEqual(archive.verify_archive(path)['files_verified'],5000)


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.raw=self.root/'syslog.jsonl';self.raw.write_bytes(b'{}\n')
        self.now=dt.datetime(2026,10,6,2,0,tzinfo=dt.timezone.utc)

    def call(self,seconds):return operation.observe(self.root,self.raw,self.root/'archives',now=self.now+dt.timedelta(seconds=seconds))

    def test_duplicate_checks_gaps_six_hour_archive_and_window_end(self):
        with mock.patch.object(operation.urllib.request,'build_opener') as network,mock.patch.object(archive,'checkpoint',return_value={'source_references_verified':1}) as saved:
            network.return_value.open.side_effect=OSError('fixture offline')
            first=self.call(0);self.assertEqual(first['samples'],1);self.assertEqual(saved.call_count,1)
            self.assertEqual(self.call(30)['samples'],1)
            next_sample=self.call(300);self.assertEqual(next_sample['samples'],2);self.assertEqual(saved.call_count,1)
            later=self.call(21600);self.assertEqual(later['gap_count'],1);self.assertEqual(saved.call_count,2)
            ended=self.call(172800);self.assertEqual(ended['status'],'observation_window_finished')
            self.assertNotIn('pass',ended);self.assertEqual(saved.call_count,2)
        lines=(self.root/'operational-observations.jsonl').read_bytes().splitlines()
        self.assertEqual(len(lines),3);self.assertEqual(json.loads(lines[0])['receiver']['status'],'unavailable')

    def test_archive_failure_is_visible_and_not_retried_each_five_minutes(self):
        with mock.patch.object(operation.urllib.request,'build_opener') as network,mock.patch.object(archive,'checkpoint',side_effect=ValueError('budget reached')) as saved:
            network.return_value.open.side_effect=OSError('fixture offline')
            self.call(0);self.call(300)
            self.assertEqual(saved.call_count,1)
            state=json.loads((self.root/'archive-state.json').read_text());self.assertEqual(state['status'],'error')
            self.assertIn('budget reached',state['reason'])

    def test_oversized_state_refused_and_redirect_not_followed(self):
        (self.root/'observation-state.json').write_bytes(b'X'*65537)
        with self.assertRaisesRegex(ValueError,'bound'):self.call(0)
        self.assertIsNone(operation.NoRedirect().redirect_request(None,None,302,'',{},'http://elsewhere/'))


if __name__=='__main__':unittest.main(verbosity=2)
