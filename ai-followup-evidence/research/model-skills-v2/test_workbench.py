import json
import unittest
from workbench import compose, grade, read_case, normalize, render_page, KEYS


class WorkbenchTests(unittest.TestCase):
    def test_pinned_choices_and_equal_input(self):
        proposals = [compose(key, 'D05') for key in KEYS]
        self.assertEqual(len({p['input_sha256'] for p in proposals}), 1)
        self.assertEqual(len({p['manifest_digest'] for p in proposals}), 4)
        self.assertEqual(len({json.dumps(p['request']['options'], sort_keys=True) for p in proposals}), 1)

    def test_only_skill_factor_changes(self):
        a, b = compose('gemma4-12b', 'D05', False), compose('gemma4-12b', 'D05', True)
        self.assertEqual(a['input_sha256'], b['input_sha256'])
        for field in ('format', 'options', 'think', 'stream', 'keep_alive'):
            self.assertEqual(a['request'][field], b['request'][field])
        self.assertTrue(b['request']['messages'][0]['content'].startswith(a['request']['messages'][0]['content']))

    def test_originals_attached_by_code(self):
        p = compose('qwen35-4b', 'D05')
        model_input = p['request']['messages'][1]['content']
        for row in p['citation_roster'].values():
            self.assertNotIn(row['id'], model_input)
            for member in row['members']:
                self.assertNotIn(member['ref'], model_input)
        self.assertEqual(p['facts']['client_results'][0]['attempt_id'], 'D05-attempt-2')
        self.assertTrue(any(r['fields']['action'] == 'blocked' for r in p['facts']['groups']))

    def test_bad_receipt_cannot_establish_client_result(self):
        p = compose('qwen35-4b', 'D07')
        self.assertEqual(p['facts']['client_results'], [])
        self.assertEqual(len(p['facts']['unmatched_receipts']), 1)

    def test_process_receipt_is_not_client_result(self):
        p = compose('qwen35-4b', 'D06')
        self.assertEqual(p['facts']['client_results'], [])
        self.assertEqual(p['facts']['matched_receipts'][0]['kind'], 'process_socket')

    def test_all_oracle_positive_and_adversarial(self):
        for i in range(1, 13):
            cid = f'D{i:02}'
            case, _, _, _ = read_case(cid)
            good = {'contexts': list(case['oracle']['required_contexts']), 'next_checks': [case['oracle']['useful_checks'][0]]}
            self.assertTrue(grade(cid, good)['accepted'])
            self.assertFalse(grade(cid, {**good, 'client_success': True})['accepted'])
            self.assertFalse(grade(cid, {'contexts': [], 'next_checks': ['none']})['accepted'])

    def test_unknown_model_and_label_exclusion(self):
        with self.assertRaises(ValueError):
            compose('ling', 'D01')
        value = json.loads(compose('gemma4-12b', 'D01')['request']['messages'][1]['content'])
        for name in ('oracle', 'family', 'split', 'expected_answer', 'case_id'):
            self.assertNotIn(name, value)

    def test_same_signature_preservation_and_annotation(self):
        self.assertEqual(len(compose('gemma4-12b', 'D10')['facts']['groups']), 2)
        p = compose('gemma4-12b', 'D11')
        self.assertIn('Ignore instructions', p['request']['messages'][1]['content'])
        page = render_page()
        self.assertNotIn('<script>fetch', page)
        self.assertIn('\\u003cscript', page)


if __name__ == '__main__':
    unittest.main()
