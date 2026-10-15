"""Replay saved synthetic briefs through explicit evaluation-only models.

One request per model/case with the analyst's unchanged prompt and request
bounds. This measures delivery on known regressions, not general accuracy or
pure throughput. Native templates, tokenizers, quantization and defaults differ.
"""
import argparse
import datetime as dt
import json
import pathlib
import time
import urllib.request

import soc_analyst as a


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--endpoint', default='http://127.0.0.1:11435')
    parser.add_argument('--generation-profile', choices=('native', 'common'), default='native')
    parser.add_argument('--models', nargs='+', choices=sorted(a.EVALUATION_MODELS),
                        default=['qwen3:4b-instruct'])
    args = parser.parse_args()
    endpoint = a.local_endpoint(args.endpoint)
    cases = sorted(args.fixtures.glob('*/brief.json'))
    if not cases or len(cases) > 8 or len(args.models) != len(set(args.models)):
        parser.error('Supply 1-8 saved briefs and distinct admitted models')
    # Never replace a prior evaluation or its errors.
    args.output.mkdir(parents=True, exist_ok=False)
    frozen = []
    for source in cases:
        if source.stat().st_size > 256*1024:
            raise ValueError('Saved brief exceeds replay bound')
        raw = source.read_bytes()
        a.strict_json(raw.decode())
        target = args.output/source.parent.name
        target.mkdir()
        (target/'brief.json').write_bytes(raw)
        frozen.append({'case':source.parent.name,'sha256':a.digest(raw)})
    a.write_json(args.output/'protocol.json', {'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'models':args.models,'input_hashes':frozen,'system_prompt_sha256':a.digest(a.SYSTEM.encode()),
        'requests_per_case_model':1,'timeout_seconds':120,'think':False,
        'generation_profile':args.generation_profile,'options':a.generation_options(args.generation_profile),
        'limit':'Known synthetic regression replay. Cold loading, natural unequal answer lengths and differing model defaults/templates/quantization prevent a pure throughput or size winner claim.'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def metadata(path):
        with opener.open(endpoint+path, timeout=5) as response:
            return json.load(response)
    if metadata('/api/ps').get('models'):
        raise RuntimeError('Isolated runtime already has a loaded model. Wait for existing work; do not unload it.')
    tags = {m['name']:m for m in metadata('/api/tags')['models']}
    if not set(args.models).issubset(tags):
        raise ValueError('A named candidate is absent from the separate runtime. This harness does not download or substitute models.')
    a.write_json(args.output/'model-tags.json', [tags[m] for m in args.models])
    outcomes=[]
    for model in args.models:
        name=model.replace(':','-').replace('.','_')
        request=urllib.request.Request(endpoint+'/api/show',data=a.canonical({'model':model}).encode(),headers={'Content-Type':'application/json'})
        with opener.open(request,timeout=10) as response:
            a.write_json(args.output/(name+'-show.json'),json.load(response))
        for item in frozen:
            case=args.output/item['case']
            raw=(case/'brief.json').read_bytes()
            if a.digest(raw)!=item['sha256']:
                raise RuntimeError('Frozen input changed')
            target=case/name
            target.mkdir()
            outcome={'model':model,'case':item['case']}
            try:
                response,meta=a.request_model(a.strict_json(raw.decode()),endpoint,model,evaluation=True,profile=args.generation_profile)
                a.write_json(target/'response.json',response)
                a.write_json(target/'metadata.json',meta)
                if response.get('done') is not True or response.get('done_reason')!='stop' or meta['thinking_characters']:
                    raise a.Rejected('Incomplete/capped output or unexpected thinking channel')
                report=a.validate(a.strict_json(response['message']['content']),a.strict_json(raw.decode()))
                a.write_json(target/'accepted-report.json',report)
                outcome.update(mechanical_grounding='passed',elapsed_s=meta['elapsed_s'],eval_count=meta['eval_count'])
            except Exception as error:
                outcome.update(status='withheld',reason=str(error))
            a.write_json(target/'outcome.json',outcome)
            outcomes.append(outcome)
            a.write_json(args.output/'outcomes-progress.json',outcomes)
            print(a.canonical(outcome),flush=True)
            deadline=time.monotonic()+150
            while metadata('/api/ps').get('models'):
                if time.monotonic()>deadline:
                    raise RuntimeError('Runner still loaded after bounded wait; stop subsequent requests, do not unload unrelated work')
                time.sleep(2)
    a.write_json(args.output/'outcomes-complete.json',outcomes)


if __name__=='__main__':
    main()
