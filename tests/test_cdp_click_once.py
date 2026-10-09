from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import antigravity_auto_submit_daemon as daemon


class CdpClickScriptTests(unittest.TestCase):
    def test_template_placeholders_are_resolved(self) -> None:
        self.assertNotIn("__HELPERS__", daemon.JS_PAYLOAD_TEMPLATE)
        self.assertNotIn("__HELPERS__", daemon.JS_CLICK_ONCE)
        # The check interval is substituted per page at inject time.
        self.assertIn("__CHECK_INTERVAL_MS__", daemon.JS_PAYLOAD_TEMPLATE)

    def test_click_once_reports_outcome(self) -> None:
        self.assertIn("clicked:submit", daemon.JS_CLICK_ONCE)
        self.assertIn("clicked:allow", daemon.JS_CLICK_ONCE)
        self.assertIn("submit ↵", daemon.JS_CLICK_ONCE)

    def test_click_log_cooldown_is_positive(self) -> None:
        self.assertGreater(daemon._CDP_CLICK_LOG_COOLDOWN_SEC, 0)


if __name__ == "__main__":
    unittest.main()
