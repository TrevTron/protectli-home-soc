import json
import unittest
from bench import PROFILES,compose,ling_payload,grade,read_case,DIMENSIONS,prompt

class BenchTests(unittest.TestCase):
    def test_clean_contract_and_control_parity(self):
        p=compose('gemma4-12b','D03');q=compose('qwen35-4b','D03')
        self.assertEqual(p['request']['messages'],q['request']['messages'])
        self.assertNotIn('only contexts and next_checks',prompt('clean-off'))
        self.assertIn('only contexts and next_checks',prompt('legacy-off'))
        for profile in PROFILES:
            native=ling_payload('D03',profile)
            self.assertEqual(native['messages'][1],p['request']['messages'][1])
            self.assertEqual(set(native['response_format']['json_schema']['schema']['required']),set(DIMENSIONS))

    def test_actual_client_and_coverage_decisions(self):
        for cid in ('D03','D04','D08','D12'):
            case,*_=read_case(cid)
            answer={k:case['oracle'][k] for k in ('client_outcome','client_refs')}
            answer.update(contexts=case['oracle']['required_contexts'],next_checks=[case['oracle']['useful_checks'][0]],
                          intrusion_established=False,delivery_complete=False)
            self.assertTrue(grade(cid,answer)['accepted'])
            answer['next_checks'].append('compare_retained_window')
            self.assertFalse(grade(cid,answer)['dimensions']['next_checks'])
        case,*_=read_case('D03')
        p=compose('gemma4-12b','D03')
        value=json.loads(p['request']['messages'][1]['content'])
        self.assertNotIn('matched_receipts',value)
        self.assertNotIn('oracle',value)
        self.assertTrue(value['original_records'])

if __name__=='__main__':unittest.main(verbosity=2)
