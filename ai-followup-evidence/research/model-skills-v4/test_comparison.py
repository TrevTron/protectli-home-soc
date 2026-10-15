import copy
import json
import unittest
from comparison import compose, grade, prior, KEYS

class ComparisonTests(unittest.TestCase):
    def answer(self,cid):
        c,*_ = prior.read_case(cid,'evaluation')
        return {'contexts':c['oracle']['required_contexts'], 'next_checks':[c['oracle']['useful_checks'][0]],
                'client_outcome':c['oracle']['client_outcome'],'client_refs':c['oracle']['client_refs'],
                'intrusion_established':False,'delivery_complete':False}

    def test_complete_receipt_join_input_and_no_oracle(self):
        for n in range(1,13):
            cid=f'F{n:02}'
            p=compose('gemma4-12b',cid)
            v=json.loads(p['request']['messages'][1]['content'])
            self.assertNotIn('matched_receipts',v)
            self.assertNotIn('unmatched_receipts',v)
            self.assertNotIn('oracle',v)
            c,raw,locators,rows=prior.read_case(cid,'evaluation')
            self.assertEqual(v['original_records'],[prior.original(raw,locators,ref) for ref in locators])
            self.assertEqual(v['receipts'],c['receipts'])
            for r in v['original_records']:
                self.assertTrue(all(k in r for k in ('attempt_id','event_utc','protocol','source_alias','source_port','destination_alias','destination_port')))
            self.assertTrue(grade(cid,self.answer(cid))['accepted'])

    def test_identical_model_workload(self):
        for n in range(1,13):
            requests=[compose(k,f'F{n:02}')['request'] for k in KEYS]
            for r in requests[1:]:
                for key in ('messages','format','options','think'):
                    self.assertEqual(r[key],requests[0][key])

    def test_wrong_tuple_process_and_retry(self):
        for cid in ('F06','F07'):
            a=self.answer(cid)
            a['client_outcome']='supplied_attempt_success'
            self.assertFalse(grade(cid,a)['dimensions']['client_outcome'])
        a=self.answer('F05');a['client_outcome']='supplied_attempt_success'
        self.assertFalse(grade('F05',a)['accepted'])
        a=self.answer('F03');a['client_refs']=['invented']
        self.assertFalse(grade('F03',a)['dimensions']['client_refs'])

    def test_coverage_and_injection_required(self):
        for cid,required in [('F11','untrusted_log_text'),('F12','comparison_incomplete'),('F08','coverage_limits')]:
            a=self.answer(cid);a['contexts']=[c for c in a['contexts'] if c!=required]
            self.assertFalse(grade(cid,a)['dimensions']['contexts'])
        a=self.answer('F09');a['delivery_complete']=True
        self.assertFalse(grade('F09',a)['accepted'])

    def test_malformed_and_boolean_gate(self):
        self.assertFalse(grade('F01',{})['accepted'])
        a=self.answer('F01');a['client_refs']=[{}]
        self.assertFalse(grade('F01',a)['accepted'])
        a=self.answer('F01');a['intrusion_established']=0
        self.assertFalse(grade('F01',a)['accepted'])

if __name__=='__main__':unittest.main(verbosity=2)
