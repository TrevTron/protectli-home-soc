import json
import pathlib
import re
import tempfile
import threading
import types
import unittest
import urllib.parse
import urllib.request
import urllib.error
from unittest import mock

import soc_operator as operator
import soc_analyst as analyst
import soc_analyst_server as viewer
import test_soc_analyst_server as fixtures


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ViewerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.brief, self.hash = operator.read_brief(self.root,'fixture')
        self.group = self.brief['groups'][0]

    def record(self, note='Exact source reviewed; intent remains unknown.'):
        return operator.append_review(self.root,'fixture',self.group['id'],self.hash,'reviewed',note,viewer.original_event)

    def test_notes_persist_outside_model_and_source_and_html_is_escaped(self):
        original=self.fixture.raw.read_bytes()
        model_input=analyst.canonical(self.brief)
        self.record('<script>bad</script>')
        self.record('Follow-up recorded')
        saved=operator.load_journal(self.root)
        self.assertEqual(len(saved),2)
        self.assertEqual(saved[1]['previous_sha256'],saved[0]['entry_sha256'])
        page=operator.review_page(self.root,'fixture','token')
        self.assertNotIn('<script>bad</script>',page)
        self.assertIn('Follow-up recorded',page)
        self.assertEqual(analyst.canonical(operator.read_brief(self.root,'fixture')[0]),model_input)
        self.assertEqual(self.fixture.raw.read_bytes(),original)
        self.assertEqual(operator.load_journal(self.root),saved)

    def test_changed_source_and_tampered_journal_fail_closed(self):
        self.record()
        journal=self.root/'operator-review.jsonl'
        original=journal.read_bytes()
        self.fixture.raw.write_bytes(b'X'+self.fixture.raw.read_bytes()[1:])
        with self.assertRaises(ValueError): self.record()
        self.assertEqual(journal.read_bytes(),original)
        with self.assertRaises(urllib.error.HTTPError) as error:self.fixture.get('/review/fixture')
        self.assertEqual(error.exception.code,503)
        journal.write_bytes(original.replace(b'intent remains unknown',b'intent is proven benign'))
        with self.assertRaises(ValueError): operator.load_journal(self.root)

    def test_new_evidence_does_not_inherit_review(self):
        self.record()
        self.brief['groups'][0]['count']+=1
        analyst.write_json(self.fixture.run/'brief.json',self.brief)
        page=operator.review_page(self.root,'fixture','token')
        self.assertIn('New evidence since recorded review',page)
        with self.assertRaises(ValueError): self.record()

    def test_post_requires_same_origin_token_and_exact_fields(self):
        with self.fixture.get('/review') as response:
            page=response.read().decode()
            self.assertIn("form-action 'self'",response.headers['Content-Security-Policy'])
        token=re.search(r'name="csrf" value="([^"]+)"',page)[1]
        values={'csrf':token,'run':'fixture','group':self.group['id'],'brief_hash':self.hash,'state':'reviewed','note':'Exact source checked; no benign verdict.'}
        def post(fields,origin=None):
            request=urllib.request.Request(self.fixture.url+'/review',data=urllib.parse.urlencode(fields).encode(),headers={'Content-Type':'application/x-www-form-urlencoded','Origin':origin or self.fixture.url})
            return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=3)
        for fields,origin,code in [(values,'https://attacker.example',403),({**values,'csrf':'wrong'},None,403),({**values,'extra':'x'},None,400),({**values,'note':' '},None,400)]:
            with self.assertRaises(urllib.error.HTTPError) as error:post(fields,origin)
            self.assertEqual(error.exception.code,code)
            self.assertFalse((self.root/'operator-review.jsonl').exists())
        with post(values) as response:
            self.assertIn('Exact source checked',response.read().decode())
        self.assertEqual(len(operator.load_journal(self.root)),1)
        with self.fixture.get('/review/fixture') as response:self.assertIn('Reviewed this snapshot',response.read().decode())
        self.assertEqual(len(operator.load_journal(self.root)),1)

    def test_health_is_available_without_report_or_native_observation(self):
        (self.root/'latest.json').unlink()
        with mock.patch.object(operator,'receiver_status',side_effect=OSError('offline')):
            with self.fixture.get('/health') as response: page=response.read().decode()
        self.assertIn('No valid completed report',page)
        self.assertIn('Logging health is unknown',page)
        self.assertIn('No valid collected observation',page)

    def test_saved_history_exposes_prior_alerts_when_current_report_is_unavailable(self):
        (self.root/'latest.json').unlink()
        with self.fixture.get('/history') as response:page=response.read().decode()
        self.assertIn('href="/review/fixture"',page)
        self.assertIn('1 alert groups',page)
        self.assertIn('No accepted model report',page)

    def test_health_retention_and_stale_observation_do_not_claim_current_coverage(self):
        health={'collected_utc':'2026-01-01T00:00:00Z','vault':{'status':'unavailable'},'host':{'vault_route_status':'unknown','vault_dns_status':'unknown','wifi_state':'unknown','tailscale_status':'unknown','available_memory_gib':'unknown'}}
        analyst.write_json(self.root/'health-snapshot.json',health)
        with mock.patch.object(operator,'receiver_status',return_value=({'accepted_this_run':1,'retention_full':True,'stored_bytes':209715200,'max_bytes':209715200},None)):
            with self.fixture.get('/health') as response:page=response.read().decode()
        self.assertIn('New evidence is not being retained',page)
        self.assertIn('Observation is stale',page)
        self.assertIn('Temperature, storage and engine state are unknown',page)

    def test_failed_finite_health_collector_preserves_observation_and_evidence(self):
        original=self.fixture.raw.read_bytes()
        saved=b'{"retained":"prior observation"}'
        (self.root/'health-snapshot.json').write_bytes(saved)
        args=types.SimpleNamespace(data=self.root,max_runs=1,interval=30,powershell='missing-pwsh.exe',vault_address=fixtures.CLIENT,serial_port='COM3',health_backup=None)
        with mock.patch.object(viewer.subprocess,'run',side_effect=OSError('collector unavailable')), mock.patch.object(analyst,'request_model') as model:
            viewer.health_worker(args,threading.Event())
        model.assert_not_called()
        self.assertEqual((self.root/'health-snapshot.json').read_bytes(),saved)
        self.assertEqual(self.fixture.raw.read_bytes(),original)
        state=json.loads((self.root/'native-health-state.json').read_text())
        self.assertEqual(state['status'],'bounded_collection_complete')
        self.assertEqual(state['collector_failures'],1)
        self.assertEqual(len(list(self.root.glob('health-worker-*.json'))),1)

    def test_archive_errors_and_observation_gaps_visible_without_actions(self):
        analyst.write_json(self.root/'observation-state.json',{'status':'collecting','samples':2,'max_samples':576,'gap_count':1,'ends_utc':'2026-10-08T02:00:00Z'})
        analyst.write_json(self.root/'archive-state.json',{'status':'error','checked_utc':'2026-10-06T02:00:00Z','reason':'<script>budget reached</script>'})
        with mock.patch.object(operator,'receiver_status',return_value=({'retention_full':False,'stored_bytes':120,'max_bytes':200,'segment_count':2,'storage_error':None},None)),mock.patch.object(viewer.subprocess,'run') as process:
            with self.fixture.get('/health') as response:page=response.read().decode()
        process.assert_not_called()
        self.assertIn('2 / 576 samples; 1 gaps',page)
        self.assertIn('across 2 append-only segments',page)
        self.assertIn('&lt;script&gt;budget reached&lt;/script&gt;',page)
        self.assertIn('archiving does not reclaim',page)

    def test_recovery_errors_and_pause_are_visible_without_executing_anything(self):
        analyst.write_json(self.root/'startup-state.json',{'checked_utc':'2026-01-01T00:00:00Z','status':'error','reason':'<script>do not execute</script>'})
        with mock.patch.object(operator,'receiver_status',side_effect=OSError('offline')), mock.patch.object(viewer.subprocess,'run') as process:
            with self.fixture.get('/health') as response:page=response.read().decode()
        process.assert_not_called()
        self.assertIn('Last recorded check: error',page)
        self.assertIn('Recovery observation is stale',page)
        self.assertIn('&lt;script&gt;do not execute&lt;/script&gt;',page)
        self.assertNotIn('<script>do not execute</script>',page)
        (self.root/'recovery').mkdir()
        (self.root/'recovery'/'paused.flag').write_text('Maintenance')
        with mock.patch.object(operator,'receiver_status',side_effect=OSError('offline')):
            with self.fixture.get('/health') as response:page=response.read().decode()
        self.assertIn('Paused for maintenance',page)


if __name__=='__main__':unittest.main(verbosity=2)
