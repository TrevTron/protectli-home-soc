import datetime as dt
import json
import pathlib
import types
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

import soc_analyst as analyst
import soc_analyst_server as viewer
import test_soc_endpoint_context as endpoint_fixtures
import test_soc_index as index_fixtures
import soc_index
from test_soc_analyst import CLIENT, NOW, event


class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.raw = self.root/'syslog.jsonl'
        self.raw.write_text(json.dumps(event())+'\n', encoding='utf-8')
        brief, sources = analyst.build_brief(self.raw, CLIENT, b'x'*32, now=NOW)
        self.ref = next(iter(sources))
        self.run = self.root/'runs'/'fixture'
        self.run.mkdir(parents=True)
        analyst.write_json(self.run/'brief.json', brief)
        analyst.write_json(self.run/'sources.json', {'source_path': str(self.raw), 'sources': sources})
        (self.run/'report.html').write_text(analyst.render(brief, None, 'Fixture: no model'), encoding='utf-8')
        analyst.write_json(self.root/'latest.json', {'run': 'fixture', 'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'period_seconds': 300})
        self.server = viewer.http.server.ThreadingHTTPServer(('127.0.0.1', 0), viewer.handler(self.root, 0, False))
        port = self.server.server_address[1]
        self.server.RequestHandlerClass = viewer.handler(self.root, port, False)
        self.url = f'http://127.0.0.1:{port}'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path, headers=None):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return opener.open(urllib.request.Request(self.url+path, headers=headers or {}), timeout=3)

    def test_report_and_original_source_are_safe_read_only_views(self):
        original = self.raw.read_bytes()
        with self.get('/') as result:
            data = result.read().decode()
            self.assertIn('Snapshot viewer only', data)
            self.assertIn("frame-ancestors 'none'", result.headers['Content-Security-Policy'])
        with self.get('/evidence/'+self.ref) as result:
            self.assertIn('Hash-checked private evidence', result.read().decode())
        self.assertEqual(self.raw.read_bytes(), original)

    def test_source_hash_change_withholds_evidence(self):
        self.raw.write_bytes(b'X'+self.raw.read_bytes()[1:])
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.get('/evidence/'+self.ref)
        self.assertEqual(raised.exception.code, 503)

    def test_rebinding_host_and_bad_reference_refused(self):
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.get('/', {'Host': 'attacker.example'})
        self.assertEqual(raised.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError):
            self.get('/evidence/../../private-key')

    def test_api_does_not_claim_periodic_monitoring_in_view_only_mode(self):
        with self.get('/api/status') as result:
            value = json.load(result)
        self.assertEqual(value['monitoring_mode'], 'snapshot_viewer')

    def test_evidence_link_survives_latest_report_change(self):
        other = self.root/'runs'/'other'
        other.mkdir()
        analyst.write_json(other/'sources.json', {'source_path': str(self.raw), 'sources': {}})
        analyst.write_json(self.root/'latest.json', {'run': 'other', 'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat()})
        with self.get('/evidence/fixture/'+self.ref) as result:
            self.assertIn('Hash-checked private evidence', result.read().decode())

    def test_flow_page_renders_verified_endpoint_context_and_withholds_changed_receipt(self):
        fixture=endpoint_fixtures.EndpointTests()
        fixture.setUp()
        self.raw.write_text(json.dumps(fixture.record)+'\n',encoding='utf-8')
        _,sources=analyst.build_brief(self.raw,CLIENT,b'x'*32,now=dt.datetime(2026,10,5,22,16,tzinfo=dt.timezone.utc))
        ref=next(iter(sources))
        analyst.write_json(self.run/'sources.json',{'source_path':str(self.raw),'sources':sources})
        receipt=self.root/'endpoint-proof.json'
        analyst.write_json(receipt,fixture.proof)
        analyst.write_json(self.root/'endpoint-context-index.json',{
            analyst.digest(self.raw.read_bytes()):{'file':receipt.name,'sha256':analyst.digest(receipt.read_bytes())}})
        self.server.RequestHandlerClass=viewer.handler(self.root,self.server.server_address[1],False,CLIENT)
        original=self.raw.read_bytes()
        with self.get('/investigate/fixture/'+ref) as response:
            page=response.read().decode()
        self.assertIn('Recorded local process context',page)
        self.assertIn('tailscaled.exe',page)
        self.assertIn('data-pacific datetime=',page)
        self.assertIn(analyst.DISPLAY_SCRIPT,page)
        receipt.write_bytes(b'{}')
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.get('/investigate/fixture/'+ref)
        self.assertEqual(raised.exception.code,503)
        self.assertEqual(self.raw.read_bytes(),original)

    def test_failed_worker_preserves_completed_report_and_records_failure(self):
        previous = (self.root/'latest.json').read_bytes()
        args = types.SimpleNamespace(data=self.root, log=self.raw, client=CLIENT, minutes=15,
                                     endpoint='http://127.0.0.1:11435', max_runs=1, interval=300,
                                     model='qwen3.5:4b', generation_profile='common')
        with mock.patch.object(viewer.subprocess, 'run', side_effect=OSError('fixture unavailable executable')) as invoked:
            viewer.worker(args, threading.Event())
        command = invoked.call_args.args[0]
        self.assertEqual(command[command.index('--model')+1], 'qwen3.5:4b')
        self.assertEqual(command[command.index('--generation-profile')+1], 'common')
        state = json.loads((self.root/'worker-state.json').read_text())
        self.assertEqual((state['model'], state['generation_profile']), ('qwen3.5:4b', 'common'))
        self.assertEqual((self.root/'latest.json').read_bytes(), previous)
        receipts = list((self.root/'worker-receipts').glob('*.json'))
        self.assertEqual(len(receipts), 1)
        self.assertEqual(json.loads(receipts[0].read_text())['status'], 'worker_error')

    def test_index_dashboard_works_without_any_model_report_and_escapes_sources(self):
        value=index_fixtures.event()
        value['received_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
        self.raw.write_bytes(index_fixtures.line(value)*2)
        soc_index.sync(self.root/'evidence.sqlite',self.raw)
        (self.root/'latest.json').unlink()
        original=self.raw.read_bytes()
        with mock.patch.object(analyst,'request_model',side_effect=AssertionError('GET called model')):
            with self.get('/') as result:
                page=result.read().decode()
                self.assertIn('2 received records',page)
                self.assertIn('Fixture &lt;script&gt;',page)
                self.assertIn('No completed report',page)
                self.assertIn("form-action 'self'",result.headers['Content-Security-Policy'])
            with self.get('/api/index') as result:
                group=json.load(result)['groups'][0]
            with self.get('/indexed/group/'+group['group_id']) as result:
                self.assertIn('Verify original record',result.read().decode())
            row=soc_index.members(self.root/'evidence.sqlite',group['group_id'])['records'][0]
            with self.get('/indexed/source/'+str(row['offset'])+'/'+row['sha256']) as result:
                self.assertIn('Hash-checked private evidence',result.read().decode())
        self.assertEqual(self.raw.read_bytes(),original)

    def test_index_citation_change_and_invalid_query_are_withheld(self):
        value=index_fixtures.event();value['received_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
        self.raw.write_bytes(index_fixtures.line(value))
        soc_index.sync(self.root/'evidence.sqlite',self.raw)
        for path in ('/?a=1&b=2&c=3&d=4&e=5','/?minutes=1&minutes=2','/?minutes=1441',
                     '/indexed/source/0/'+'0'*64):
            with self.subTest(path=path),self.assertRaises(urllib.error.HTTPError) as raised:
                self.get(path)
            self.assertEqual(raised.exception.code,503)
        group=soc_index.groups(self.root/'evidence.sqlite')['groups'][0]
        row=soc_index.members(self.root/'evidence.sqlite',group['group_id'])['records'][0]
        self.raw.write_bytes(b'X'+self.raw.read_bytes()[1:])
        with self.assertRaises(urllib.error.HTTPError) as raised:
            self.get('/indexed/source/0/'+row['sha256'])
        self.assertEqual(raised.exception.code,503)


class DeliveryTests(unittest.TestCase):
    def test_unavailable_model_preserves_evidence_and_withholds_findings(self):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder)
            source=root/'source.jsonl'
            source.write_text(json.dumps(event())+'\n')
            original=source.read_bytes()
            argv=['analyst','--log',str(source),'--client',CLIENT,'--salt-file',str(root/'aliases.key'),
                  '--output',str(root/'run'),'--as-of',NOW.isoformat()]
            with mock.patch('sys.argv',argv),mock.patch.object(analyst,'request_model',side_effect=OSError('model unavailable fixture')):
                self.assertEqual(analyst.main(),2)
            self.assertEqual(source.read_bytes(),original)
            self.assertTrue((root/'run'/'brief.json').exists())
            self.assertIn('model unavailable fixture',(root/'run'/'report.html').read_text())
            self.assertFalse((root/'run'/'accepted-report.json').exists())

    def test_token_cap_and_bad_output_are_not_delivered(self):
        for reason, content in [('length', '{}'), ('stop', '{"summary":"definitely malicious"}')]:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as folder:
                root = pathlib.Path(folder)
                source = root/'source.jsonl'
                source.write_text(json.dumps(event())+'\n')
                response = {'done': True, 'done_reason': reason, 'message': {'content': content}}
                argv = ['analyst', '--log', str(source), '--client', CLIENT, '--salt-file', str(root/'aliases.key'),
                        '--output', str(root/'run'), '--as-of', NOW.isoformat()]
                with mock.patch('sys.argv', argv), mock.patch.object(analyst, 'request_model', return_value=(response, {})):
                    self.assertEqual(analyst.main(), 2)
                self.assertFalse((root/'run'/'accepted-report.json').exists())
                self.assertIn('withheld', (root/'run'/'rejection.json').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
