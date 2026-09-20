"""Isolated prequalification transfer block; all fixtures are fictional."""

import ast
import logging
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from test_document_attachments import load_module, ROOT


class PrequalifyTransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tests/offline")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "uploads"
        self.root.mkdir()
        self.file = self.root / "fictional.pdf"
        self.file.write_text("fictional identity fixture")

    def transfer(self, reference, fail_copy=False):
        tree = ast.parse((ROOT / "backend/server.py").read_text())
        handler = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                       and node.name == "create_client_from_prequalify")
        block = next(node for node in handler.body if isinstance(node, ast.If)
                     and ast.unparse(node.test) == "prequalify_id_file")
        namespace = {
            "prequalify_id_file": reference, "id_file_url": None, "id_uploaded": False,
            "client_id": "fictional-client", "UPLOAD_DIR": self.root,
            "__file__": str(Path(self.temp.name) / "server.py"),
            "Path": Path, "os": os, "shutil": shutil,
            "logger": logging.getLogger("offline-transfer"),
            "resolve_document_path": load_module("document_paths").resolve_document_path,
        }
        # No legacy absolute path probe reaches the filesystem.
        with patch.object(Path, "exists", lambda path: path == self.file), \
                patch.object(shutil, "copy2", side_effect=OSError("synthetic failure")
                             if fail_copy else None) as copy:
            exec(compile(ast.Module(body=[block], type_ignores=[]),
                         "prequalify-transfer", "exec"), namespace)
        return namespace, copy

    def test_supported_reference_copies_into_local_client_path(self):
        for reference in (str(self.file), "/uploads/fictional.pdf", "fictional.pdf"):
            with self.subTest(reference=reference):
                state, copy = self.transfer(reference)
                target = self.root / "fictional-client_id.pdf"
                copy.assert_called_once_with(self.file, target)
                self.assertEqual(state["id_file_url"], str(target))
                self.assertTrue(state["id_uploaded"])

    def test_missing_and_unconfined_references_are_not_marked_uploaded(self):
        for reference in ("missing.pdf", "../fictional.pdf", "/outside/fictional.pdf",
                          "/uploads/../fictional.pdf"):
            with self.subTest(reference=reference):
                state, copy = self.transfer(reference)
                self.assertIsNone(state["id_file_url"])
                self.assertFalse(state["id_uploaded"])
                copy.assert_not_called()

    def test_copy_failure_does_not_preserve_original_reference(self):
        with self.assertLogs("offline-transfer", level="WARNING") as logs:
            state, copy = self.transfer(str(self.file), fail_copy=True)
        copy.assert_called_once()
        self.assertIsNone(state["id_file_url"])
        self.assertFalse(state["id_uploaded"])
        self.assertNotIn(str(self.file), " ".join(logs.output))


if __name__ == "__main__":
    unittest.main(verbosity=2)
