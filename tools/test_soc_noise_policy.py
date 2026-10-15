"""Changed scopes, priority floors, evidence retention, expiry and rollback."""
import copy
import unittest

import soc_noise_policy as noise


class NoiseTests(unittest.TestCase):
    def setUp(self):
        self.policy={'version':1,'id':'documented-stun','revision':1,'reason':'Synthetic expected endpoint case inspected.',
            'supporting_case_sha256':'a'*64,'created_utc':'2026-10-06T18:00:00Z','expires_utc':'2026-10-07T18:00:00Z',
            'window_seconds':900,'max_count':30,'scope':{'sid':2016150,'rev':4,'source_ip':'192.0.2.10',
            'destination_ip':'198.51.100.22','protocol':'UDP','destination_port':3478,'action':'allowed','severity':3}}
        self.now='2026-10-06T18:10:00Z'
        self.group={**self.policy['scope'],'id':'g01','priority_floor':'review','count':20,'window_seconds':900,
            'evidence_refs':['E-'+'a'*16],'sources_verified':True,'comparison_available':True,'scope_complete':True}

    def preview(self,groups=None):return noise.preview(self.policy,groups or [self.group],now=self.now)

    def test_expected_labels_preserve_counts_refs_visibility_and_input(self):
        before=copy.deepcopy(self.group);receipt=self.preview();row=receipt['groups'][0]
        self.assertEqual(row['label'],'expected_context');self.assertTrue(row['keep_visible'])
        self.assertEqual(row['count'],20);self.assertEqual(row['evidence_refs'],self.group['evidence_refs'])
        self.assertEqual(receipt['suppressed_records'],0);self.assertEqual(before,self.group)

    def test_endpoint_port_rule_revision_protocol_action_severity_changes_stay_review(self):
        for field,value in [('source_ip','192.0.2.11'),('destination_ip','203.0.113.10'),('destination_port',8443),
                ('sid',2016149),('rev',5),('protocol','TCP'),('action','blocked'),('severity',2),('rev',True)]:
            with self.subTest(field=field,value=value):
                row=self.preview([{**self.group,field:value}])['groups'][0]
                self.assertEqual(row['label'],'review')

    def test_rare_block_and_severity_one_inside_repeats_keep_priority(self):
        groups=[self.group,{**self.group,'id':'g02','action':'blocked','severity':1,'count':1}]
        receipt=self.preview(groups);self.assertEqual(receipt['visible_groups'],2)
        self.assertEqual(receipt['groups'][1]['priority_floor'],'review_first')
        self.assertEqual(receipt['groups'][1]['label'],'review')

    def test_missing_context_bad_refs_and_bursts_are_never_expected(self):
        for field,value in [('sources_verified',False),('comparison_available',False),('scope_complete',False),
                ('count',31),('count',True),('window_seconds',300),('evidence_refs',[])]:
            with self.subTest(field=field):self.assertEqual(self.preview([{**self.group,field:value}])['expected_groups'],0)

    def test_expiry_and_not_started_are_visible(self):
        for at in ('2026-10-05T18:00:00Z','2026-10-07T18:00:00Z'):
            self.assertEqual(noise.preview(self.policy,[self.group],now=at)['expected_groups'],0)

    def test_unsafe_broad_policy_long_expiry_and_missing_revision_refused(self):
        for key,value in [('destination_ip','*'),('destination_port',0),('rev',None),('action','blocked'),('severity',1)]:
            policy=copy.deepcopy(self.policy);policy['scope'][key]=value
            with self.assertRaises(ValueError):noise.validate(policy)
        with self.assertRaisesRegex(ValueError,'Expiry'):noise.validate({**self.policy,'expires_utc':'2026-11-06T18:00:00Z'})

    def test_duplicate_scopes_cannot_split_burst_below_count_limit(self):
        with self.assertRaisesRegex(ValueError,'combined counts'):self.preview([self.group,{**self.group,'id':'g02'}])

    def test_activation_requires_exact_review_support_and_fresh_preview(self):
        receipt=self.preview()
        for sha,case,now in [('0'*64,'a'*64,self.now),(receipt['preview_sha256'],'b'*64,self.now),
                             (receipt['preview_sha256'],'a'*64,'2026-10-06T20:00:00Z')]:
            with self.assertRaises(ValueError):noise.activate(self.policy,receipt,reviewed_preview_sha256=sha,
                verified_case_sha256=case,now=now)
        changed=copy.deepcopy(receipt);changed['groups'][0]['count']=1
        with self.assertRaisesRegex(ValueError,'changed'):noise.activate(self.policy,changed,
            reviewed_preview_sha256=receipt['preview_sha256'],verified_case_sha256='a'*64,now=self.now)

    def test_revision_and_rollback_preserve_previous_offline_state(self):
        receipt=self.preview();first=noise.activate(self.policy,receipt,reviewed_preview_sha256=receipt['preview_sha256'],
            verified_case_sha256='a'*64,now=self.now)
        self.assertFalse(first['live_applied'])
        original_count=first['policy']['max_count'];self.policy['max_count']=25
        self.assertEqual(first['policy']['max_count'],original_count)
        self.policy['max_count']=original_count
        second_policy={**self.policy,'revision':2};receipt2=noise.preview(second_policy,[self.group],now=self.now)
        second=noise.activate(second_policy,receipt2,reviewed_preview_sha256=receipt2['preview_sha256'],
            verified_case_sha256='a'*64,now=self.now,previous=first)
        restored=noise.rollback(second,expected_state_sha256=noise.digest(second));self.assertEqual(restored['restored'],first)
        with self.assertRaisesRegex(ValueError,'state changed'):noise.rollback(second,expected_state_sha256='0'*64)
        with self.assertRaisesRegex(ValueError,'increase'):noise.activate(self.policy,receipt,
            reviewed_preview_sha256=receipt['preview_sha256'],verified_case_sha256='a'*64,now=self.now,previous=first)


if __name__=='__main__':unittest.main(verbosity=2)
