import json
import pathlib
import tempfile
import unittest

import soc_flow_review as flow
from test_soc_analyst import CLIENT, event


def anchor(action='blocked'):
    record=event(sid=900001,action=action)
    eve=json.loads(record['raw'][record['raw'].index('{'):])
    eve.update(proto='TCP',src_port=80,dest_port=55000)
    record['raw']='<174>1 fixture suricata - - - '+json.dumps(eve)
    return record


def pf(source=CLIENT,sport=55000,action='pass',direction='in',interface='igc0'):
    fields=['88','','','tracker',interface,'match',action,direction,'4','0x0','','64','1','0','DF','6','tcp','52',source,'203.0.113.5',str(sport),'80','0','S']
    return {'received_utc':anchor()['received_utc'],'app':'filterlog',
            'raw':'<134>1 fixture host filterlog 1 - [meta sequenceId="1"] '+','.join(fields)}


class FlowTests(unittest.TestCase):
    def run_review(self, records):
        with tempfile.TemporaryDirectory() as directory:
            path=pathlib.Path(directory)/'source.jsonl'
            path.write_text(''.join(json.dumps(v)+'\n' for v in records))
            original=path.read_bytes()
            result=flow.investigate(path,anchor(),CLIENT)
            self.assertEqual(path.read_bytes(),original)
            for match in result['matches']:
                actual=original[match['byte_offset']:match['byte_offset']+match['byte_length']]
                self.assertEqual(flow.a.digest(actual),match['sha256'])
            return result

    def test_pass_and_block_correlate_bidirectionally_without_claiming_client_outcome(self):
        result=self.run_review([pf(),anchor()])
        self.assertEqual({v['sensor'] for v in result['matches']},{'pf','suricata'})
        self.assertIn('Different inspection layers',result['interpretation'][0])
        self.assertFalse(result['coverage']['complete_delivery_proven'])

    def test_same_port_nat_and_other_flow_are_not_guessed_as_match(self):
        result=self.run_review([pf(source='198.51.100.2'),pf(sport=55001),anchor()])
        self.assertEqual(result['total_matches'],1)
        self.assertIn('No exact pre-NAT PF match',result['interpretation'][0])

    def test_suricata_only_block_remains_visible_without_inventing_pf_or_client_failure(self):
        result=self.run_review([anchor()])
        self.assertIn('No exact pre-NAT PF match',result['interpretation'][0])
        self.assertIn('Suricata reported a blocked alert',result['interpretation'][1])
        self.assertIn('verify the separate client result',result['interpretation'][1])
        self.assertEqual(result['total_matches'],1)

    def test_unsupported_or_contradictory_pf_format_is_visible(self):
        item=pf()
        item['raw']=item['raw'].replace(',6,tcp,',',17,tcp,')
        result=self.run_review([item,anchor()])
        self.assertEqual(result['coverage']['unsupported_sensor_records_in_window'],1)

    def test_other_owned_device_anchor_is_refused(self):
        with self.assertRaisesRegex(ValueError,'owned client'):
            flow.investigate('not_read',anchor(),'192.0.2.11')

    def test_outside_time_window_cannot_be_correlated(self):
        item=pf()
        item['received_utc']='2026-10-05T20:00:00+00:00'
        self.assertEqual(self.run_review([item,anchor()])['total_matches'],1)


if __name__=='__main__':
    unittest.main(verbosity=2)
