# Check saved model-study results

Current release note, October 7: Trevor dropped the fixed 48-hour clause. [Observed operation and recovery](OPERATING_REVIEW_2026-10-07.md) retains interruptions and failures. Current storage uses activated rolling-v2; [Quickstart](QUICKSTART.md) is the operating path. Earlier dated budgets, test counts and pending labels below are historical.

Historical capacity checkpoint, October 6 (before rolling-v2): 1 GiB raw budget, 4 GiB private archives, streaming archive verification and early capacity warnings are deployed and verified. All 89 software checks pass. The 48-hour window remains collecting, with no elapsed-time acceptance. The 416 model outcomes and original evidence remain unchanged. No external release has occurred. Earlier dated checkpoint results below remain historical.

`tools/verify_model_study.py` checks saved evidence without calling an inference endpoint. It supports the expanded comparison, simulation-source holdout and common-settings pass. All 200/168/48 studies are complete. Their public subset folders are in model-evidence, and the selected Qwen3.5 4B/common profile is documented in [the expanded results](MODEL_COMPARISON_EXPANDED_RESULTS.md).

From the repository root, replace `study-directory` with a saved study folder:

```powershell
python tools/verify_model_study.py --study study-directory
```

Require every scheduled request to have a terminal outcome:

```powershell
python tools/verify_model_study.py --study study-directory --require-complete
```

Write a new verification receipt:

```powershell
python tools/verify_model_study.py --study study-directory --output new-audit.json
```

The output file must not already exist. An in-progress study reports `partial_receipts_verified`; it cannot pass the complete gate. A timeout is a terminal withheld outcome, so a completed study can contain failures.

The verifier checks the frozen file hashes and schedule, derives each model input and schema from its saved brief, and reconstructs returned request hashes from the prompt and explicit options. It checks the response model name, content/thinking lengths, actual generated and prompt token counts, stop reason, and accepted structured report. The exact frozen utility criteria are recalculated separately from grounding. Large frozen evidence assets are hashed in bounded chunks; parsed JSON files retain a smaller size limit. Frozen Python source is inspected for literal prompt assignments when needed and is never executed.

It also reports the number of source cases and distinct model inputs. Thirteen simulation cases currently share one empty model brief. Their packet/engine evidence remains distinct, but repeating that brief does not create thirteen independent reasoning tasks.

These checks establish consistency within the supplied evidence package. They do not authenticate its author or prove an inference true. A written answer still needs the recorded semantic review against its supplied facts, references, eligible contexts and uncertainty. A well-formed structured answer can omit useful context, and a signature match cannot establish intent or the client's outcome.

Eight offline tests cover modified facts even after response hashes are recomputed, altered model/options, fabricated utility scores, a capped response marked delivered, incomplete completion and path escapes. They also exercise literal prompt extraction while the frozen source contains code that would fail if executed. The new written-answer regression accepts exact LF storage or Python's exact whole-file Windows LF-to-CRLF translation, rejects changed wording and mixed line endings, and checks a separate SHA256 for the physical saved file. API response-content hashes remain unchanged. The final local candidate passes all 89 software tests, with 41 top-level tool files matching the working sources and 17 PowerShell scripts parsing cleanly.

The reviewed public subset, local repository manifest and ZIP have been prepared and checked. Private originals are retained. The selected operating model/profile passed fresh source-bound live validation. No GitHub repository, push or publication has occurred.

## Preserve evidence bytes through Git

The draft now includes `.gitattributes` with `* -text`, disabling automatic line-ending conversion so stored file hashes remain reproducible. This follows the [Git attributes documentation](https://git-scm.com/docs/gitattributes). A private two-file probe retained both LF and CRLF fixture bytes through three local checkout settings, including explicit LF mode. Two negative controls without byte-preserving attributes changed fixture hashes. Six positive file hashes matched. These tests used Git2.55.0.windows.3 locally; noLinux host execution is claimed.

Those Git byte-preservation checks used separate private fixture repositories and local clones. No project Git repository was initialized, staged, committed or pushed. The completed local draft contains 1,997 noncache files, including 1,791 model-evidence subset files; the final manifest and ZIP verification receipt are separate review artifacts.


## Read review state separately from the original run

The runner preserves its original outcome fields, including `manual_review: pending`, and its terminal status `requests_complete_manual_review_pending`. Those fields describe what was recorded when inference ended. Later judgments are appended to a separate review journal with the original outcome and response hashes; they do not rewrite the model outputs. Likewise, a frozen protocol can say no requests have executed yet because it was saved before execution.

The offline verifier reports delivered written answers as requiring separate semantic review. It does not read or authenticate that review journal, so that count is not a live count of unanswered reviews. Review completion must be checked against the separate source-hash-linked records. Exact repeated requests and full answers can reuse an individually assessed first-repeat judgment only with explicit parity and source-review provenance. This verifies repeated behavior on the same task; it does not create an independent assessment or another evidence case.

## Verify the included completed studies

Run each command from the repository root. Failures remain terminal outcomes; complete does not mean every model delivered.

```powershell
py -3.12 tools/verify_model_study.py --study model-evidence/evaluation-expanded-v2-20261005 --require-complete
py -3.12 tools/verify_model_study.py --study model-evidence/evaluation-simulation-holdout-20261005 --require-complete
py -3.12 tools/verify_model_study.py --study model-evidence/evaluation-normalized-20261005 --require-complete
```

The derived public manifests contain 54, 88 and 52 frozen files. The private full manifests retain 60, 151 and 52. Omitted private source/capture assets are declared in PUBLIC_SUBSET_PROVENANCE.json rather than silently removed from a full manifest. The 372 returned-request hashes, timeout receipts and capped responses remain available. The separate journals account for written and structured reviews; a verifier semantic-review-required count does not imply they are unreviewed.
