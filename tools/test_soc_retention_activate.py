"""Activation requires the recorded stopped source and preserves a complete baseline."""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest

import soc_evidence as evidence
import soc_preserved_evidence as preserved
import soc_retention_activate as activate


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'syslog.jsonl'
        self.rows=b'{"raw":"before"}\n';evidence.SegmentWriter(self.source,1000,100).append(self.rows)
        self.receipt=self.root/'receipt';self.receipt.mkdir()
        self.preflight={'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'receiver_absent':True,'collector_sockets_absent':True,'recovery_paused':True,
            'log':str(self.source),'receipt':str(self.receipt)}
        self.save()
        (self.receipt/'original-segments.json').write_bytes(evidence.index_path(self.source).read_bytes())

    def save(self):
        (self.receipt/'maintenance-preflight.json').write_text(json.dumps(self.preflight))

    def test_activation_keeps_baseline_and_original_offsets(self):
        result=activate.activate(self.source,self.receipt)
        self.assertEqual(result['baseline']['verified_prefix_bytes'],len(self.rows))
        self.assertEqual(result['retention']['mode'],'rolling-v2')
        self.assertEqual(preserved.baseline_record(self.source,{'byte_offset':0,
            'byte_length':len(self.rows),'sha256':preserved.digest(self.rows)}),self.rows)
        self.assertEqual(evidence.open_evidence(self.source).read(),self.rows)

    def test_unpaused_or_stale_preflight_cannot_migrate(self):
        self.preflight['recovery_paused']=False;self.save()
        with self.assertRaisesRegex(ValueError,'paused'):activate.activate(self.source,self.receipt)
        self.preflight.update(recovery_paused=True,started_utc='2020-01-01T00:00:00+00:00');self.save()
        with self.assertRaisesRegex(ValueError,'stale'):activate.activate(self.source,self.receipt)
        self.assertEqual(evidence.layout(self.source)[1]['version'],1)

    def test_changed_manifest_is_preserved_without_migrating(self):
        (self.receipt/'original-segments.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'changed since'):activate.activate(self.source,self.receipt)
        self.assertFalse(preserved.descriptor(self.source).exists())

    def test_prior_baseline_from_interrupted_migration_is_verified_and_reused(self):
        baseline=preserved.create_baseline(self.source)
        result=activate.activate(self.source,self.receipt)
        self.assertEqual(result['baseline']['verified_prefix_bytes'],baseline['prefix_bytes'])
        self.assertEqual(len(list(self.root.glob('*.baseline-*'))),1)


if __name__=='__main__':unittest.main(verbosity=2)
