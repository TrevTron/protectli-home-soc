"""Transport controls for context proof and explicitly bounded reviewer thinking."""
import copy
from pathlib import Path
from unittest.mock import patch
import soc_investigation_run as runner
import test_soc_investigation_run as original


class GuardTransportTests(original.RunnerTests):
    def test_runtime_input_truncation_withheld_and_following_halted(self):
        job=copy.deepcopy(self.job)
        client=original.FakeClient();client.response['prompt_eval_count']=2050
        trace=b'truncating input prompt\nnew prompt, n_ctx_slot = 4096, task.n_tokens = 2050\n'
        with patch.object(runner.context_guard,'start',return_value=0),patch.object(runner.context_guard,'capture',return_value=trace):
            outcome=runner.one_request(client,job,self.root/'truncated',memory_guard=lambda:32*1024**3,runtime_log=self.root/'trace')
        self.assertEqual(outcome['status'],'withheld');self.assertTrue(outcome['halt_following_requests'])
        self.assertTrue(outcome['input_context']['input_truncated'])
        self.assertTrue((self.root/'truncated'/'response.raw.json').exists())

    def test_reviewer_thinking_requires_explicit_permission_and_natural_stop(self):
        for name,permitted,stop in [('denied',False,'stop'),('allowed',True,'stop'),('capped',True,'length')]:
            job=copy.deepcopy(self.job);job['role']='reviewer';job['payload']['format']={'type':'object'}
            job['payload']['think']=True;job['payload']['options']['num_predict']=2048;job['allow_thinking']=permitted
            client=original.FakeClient();client.response['message']['thinking']='Test-only model channel.';client.response['done_reason']=stop
            result=runner.one_request(client,job,self.root/name,memory_guard=lambda:32*1024**3)
            self.assertEqual(result['status'],'completed' if permitted and stop=='stop' else 'withheld')
            self.assertEqual(result['thinking_characters'],24)
            self.assertTrue((self.root/name/'response.raw.json').exists())


if __name__=='__main__':
    import unittest
    unittest.main()
