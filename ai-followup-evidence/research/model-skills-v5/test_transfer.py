"""Adversarial oracle and cross-artifact input checks before evaluation."""
import copy
import json
import unittest
from bench import HERE,KEYS,compose,ling_payload,read_case,grade
from prepare_transfer import oracle,JOIN

class TransferTests(unittest.TestCase):
    def test_near_match_is_not_a_client_result(self):
        e=dict(zip(JOIN,('a','2026-10-07T01:00:00+00:00','UDP','s',51217,'d',3478)))
        e.update(action='allowed',raw_note='Constructed evidence')
        coverage={'retained_window_complete':True,'prior_window_available':True}
        for field in JOIN:
            r=copy.deepcopy(e);r.update(kind='client_result',result='success',receipt_id='wrong')
            r[field]=r[field]+1 if isinstance(r[field],int) else r[field]+'-other'
            result=oracle([e],[r],coverage)
            self.assertEqual(result['client_outcome'],'unknown');self.assertEqual(result['client_refs'],[])
        r=copy.deepcopy(e);r.update(kind='process_socket',result='success',receipt_id='process')
        self.assertEqual(oracle([e],[r],coverage)['client_outcome'],'unknown')

    def test_all_fresh_cases_and_paired_inputs(self):
        mapping=json.loads((HERE/'transfer-cases/PRE_EVALUATION_SEAL.json').read_text())['mapping_private']
        expected={'allowed_client_success':'supplied_attempt_success','allowed_client_failure':'supplied_attempt_failure',
                  'block_then_retry_success':'retry_success_first_attempt_unknown'}
        for cid,family in mapping.items():
            case,raw,locators,groups=read_case(cid)
            self.assertEqual(case['oracle']['client_outcome'],expected.get(family,'unknown'))
            answer={k:case['oracle'][k] for k in ('client_outcome','client_refs')}
            answer.update(contexts=case['oracle']['required_contexts'],next_checks=[case['oracle']['useful_checks'][0]],
                          intrusion_established=False,delivery_complete=False)
            self.assertTrue(grade(cid,answer)['accepted'])
            native=ling_payload(cid,'clean-off')
            for key in KEYS:
                p=compose(key,cid)['request']
                self.assertEqual(p['messages'],native['messages'])
                self.assertEqual(p['format'],native['response_format']['json_schema']['schema'])
            value=json.loads(native['messages'][1]['content'])
            self.assertNotIn('oracle',value);self.assertNotIn('family',value)
            self.assertNotIn('matched_receipts',value);self.assertNotIn('unmatched_receipts',value)
            if raw:self.assertTrue(all(len(value['receipts'])>=3 for _ in [0]))

if __name__=='__main__':unittest.main()
