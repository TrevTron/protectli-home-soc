import unittest
from operator_contract import prepare, validate, report


class OperatorTests(unittest.TestCase):
    def test_all_twelve_menus_follow_independent_fixture_oracles(self):
        from workbench import read_case
        for i in range(1, 13):
            cid = f'D{i:02}'
            p = prepare('gemma4-12b', cid)
            case, _, _, _ = read_case(cid)
            self.assertTrue(set(p['fixed_context']['next_checks']) <= set(case['oracle']['useful_checks']))
            for code in p['fixed_context']['next_checks']:
                self.assertTrue(validate(cid, {'next_check': code})['accepted'])
                result = report(cid, {'next_check': code})
                self.assertEqual(result['context_source'], 'deterministic_code')
                self.assertEqual(result['next_check_source'], 'validated_model_selection')
                self.assertEqual(result['citation_roster'], p['citation_roster'])

    def test_cannot_invent_outcome_or_source(self):
        for answer in ({'next_check': 'disable_firewall'}, {'next_check': 'inspect_rule', 'client_success': True},
                       {'next_check': ['inspect_rule']}, {'next_check': 'correlate_client_receipt'}):
            self.assertFalse(validate('D05', answer)['accepted'])

    def test_empty_case_and_changed_signature(self):
        self.assertEqual(prepare('qwen35-4b', 'D09')['fixed_context']['next_checks'], ['inspect_coverage'])
        self.assertEqual(len(prepare('qwen35-4b', 'D10')['citation_roster']), 2)


if __name__ == '__main__':
    unittest.main()
