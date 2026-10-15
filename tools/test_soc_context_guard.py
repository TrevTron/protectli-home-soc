from pathlib import Path
import tempfile
import unittest
import soc_context_guard as guard


class ContextGuardTests(unittest.TestCase):
    def test_complete_prefill_verified(self):
        raw=b'slot operator(): new prompt, n_ctx_slot = 8192, n_keep = 4, task.n_tokens = 5464\n'
        self.assertTrue(guard.assess(raw,context=8192,prompt_tokens=5464)['verified_full_context'])

    def test_truncation_refused_even_if_actual_token_count_matches(self):
        raw=b'truncating input prompt limit=2050 prompt=5464 new=2050\nnew prompt, n_ctx_slot = 4096, task.n_tokens = 2050\n'
        result=guard.assess(raw,context=4096,prompt_tokens=2050)
        self.assertTrue(result['input_truncated']);self.assertFalse(result['verified_full_context'])

    def test_empty_startup_warmup_retained_without_masking_a_second_real_request(self):
        warmup=b'new prompt, n_ctx_slot = 8192, task.n_tokens = 0\n'
        actual=b'new prompt, n_ctx_slot = 8192, task.n_tokens = 5464\n'
        result=guard.assess(warmup+actual,context=8192,prompt_tokens=5464)
        self.assertTrue(result['verified_full_context'])
        self.assertEqual(result['logged_prompt_tokens'],[0,5464])
        self.assertFalse(guard.assess(warmup+actual*2,context=8192,prompt_tokens=5464)['verified_full_context'])

    def test_unknown_ambiguous_context_or_token_mismatch_refused(self):
        good=b'new prompt, n_ctx_slot = 8192, task.n_tokens = 5464\n'
        for raw,context,count in [(b'',8192,5464),(good*2,8192,5464),(good,4096,5464),(good,8192,5463)]:
            self.assertFalse(guard.assess(raw,context=context,prompt_tokens=count)['verified_full_context'])

    def test_only_new_append_bytes_captured_and_rotation_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'trace';p.write_bytes(b'old trace\n');offset=guard.start(p)
            with p.open('ab') as stream:stream.write(b'new trace\n')
            self.assertEqual(guard.capture(p,offset),b'new trace\n')
            p.write_bytes(b'rotated')
            with self.assertRaises(ValueError):guard.capture(p,offset)


if __name__=='__main__':unittest.main()
