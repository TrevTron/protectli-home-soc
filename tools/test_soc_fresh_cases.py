"""New-case identity, source integrity and hidden assignment before inference."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import soc_fresh_cases as fresh
import soc_investigation_eval as evaluation


class FreshTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'fresh';fresh.build(self.root)

    def test_new_unique_sources_and_balanced_distinct_human_cases(self):
        result=fresh.verify(self.root);self.assertEqual(result['distinct_cases'],24)
        self.assertEqual(result['model_requests'],0);self.assertEqual(result['human_answers'],0)
        assignment=evaluation.load(self.root/'human-assignment-private.json')['assignments']
        self.assertEqual(len({r['case'] for r in assignment}),18)
        orders=[''.join(r['condition'] for r in assignment if r['block']==b) for b in range(1,7)]
        self.assertEqual(set(orders),{'ABC','ACB','BAC','BCA','CAB','CBA'})
        self.assertEqual([sum(r['session']==s for r in assignment) for s in range(1,4)],[6,6,6])

    def test_changed_endpoint_action_and_rare_block_remain_separate(self):
        brief=evaluation.load(self.root/'batch-1/M03/brief.json')
        self.assertEqual(len(brief['groups']),3)
        blocked=[g for g in brief['groups'] if g['action']=='blocked']
        self.assertEqual(blocked[0]['count'],1);self.assertEqual(blocked[0]['priority_floor'],'review_first')
        self.assertEqual(len({g['destination_alias'] for g in brief['groups']}),2)
        mixed=evaluation.load(self.root/'batch-1/M06/brief.json')
        self.assertEqual(len(mixed['groups']),3);self.assertEqual(mixed['groups'][0]['action'],'blocked')

    def test_missing_context_and_no_alerts_do_not_become_all_clear(self):
        for cid in ('M04','M05'):
            oracle=evaluation.load(self.root/f'batch-1/{cid}/oracle.json')
            self.assertIn('collection_gap_limits_comparison',oracle['required_decisions'])
            self.assertFalse(oracle['complete_delivery_proven']);self.assertEqual(oracle['client_outcome'],'unknown')
        self.assertIn('no_alerts_in_supplied_records',evaluation.load(self.root/'batch-1/M05/oracle.json')['required_decisions'])

    def test_raw_tampering_and_assignment_mutation_are_refused(self):
        path=self.root/'batch-1/M01/records.jsonl';before=path.read_bytes();path.write_bytes(before+b'{}\n')
        with self.assertRaisesRegex(ValueError,'binding'):fresh.verify(self.root)
        path.write_bytes(before);p=self.root/'human-assignment-private.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError,'assignment'):fresh.verify(self.root)

    def test_rehashed_endpoint_change_still_fails_independent_design_check(self):
        path=self.root/'batch-1/M01/records.jsonl';raw=path.read_bytes().replace(b'198.51.100.22',b'203.0.113.200')
        path.write_bytes(raw)
        manifest=self.root/'batch-1/manifest.json';value=evaluation.load(manifest)
        value['files']['M01/records.jsonl']=evaluation.digest(raw);manifest.write_text(json.dumps(value))
        folder=path.parent;origin=evaluation.load(folder/'origin.json')
        salt=('fresh-constructed-'+str(origin['seed'])+'-'+str(origin['number'])).encode()
        with self.assertRaisesRegex(ValueError,'endpoints changed'):
            fresh.independent_design_check(raw,evaluation.load(folder/'brief.json'),
                evaluation.load(folder/'sources.json'),origin['design_specs'],salt)
        with self.assertRaises(ValueError):fresh.verify(self.root)

    def test_frozen_tool_removal_is_refused(self):
        path=self.root/'PRE_REQUEST_SEAL.json';value=evaluation.load(path)
        value['tools'].pop('soc_context_guard.py');path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'tool membership'):fresh.verify(self.root)

    def test_frozen_tools_import_without_working_project_path(self):
        path=self.root/'frozen-tools'
        result=subprocess.run([sys.executable,'-I','-c',
            "import sys;sys.path.insert(0,sys.argv[1]);import soc_fresh_cases;print(soc_fresh_cases.contract.REVISION)",str(path)],
            cwd=path,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('8192',result.stdout)

    def test_build_makes_no_network_requests_and_refuses_existing_output(self):
        with mock.patch('urllib.request.urlopen',side_effect=AssertionError('No network')):
            root=Path(self.temp.name)/'another';fresh.build(root,seed=6100632);fresh.verify(root)
        with self.assertRaisesRegex(ValueError,'must not exist'):fresh.build(self.root)

    def test_new_seed_changes_empty_sources_as_well_as_alert_sources(self):
        later=Path(self.temp.name)/'later';fresh.build(later,seed=6100632)
        old={evaluation.digest(p.read_bytes()) for p in self.root.glob('batch-*/*/records.jsonl')}
        new={evaluation.digest(p.read_bytes()) for p in later.glob('batch-*/*/records.jsonl')}
        self.assertEqual(len(new),24);self.assertFalse(new&old)


if __name__=='__main__':unittest.main(verbosity=2)
