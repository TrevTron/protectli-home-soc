"""Resume the interrupted pinned inbound download, preserving its original prefix."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import urllib.request
from workbench import HERE, sha, canonical


def main():
    root = HERE / 'ling-isolated'
    model = json.loads((HERE / 'ling-official-candidate.json').read_text(encoding='utf-8-sig'))
    weight = next(s for s in model['siblings'] if s['rfilename'] == 'Ling-3.0-tiny-Q4_K_M.gguf')
    path = root / weight['rfilename']
    original_bytes = path.stat().st_size
    if not 0 < original_bytes < weight['size']:
        raise ValueError('Expected an incomplete pinned file')
    with path.open('rb') as stream:
        prefix_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    receipt = {'utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'reason': 'Initial HTTPS read timed out',
               'original_prefix_bytes': original_bytes, 'original_prefix_sha256': prefix_sha,
               'existing_bytes_preserved_by_append': True, 'model_inference_requests': 0}
    with (root / 'download-attempt-01.json').open('x') as stream:
        stream.write(canonical(receipt) + '\n')
    url = f"https://huggingface.co/{model['id']}/resolve/{model['sha']}/{weight['rfilename']}"
    request = urllib.request.Request(url, headers={'Range': f'bytes={original_bytes}-', 'User-Agent': 'Protectli-local-research/1.0'})
    start, last, total = time.monotonic(), time.monotonic(), original_bytes
    with urllib.request.urlopen(request, timeout=60) as response:
        expected = f"bytes {original_bytes}-{weight['size']-1}/{weight['size']}"
        if response.status != 206 or response.headers.get('Content-Range') != expected:
            raise ValueError('Server did not honor the pinned exact byte range; append refused')
        with path.open('ab') as stream:
            while chunk := response.read(4 * 1024 * 1024):
                total += len(chunk)
                if total > weight['size'] or time.monotonic() - start > 900:
                    raise ValueError('Pinned download size/time bound')
                stream.write(chunk)
                if time.monotonic() - last > 5:
                    print(canonical({'resumed_bytes': total, 'expected_bytes': weight['size']}), flush=True)
                    last = time.monotonic()
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if total != weight['size'] or actual != weight['lfs']['sha256']:
        raise ValueError('Full artifact identity differs')
    with path.open('rb') as stream:
        remaining, prefix = original_bytes, hashlib.sha256()
        while remaining:
            chunk = stream.read(min(4 * 1024 * 1024, remaining))
            if not chunk:
                raise ValueError('Original prefix missing')
            prefix.update(chunk)
            remaining -= len(chunk)
    if prefix.hexdigest() != prefix_sha:
        raise ValueError('Original prefix altered')
    release = json.loads((HERE / 'llama-nightly-candidate.json').read_text(encoding='utf-8-sig'))
    binary = next(a for a in release['assets'] if a['name'] == 'llama-b11429-bin-win-cpu-x64.zip')
    zip_path = root / binary['name']
    if sha(zip_path.read_bytes()) != binary['digest'].removeprefix('sha256:'):
        raise ValueError('Official runtime archive changed')
    artifacts = [{'file': path.name, 'bytes': total, 'sha256': actual, 'verified': True, 'url': url},
                 {'file': zip_path.name, 'bytes': zip_path.stat().st_size, 'sha256': sha(zip_path.read_bytes()), 'verified': True, 'url': binary['browser_download_url']}]
    files = {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in (root / 'runtime').rglob('*') if p.is_file()}
    with (root / 'download-verified.json').open('x') as stream:
        stream.write(canonical({'artifacts': artifacts, 'runtime_files': files, 'initial_prefix_preserved': True}) + '\n')
    print(canonical({'verified': True, 'bytes': total, 'original_prefix_preserved': True}), flush=True)


if __name__ == '__main__':
    main()
