from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.generate_dashboard import RUN_OUTPUT_FILES, _write_run_bundle


class RunBundleTests(unittest.TestCase):
    def test_bundle_contains_each_run_file_but_not_itself(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            output_dir = Path(temporary_dir)
            for filename in RUN_OUTPUT_FILES:
                (output_dir / filename).write_text(filename, encoding="utf-8")

            bundle_path = _write_run_bundle(output_dir)

            with zipfile.ZipFile(bundle_path) as bundle:
                self.assertEqual(set(bundle.namelist()), set(RUN_OUTPUT_FILES))
                self.assertNotIn("run_bundle.zip", bundle.namelist())
                self.assertEqual(bundle.read("dashboard.html"), b"dashboard.html")

    def test_bundle_fails_clearly_if_a_run_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            with self.assertRaisesRegex(FileNotFoundError, "Missing run output"):
                _write_run_bundle(Path(temporary_dir))


if __name__ == "__main__":
    unittest.main()
