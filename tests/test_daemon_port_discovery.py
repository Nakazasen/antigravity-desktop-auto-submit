from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import antigravity_auto_submit_daemon as daemon


class DynamicPortDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        daemon._DISCOVERED_DEBUG_PORTS.clear()
        daemon._LAST_PROCESS_PORT_SCAN_MONO = 0.0

    def test_process_ports_are_parsed_for_antigravity_only(self) -> None:
        tasklist = (
            '"Antigravity.exe","1036","Console","1","100,000 K"\n'
            '"Antigravity IDE.exe","18960","Console","1","200,000 K"\n'
        )
        netstat = "\n".join(
            [
                "TCP 127.0.0.1:56307 0.0.0.0:0 LISTENING 1036",
                "TCP 127.0.0.1:56314 127.0.0.1:60000 ESTABLISHED 1036",
                "TCP 127.0.0.1:9222 0.0.0.0:0 LISTENING 18960",
            ]
        )

        with patch.object(daemon, "_run_hidden", side_effect=[tasklist, netstat]):
            self.assertEqual(daemon._ports_from_antigravity_processes(), [56307, 56314])

    def test_stale_port_file_falls_back_to_live_process_port(self) -> None:
        listening = {56307, 56314}

        with (
            patch.object(daemon, "_ports_from_files", return_value=[]),
            patch.object(
                daemon,
                "_ports_from_antigravity_processes",
                return_value=[56307, 56314],
            ) as discover,
            patch.object(
                daemon,
                "is_port_listening",
                side_effect=lambda port: port in listening,
            ),
            patch.object(
                daemon,
                "_port_speaks_cdp",
                side_effect=lambda port: port == 56307,
            ),
            patch.object(daemon.time, "monotonic", return_value=100.0),
        ):
            self.assertEqual(daemon.get_active_ports(), ["56307"])
            self.assertEqual(daemon._DISCOVERED_DEBUG_PORTS, {56307})
            discover.assert_called_once_with()

    def test_cached_live_port_avoids_repeated_process_scan(self) -> None:
        daemon._DISCOVERED_DEBUG_PORTS.add(56307)
        daemon._LAST_PROCESS_PORT_SCAN_MONO = 100.0

        with (
            patch.object(daemon, "_ports_from_files", return_value=[]),
            patch.object(daemon, "_ports_from_antigravity_processes") as discover,
            patch.object(
                daemon,
                "is_port_listening",
                side_effect=lambda port: port == 56307,
            ),
            patch.object(
                daemon,
                "_port_speaks_cdp",
                side_effect=lambda port: port == 56307,
            ),
            patch.object(daemon.time, "monotonic", return_value=105.0),
        ):
            self.assertEqual(daemon.get_active_ports(), ["56307"])
            discover.assert_not_called()


if __name__ == "__main__":
    unittest.main()
