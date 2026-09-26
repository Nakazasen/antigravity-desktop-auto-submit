from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import antigravity_auto_submit_daemon as daemon


class ConsoleQuickEditTests(unittest.TestCase):
    def test_safe_mode_clears_quick_edit_and_mouse_but_keeps_other_flags(self) -> None:
        mode = 0x01F7  # QuickEdit + mouse input + extended + other bits on.
        safe = daemon._quick_edit_safe_mode(mode)
        self.assertEqual(safe & daemon._ENABLE_QUICK_EDIT_MODE, 0)
        self.assertEqual(safe & daemon._ENABLE_MOUSE_INPUT, 0)
        self.assertNotEqual(safe & daemon._ENABLE_EXTENDED_FLAGS, 0)
        # Unrelated bits must survive.
        self.assertEqual(safe & 0x0007, mode & 0x0007)

    def test_safe_mode_is_idempotent(self) -> None:
        once = daemon._quick_edit_safe_mode(0x01F7)
        self.assertEqual(daemon._quick_edit_safe_mode(once), once)

    def test_disable_is_noop_off_windows(self) -> None:
        with mock.patch.object(os, "name", "posix"):
            self.assertFalse(daemon._disable_console_quick_edit())


if __name__ == "__main__":
    unittest.main()
