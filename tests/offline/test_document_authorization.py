"""Fictional policy matrix and isolated handler tests, without server startup."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from test_document_attachments import load_module

ROOT = Path(__file__).resolve().parents[2]
POLICY = load_module('document_authorization')

class RejectedRequest(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        super().__init__(detail)


def handlers(db):
    tree = ast.parse((ROOT / 'backend/server.py').read_text())
    namespace = {'db': db, 'HTTPException': RejectedRequest,
                 'can_access_documents': POLICY.can_access_documents}
    names = {'require_document_access', 'list_client_documents', 'upload_client_document',
             'delete_single_document', 'update_client_documents', 'download_client_document',
             'create_client_from_prequalify', 'sync_prequalify_to_client', 'delete_prequalify_submission',
             'get_public_document_info', 'update_document_language_preference',
             'upload_public_documents', 'generate_document_link',
             'send_documents_sms', 'send_documents_email'}
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name in names:
            node.decorator_list = []
            node.args.defaults = []
            for arg in node.args.args:
                arg.annotation = None
            nodes.append(node)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'isolated-handlers', 'exec'), namespace)
    return namespace


class DocumentAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_fictional_matrix(self):
        for role in ('admin', 'bdc_manager', 'bdc', 'telemarketer', 'salesperson', 'unknown', None):
            for owner_role in ('admin', 'bdc_manager', 'bdc', 'telemarketer', 'salesperson', 'unknown', None):
                for own in (False, True):
                    for accepted in (False, True):
                        for sold in (False, True):
                            for action in ('read', 'write', 'delete', 'invalid'):
                                user = {'id': 'fictional-user', 'role': role}
                                client = {'id': 'fictional-client', 'created_by': 'fictional-user' if own else 'fictional-owner',
                                          'collaboration_users': ['fictional-user'] if accepted else [], 'is_sold': sold}
                                db = SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value={'role': owner_role} if owner_role else None)))
                                expected = action != 'invalid' and (role == 'admin' or (
                                    role in ('bdc_manager', 'bdc', 'telemarketer', 'salesperson') and (
                                        (role in ('bdc_manager', 'bdc') and owner_role in ('bdc_manager', 'bdc', 'telemarketer', 'salesperson')) or
                                        (role in ('telemarketer', 'salesperson') and own) or (accepted and action == 'read'))))
                                with self.subTest(role=role, owner_role=owner_role, own=own, accepted=accepted, sold=sold, action=action):
                                    self.assertEqual(await POLICY.can_access_documents(db, user, client, action), expected)

    async def test_ambiguous_and_anonymous_deny(self):
        db = SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value=None)))
        for user in (None, {}, {'role': 'admin'}, {'id': 'fictional', 'role': []}, {'id': 'fictional', 'role': 'unknown'}):
            self.assertFalse(await POLICY.can_access_documents(db, user, {'id': 'fictional'}))
        for client in (None, {}, {'id': 'fictional'}, {'id': 'fictional', 'created_by': ''}):
            self.assertFalse(await POLICY.can_access_documents(db, {'id': 'fictional', 'role': 'telemarketer'}, client))

    async def test_handlers_enforce_before_side_effects(self):
        for role, accepted in (('telemarketer', False), ('telemarketer', True), ('bdc_manager', False), ('unknown', True)):
            client = {'id': 'fictional-client', 'created_by': 'fictional-admin',
                      'collaboration_users': ['fictional-user'] if accepted else [], 'id_documents': []}
            db = SimpleNamespace(clients=SimpleNamespace(find_one=AsyncMock(return_value=client), update_one=AsyncMock()),
                                 users=SimpleNamespace(find_one=AsyncMock(return_value={'role':'admin'})))
            ns = handlers(db); user = {'id': 'fictional-user', 'role': role}
            for name, args in (
                ('list_client_documents', ('fictional-client', 'id', user)),
                ('download_client_document', ('fictional-client', 'id', None, user)),
                ('upload_client_document', ('fictional-client', 'id', [], user)),
                ('delete_single_document', ('fictional-client', 'id', 'fictional-doc', user)),
                ('update_client_documents', ('fictional-client', False, False, False, user))):
                if name == 'download_client_document' and role == 'telemarketer' and accepted:
                    continue  # Allowed download filesystem behavior is covered separately.
                if name == 'list_client_documents' and role == 'telemarketer' and accepted:
                    self.assertEqual(await ns[name](*args), {'documents': [], 'count': 0})
                else:
                    with self.assertRaises(RejectedRequest) as denied:
                        await ns[name](*args)
                    self.assertEqual(denied.exception.status_code, 403)
            db.clients.update_one.assert_not_called()

    async def test_public_handlers_deny_without_database(self):
        ns = handlers(None)
        for name, args in (
            ('get_public_document_info', ('fictional-token',)),
            ('update_document_language_preference', ('fictional-token', None)),
            ('upload_public_documents', ('fictional-token', [], [], [], None)),
            ('generate_document_link', ('fictional-client', 'fictional-record', {})),
            ('send_documents_sms', ('fictional-client', 'fictional-record', {})),
            ('send_documents_email', ('fictional-client', {}))):
            with self.subTest(handler=name), self.assertRaises(RejectedRequest) as denied:
                await ns[name](*args)
            self.assertEqual(denied.exception.status_code, 403)

    async def test_transfer_and_deletion_reject_non_admin_before_lookup(self):
        ns = handlers(None)
        for name in ('create_client_from_prequalify', 'sync_prequalify_to_client', 'delete_prequalify_submission'):
            for role in ('bdc_manager', 'bdc', 'telemarketer', 'salesperson', 'unknown'):
                with self.subTest(handler=name, role=role), self.assertRaises(RejectedRequest) as denied:
                    await ns[name]('fictional-submission', {'id': 'fictional-user', 'role': role})
                self.assertEqual(denied.exception.status_code, 403)

    async def test_metadata_redaction_preserves_crm_fields(self):
        client = {'id':'fictional-client', 'created_by':'fictional-owner', 'first_name':'Fictional',
                  **dict.fromkeys(POLICY.DOCUMENT_FIELDS, 'fictional-document')}
        result = await POLICY.redact_documents(None, {'id':'fictional-other', 'role':'telemarketer'}, client)
        self.assertEqual(result, {'id':'fictional-client', 'created_by':'fictional-owner', 'first_name':'Fictional'})
        self.assertEqual(await POLICY.redact_documents(None, {'id':'fictional-owner', 'role':'salesperson'}, client), client)

    def test_all_operation_guards_and_no_static_uploads(self):
        source = (ROOT / 'backend/server.py').read_text(); tree = ast.parse(source)
        for name in ('download_client_document', 'create_client_from_prequalify', 'sync_prequalify_to_client',
                     'delete_prequalify_submission', 'send_record_report'):
            node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
            self.assertIn('await require_document_access(', ast.unparse(node), name)
        self.assertNotIn('app.mount(', source)
        node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'submit_prequalify_with_file')
        self.assertIsInstance(node.body[1], ast.If)
        self.assertIn('Public document uploads are disabled', ast.unparse(node.body[1]))

if __name__ == '__main__':
    unittest.main()
