"""Adversarial controls for the offline public verifier; no model or network."""
import json
import tempfile
import unittest
from pathlib import Path
from verify_ai_followup_evidence import decisions, file_manifest, sha, source_case

class PublicFollowupControls(unittest.TestCase):
    def test_manifest_refuses_escape(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)
            root = parent / 'evidence'
            root.mkdir()
            (parent / 'outside.txt').write_bytes(b'outside')
            (root / 'PUBLIC_EXPORT_MANIFEST.json').write_text(json.dumps({'files': {'../outside.txt': {'public_sha256': sha(b'outside')}}}))
            with self.assertRaisesRegex(ValueError, 'escapes'):
                file_manifest(root)

    def test_manifest_refuses_added_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'PUBLIC_EXPORT_MANIFEST.json').write_text('{"files":{}}')
            (root / 'unreviewed.txt').write_text('extra')
            with self.assertRaisesRegex(ValueError, 'membership'):
                file_manifest(root)

    def test_manifest_refuses_modified_answer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'answer.json').write_bytes(b'changed')
            (root / 'PUBLIC_EXPORT_MANIFEST.json').write_text(json.dumps({'files': {'answer.json': {'public_sha256': sha(b'original')}}}))
            with self.assertRaisesRegex(ValueError, 'changed'):
                file_manifest(root)

    def fixture(self):
        case = {'oracle': {'eligible_contexts': ['coverage_limits'], 'required_contexts': ['coverage_limits'],
                'useful_checks': ['inspect_coverage'], 'client_outcome': 'unknown', 'client_refs': []}}
        answer = {'contexts': ['coverage_limits'], 'next_checks': ['inspect_coverage'], 'client_outcome': 'unknown',
                  'client_refs': [], 'intrusion_established': False, 'delivery_complete': False}
        return case, answer

    def test_extra_permitted_but_unuseful_check_fails(self):
        case, answer = self.fixture()
        answer['next_checks'].append('compare_retained_window')
        self.assertFalse(decisions(case, [], [], answer)['next_checks'])

    def test_client_success_without_receipt_fails(self):
        case, answer = self.fixture()
        answer['client_outcome'] = 'supplied_attempt_success'
        self.assertFalse(decisions(case, [], [], answer)['client_outcome'])

    def test_mutated_client_reference_fails(self):
        case, answer = self.fixture()
        case['oracle']['client_refs'] = ['R-exact-01']
        answer['client_refs'] = ['R-exact-O1']
        self.assertFalse(decisions(case, [], [], answer)['client_refs'])

    def test_near_match_receipt_cannot_support_oracle(self):
        record = {'attempt_id': 'attempt-1', 'event_utc': '2026-10-07T01:00:00Z', 'received_utc': '2026-10-07T01:00:02Z',
                  'protocol': 'TCP', 'source_alias': 'client', 'source_port': 1000, 'destination_alias': 'server', 'destination_port': 443}
        receipt = {**record, 'source_port': 1001, 'kind': 'client_result', 'result': 'success', 'receipt_id': 'R-01'}
        raw = (json.dumps(record) + '\n').encode()
        digest = sha(raw)
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            folder = base / 'cases-v3/development/D01'
            folder.mkdir(parents=True)
            (folder / 'evidence.jsonl').write_bytes(raw)
            (folder / 'locators.json').write_text(json.dumps({'E-' + digest[:16]: {'offset': 0, 'length': len(raw), 'sha256': digest}}))
            (folder / 'case-private.json').write_text(json.dumps({'receipts': [receipt], 'oracle': {'client_refs': ['R-01'], 'client_outcome': 'supplied_attempt_success'}}))
            with self.assertRaisesRegex(ValueError, 'Receipt oracle'):
                source_case(base, 'model-skills-v2', 'development-01', 'D01')

if __name__ == '__main__':
    unittest.main()
