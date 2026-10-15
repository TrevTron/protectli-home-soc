# Coverage and receipt decision procedure

Read these fields independently before selecting codes.

1. `udp_delivery_complete: false` means delivery is unproved. Select `coverage_limits`. It does not mean the retained prior window is missing.
2. If `prior_window_available: true` and `retained_window_complete: true`, omit `comparison_incomplete`, `inspect_coverage` and `compare_retained_window` in this bounded context-selection task. If either is false, select `comparison_incomplete` and propose `inspect_coverage`.
3. Nonempty groups require both `sensor_action_not_client_result` and `rule_match_not_intrusion_proof`. Include them alongside coverage, rather than substituting one warning for another.
4. Empty groups still require `coverage_limits`; they do not require sensor/rule context.
5. A matched client result requires `client_receipt_scoped_to_attempt`. Once that result is supplied, choose `inspect_rule` or `correlate_process_receipt`; do not ask for the same client result again.
6. A matched process/socket receipt requires `process_receipt_not_client_result`. Choose `correlate_client_receipt` or `inspect_rule` because process ownership cannot establish client success.
7. An unmatched receipt establishes no result for these groups. Choose a matching client receipt, a contemporaneous process receipt or the exact rule.
8. Use `untrusted_log_text` only when an annotation actually tries to instruct the analyst. A plain statement that a fixture is synthetic does not do that.
9. With nonempty evidence, no client/process result and complete retained/prior coverage, choose one to three of `correlate_client_receipt`, `correlate_process_receipt`, `inspect_rule`.
10. Do not use `none` for these cases because the relevant rule or outcome remains unresolved.

Worked example: 8 supplied records, available prior window, complete retained window, unproved UDP delivery, no matched receipts. Select sensor-action, rule-match and coverage warnings. A matching client result, socket owner or rule inspection can resolve the remaining uncertainty. Do not add the comparison warning.

Worked example: one blocked event and a matched client-success receipt for a different later attempt. Keep the sensor/rule/coverage warnings and scope the client receipt to its supplied attempt. The original block remains visible. A process or rule check can add context; repeating the supplied client result is unnecessary.
