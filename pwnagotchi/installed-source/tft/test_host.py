#!/usr/bin/env python3
"""Check host mode switching without restarting services or transmitting."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, call

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pwnagotchi
from pwnagotchi import grid


class HostIntegration(unittest.TestCase):
    def test_mode_switch_uses_host_service(self):
        for mode, marker, opposite in (
            ('AUTO', 'auto', 'manual'), ('MANU', 'manual', 'auto')
        ):
            with self.subTest(mode=mode), \
                 patch.dict('os.environ', PWNAGOTCHI_HOST_INTEGRATION='1'), \
                 patch('os.path.exists', return_value=True), \
                 patch('os.unlink') as unlink, patch('os.system') as system:
                pwnagotchi.restart(mode)
                unlink.assert_called_once_with('/root/.pwnagotchi-' + opposite)
                self.assertEqual(system.call_args_list, [
                    call('touch /root/.pwnagotchi-' + marker),
                    call('systemctl restart pwnagotchi.service')])

    def test_mesh_enable_and_disable_endpoints(self):
        with patch.object(grid, 'call') as request:
            grid.advertise(True)
            grid.advertise(False)
            self.assertEqual(request.call_args_list,
                             [call('/mesh/true'), call('/mesh/false')])


if __name__ == '__main__':
    unittest.main()
