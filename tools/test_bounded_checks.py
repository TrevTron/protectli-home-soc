"""Check thermal refusal and child cleanup without launching load or hardware calls."""
import unittest
from unittest.mock import Mock, patch

import vault_bounded_checks as checks


class ThermalSafetyTests(unittest.TestCase):
    def test_hot_preflight_never_starts_load(self):
        reading = {'cpu_c': [79, 80, 79, 79]}
        with patch.object(checks, 'sample', return_value=reading), \
             patch.object(checks, 'emit') as emit, \
             patch.object(checks.subprocess, 'Popen') as launch:
            checks.stress(30)
        launch.assert_not_called()
        self.assertIn({'type': 'thermal_stop', 'phase': 'before_load'},
                      [call.args[0] for call in emit.call_args_list])

    def test_sensor_failure_stops_only_owned_children(self):
        jobs = [Mock() for _ in range(4)]
        for job in jobs:
            job.poll.return_value = None
        readings = [{'cpu_c': [50] * 4}, RuntimeError('sensor unavailable'),
                    {'cpu_c': [50] * 4}]
        with patch.object(checks, 'sample', side_effect=readings), \
             patch.object(checks, 'emit'), \
             patch.object(checks.subprocess, 'Popen', side_effect=jobs):
            with self.assertRaisesRegex(RuntimeError, 'sensor unavailable'):
                checks.stress(30)
        for job in jobs:
            job.terminate.assert_called_once()
            job.wait.assert_called_once_with(timeout=3)

    def test_invalid_sensor_value_fails_closed(self):
        for value in ('nanC', 'infC', '0C', '151C'):
            with self.subTest(value=value), \
                 patch.object(checks.subprocess, 'check_output', return_value=value):
                with self.assertRaisesRegex(RuntimeError, 'Invalid CPU temperature'):
                    checks.sample()


if __name__ == '__main__':
    unittest.main()
