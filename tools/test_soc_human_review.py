"""QA-only local server tests. No participant data or answers are used."""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error


class HumanReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        page=b'<html>QA only</html>';data=json.dumps({'cases':[{'id':'Practice'},{'id':'T01'}]}).encode()
        (root/'index.html').write_bytes(page);(root/'participant-data.json').write_bytes(data)
        (root/'display-seal.json').write_text(json.dumps({'sha256':hashlib.sha256(data).hexdigest(),'html_sha256':hashlib.sha256(page).hexdigest()}))
        with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
        self.address=f'http://127.0.0.1:{self.port}'
        self.process=subprocess.Popen([sys.executable,str(Path(__file__).parent/'soc_human_review.py'),'serve','--root',str(root),'--port',str(self.port)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        self.addCleanup(self.stop)
        deadline=time.monotonic()+5
        while True:
            try:self.token=self.get('/data')['token'];break
            except OSError:
                if time.monotonic()>deadline:raise RuntimeError('QA server did not start')
                time.sleep(.05)
    def stop(self):
        self.process.terminate();self.process.wait(timeout=5);self.process.stderr.close()
    def get(self,path):
        with urllib.request.urlopen(self.address+path,timeout=2) as r:return json.load(r)
    def post(self,stage='initial',cid='Practice',origin=None):
        initial={k:'QA test only' for k in ('what_happened','sensor_action','client_outcome','supporting_reference','unknown','next_check')}
        initial.update(prior_exposure='no',disposition='insufficient')
        final={'conclusion':'QA test only','effort':2,'feedback':'test','next_check_result':'not performed; no additional receipt supplied'}
        request=urllib.request.Request(self.address+'/answer',data=json.dumps({'case':cid,'stage':stage,'answer':initial if stage=='initial' else final,'timing':{'elapsed_seconds':5}}).encode(),headers={'Content-Type':'application/json','Origin':origin or self.address,'X-Pilot-Token':self.token})
        with urllib.request.urlopen(request,timeout=2) as r:return json.load(r)
    def test_answers_lock_in_order_and_final_does_not_replace_initial(self):
        first=self.post();final=self.post('final');self.post(cid='T01')
        rows=self.get('/answers')['answers']
        self.assertEqual(len(rows),3);self.assertEqual(rows[0],first);self.assertEqual(rows[1],final)
        self.assertTrue(first['practice']);self.assertFalse(rows[2]['practice'])
        for row in rows:
            original=dict(row);digest=original.pop('sha256')
            self.assertEqual(hashlib.sha256(json.dumps(original,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest(),digest)
    def test_duplicate_wrong_order_and_final_without_initial_are_rejected(self):
        for stage,cid in [('final','Practice'),('initial','T01')]:
            with self.assertRaises(urllib.error.HTTPError) as caught:self.post(stage,cid)
            self.assertEqual(caught.exception.code,409)
        self.post()
        with self.assertRaises(urllib.error.HTTPError):self.post()
        self.assertEqual(len(self.get('/answers')['answers']),1)
    def test_no_answer_key_or_file_route_and_cross_origin_writes_are_refused(self):
        for path in ('/rubric-private.json','/../participant-data.json','/oracle.json'):
            with self.assertRaises(urllib.error.HTTPError) as caught:self.get(path)
            self.assertEqual(caught.exception.code,404)
        with self.assertRaises(urllib.error.HTTPError):self.post(origin='https://example.com')
        self.assertEqual(self.get('/answers')['answers'],[])


if __name__=='__main__':unittest.main(verbosity=2)
