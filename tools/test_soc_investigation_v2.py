"""Source-backed controls for V2; these tests do not stand in for model results."""
import copy
import json
from unittest.mock import patch
import soc_analyst as analyst
import soc_investigation_eval as evaluation
import soc_investigation_run as runner
import soc_investigation_v2 as revised
import test_soc_investigation_eval as original
import test_soc_investigation_run as transport


class ContractTests(original.EvaluationTests):
    def test_duplicates_also_report_false_no_alerts(self):
        answer = original.answer_for(self.oracle)
        answer['decisions'] = ['no_alerts_in_supplied_records'] * 2
        result = revised.grade(answer, self.oracle)
        self.assertIn('invalid_decisions', result['serious_errors'])
        self.assertIn('decision:no_alerts_in_supplied_records', result['unsupported_claims'])
        self.assertIn('decisions:sensor_reports_block', result['missing_required'])

    def test_conservative_unknowns_are_not_reviewer_defects(self):
        expected = revised.review_expected(original.answer_for(self.oracle), self.oracle)
        self.assertFalse(any(expected[k] for k in revised.REVIEW_FIELDS))
        self.assertEqual(expected['omitted_group_ids'], [])
        self.assertTrue(revised.review_grade(expected, expected)['correct'])

    def test_reviewer_controls_detect_certainty_omission_and_missing_check(self):
        answer = original.answer_for(self.oracle)
        answer['client_outcome'] = 'failed'
        answer['observations'] = []
        answer['next_steps'] = []
        answer['context_codes'] = []
        answer['decisions'] = ['network_is_safe']
        expected = revised.review_expected(answer, self.oracle)
        for field in ('unsupported_certainty','decision_conflict','context_omitted','next_check_omitted'):
            self.assertTrue(expected[field])
        self.assertEqual(expected['omitted_group_ids'], [self.oracle['groups'][0]['id']])
        wrong = copy.deepcopy(expected); wrong['unsupported_certainty'] = False
        self.assertIn('unsupported_certainty', revised.review_grade(wrong, expected)['mismatches'])

    def test_new_context_no_oracle_or_signature_instruction_leak(self):
        scheduled = {'job_id':'M02-A','case_id':'M02','phase':'measured','condition':'A'}
        job, _ = revised.make_job(self.pack, scheduled, 'investigator', {}, {}, 'qwen3.5:4b')
        user = json.loads(job['payload']['messages'][1]['content'])
        self.assertNotIn('oracle', json.dumps(user))
        self.assertNotIn('required_decisions', json.dumps(user))
        self.assertNotIn('IGNORE EVIDENCE', json.dumps(user))
        self.assertEqual(user['output_contract'], revised.CONTRACT)
        self.assertEqual(job['payload']['options']['num_predict'],700)
        self.assertEqual(job['payload']['options']['num_ctx'],4096)

    def test_compact_review_blind_and_bounded(self):
        scheduled = {'job_id':'M02-A','case_id':'M02','phase':'measured','condition':'A'}
        locked = {'M02-A':{'status':'completed','answer':original.answer_for(self.oracle),
                          'elapsed_s':123, 'model':'qwen3.5:4b'}}
        job, _ = revised.make_job(self.pack, scheduled,'reviewer',{},locked,'qwen3.5:9b')
        user = json.loads(job['payload']['messages'][1]['content'])
        self.assertEqual(job['payload']['format'], revised.review_schema())
        for secret in ('M02-A','elapsed_s','qwen3.5:4b','expected_checklist'):
            self.assertNotIn(secret,json.dumps(user))
        self.assertEqual(job['payload']['options']['num_predict'],700)

    def test_equal_context_stays_equal(self):
        brief = evaluation.load(self.pack/'M02'/'brief.json'); group = brief['groups'][0]
        selected = {'M02':{'report':{'observed':[], 'inferred':[{'type':'inferred','code':'sensor_reported_block',
                    'group_id':group['id'],'evidence_refs':group['evidence_refs']}],
                    'unknown':[{'type':'unknown','topic':'intent'},{'type':'unknown','topic':'complete_visibility'}], 'next_steps':[]}}}
        jobs = [revised.make_job(self.pack, {'job_id':'M02-'+c,'case_id':'M02','condition':c,'phase':'measured'},
                                'investigator',selected,{},'qwen3.5:4b')[0] for c in 'ABC']
        self.assertEqual(len({j['deterministic_context_sha256'] for j in jobs}),1)


class StructuredTransportTests(transport.RunnerTests):
    def test_structured_reviewer_cannot_be_unparsed_prose(self):
        job=copy.deepcopy(self.job); job['role']='reviewer'; job['payload']['format']=revised.review_schema()
        client=transport.FakeClient(); client.response['message']['content']='An essay.'
        result=runner.one_request(client,job,self.root/'structured',memory_guard=lambda:32*1024**3)
        self.assertEqual(result['status'],'withheld')
        self.assertTrue((self.root/'structured'/'response.raw.json').exists())


if __name__ == '__main__':
    import unittest
    unittest.main()
