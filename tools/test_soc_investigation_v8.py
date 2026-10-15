"""Check the new budget without leaking oracle labels into model requests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import soc_investigation_eval as evaluation
import soc_investigation_v8 as revised
import test_soc_investigation_eval as fixtures


class ResourceContractTests(unittest.TestCase):
    def setUp(self):fixtures.EvaluationTests.setUp(self)

    def test_every_role_has_the_same_recorded_larger_budget(self):
        scheduled={'job_id':'M02-A','case_id':'M02','phase':'measured','condition':'A'}
        locked={'M02-A':{'status':'completed','answer':fixtures.answer_for(self.oracle)}}
        for role in ('analyst','investigator','reviewer'):
            job,reason=revised.make_job(self.pack,scheduled,role,{},locked,
                'qwen3.5:9b' if role=='reviewer' else 'qwen3.5:4b')
            self.assertIsNone(reason)
            self.assertFalse(job['payload']['think'])
            self.assertEqual(job['payload']['options']['num_ctx'],8192)
            self.assertEqual(job['payload']['options']['num_predict'],2048)
            self.assertEqual(job['payload']['options']['num_thread'],16)
            self.assertEqual(job['payload']['options']['num_gpu'],99)

    def test_conditions_keep_identical_deterministic_context_and_no_oracle(self):
        brief=evaluation.load(self.pack/'M02/brief.json');group=brief['groups'][0]
        selected={'M02':{'report':{'observed':[], 'inferred':[{'type':'inferred','code':'sensor_reported_block',
            'group_id':group['id'],'evidence_refs':group['evidence_refs']}],
            'unknown':[{'type':'unknown','topic':'intent'},{'type':'unknown','topic':'complete_visibility'}], 'next_steps':[]}}}
        jobs=[revised.make_job(self.pack,{'job_id':'M02-'+c,'case_id':'M02','phase':'measured','condition':c},
            'investigator',selected,{},'qwen3.5:4b')[0] for c in 'ABC']
        self.assertEqual(len({j['deterministic_context_sha256'] for j in jobs}),1)
        for job in jobs:
            user=json.loads(job['payload']['messages'][1]['content'])
            self.assertNotIn('required_decisions',json.dumps(user))
            self.assertNotIn('oracle',json.dumps(user))

    def test_assistance_failure_does_not_remove_the_evidence_only_condition(self):
        scheduled={'job_id':'M02-A','case_id':'M02','phase':'measured','condition':'A'}
        job,_=revised.make_job(self.pack,scheduled,'investigator',{}, {},'qwen3.5:4b')
        self.assertIsNotNone(job)
        scheduled.update(job_id='M02-B',condition='B')
        job,reason=revised.make_job(self.pack,scheduled,'investigator',{}, {},'qwen3.5:4b')
        self.assertIsNone(job);self.assertIn('withheld',reason)


class CheckpointTests(unittest.TestCase):
    def test_three_finished_batches_write_distinct_immutable_checkpoints(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cases=root/'cases';output=root/'output'
            cases.mkdir();output.mkdir();(cases/'PRE_REQUEST_SEAL.json').write_bytes(b'sealed')
            evaluation.write(output/'EXECUTION_PRE_REQUEST_SEAL.json',{
                'revision':revised.REVISION,'options':revised.OPTIONS,'timeout_seconds':300,
                'tools':{},'case_exposure':'test',
                'case_pre_request_seal_sha256':evaluation.digest(b'sealed')})
            with patch.object(revised.fresh,'verify'), \
                 patch.object(revised.runner,'run',return_value={'halt_reason':None}) as run, \
                 patch.object(revised.v2,'assess',side_effect=[{'batch':n} for n in (1,2,3)]):
                result=revised.execute(cases,output,root/'backend',root/'runtime')
            self.assertEqual(run.call_count,3)
            self.assertEqual(result,[{'batch':n} for n in (1,2,3)])
            for number in (1,2,3):
                self.assertEqual(evaluation.load(output/f'progress-{number}.json'),result[:number])
            self.assertEqual(evaluation.load(output/'complete.json'),result)
            self.assertFalse((output/'progress.json').exists())


if __name__=='__main__':unittest.main(verbosity=2)
