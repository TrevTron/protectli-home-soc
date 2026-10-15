"""Verify the per-request isolated-runtime trace, including prompt truncation.

This depends on the recorded Ollama runtime's stderr format. Unknown, incomplete,
rotated or ambiguous traces are refused, never silently considered full context.
"""
from pathlib import Path
import re
import hashlib

MAX_TRACE=4*1024*1024


def start(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('Runtime trace must be an existing regular file')
    return path.stat().st_size


def capture(path,offset):
    path=Path(path)
    if path.is_symlink():raise ValueError('Runtime trace link refused')
    length=path.stat().st_size-offset
    if length<0 or length>MAX_TRACE:raise ValueError('Runtime trace rotated or exceeds bound')
    with path.open('rb') as stream:
        stream.seek(offset);raw=stream.read(length)
    if len(raw)!=length:raise ValueError('Runtime trace changed during capture')
    return raw


def assess(raw,*,context,prompt_tokens):
    text=raw.decode('utf-8',errors='replace')
    result={'trace_sha256':hashlib.sha256(raw).hexdigest(),'trace_bytes':len(raw),
            'requested_context':context,'returned_prompt_tokens':prompt_tokens,
            'input_truncated':'truncating input prompt' in text}
    prompts=[int(v) for v in re.findall(r'task\.n_tokens\s*=\s*(\d+)',text)]
    contexts=[int(v) for v in re.findall(r'new prompt, n_ctx_slot\s*=\s*(\d+)',text)]
    result.update(logged_prompt_tokens=prompts,logged_contexts=contexts)
    # A newly loaded runner may issue an empty warmup before the actual request.
    # Preserve it, but require exactly one positive prefill and matching contexts.
    positive=[v for v in prompts if v>0]
    result['verified_full_context']=(not result['input_truncated'] and type(prompt_tokens) is int
        and positive==[prompt_tokens] and len(contexts)==len(prompts) and all(v==context for v in contexts))
    result['boundary']='One isolated sequential request; retained append slice and runtime-specific trace format. No general tokenizer estimate.'
    return result
