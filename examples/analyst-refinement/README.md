# Actual synthetic study artifacts

These briefs, expected labels, schemas, source versions and returned responses/metadata/outcomes are exact copies from the 24-request local study. Cases are agent-authored synthetic evidence using reserved documentation addresses, not live attacks or independent human ground truth. All failures remain present. Raw fixtures, original source locators, host/process samples and live client receipts stay private.

v4 contains two development cases per model. v5 contains the one additional common mixed-priority request after the shared typed-value grammar revision, then the three pre-frozen new cases per model. selected-contract.json records selection before new-case answers. The expected files are review labels, never model input. Native templates/quantization/defaults differ and the old common prompt originated during baseline development.

To replay the final contract, use the current tools/evaluate_analyst_models.py with --fixtures pointing to v5/unseen, the separately owned loopback runtime and a fresh output directory. Stop periodic inference first and wait for normal unload. The harness does not download models or overwrite old results. Replaying these published cases is regression work, not another unseen estimate. For an exact older contract replay, place that version's soc_analyst.py beside a copy of the replay harness in a fresh local directory; do not overwrite the production tools.

[Methods and individual timings](../../docs/MODEL_REFINEMENT_RESULTS.md) explain grounding versus missing useful context, capped/timeout behavior and resource limits. All source/model artifacts remain governed by their stated licenses; no weights are bundled.
