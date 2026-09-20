"""Execute only attachment selection, with synthetic files and no providers."""

import ast
import importlib.util
import logging
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"backend/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tests/offline")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "uploads"
        self.root.mkdir()
        self.file = self.root / "fictional.pdf"
        self.file.write_text("fictional attachment")

    def select(self, client, cosigners=(), enabled=True):
        tree = ast.parse((ROOT / "backend/server.py").read_text())
        block = next(node for node in ast.walk(tree)
                     if isinstance(node, ast.If)
                     and ast.unparse(node.test) == "request.attach_documents")
        namespace = {
            "request": SimpleNamespace(attach_documents=enabled),
            "client": client, "cosigners_data": list(cosigners),
            "attachments": [], "UPLOAD_DIR": self.root,
            "os": os, "logger": logging.getLogger("offline-attachments"),
        }
        # Import only the standalone helper if it has been implemented.
        helper = ROOT / "backend/document_attachments.py"
        if helper.is_file():
            with patch.dict("sys.modules", {"document_paths": load_module("document_paths")}):
                namespace["collect_document_attachments"] = load_module(
                    "document_attachments").collect_document_attachments
        # Legacy exists() calls are mocked: never probe stored arbitrary paths.
        with patch.object(os.path, "exists", return_value=False) as exists:
            exec(compile(ast.Module(body=[block], type_ignores=[]),
                         "attachment-selection", "exec"), namespace)
        return namespace["attachments"], exists

    def test_local_array_and_legacy_references_deduplicate(self):
        result, _ = self.select({
            "first_name": "Fictional", "last_name": "Person",
            "id_documents": [{"path": "/uploads/fictional.pdf"}],
            "id_file_url": str(self.file),
        })
        self.assertEqual(result, [{"path": str(self.file), "name": "Fictional_Person_ID.pdf"}])

    def test_cosigner_legacy_and_file_path_compatibility(self):
        result, _ = self.select({}, [{"info": {
            "first_name": "Fictional",
            "income_documents": [{"file_path": "fictional.pdf"}],
            "income_proof_file_url": "/uploads/fictional.pdf",
        }}])
        self.assertEqual(result, [{"path": str(self.file), "name": "CoSigner1_Fictional_Ingresos.pdf"}])

    def test_invalid_references_never_probe_unconfined_paths(self):
        result, exists = self.select({
            "id_documents": [{"path": "/outside/fictional.pdf"}],
            "id_file_url": "../fictional.pdf",
        }, [{"info": {"id_file_url": "/outside/fictional.pdf"}}])
        self.assertEqual(result, [])
        exists.assert_not_called()

    def test_disabled_attachments_do_not_resolve(self):
        result, exists = self.select({"id_file_url": str(self.file)}, enabled=False)
        self.assertEqual(result, [])
        exists.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
