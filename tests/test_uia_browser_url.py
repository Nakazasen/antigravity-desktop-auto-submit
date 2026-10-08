from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import uia_permission_submit as uia


def _fake_browser(values: list) -> tuple:
    """Fake (auto, scan_root) whose address-bar edits expose `values`.

    None means the edit has no Value pattern.
    """
    auto = mock.MagicMock()
    edits = mock.MagicMock()
    edits.Length = len(values)
    elements = []
    for value in values:
        element = mock.MagicMock()
        if value is None:
            element.GetCurrentPattern.return_value = None
        else:
            pattern = mock.MagicMock()
            holder = mock.MagicMock()
            holder.CurrentValue = value
            pattern.QueryInterface.return_value = holder
            element.GetCurrentPattern.return_value = pattern
        elements.append(element)
    edits.GetElement.side_effect = lambda index: elements[index]
    auto.CreatePropertyCondition.return_value = mock.MagicMock()
    scan_root = mock.MagicMock()
    scan_root.FindAll.return_value = edits
    return auto, scan_root


class BrowserLocalUrlTests(unittest.TestCase):
    def test_local_antigravity_conv_url_is_accepted(self) -> None:
        auto, scan = _fake_browser(
            ["https://127.0.0.1:54975/c/85e3d0b2-0b1d-4627-a9f1-66b60d533f2e"]
        )
        self.assertEqual(
            uia._browser_local_url(auto, scan),
            "https://127.0.0.1:54975/c/85e3d0b2-0b1d-4627-a9f1-66b60d533f2e",
        )

    def test_open_web_is_never_a_host(self) -> None:
        for url in (
            "https://example.com/submit",
            "https://mail.google.com/",
            "http://localhost:3000/my-app",
        ):
            auto, scan = _fake_browser([url])
            self.assertEqual(uia._browser_local_url(auto, scan), "")

    def test_missing_value_pattern_is_rejected(self) -> None:
        auto, scan = _fake_browser([None])
        self.assertEqual(uia._browser_local_url(auto, scan), "")

    def test_chrome_window_still_needs_url_proof(self) -> None:
        title = "Google Drive Folder Analysis - VideoYoutube - Antigravity - Google Chrome"
        self.assertFalse(uia._is_agent_host_window(title))
        self.assertFalse(uia._is_agent_host_window(title, "chrome.exe"))
        self.assertEqual(uia._host_label(title, "chrome.exe"), "Chrome")
        self.assertEqual(uia._host_label(title, "msedge.exe"), "Edge")


if __name__ == "__main__":
    unittest.main()
