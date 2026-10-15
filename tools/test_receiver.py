"""Bounded local tests. These do not claim receipt from the Vault."""
import json
import argparse
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import urllib.request

from soc_receiver import Store, event_from_datagram, run


def unused_port(kind):
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ReceiverTests(unittest.TestCase):
    def test_invalid_bind_refused_before_storage_or_socket(self):
        for address in ('', '0', '0x0', '0.0.0.0', 'localhost', '::', '224.0.0.1', '255.255.255.255'):
            with self.subTest(address=address):
                args = argparse.Namespace(bind=address, output='unused.jsonl', max_mib=64, segment_mib=32, port=5514)
                with mock.patch('soc_receiver.Store') as store, mock.patch('soc_receiver.socket.socket') as socket_factory:
                    with self.assertRaisesRegex(ValueError, 'specific owned unicast IPv4'):
                        run(args)
                    store.assert_not_called()
                    socket_factory.assert_not_called()

    def test_cli_rejects_non_literal_and_wildcard_bind_without_evidence_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / 'must-not-exist.jsonl'
            for address in ('', '0', '0x0', '0.0.0.0', 'localhost', '::'):
                with self.subTest(address=address):
                    result = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name('soc_receiver.py')),
                                             '--bind', address, '--allow-source', '192.0.2.1', '--output', str(output)],
                                            capture_output=True, text=True, timeout=5)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn('invalid receiver_bind_address value', result.stderr)
                    self.assertFalse(output.exists())

    def test_capacity_forecast_waits_for_samples_and_warns_before_full(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(pathlib.Path(directory)/'forecast.jsonl',10000)
            with mock.patch('soc_receiver.time.monotonic',return_value=0):
                first=store.snapshot()
            self.assertIsNone(first['estimated_hours_remaining'])
            store.add({'raw':'x'*200})
            with mock.patch('soc_receiver.time.monotonic',return_value=60):
                later=store.snapshot()
            self.assertFalse(later['retention_full'])
            self.assertTrue(later['capacity_warning'])
            self.assertGreater(later['growth_bytes_per_second'],0)
            self.assertLess(later['estimated_hours_remaining'],24)

    def test_capacity_watermark_without_growth_history(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(pathlib.Path(directory)/'watermark.jsonl',1000)
            store.add({'raw':'x'*850})
            value=store.snapshot()
            self.assertTrue(value['capacity_warning'])
            self.assertFalse(value['retention_full'])

    def test_structured_alert_survives_a_general_log_flood_and_restart(self):
        eve = {"event_type": "alert", "timestamp": "2026-10-05T12:00:00-0700",
               "src_ip": "203.0.113.1", "dest_ip": "192.0.2.2", "dest_port": 57570,
               "alert": {"signature_id": 2100498, "action": "allowed", "signature": "<script>untrusted</script>"}}
        raw = '<174>1 2026-10-05T12:00:00-07:00 vault suricata 10 - [meta sequenceId="1"] ' + json.dumps(eve)
        item = event_from_datagram(raw.encode(), "127.0.0.1")
        self.assertEqual(item["raw"], raw)
        self.assertEqual(item["eve"]["alert"]["signature_id"], 2100498)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "logs.jsonl"
            store = Store(path, 2_000_000)
            store.add(item)
            for index in range(501):
                store.add({"app": "configd.py", "raw": f"normal system event {index}"})
            self.assertFalse(any("eve" in event for event in store.snapshot()["events"]))
            self.assertEqual(store.snapshot()["security_events"][0]["eve"]["dest_port"], 57570)
            self.assertEqual(Store(path, 2_000_000).snapshot()["security_events"][0]["raw"], raw)

    def test_malformed_eve_remains_raw_evidence(self):
        raw = b'<174>1 2026-10-05T12:00:00-07:00 vault suricata 10 - - {broken JSON}'
        item = event_from_datagram(raw, "127.0.0.1")
        self.assertEqual(item["raw"], raw.decode())
        self.assertNotIn("eve", item)

    def test_preserves_rfc5424_time_and_untrusted_message(self):
        raw = b'<134>1 2026-10-05T11:00:00-07:00 vault suricata 10 - - <script>alert(1)</script>'
        item = event_from_datagram(raw, "127.0.0.1")
        self.assertEqual(item["source_timestamp"], "2026-10-05T11:00:00-07:00")
        self.assertEqual(item["app"], "suricata")
        self.assertEqual(item["severity"], "info")
        self.assertEqual(item["raw"], raw.decode())

    def test_storage_bound_preserves_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "logs.jsonl"
            store = Store(path, 500)
            store.add({"raw": "first evidence"})
            original = path.read_bytes()
            store.add({"raw": "x" * 501})
            self.assertTrue(store.snapshot()["retention_full"])
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(Store(path, 500).snapshot()["events"][0]["raw"], "first evidence")

    def test_udp_to_http_rejects_other_source_and_restores_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "logs.jsonl"
            udp_port, http_port = unused_port(socket.SOCK_DGRAM), unused_port(socket.SOCK_STREAM)
            command = [sys.executable, str(pathlib.Path(__file__).with_name("soc_receiver.py")),
                       "--bind", "127.0.0.1", "--allow-source", "127.0.0.1", "--port", str(udp_port),
                       "--dashboard-port", str(http_port), "--output", str(path)]
            url = f"http://127.0.0.1:{http_port}/api/events"

            def read_when(predicate):
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    try:
                        with urllib.request.urlopen(url, timeout=0.5) as response:
                            result = json.load(response)
                        if predicate(result):
                            return result
                    except OSError:
                        pass
                    time.sleep(0.05)
                self.fail("Receiver did not reach expected state within 5 seconds")

            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                read_when(lambda result: result["accepted_this_run"] == 0)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                    sender.bind(("127.0.0.2", 0))
                    sender.sendto(b"unapproved source", ("127.0.0.1", udp_port))
                read_when(lambda result: result["rejected_sources"] == 1)
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                    sender.sendto(b"<134>1 2026-10-05T11:00:00-07:00 vault syslog 1 - - bounded-test-123", ("127.0.0.1", udp_port))
                result = read_when(lambda result: result["accepted_this_run"] == 1)
                self.assertIn("bounded-test-123", result["events"][0]["raw"])
                self.assertNotIn("unapproved", path.read_text())
                request = urllib.request.Request(url, headers={"Host": "untrusted.example"})
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    urllib.request.urlopen(request, timeout=1)
                self.assertEqual(denied.exception.code, 403)
                request = urllib.request.Request(url, headers={"Sec-Fetch-Site": "cross-site"})
                with self.assertRaises(urllib.error.HTTPError) as denied:
                    urllib.request.urlopen(request, timeout=1)
                self.assertEqual(denied.exception.code, 403)
                request = urllib.request.Request(f"http://127.0.0.1:{http_port}/", headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate"})
                with urllib.request.urlopen(request, timeout=1) as response:
                    self.assertEqual(response.status, 200)
            finally:
                process.terminate()
                process.communicate(timeout=5)
            process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                result = read_when(lambda result: bool(result["events"]))
                self.assertEqual(result["accepted_this_run"], 0)
                self.assertIn("bounded-test-123", result["events"][0]["raw"])
                with urllib.request.urlopen(f"http://127.0.0.1:{http_port}/", timeout=1) as response:
                    self.assertIn("td.textContent=text", response.read().decode())
            finally:
                process.terminate()
                process.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
