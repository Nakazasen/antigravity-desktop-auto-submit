from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from comtypes.client import GetModule

GetModule("UIAutomationCore.dll")

import uia_permission_submit as uia


def _element_with_invoke(*, pattern=True, raises=False):
    element = mock.MagicMock()
    if raises:
        element.GetCurrentPattern.side_effect = Exception("no UIA")
    else:
        element.GetCurrentPattern.return_value = (
            mock.MagicMock() if pattern else None
        )
    return element


class InvokePrefersNoMouseTests(unittest.TestCase):
    def test_successful_invoke_skips_physical_click(self) -> None:
        with mock.patch.object(uia, "_click_bounding_rect") as click:
            self.assertTrue(uia._invoke(_element_with_invoke(pattern=True)))
            click.assert_not_called()

    def test_missing_pattern_falls_back_to_physical_click(self) -> None:
        with mock.patch.object(
            uia, "_click_bounding_rect", return_value=True
        ) as click:
            self.assertTrue(uia._invoke(_element_with_invoke(pattern=False)))
            click.assert_called_once()

    def test_failed_invoke_and_failed_click_returns_false(self) -> None:
        with mock.patch.object(
            uia, "_click_bounding_rect", return_value=False
        ):
            self.assertFalse(uia._invoke(_element_with_invoke(raises=True)))


if __name__ == "__main__":
    unittest.main()
