"""Meaningful fake-transport controls, never actual inference requests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import contextlib
import io
from unittest.mock import patch

import soc_analyst as analyst
import soc_investigation_eval as evaluation
import soc_investigation_run as runner
import test_soc_investigation_eval as pack_tests


class FakeClient:
    def __init__(self, *, response=None, busy=False, error=None):
        self.calls = []
        self.response = response or {'message': {'content': '{}', 'thinking': ''},
                                     'done': True, 'done_reason': 'stop', 'eval_count': 8,
                                     'prompt_eval_count': 22, 'eval_duration': 100, 'total_duration': 200}
        self.busy, self.error = busy, error

    def request(self, route, payload=None, timeout=5, max_bytes=runner.MAX_RESPONSE):
        self.calls.append((route, payload, timeout, max_bytes))
        if route == '/api/ps': value = {'models': [{'name': 'owned-job'}]} if self.busy else {'models': []}
        elif route == '/api/chat':
            if self.error: raise self.error
            value = self.response
        else: raise AssertionError('Unexpected API route '+route)
        return evaluation.encoded(value), value


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.job = {'job_id': 'M01-A', 'role': 'investigator', 'phase': 'measured',
                    'case_id': 'M01', 'condition': 'A', 'brief_sha256': 'a'*64,
                    'deterministic_context_sha256': 'b'*64,
                    'payload': {'model': 'qwen3.5:4b', 'stream': False, 'think': False,
                                'keep_alive': 0, 'options': dict(analyst.generation_options('common'), num_gpu=99),
                                'messages': [{'role': 'user', 'content': '{}'}]}}

    def test_protected_remote_and_other_ports_refused(self):
        for url in ('http://127.0.0.1:11434', 'http://127.0.0.1:11435', 'https://example.com',
                    'http://127.0.0.1:11436/evil', 'http://localhost:11436'):
            with self.assertRaises(ValueError): runner.endpoint(url)
        self.assertEqual(runner.endpoint(runner.ENDPOINT), runner.ENDPOINT)

    def test_exact_one_request_and_tokens_preserved(self):
        client = FakeClient()
        outcome = runner.one_request(client, self.job, self.root/'job', memory_guard=lambda: 32*1024**3)
        self.assertEqual(outcome['status'], 'completed')
        chats = [c for c in client.calls if c[0] == '/api/chat']
        self.assertEqual(len(chats), 1); self.assertEqual(chats[0][2], 120)
        self.assertEqual(chats[0][3], analyst.MAX_MODEL_RESPONSE)
        self.assertEqual(outcome['eval_count'], 8)
        self.assertEqual(outcome['prompt_eval_count'], 22)
        self.assertEqual(outcome['requested_backend'].split(',')[0], 'Vulkan')
        self.assertTrue((self.root/'job'/'response.raw.json').exists())

    def test_busy_runtime_not_unloaded(self):
        client = FakeClient(busy=True)
        result = runner.one_request(client, self.job, self.root/'job', memory_guard=lambda: 32*1024**3)
        self.assertEqual(result['status'], 'withheld')
        self.assertFalse(result['request_sent'])
        self.assertTrue(result['halt_following_requests'])
        self.assertEqual([c[0] for c in client.calls], ['/api/ps'])

    def test_memory_refusal_before_network(self):
        client = FakeClient()
        with patch.object(analyst, 'available_memory', return_value=8*1024**3):
            result = runner.one_request(client, self.job, self.root/'job')
        self.assertEqual(result['status'], 'withheld'); self.assertEqual(client.calls, [])
        self.assertTrue(result['halt_following_requests'])

    def test_unknown_memory_refused(self):
        with patch.object(analyst, 'available_memory', return_value=None):
            with self.assertRaises(ValueError): runner.resource_guard()

    def test_timeout_no_retry(self):
        client = FakeClient(error=TimeoutError('120 second timeout'))
        result = runner.one_request(client, self.job, self.root/'job', memory_guard=lambda: 32*1024**3)
        self.assertEqual(result['status'], 'withheld')
        self.assertEqual(len([c for c in client.calls if c[0] == '/api/chat']), 1)

    def test_http_error_raw_body_retained(self):
        client = FakeClient(error=runner.TransportError('HTTP error 500', b'{"error":"fixture"}', status=500))
        result = runner.one_request(client, self.job, self.root/'job', memory_guard=lambda: 32*1024**3)
        self.assertEqual(result['status'], 'withheld'); self.assertEqual(result['http_status'], 500)
        self.assertEqual((self.root/'job'/'response-error.raw.bin').read_bytes(), b'{"error":"fixture"}')

    def test_capped_thinking_empty_and_invalid_content_withheld(self):
        for name, changes in [('capped', {'done_reason': 'length'}), ('thinking', {'message': {'content': '{}', 'thinking': 'secret'}}),
                              ('empty', {'message': {'content': ''}}), ('invalid', {'message': {'content': 'bad'}})]:
            client = FakeClient(); client.response.update(changes)
            result = runner.one_request(client, self.job, self.root/name, memory_guard=lambda: 32*1024**3)
            self.assertEqual(result['status'], 'withheld')
            self.assertTrue((self.root/name/'response.raw.json').exists())

    def test_existing_outcome_not_replaced(self):
        path = self.root/'job'; path.mkdir()
        with self.assertRaises(FileExistsError):
            runner.one_request(FakeClient(), self.job, path, memory_guard=lambda: 32*1024**3)

    def test_model_alias_digest_not_independent(self):
        tags = {'models': [{'name': 'qwen3.5:4b', 'digest': 'a'*64},
                           {'name': 'qwen3.5:9b', 'digest': 'a'*64}]}
        with self.assertRaises(ValueError): runner.admit_models(tags, 'qwen3.5:4b', 'qwen3.5:4b', 'qwen3.5:9b')
        tags['models'][1]['digest'] = 'b'*64
        admitted = runner.admit_models(tags, 'qwen3.5:4b', 'qwen3.5:4b', 'qwen3.5:9b')
        self.assertNotEqual(admitted['reviewer']['digest'], admitted['analyst']['digest'])

    def test_uninstalled_or_unadmitted_model_refused(self):
        with self.assertRaises(ValueError): runner.admit_models({'models': []}, 'missing', 'missing', 'missing')

    def test_schedule_complete_deterministic_and_seeded(self):
        cases = [{'id': 'M01', 'phase': 'measured'}, {'id': 'P01', 'phase': 'practice'}]
        first = runner.make_schedule(cases, 17)
        self.assertEqual(first, runner.make_schedule(cases, 17))
        self.assertEqual(len(first['investigator']), 6)
        self.assertEqual({j['job_id'] for j in first['investigator']},
                         {'M01-A','M01-B','M01-C','P01-A','P01-B','P01-C'})


class JobIntegrationTests(unittest.TestCase):
    def setUp(self):
        pack_tests.EvaluationTests.setUp(self)
    def test_assisted_failure_keeps_unassisted_job(self):
        scheduled = {'job_id': 'M01-A', 'case_id': 'M01', 'phase': 'measured', 'condition': 'A'}
        job, reason = runner.make_job(self.pack, scheduled, 'investigator', {}, {}, 'qwen3.5:4b')
        self.assertIsNone(reason); self.assertIsNotNone(job)
        scheduled.update(job_id='M01-B', condition='B')
        job, reason = runner.make_job(self.pack, scheduled, 'investigator', {}, {}, 'qwen3.5:4b')
        self.assertIsNone(job); self.assertIn('withheld', reason)

    def test_reviewer_blind_to_condition_identity_and_duration(self):
        scheduled = {'job_id': 'M02-A', 'case_id': 'M02', 'phase': 'measured', 'condition': 'A'}
        locked = {'M02-A': {'status': 'completed', 'elapsed_s': 123, 'model': 'qwen3.5:4b',
                            'answer': pack_tests.answer_for(self.oracle)}}
        job, reason = runner.make_job(self.pack, scheduled, 'reviewer', {}, locked, 'qwen3.5:9b')
        self.assertIsNone(reason)
        content = json.loads(job['payload']['messages'][1]['content'])
        self.assertEqual(set(content), {'evidence', 'answer'})
        self.assertNotIn('M02-A', json.dumps(content)); self.assertNotIn('elapsed_s', json.dumps(content))
        self.assertNotIn('qwen3.5:4b', json.dumps(content))

    def test_gpu_bounds_explicit_and_context_equal(self):
        scheduled = {'job_id': 'M02-A', 'case_id': 'M02', 'phase': 'measured', 'condition': 'A'}
        brief = evaluation.load(self.pack/'M02'/'brief.json')
        group = brief['groups'][0]
        selected = {'M02': {'report': {'observed': [], 'inferred': [{'type': 'inferred',
            'code': 'sensor_reported_block', 'group_id': group['id'], 'evidence_refs': group['evidence_refs']}],
            'unknown': [{'type': 'unknown', 'topic': 'intent'}, {'type': 'unknown', 'topic': 'complete_visibility'}], 'next_steps': []}}}
        jobs = []
        for condition in ('A','B','C'):
            scheduled.update(job_id='M02-'+condition, condition=condition)
            job, _ = runner.make_job(self.pack, scheduled, 'investigator', selected, {}, 'qwen3.5:4b'); jobs.append(job)
        self.assertEqual(len({j['deterministic_context_sha256'] for j in jobs}), 1)
        for job in jobs:
            payload = job['payload']; self.assertEqual(payload['options']['num_gpu'], 99)
            self.assertEqual(payload['options']['num_predict'], 700)
            self.assertEqual(payload['options']['num_ctx'], 4096)
            self.assertEqual(payload['keep_alive'], 0); self.assertFalse(payload['think'])

    def test_full_fake_run_retains_all_requests_scores_and_reviews(self):
        class FullClient:
            def request(self, route, payload=None, timeout=5, max_bytes=runner.MAX_RESPONSE):
                if route == '/api/ps': result = {'models': []}
                elif route == '/api/tags': result = {'models': [
                    {'name': 'qwen3.5:4b', 'digest': 'a'*64}, {'name': 'qwen3.5:9b', 'digest': 'b'*64}]}
                elif route == '/api/version': result = {'version': 'test-only-fake'}
                elif route == '/api/show': result = {'model': payload['model'], 'test_only': True}
                elif route == '/api/chat':
                    context = json.loads(payload['messages'][1]['content'])
                    groups = context.get('groups', [])
                    if payload['messages'][0]['content'] == analyst.SYSTEM:
                        answer = {'observed': [], 'inferred': [{'type': 'inferred',
                            'group_id': g['id'], 'code': analyst.eligible(g)[0],
                            'evidence_refs': g['evidence_refs'][:1]} for g in groups],
                            'unknown': [{'type': 'unknown', 'topic': 'intent'},
                                        {'type': 'unknown', 'topic': 'complete_visibility'}], 'next_steps': []}
                        content = analyst.canonical(answer)
                    elif payload['messages'][0]['content'] == evaluation.INVESTIGATOR_SYSTEM:
                        decisions = ['alert_match_requires_context'] if groups else ['no_alerts_in_supplied_records']
                        if any(g['action']=='blocked' for g in groups): decisions.append('sensor_reports_block')
                        steps = ['inspect_event'] if groups else ['check_visibility']
                        if context['context'].get('constructed_missing_context'):
                            decisions.append('collection_gap_limits_comparison')
                            if 'check_visibility' not in steps: steps.append('check_visibility')
                        answer = {'observations': [{k:g[k] for k in ('id','sid','action','count','evidence_refs')} for g in groups],
                            'decisions': decisions, 'context_codes': sorted(context['interpretation_catalog']),
                            'client_outcome': 'unknown', 'intrusion_status': 'unestablished',
                            'complete_delivery_proven': False, 'next_steps': steps}
                        content = analyst.canonical(answer)
                    else:
                        content = 'Supplementary fake review; no human evidence.'
                    result = {'message': {'content': content, 'thinking': ''}, 'done': True,
                              'done_reason': 'stop', 'eval_count': 42, 'prompt_eval_count': 123,
                              'eval_duration': 1, 'total_duration': 2}
                else: raise AssertionError(route)
                return evaluation.encoded(result), result
        backend = self.root/'backend.txt'; backend.write_text('test-only backend evidence')
        output = self.root/'run'
        with patch.object(analyst, 'available_memory', return_value=32*1024**3), contextlib.redirect_stdout(io.StringIO()):
            complete = runner.run(self.pack, output, analyst_model='qwen3.5:4b', investigator_model='qwen3.5:4b',
                                  reviewer_model='qwen3.5:9b', backend_receipt=backend, client=FullClient())
        self.assertEqual(complete['actual_requests'], 56)
        self.assertEqual(complete['completed_by_role'], {'analyst':8,'investigator':24,'reviewer':24})
        self.assertTrue(complete['all_scheduled_outcomes_retained'])
        self.assertEqual(evaluation.load(output/'deterministic-scores.json')['measured_correct'], 18)
        self.assertEqual(len(list(output.glob('*/**/response.raw.json'))), 56)
        self.assertTrue(evaluation.load(output/'protocol.json')['analyst_investigator_digest_reused'])

    def test_midrun_memory_refusal_stops_every_later_request(self):
        class MetadataOnlyClient:
            def __init__(self): self.chat_calls = 0
            def request(self, route, payload=None, timeout=5, max_bytes=runner.MAX_RESPONSE):
                if route == '/api/ps': result = {'models': []}
                elif route == '/api/tags': result = {'models': [
                    {'name':'qwen3.5:4b','digest':'a'*64}, {'name':'qwen3.5:9b','digest':'b'*64}]}
                elif route == '/api/version': result = {'version':'test-only'}
                elif route == '/api/show': result = {'test_only':True}
                elif route == '/api/chat':
                    self.chat_calls += 1
                    raise AssertionError('Memory halt must stop generation')
                else: raise AssertionError(route)
                return evaluation.encoded(result), result
        client = MetadataOnlyClient()
        backend = self.root/'backend.txt'; backend.write_text('Nonempty is only a retained fixture, not offload proof')
        with patch.object(analyst, 'available_memory', side_effect=[32*1024**3, 8*1024**3]), contextlib.redirect_stdout(io.StringIO()):
            result = runner.run(self.pack, self.root/'halted', analyst_model='qwen3.5:4b',
                                investigator_model='qwen3.5:4b', reviewer_model='qwen3.5:9b',
                                backend_receipt=backend, client=client)
        self.assertEqual(client.chat_calls, 0)
        self.assertEqual(result['actual_requests'], 0)
        self.assertTrue(result['all_scheduled_outcomes_retained'])
        self.assertIn('preflight halt', result['halt_reason'])


if __name__ == '__main__': unittest.main()
