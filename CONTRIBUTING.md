# Reproducing and improving the build

Use an owned lab and retain failed runs as well as successes. For a result, record hardware, firmware/OS/rule snapshot, interface map, traffic route, workload, timing definition, repetitions and relevant temperature/counter boundaries. Keep controlled client receipts and matching original events private; submit a minimal sanitized reproduction instead of a raw export.

For model changes, preserve the brief and expected context before answers, distinguish development from new cases, and record the exact model digest, quantization, template, request settings, generated-token count, stop reason, complete answer and validation failure. A token ceiling is not an observed output length. Do not remove guards, extend deadlines or weaken validation to make a candidate pass.

Run `py -3.12 -m unittest discover -s tools -p 'test_*.py' -v` for software changes. Document separate appliance checks only if actually performed. Keep a new test round separate from earlier results and explain what the evidence can and cannot support.

Do not include passwords, keys, account hashes, private addresses, endpoint identifiers, raw JSONL/PCAP/XML, or someone else's traffic in an issue or patch. The examples use documentation addresses. The proposed license and attribution are in [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
