"""Synthetic filesystem tests; never import the server or inherited uploads."""

import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


class DocumentPathTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "document_paths", ROOT / "backend/document_paths.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.resolve = module.resolve_document_path
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tests/offline")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "uploads"
        self.root.mkdir()
        self.file = self.root / "clients" / "fictional.pdf"
        self.file.parent.mkdir()
        self.file.write_text("fictional document")

    def test_supported_local_references(self):
        for value in (str(self.file), "/uploads/clients/fictional.pdf", "clients/fictional.pdf"):
            with self.subTest(value=value):
                self.assertEqual(self.resolve(value, self.root), self.file)

    def test_invalid_missing_and_directory_references(self):
        for value in (None, "", 123, "missing.pdf", "clients", "bad\x00.pdf"):
            with self.subTest(value=value):
                self.assertIsNone(self.resolve(value, self.root))

    def test_rejects_escape_even_when_basename_exists(self):
        outside = Path(self.temp.name) / "fictional.pdf"
        outside.write_text("fictional outside document")
        for value in (str(outside), "../fictional.pdf", "/uploads/../fictional.pdf",
                      "clients/../clients/fictional.pdf", "https://example.invalid/fictional.pdf"):
            with self.subTest(value=value):
                self.assertIsNone(self.resolve(value, self.root))

    def test_rejects_file_and_directory_symlinks(self):
        (self.root / "alias.pdf").symlink_to(self.file)
        (self.root / "alias").symlink_to(self.file.parent, target_is_directory=True)
        for value in ("alias.pdf", "alias/fictional.pdf"):
            with self.subTest(value=value):
                self.assertIsNone(self.resolve(value, self.root))

    def test_filesystem_errors_fail_closed(self):
        with patch.object(Path, "is_file", side_effect=PermissionError):
            self.assertIsNone(self.resolve(str(self.file), self.root))

    def test_download_handler_uses_confined_resolver(self):
        # Execute only the nested helper AST, never server imports or startup.
        tree = ast.parse((ROOT / "backend/server.py").read_text())
        handler = next(node for node in tree.body
                       if isinstance(node, ast.AsyncFunctionDef)
                       and node.name == "download_client_document")
        helper = next(node for node in handler.body
                      if isinstance(node, ast.FunctionDef) and node.name == "find_file")
        namespace = {"resolve_document_path": self.resolve, "UPLOAD_DIR": self.root}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), "download-helper", "exec"), namespace)
        self.assertEqual(namespace["find_file"]("/uploads/clients/fictional.pdf"), self.file)
        self.assertIsNone(namespace["find_file"]("../fictional.pdf"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
