import copy
import json
import unittest
import soc_investigation_eval as evaluation
import soc_investigation_v2 as v2
import soc_investigation_v5 as v5
import test_soc_investigation_eval as fixtures


class SlotTests(unittest.TestCase):
    def setUp(self):fixtures.EvaluationTests.setUp(self)

    def encode(self,answer):
        value=copy.deepcopy(answer)
        for field,names in v5.MAPS.items():value[field]={name:name in answer[field] for name in names}
        return value

    def test_roundtrip_keeps_incorrect_decision_instead_of_repairing_it(self):
        answer=fixtures.answer_for(self.oracle);answer['decisions']=['network_is_safe']
        self.assertEqual(v5.decode(self.encode(answer)),answer)
        self.assertFalse(v2.grade(v5.decode(self.encode(answer)),self.oracle)['correct'])

    def test_missing_slots_and_non_booleans_refused(self):
        value=self.encode(fixtures.answer_for(self.oracle));value['decisions'].pop('confirmed_intrusion')
        with self.assertRaises(ValueError):v5.decode(value)
        value=self.encode(fixtures.answer_for(self.oracle));value['decisions']['confirmed_intrusion']=0
        with self.assertRaises(ValueError):v5.decode(value)

    def test_changed_numeric_facts_remain_wrong(self):
        answer=fixtures.answer_for(self.oracle);answer['observations'][0]['count']+=1
        checked=v2.grade(v5.decode(self.encode(answer)),self.oracle)
        self.assertIn('wrong_fact:'+self.oracle['groups'][0]['id'],checked['unsupported_claims'])

    def test_system_contract_trusted_and_never_contains_oracle(self):
        job,_=v5.make_job(self.pack,{'job_id':'M06-A','case_id':'M06','condition':'A','phase':'measured'},
                          'investigator',{}, {},'qwen3.5:4b')
        payload=job['payload'];user=json.loads(payload['messages'][1]['content'])
        self.assertNotIn('output_contract',user)
        self.assertNotIn('required_decisions',json.dumps(payload))
        self.assertNotIn('IGNORE EVIDENCE',json.dumps(payload))
        self.assertEqual(payload['format'],v5.schema())
        self.assertEqual(payload['options']['num_predict'],700)

    def test_duplicate_observation_ids_detected_when_values_differ(self):
        answer=fixtures.answer_for(self.oracle);duplicate=copy.deepcopy(answer['observations'][0]);duplicate['count']+=1
        answer['observations'].append(duplicate)
        self.assertTrue(v2.review_expected(answer,self.oracle)['duplicate_entries'])


if __name__=='__main__':unittest.main()
