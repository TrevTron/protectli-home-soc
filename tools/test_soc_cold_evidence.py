"""Exercise old-source restoration, pins and refusal of unsafe cleanup proposals."""
from pathlib import Path
import datetime as dt
import json
import tempfile
import unittest

import soc_archive as archives
import soc_cold_evidence as cold
import soc_evidence as evidence


class ColdTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.raw=self.root/'syslog.jsonl';self.data=self.root/'analyst';self.data.mkdir()
        self.now=dt.datetime(2026,10,6,tzinfo=dt.timezone.utc)
        self.old=(json.dumps({'received_utc':'2026-09-20T00:00:00Z','raw':'old original'})+'\n').encode()
        self.new=(json.dumps({'received_utc':'2026-10-06T00:00:00Z','raw':'new original'})+'\n').encode()
        self.writer=evidence.SegmentWriter(self.raw,10000,len(self.old))
        self.writer.append(self.old);self.writer.append(self.new)
        self.archives=self.root/'archives';self.receipt=archives.checkpoint(self.raw,self.data,self.archives,now=self.now)
        self.catalog=self.root/'catalog.json';cold.write_catalog(self.archives,self.catalog)
        self.source={'byte_offset':0,'byte_length':len(self.old),'sha256':cold.digest(self.old)}

    def test_cold_source_opens_without_any_hot_file(self):
        self.raw.rename(self.root/'disposable-hot-copy.offline')
        self.assertEqual(cold.archived_record(self.catalog,self.archives,self.source),self.old)

    def test_source_crossing_archived_member_boundary_is_exact(self):
        raw=self.old[-5:]+self.new[:10]
        source={'byte_offset':len(self.old)-5,'byte_length':len(raw),'sha256':cold.digest(raw)}
        self.assertEqual(cold.archived_record(self.catalog,self.archives,source),raw)

    def test_wrong_hash_or_out_of_archive_range_is_withheld(self):
        with self.assertRaisesRegex(ValueError,'digest mismatch'):
            cold.archived_record(self.catalog,self.archives,{**self.source,'sha256':'0'*64})
        with self.assertRaisesRegex(ValueError,'covers'):
            cold.archived_record(self.catalog,self.archives,{**self.source,'byte_offset':9999})

    def test_changed_archive_and_forged_catalog_are_rejected(self):
        path=self.archives/self.receipt['archive'];original=path.read_bytes();path.write_bytes(original+b'X')
        with self.assertRaisesRegex(ValueError,'changed'):cold.archived_record(self.catalog,self.archives,self.source)
        path.write_bytes(original)
        value=json.loads(self.catalog.read_text());value['archives'][0]['members'][0]['start']=1
        self.catalog.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'Catalog does not match'):cold.archived_record(self.catalog,self.archives,self.source)

    def test_paths_types_oversized_sources_and_catalogs_fail_closed(self):
        for source in ({**self.source,'byte_offset':True},{**self.source,'byte_length':cold.MAX_RECORD+1}):
            with self.assertRaises(ValueError):cold.archived_record(self.catalog,self.archives,source)
        value=json.loads(self.catalog.read_text());value['archives'][0]['archive']='../outside.zip'
        self.catalog.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'Unsafe'):cold.archived_record(self.catalog,self.archives,self.source)

    def test_pin_preserves_full_record_and_explicit_context_after_hot_unavailable(self):
        ref='E-'+self.source['sha256'][:16];target=self.root/'pinned-case'
        result=cold.pin_case(self.catalog,self.archives,{ref:self.source},target,context={'review_note':'Record checked','client_outcome':'unknown'})
        self.assertEqual(result['pinned_sources_verified'],1)
        self.raw.rename(self.root/'disposable-hot-copy.offline')
        self.assertEqual(cold.verify_pin(target),result)
        (target/(ref+'.jsonl')).write_bytes(b'wrong\n')
        with self.assertRaisesRegex(ValueError,'changed'):cold.verify_pin(target)

    def test_preview_only_old_sealed_segments_and_preserves_all_originals(self):
        before={p.name:p.read_bytes() for p,_ in evidence.layout(self.raw)[0]}
        plan=cold.retention_preview(self.raw,self.catalog,self.archives,now=self.now)
        self.assertTrue(plan['segments'][0]['eligible_for_cold']);self.assertFalse(plan['segments'][1]['eligible_for_cold'])
        self.assertEqual(plan['segments'][1]['reason'],'active_segment');self.assertFalse(plan['deletion_enabled'])
        self.assertEqual(before,{p.name:p.read_bytes() for p,_ in evidence.layout(self.raw)[0]})
        pinned=cold.retention_preview(self.raw,self.catalog,self.archives,now=self.now,pinned_sources=[self.source])
        self.assertEqual(pinned['eligible_bytes'],0)

    def test_corrupt_archive_keeps_segment_and_reports_failure(self):
        path=self.archives/self.receipt['archive'];path.write_bytes(path.read_bytes()+b'X')
        plan=cold.retention_preview(self.raw,self.catalog,self.archives,now=self.now)
        self.assertEqual(plan['eligible_bytes'],0);self.assertTrue(plan['archive_failures'])

    def test_pinned_context_mutation_refused_against_saved_receipt(self):
        ref='E-'+self.source['sha256'][:16];target=self.root/'pin'
        result=cold.pin_case(self.catalog,self.archives,{ref:self.source},target,context={'outcome':'unknown'})
        value=json.loads((target/'case.json').read_text());value['context']['outcome']='safe'
        (target/'case.json').write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'context/manifest changed'):
            cold.verify_pin(target,result['case_sha256'])

    def test_pin_failure_does_not_create_a_partial_destination(self):
        target=self.root/'pin'
        with self.assertRaisesRegex(ValueError,'reference'):
            cold.pin_case(self.catalog,self.archives,{'E-'+'f'*16:self.source},target,context={})
        self.assertFalse(target.exists())

    def test_bad_timestamp_future_date_or_recent_record_keeps_segment(self):
        for date,reason in [('not-a-date','unknown_record_age'),('2030-01-01T00:00:00Z','future_timestamp'),
                            ('2026-10-05T00:00:00Z','within_hot_window')]:
            with self.subTest(date=date),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);raw=root/'syslog.jsonl';data=root/'data';data.mkdir()
                line=(json.dumps({'received_utc':date})+'\n').encode();writer=evidence.SegmentWriter(raw,10000,len(line))
                writer.append(line);writer.append(b'{}\n');archives.checkpoint(raw,data,root/'archives',now=self.now)
                cold.write_catalog(root/'archives',root/'catalog.json')
                plan=cold.retention_preview(raw,root/'catalog.json',root/'archives',now=self.now)
                self.assertEqual(plan['eligible_bytes'],0);self.assertEqual(plan['segments'][0]['reason'],reason)


if __name__=='__main__':unittest.main(verbosity=2)
