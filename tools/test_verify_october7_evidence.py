"""Adversarial checks for the saved-evidence verifier's trust boundaries."""
import json
from pathlib import Path
import tempfile
import unittest

import soc_analyst as analyst
import soc_context_guard as guard
import verify_october7_evidence as verifier


class ExportVerificationTests(unittest.TestCase):
    def test_extra_unmanifested_file_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'PUBLIC_EXPORT_MANIFEST.json').write_text(json.dumps({'files':{}}))
            (root/'unreviewed-owner.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'membership'):
                verifier.verify_manifest(root)

    def test_changed_public_member_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);raw=b'original'
            entry={'public_sha256':verifier.digest(raw),'source_sha256':verifier.digest(raw),
                   'public_bytes':len(raw),'source_bytes':len(raw),'transformation':'exact source bytes'}
            (root/'PUBLIC_EXPORT_MANIFEST.json').write_text(json.dumps({'files':{'request.json':entry}}))
            (root/'request.json').write_bytes(b'modified')
            with self.assertRaisesRegex(ValueError,'hash/size'):
                verifier.verify_manifest(root)

    def test_redaction_cannot_hide_truncation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);d=root/'request';d.mkdir()
            original=b'private-path new prompt, n_ctx_slot = 8192 task.n_tokens = 123\n'
            public=b'redacted-path new prompt, n_ctx_slot = 8192 task.n_tokens = 123\ntruncating input prompt\n'
            (d/'runtime-request.stderr.bin').write_bytes(public)
            proof=guard.assess(original,context=8192,prompt_tokens=123)
            entries={'request/runtime-request.stderr.bin':{'source_sha256':verifier.digest(original),'source_bytes':len(original)}}
            with self.assertRaisesRegex(ValueError,'full context'):
                verifier.trace_check(root,d,{'input_context':proof},{'prompt_eval_count':123},guard,entries)

    def test_declared_path_redaction_retains_context_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);d=root/'request';d.mkdir()
            original=b'private-local-path new prompt, n_ctx_slot = 8192 task.n_tokens = 123\n'
            public=original.replace(b'private-local-path',b'redacted')
            (d/'runtime-request.stderr.bin').write_bytes(public)
            proof=guard.assess(original,context=8192,prompt_tokens=123)
            entries={'request/runtime-request.stderr.bin':{'source_sha256':verifier.digest(original),'source_bytes':len(original)}}
            verifier.trace_check(root,d,{'input_context':proof},{'prompt_eval_count':123},guard,entries)

    def test_unexpected_thinking_refused_even_with_matching_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            d=Path(folder)
            payload={'options':{},'think':False,'keep_alive':0}
            raw={'done':True,'done_reason':'stop','message':{'content':'{}','thinking':'unsupported hidden answer'}}
            req=analyst.canonical(payload).encode();resp=analyst.canonical(raw).encode()
            (d/'request.json').write_bytes(req);(d/'response.raw.json').write_bytes(resp)
            outcome={'request_sha256':verifier.digest(req),'response_sha256':verifier.digest(resp),
                     'combined_output_sha256':verifier.digest(analyst.canonical(raw['message']).encode()),'options':{}}
            with self.assertRaisesRegex(ValueError,'naturally complete'):
                verifier.output_check(d,outcome,analyst,cpu=False)


if __name__=='__main__':unittest.main()
