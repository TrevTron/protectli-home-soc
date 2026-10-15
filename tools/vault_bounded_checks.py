"""Run on the owned Vault console. LAN endpoint test, then optional bounded CPU load.

No forwarding-throughput claim: this server terminates traffic on the Vault.
Only Python's standard library is used. Never bind this endpoint to WAN.
"""
import argparse
import datetime
import json
import math
import socket
import subprocess
import time


def sample():
    def query(name):
        return subprocess.check_output(['sysctl', '-n', name], text=True, timeout=3).strip()
    temperatures = [float(query(f'dev.cpu.{i}.temperature').removesuffix('C')) for i in range(4)]
    if any(not math.isfinite(value) or value <= 0 or value > 150 for value in temperatures):
        raise RuntimeError('Invalid CPU temperature reading; no load may continue')
    return {
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'cpu_c': temperatures,
        'load': query('vm.loadavg'),
        'physmem': int(query('hw.physmem')),
        'free_pages': int(query('vm.stats.vm.v_free_count')),
    }


def emit(value):
    print(json.dumps(value), flush=True)


def serve(address, client):
    # Four 128 MiB downloads maximum, 90 seconds maximum. Exact client only.
    block = bytes(1024 * 1024)
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((address, 5201))
        listener.listen(1)
        deadline = time.monotonic() + 90
        count = 0
        emit({'type': 'listener', 'address': address, 'port': 5201, 'client': client, 'sample': sample()})
        while count < 4 and time.monotonic() < deadline:
            listener.settimeout(max(0.1, deadline - time.monotonic()))
            try:
                connection, peer = listener.accept()
            except TimeoutError:
                break
            with connection:
                connection.settimeout(10)
                if peer[0] != client:
                    emit({'type': 'rejected_client'})
                    continue
                connection.sendall(b'VAULT-LAN-128M\n')
                count += 1
                start = time.monotonic()
                total = 0
                try:
                    for _ in range(128):
                        if time.monotonic() > deadline:
                            raise TimeoutError('Total server time bound')
                        connection.sendall(block)
                        total += len(block)
                    connection.shutdown(socket.SHUT_WR)
                except (TimeoutError, OSError) as error:
                    emit({'type': 'transfer_error', 'trial': count, 'error': str(error)})
                emit({'type': 'transfer', 'trial': count, 'bytes_sent': total, 'seconds': time.monotonic() - start, 'sample': sample()})
        emit({'type': 'listener_closed', 'connections': count})


def stress(seconds):
    # Kill only the children created here. Retain native kernel thermal controls.
    jobs = []
    try:
        initial = sample()
        emit({'type': 'stress_start', 'seconds_max': seconds, 'temperature_stop_c': 80, 'sample': initial})
        if max(initial['cpu_c']) >= 80:
            emit({'type': 'thermal_stop', 'phase': 'before_load'})
            return
        for _ in range(4):
            jobs.append(subprocess.Popen(['/usr/bin/yes'], stdout=subprocess.DEVNULL))
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            reading = sample()
            emit({'type': 'stress_sample', 'sample': reading})
            if max(reading['cpu_c']) >= 80:
                emit({'type': 'thermal_stop'})
                break
            if any(job.poll() is not None for job in jobs):
                raise RuntimeError('A load process exited unexpectedly')
            time.sleep(5)
    finally:
        for job in jobs:
            if job.poll() is None:
                job.terminate()
        for job in jobs:
            try:
                job.wait(timeout=3)
            except subprocess.TimeoutExpired:
                job.kill()
                job.wait(timeout=3)
        emit({'type': 'stress_stopped', 'sample': sample()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_subparsers(dest='mode', required=True)
    endpoint = mode.add_parser('serve')
    endpoint.add_argument('--address', required=True)
    endpoint.add_argument('--client', required=True)
    load = mode.add_parser('stress')
    load.add_argument('--seconds', type=int, choices=range(30, 301), default=180)
    args = parser.parse_args()
    if args.mode == 'serve':
        serve(args.address, args.client)
    else:
        stress(args.seconds)
