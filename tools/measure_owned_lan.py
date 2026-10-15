"""Four bounded 128 MiB downloads from an owned LAN endpoint.

Records application payload throughput. This is not an Internet-speed test or
firewall forwarding benchmark. Addresses are required rather than guessed.
"""
import argparse
import datetime
import json
import socket
import time


def measure(address, source):
    for trial in range(1, 5):
        result = {'trial': trial, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source': source, 'endpoint': address, 'scope': 'LAN endpoint download, not forwarding'}
        start = time.monotonic()
        try:
            with socket.socket() as stream:
                stream.settimeout(10)
                stream.bind((source, 0))
                stream.connect((address, 5201))
                result['connect_ms'] = (time.monotonic() - start) * 1000
                result['client_port'] = stream.getsockname()[1]
                header = bytearray()
                while not header.endswith(b'\n') and len(header) < 32:
                    data = stream.recv(1)
                    if not data:
                        raise RuntimeError('Truncated protocol header')
                    header.extend(data)
                if bytes(header) != b'VAULT-LAN-128M\n':
                    raise RuntimeError('Wrong endpoint protocol')
                started = time.monotonic()
                total = 0
                while total <= 128 * 1024 * 1024:
                    if time.monotonic() - started > 15:
                        raise TimeoutError('Bounded transfer time exceeded')
                    data = stream.recv(1024 * 1024)
                    if not data:
                        break
                    total += len(data)
                elapsed = time.monotonic() - started
                result.update(bytes=total, seconds=elapsed, payload_mbps=total * 8 / elapsed / 1_000_000, complete=total == 128 * 1024 * 1024)
        except (OSError, RuntimeError) as error:
            result.update(complete=False, error=str(error))
        print(json.dumps(result), flush=True)
        time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--address', required=True)
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    measure(args.address, args.source)
