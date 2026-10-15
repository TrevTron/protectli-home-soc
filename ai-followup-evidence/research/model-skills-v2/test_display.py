import copy
import unittest
from workbench import compose, read_case, original, grade
from display import deterministic_context, render_page


class DisplayTests(unittest.TestCase):
    def test_code_fallback_matches_each_sealed_case(self):
        for i in range(1, 13):
            cid = f'D{i:02}'
            p = compose('qwen35-4b', cid)
            case, raw, locators, _ = read_case(cid)
            p['original_records'] = {ref: original(raw, locators, ref) for ref in locators}
            result = deterministic_context(p)
            self.assertTrue(grade(cid, result)['accepted'], (cid, result))
            self.assertNotIn('oracle', p)
            self.assertEqual(deterministic_context(copy.deepcopy(p)), result)

    def test_originals_escape_and_old_ling_excluded(self):
        page = render_page([])
        self.assertIn('Ling 3.0 tiny', page)
        self.assertNotIn('mini 2.0', page)
        self.assertNotIn('<script>fetch', page)
        self.assertIn('Displaying the context and checks supplied by code.', page)
        self.assertIn('original_records', page)


if __name__ == '__main__':
    unittest.main()
