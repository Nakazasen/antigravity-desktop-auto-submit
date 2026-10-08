from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import antigravity_auto_submit_daemon as daemon


class FileLogTests(unittest.TestCase):
    def test_tee_writes_to_both_console_and_file(self) -> None:
        import tempfile

        console = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "daemon.log")
            tee = daemon._TeeStream(console, path)
            try:
                tee.write("hello\n")
                tee.flush()
                self.assertEqual(console.getvalue(), "hello\n")
                self.assertEqual(Path(path).read_text(encoding="utf-8"), "hello\n")
            finally:
                tee.close()

    def test_tee_survives_dead_console(self) -> None:
        import tempfile

        class Dead:
            def write(self, data):
                raise OSError("gone")

            def flush(self):
                raise OSError("gone")

        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "daemon.log")
            tee = daemon._TeeStream(Dead(), path)
            try:
                self.assertEqual(tee.write("x"), 1)
                tee.flush()
                self.assertEqual(Path(path).read_text(encoding="utf-8"), "x")
            finally:
                tee.close()

    def test_enable_file_log_rejects_empty_path(self) -> None:
        self.assertFalse(daemon._enable_file_log(""))


if __name__ == "__main__":
    unittest.main()
