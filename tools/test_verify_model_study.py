"""Offline package corruption checks. Synthetic receipts; no model or appliance calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import soc_analyst as analyst
import verify_model_study as verifier
from test_soc_analyst import CLIENT, NOW, event

class OfflineStudyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        raw = self.root / 'test-input.jsonl'
        raw.write_text(json.dumps(event()) + '\n', encoding='utf-8')
        brief, _ = analyst.build_brief(raw, CLIENT, b'x' * 32, now=NOW)
        group = brief['groups'][0]
        report = {'observed': [{'type': 'observed', 'group_id': group['id'], 'field': 'count', 'value': group['count']}],
                  'inferred': [{'type': 'inferred', 'group_id': group['id'], 'code': 'stun_may_be_normal',
                                'evidence_refs': group['evidence_refs'][:1]}],
                  'unknown': [{'type': 'unknown', 'topic': 'intent'}, {'type': 'unknown', 'topic': 'complete_visibility'}],
                  'next_steps': [{'group_id': group['id'], 'action': 'inspect_event'}]}
        self.case = self.root / 'cases/control'
        self.case.mkdir(parents=True)
        for name, value in [('brief.json', brief), ('model-input.json', analyst.model_input(brief)),
                            ('schema.json', analyst.schema(brief))]:
            self.save(self.case / name, value)
        expected = {'required_contexts': [{'code': 'stun_may_be_normal', 'any_group_ids': [group['id']]}],
                    'empty_report': False, 'review_first_any_groups': []}
        self.save(self.case / 'expected.json', expected)
        self.item = {'phase': 'production_contract', 'case': 'control', 'model': 'qwen3:4b-instruct',
                     'repeat': 1, 'structured': True, 'deadline_seconds': 120}
        self.save(self.root / 'schedule.json', [self.item])
        self.save(self.root / 'protocol.json', {'prompts': {'structured': analyst.SYSTEM, 'written_analysis': analyst.FREEFORM_SYSTEM}})
        self.freeze()
        self.target = self.root / 'execution/001'
        self.target.mkdir(parents=True)
        content = analyst.canonical(report)
        response = {'model': self.item['model'], 'message': {'content': content}, 'done': True,
                    'done_reason': 'stop', 'eval_count': 100, 'prompt_eval_count': 500}
        payload = {'model': self.item['model'], 'stream': False, 'think': False, 'keep_alive': 0,
                   'options': verifier.BASE_OPTIONS,
                   'messages': [{'role': 'system', 'content': analyst.SYSTEM},
                                {'role': 'user', 'content': analyst.canonical(analyst.model_input(brief))}],
                   'format': analyst.schema(brief)}
        metadata = {'model': self.item['model'], 'endpoint': 'http://127.0.0.1:11435',
                    'options': copy.deepcopy(verifier.BASE_OPTIONS),
                    'request_sha256': verifier.digest(analyst.canonical(payload).encode()),
                    'system_prompt_sha256': verifier.digest(analyst.SYSTEM.encode()),
                    'schema_sha256': verifier.digest(analyst.canonical(analyst.schema(brief)).encode()),
                    'content_characters': len(content), 'thinking_characters': 0,
                    'eval_count': 100, 'prompt_eval_count': 500, 'done_reason': 'stop'}
        outcome = {'number': 1, **self.item, 'status': 'delivered',
                   'brief_sha256': verifier.digest((self.case / 'brief.json').read_bytes()),
                   'content_sha256': verifier.digest(content.encode()), 'eval_count': 100,
                   'prompt_eval_count': 500, 'done_reason': 'stop',
                   'quality': verifier.quality(report, expected)}
        for name, value in [('response.json', response), ('metadata.json', metadata),
                            ('accepted-report.json', report), ('outcome.json', outcome)]:
            self.save(self.target / name, value)

    def save(self, path, value):
        path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

    def load(self, name):
        return json.loads((self.target / name).read_text())

    def freeze(self):
        files = list(self.root.glob('cases/*/*.json')) + [self.root / 'protocol.json', self.root / 'schedule.json']
        if (self.root / 'soc_analyst.py').exists(): files.append(self.root / 'soc_analyst.py')
        self.save(self.root / 'frozen-manifest.json', [{'file': p.relative_to(self.root).as_posix(),
                  'sha256': verifier.digest(p.read_bytes())} for p in files])

    def test_complete_receipts_offline_and_source_never_executed(self):
        (self.root / 'soc_analyst.py').write_text("raise AssertionError('untrusted study code executed')\nSYSTEM = " +
             repr(analyst.SYSTEM) + '\nFREEFORM_SYSTEM = ' + repr(analyst.FREEFORM_SYSTEM) + '\n', encoding='utf-8')
        self.save(self.root / 'protocol.json', {})
        self.freeze()
        with patch.object(analyst, 'request_model', side_effect=AssertionError('inference invoked')):
            result = verifier.verify(self.root, require_complete=True)
        self.assertEqual(result['completed'], 1)
        self.assertEqual(result['returned_request_hashes_verified'], 1)

    def test_frozen_input_corruption_rejected(self):
        with (self.case / 'brief.json').open('a', encoding='utf-8') as stream: stream.write(' ')
        with self.assertRaisesRegex(ValueError, 'Frozen file hash differs'): verifier.verify(self.root)

    def test_consistent_hashes_cannot_hide_wrong_observed_count(self):
        response = self.load('response.json'); report = json.loads(response['message']['content'])
        report['observed'][0]['value'] += 1
        content = analyst.canonical(report); response['message']['content'] = content
        metadata = self.load('metadata.json'); metadata['content_characters'] = len(content)
        outcome = self.load('outcome.json'); outcome['content_sha256'] = verifier.digest(content.encode())
        for name, value in [('response.json', response), ('metadata.json', metadata),
                            ('outcome.json', outcome), ('accepted-report.json', report)]: self.save(self.target / name, value)
        with self.assertRaises(analyst.Rejected): verifier.verify(self.root)

    def test_options_and_model_identity_corruption_rejected(self):
        metadata = self.load('metadata.json'); metadata['options']['num_thread'] = 4
        self.save(self.target / 'metadata.json', metadata)
        with self.assertRaisesRegex(ValueError, 'options differ'): verifier.verify(self.root)
        metadata['options']['num_thread'] = 2; metadata['options']['num_gpu'] = False
        self.save(self.target / 'metadata.json', metadata)
        with self.assertRaisesRegex(ValueError, 'options differ'): verifier.verify(self.root)
        metadata['options']['num_gpu'] = 0; self.save(self.target / 'metadata.json', metadata)
        response = self.load('response.json'); response['model'] = 'qwen3.5:4b'
        self.save(self.target / 'response.json', response)
        with self.assertRaisesRegex(ValueError, 'Model identity differs'): verifier.verify(self.root)

    def test_utility_tampering_and_cap_as_delivery_rejected(self):
        outcome = self.load('outcome.json'); outcome['quality']['complete'] = False
        self.save(self.target / 'outcome.json', outcome)
        with self.assertRaisesRegex(ValueError, 'utility score differs'): verifier.verify(self.root)
        outcome['quality']['complete'] = True; outcome['done_reason'] = 'length'
        response = self.load('response.json'); response['done_reason'] = 'length'
        metadata = self.load('metadata.json'); metadata['done_reason'] = 'length'
        for name, value in [('outcome.json', outcome), ('response.json', response), ('metadata.json', metadata)]: self.save(self.target / name, value)
        with self.assertRaisesRegex(ValueError, 'Delivered response incomplete'): verifier.verify(self.root)

    def test_incomplete_study_cannot_pass_complete_gate(self):
        (self.target / 'outcome.json').unlink()
        self.assertEqual(verifier.verify(self.root)['status'], 'partial_receipts_verified')
        with self.assertRaisesRegex(ValueError, 'Study is incomplete'): verifier.verify(self.root, require_complete=True)

    def test_manifest_escape_refused_before_reading(self):
        self.save(self.root / 'frozen-manifest.json', [{'file': '../outside.json', 'sha256': '0' * 64}])
        with self.assertRaisesRegex(ValueError, 'escapes study root'): verifier.verify(self.root)

    def test_written_windows_storage_and_changed_wording(self):
        content = 'Observed allowed event.\nIntent is unknown.\nReview the supplied source.\n'
        self.item.update(phase='written_analysis', structured=False, deadline_seconds=300)
        self.save(self.root / 'schedule.json', [self.item])
        self.freeze()
        response = self.load('response.json')
        response['message']['content'] = content
        brief = json.loads((self.case/'brief.json').read_text())
        payload = {'model': self.item['model'], 'stream': False, 'think': False, 'keep_alive': 0,
                   'options': verifier.BASE_OPTIONS,
                   'messages': [{'role': 'system', 'content': analyst.FREEFORM_SYSTEM},
                                {'role': 'user', 'content': analyst.canonical(analyst.model_input(brief))}]}
        metadata = self.load('metadata.json')
        metadata.update(request_sha256=verifier.digest(analyst.canonical(payload).encode()),
                        system_prompt_sha256=verifier.digest(analyst.FREEFORM_SYSTEM.encode()),
                        schema_sha256=None, content_characters=len(content))
        outcome = self.load('outcome.json')
        outcome.update(self.item)
        outcome['content_sha256'] = verifier.digest(content.encode())
        for name, value in [('response.json', response), ('metadata.json', metadata), ('outcome.json', outcome)]:
            self.save(self.target/name, value)
        analysis = self.target/'analysis.txt'
        for stored, expected_storage in [(content, 'literal'), (content.replace('\n', '\r\n'), 'windows_text')]:
            with self.subTest(storage=expected_storage):
                analysis.write_bytes(stored.encode())
                result = verifier.verify(self.root, require_complete=True)
                self.assertEqual(result['written_analysis_storage'], [
                    {'number': 1, 'file_sha256': verifier.digest(stored.encode()), 'newline_storage': expected_storage}])
        analysis.write_bytes(content.replace('unknown', 'known').replace('\n', '\r\n').encode())
        with self.assertRaisesRegex(ValueError, 'Saved written analysis differs'): verifier.verify(self.root)
        analysis.write_bytes(content.replace('\n', '\r\n', 1).encode())
        with self.assertRaisesRegex(ValueError, 'Saved written analysis differs'): verifier.verify(self.root)

if __name__ == '__main__':
    unittest.main()
