from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import uia_permission_submit as uia


class AgentHostWindowTests(unittest.TestCase):
    def test_visual_studio_code_title_is_a_host(self) -> None:
        title = "Antigravity Settings - VideoYoutube - Visual Studio Code"
        self.assertTrue(uia._is_agent_host_window(title))
        self.assertEqual(uia._host_label(title), "VS Code")

    def test_visual_studio_code_insiders_title_is_a_host(self) -> None:
        title = "folder - Visual Studio Code - Insiders"
        self.assertTrue(uia._is_agent_host_window(title))
        self.assertEqual(uia._host_label(title), "VS Code")

    def test_antigravity_ide_title_stays_a_host(self) -> None:
        title = "VideoYoutube - Antigravity IDE - HANDOFF_STATUS.md"
        self.assertTrue(uia._is_agent_host_window(title))
        self.assertEqual(uia._host_label(title), "Antigravity IDE")

    def test_custom_vscode_title_matches_process_image(self) -> None:
        self.assertTrue(uia._is_agent_host_window("My editor", "Code.exe"))
        self.assertEqual(uia._host_label("My editor", "Code.exe"), "VS Code")
        self.assertTrue(uia._is_agent_host_window("My editor", "Code - Insiders.exe"))

    def test_desktop_and_unrelated_windows_are_not_hosts(self) -> None:
        self.assertFalse(uia._is_agent_host_window("Antigravity"))
        self.assertFalse(uia._is_agent_host_window("Antigravity", "Antigravity.exe"))
        self.assertFalse(uia._is_agent_host_window("Select Antigravity Auto-Submit", "cmd.exe"))

    def test_permission_submit_still_requires_the_dialog_button(self) -> None:
        self.assertTrue(uia._is_permission_submit("Submit ↵"))
        self.assertTrue(uia._is_permission_submit("Submit"))
        self.assertFalse(uia._is_permission_submit("Change permissions"))
        self.assertTrue(uia._is_allow_prompt("Allow listing specs directory?"))
        self.assertTrue(uia._is_skip("Skip"))


if __name__ == "__main__":
    unittest.main()
