"""Bind the completed private workbench without copying secrets or model binaries."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
DOC = PROJECT / "docs/ai-followup-20261007/NEXT_STEP_WORKBENCH_RESULTS_V1.md"


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    target = HERE / "FINAL_SEAL.json"
    if target.exists():
        raise RuntimeError("The completed seal already exists; do not overwrite it")
    ledger = json.loads((HERE / "VERIFIED_LEDGER.json").read_text(encoding="utf-8"))
    summary = ledger["summary"]
    assert summary["operator_demonstrations"] == summary["operator_delivered"] == 15
    assert summary["requests_retained"] == 57
    assert summary["original_evidence_hashes_unchanged"] == 563
    assert summary["prior_sealed_files_unchanged"] == 28
    assert summary["sealed_case_files_unchanged"] == 216
    checks = json.loads((HERE / "browser-model-checks.json").read_text(encoding="utf-8"))
    assert len(checks["checks"]) == 5
    assert all(c["status"] == "The model selected a permitted next check. Context and citations are supplied by code."
               for c in checks["checks"])
    files = [DOC]
    excluded = []
    for path in sorted(HERE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(HERE)
        if ("runtime" in rel.parts or "__pycache__" in rel.parts
                or path.name == "api-key.txt"
                or path.suffix.lower() in {".gguf", ".zip", ".part"}
                or path.stat().st_size > 16 * 1024 * 1024):
            excluded.append(str(rel).replace("\\", "/"))
        else:
            files.append(path)
    manifest = [{"path": str(path.relative_to(PROJECT)).replace("\\", "/"),
                 "bytes": path.stat().st_size, "sha256": digest(path)} for path in files]
    seal = {"sealed_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Private workbench code, documentation, retained requests, outcomes and verification receipts",
            "large_artifacts": "Model and runtime bytes are bound by download-verified.json and pins.json; private API-key files are excluded",
            "excluded_files_relative_to_workbench": excluded,
            "summary": summary, "files": manifest}
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(seal, stream, indent=2)
        stream.write("\n")
    saved = json.loads(target.read_text(encoding="utf-8"))
    for item in saved["files"]:
        path = PROJECT / item["path"]
        assert path.stat().st_size == item["bytes"] and digest(path) == item["sha256"], item["path"]
    print(json.dumps({"seal": str(target), "files_verified": len(manifest),
                      "operator_demonstrations": 15, "browser_model_choices": 5}))


if __name__ == "__main__":
    main()
