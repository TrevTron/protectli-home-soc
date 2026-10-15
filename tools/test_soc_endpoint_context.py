"""False attribution, tuple reuse and retained endpoint-receipt integrity."""
import copy
import datetime as dt
import json
import pathlib
import tempfile
import unittest

import soc_analyst as a
import soc_endpoint_context as c


class EndpointTests(unittest.TestCase):
    def setUp(self):
        eve={'event_type':'alert','alert':{'signature_id':2071648,'action':'allowed','severity':3},
             'proto':'TCP','src_ip':'192.0.2.10','src_port':54321,'dest_ip':'203.0.113.5','dest_port':443,
             'flow':{'start':'2026-10-05T22:15:10.4+00:00'}}
        self.record={'app':'suricata','received_utc':'2026-10-05T22:15:11+00:00','raw':'<174>1 fixture suricata - - - '+json.dumps(eve)}
        self.proof={'captured_utc':'2026-10-05T22:41:14+00:00',
            'exact_tuple':{k:eve[k] for k in ('proto','src_ip','src_port','dest_ip','dest_port')},
            'active_connection':[{'LocalAddress':eve['src_ip'],'LocalPort':eve['src_port'],
                'RemoteAddress':eve['dest_ip'],'RemotePort':eve['dest_port'],'OwningProcess':123,
                'CreationTime':'2026-10-05T22:15:10+00:00'}],
            'process':{'ProcessId':123,'ParentProcessId':456,'Name':'tailscaled.exe','CreationDate':'2026-10-04T22:00:00+00:00'},
            'service':{'ProcessId':456,'Name':'Tailscale','State':'Running'},'signature_status':'Valid'}

    def test_actual_shape_is_historical_context_without_intent_verdict(self):
        result=c.verify(self.proof,self.record,'192.0.2.10')
        self.assertEqual(result['process_name'],'tailscaled.exe')
        self.assertIn('does not establish benign intent',result['meaning'])
        self.assertIn('does not prove the running executable path',result['signature_limit'])

    def test_wrong_process_parent_port_or_reused_tuple_rejected(self):
        for section,key,value in [('process','ProcessId',999),('process','ParentProcessId',999),
            ('active_connection','RemotePort',444),('active_connection','CreationTime','2026-10-05T22:16:10+00:00')]:
            with self.subTest(key=key):
                proof=copy.deepcopy(self.proof)
                target=proof[section][0] if section=='active_connection' else proof[section]
                target[key]=value
                with self.assertRaises(ValueError): c.verify(proof,self.record,'192.0.2.10')
        with self.assertRaises(ValueError): c.verify(self.proof,self.record,'192.0.2.11')

    def test_receipt_hash_and_locator_are_checked_and_unknown_stays_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root=pathlib.Path(directory)
            raw=json.dumps(self.record)+'\n'
            proof=root/'proof.json'
            a.write_json(proof,self.proof)
            index={a.digest(raw.encode()):{'file':'proof.json','sha256':a.digest(proof.read_bytes())}}
            a.write_json(root/'endpoint-context-index.json',index)
            self.assertEqual(c.load(root,raw,'192.0.2.10')['process_name'],'tailscaled.exe')
            self.assertIsNone(c.load(root,raw+' ','192.0.2.10'))
            proof.write_bytes(b'{}')
            with self.assertRaises(ValueError): c.load(root,raw,'192.0.2.10')
            index[a.digest(raw.encode())]['file']='../private.json'
            a.write_json(root/'endpoint-context-index.json',index)
            with self.assertRaises(ValueError): c.load(root,raw,'192.0.2.10')


if __name__=='__main__':
    unittest.main()
