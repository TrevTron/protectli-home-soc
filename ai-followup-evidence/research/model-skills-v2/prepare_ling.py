"""Fetch pinned official inbound artifacts into this isolated workbench only."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import zipfile
from workbench import HERE, sha, canonical

ROOT = HERE / 'ling-isolated'


def download(url, path, expected_size, expected_sha):
    if path.exists():
        raise ValueError('Preserve existing download; no replacement')
    total, last, digest = 0, time.monotonic(), hashlib.sha256()
    request = urllib.request.Request(url, headers={'User-Agent': 'Protectli-local-research/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response, path.open('xb') as stream:
        while chunk := response.read(4 * 1024 * 1024):
            total += len(chunk)
            if total > expected_size:
                raise ValueError('Download exceeds pinned size')
            digest.update(chunk)
            stream.write(chunk)
            if time.monotonic() - last >= 5:
                print(canonical({'artifact': path.name, 'received_bytes': total, 'expected_bytes': expected_size}), flush=True)
                last = time.monotonic()
    if total != expected_size or digest.hexdigest() != expected_sha:
        raise ValueError('Pinned size or SHA256 differs')
    return {'file': path.name, 'bytes': total, 'sha256': digest.hexdigest(), 'verified': True, 'url': url}


def main():
    ROOT.mkdir(exist_ok=False)
    release = json.loads((HERE / 'llama-nightly-candidate.json').read_text(encoding='utf-8-sig'))
    model = json.loads((HERE / 'ling-official-candidate.json').read_text(encoding='utf-8-sig'))
    binary = next(a for a in release['assets'] if a['name'] == 'llama-b11429-bin-win-cpu-x64.zip')
    weight = next(s for s in model['siblings'] if s['rfilename'] == 'Ling-3.0-tiny-Q4_K_M.gguf')
    pin = {'runtime_release': release, 'model': model, 'purpose': 'Isolated Ling 3.0 tiny CPU compatibility and development. No old mini, no default or SOC model-store modification.'}
    (ROOT / 'pins.json').write_text(canonical(pin) + '\n')
    receipt = []
    receipt.append(download(binary['browser_download_url'], ROOT / binary['name'], binary['size'], binary['digest'].removeprefix('sha256:')))
    output = ROOT / 'runtime'
    output.mkdir()
    with zipfile.ZipFile(ROOT / binary['name']) as archive:
        for item in archive.infolist():
            destination = (output / item.filename).resolve()
            if not destination.is_relative_to(output.resolve()) or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Archive path/link refused')
        archive.extractall(output)
    url = f"https://huggingface.co/{model['id']}/resolve/{model['sha']}/{weight['rfilename']}"
    receipt.append(download(url, ROOT / weight['rfilename'], weight['lfs']['size'], weight['lfs']['sha256']))
    files = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in output.rglob('*') if p.is_file()}
    (ROOT / 'download-verified.json').write_text(canonical({'artifacts': receipt, 'runtime_files': files}) + '\n')
    print(canonical({'verified': True, 'artifact_count': len(receipt), 'runtime_files': len(files)}), flush=True)


if __name__ == '__main__':
    main()
