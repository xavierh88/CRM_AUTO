"""Offline upload protections: inspect fictional path strings, never documents.

Run directly with Python's standard library; no server, pytest plugins, database,
environment files, or provider dependencies are loaded.
"""

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]


class UploadIgnoreTests(unittest.TestCase):
    def assert_ignored(self, path, expected=True):
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", "--", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn(result.returncode, (0, 1), result.stderr)
        self.assertEqual(result.returncode, 0 if expected else 1, path)

    def test_upload_directory_entries_are_ignored(self):
        for path in ("backend/uploads", "uploads"):
            with self.subTest(path=path):
                self.assert_ignored(path)

    def test_upload_contents_are_ignored_at_every_depth(self):
        for root in ("backend/uploads", "uploads"):
            for suffix in (
                "fictional.pdf",
                "fictional-client/identity.png",
                "temp/fictional-client/page.txt",
                ".fictional-hidden",
                "fictional document.PDF",
                "fictional-without-extension",
            ):
                path = f"{root}/{suffix}"
                with self.subTest(path=path):
                    self.assert_ignored(path)

    def test_similarly_named_source_files_are_not_ignored(self):
        for path in (
            "backend/uploads.py",
            "backend/uploads_validation.py",
            "tests/offline/test_upload_ignore.py",
            "frontend/src/components/Uploads.jsx",
        ):
            with self.subTest(path=path):
                self.assert_ignored(path, expected=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
