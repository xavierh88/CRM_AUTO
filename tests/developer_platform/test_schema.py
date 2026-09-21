"""Synthetic, offline Developer Mode contracts."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from backend.developer_platform.schema import (
    Actor, Field, Form, Menu, Module, Schema, SchemaService, validate_values,
)

NOW = datetime(2026, 9, 21, tzinfo=timezone.utc)
DEV = Actor('fictional-dev', 'sandbox', 'SYSTEM_DEVELOPER', NOW)


def sample():
    return Schema(
        modules=(Module('trade_ins', 'Trade Ins', 'car', ('ADMIN',)),),
        fields=(Field('condition', 'trade_ins', 'condition', 'Condition', 'select',
                      options=('good', 'fair'), required=True),),
        forms=(Form('intake', 'trade_ins', 'Intake', ('condition',)),),
        menus=(Menu('trade_menu', 'Trade Ins', 'trade_ins', 'intake'),),
    )


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.service = SchemaService('sandbox', clock=lambda: NOW)

    def apply(self, schema):
        preview = self.service.preview(DEV, schema, 'Synthetic setup')
        return self.service.confirm(DEV, preview.id, preview.confirmation)

    def test_preview_confirm_audit_rollback(self):
        preview = self.service.preview(DEV, sample(), 'Synthetic setup')
        self.assertEqual(self.service.current(DEV).version, 0)
        self.assertEqual(preview.changes, ('modules:trade_ins:added', 'fields:condition:added',
                                          'forms:intake:added', 'menus:trade_menu:added'))
        version = self.service.confirm(DEV, preview.id, preview.confirmation)
        self.assertEqual(version.version, 1)
        self.assertEqual(version.schema.fields[0].created_by, DEV.id)
        self.assertEqual(version.schema.fields[0].version, 1)
        rollback = self.service.preview_rollback(DEV, 0, 'Undo synthetic setup')
        self.assertEqual(self.service.current(DEV).version, 1)
        reverted = self.service.confirm(DEV, rollback.id, rollback.confirmation)
        self.assertEqual(reverted.version, 2)
        self.assertEqual(reverted.schema, Schema())
        events = self.service.audit(DEV)
        self.assertEqual([e.action for e in events], ['PREVIEW', 'APPLY', 'PREVIEW_ROLLBACK', 'ROLLBACK'])
        self.assertEqual((events[-1].old_version, events[-1].new_version), (1, 2))
        self.assertEqual(events[-1].who, DEV.id)
        self.assertEqual(self.service.history(DEV)[1], version)

    def test_role_tenant_reauthentication_and_human_boundary(self):
        for actor in (replace(DEV, role='ADMIN'), replace(DEV, role='DEMO'),
                      replace(DEV, tenant='other'), replace(DEV, human=False),
                      replace(DEV, reauthenticated_at=NOW-timedelta(minutes=6)),
                      replace(DEV, reauthenticated_at=NOW+timedelta(seconds=1))):
            with self.subTest(actor=actor):
                for operation in (lambda: self.service.preview(actor, sample(), 'test'),
                                  lambda: self.service.current(actor),
                                  lambda: self.service.audit(actor),
                                  lambda: self.service.history(actor),
                                  lambda: self.service.preview_rollback(actor, 0, 'test'),
                                  lambda: self.service.confirm(actor, 'unknown', 'yes')):
                    with self.assertRaises(PermissionError):
                        operation()
        self.assertEqual(self.service.current(DEV).version, 0)

    def test_confirmation_binding_replay_and_stale(self):
        first = self.service.preview(DEV, sample(), 'first')
        second = self.service.preview(DEV, sample(), 'second')
        with self.assertRaises(ValueError):
            self.service.confirm(DEV, first.id, 'yes')
        with self.assertRaises(PermissionError):
            self.service.confirm(replace(DEV, id='other-dev'), first.id, first.confirmation)
        self.service.confirm(DEV, first.id, first.confirmation)
        for preview in (first, second):
            with self.assertRaises(ValueError):
                self.service.confirm(DEV, preview.id, preview.confirmation)
        self.assertEqual(self.service.current(DEV).version, 1)

    def test_expiry_and_reauthentication_at_confirmation(self):
        clock = [NOW]
        service = SchemaService('sandbox', clock=lambda: clock[0])
        preview = service.preview(DEV, sample(), 'test')
        clock[0] += timedelta(minutes=6)
        with self.assertRaises(PermissionError):
            service.confirm(DEV, preview.id, preview.confirmation)
        with self.assertRaises(ValueError):
            service.confirm(replace(DEV, reauthenticated_at=clock[0]), preview.id, preview.confirmation)

    def test_schema_references_duplicates_and_code_rejected(self):
        bad = [replace(sample(), fields=sample().fields*2),
               replace(sample(), modules=()),
               replace(sample(), forms=(Form('bad', 'trade_ins', 'Bad', ('missing',)),)),
               replace(sample(), menus=(Menu('bad', 'Bad', 'trade_ins', 'missing'),)),
               replace(sample(), modules=(Module('trade_ins', 'Trade', 'car', ('SYSTEM_DEVELOPER',)),))]
        for schema in bad:
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                self.service.preview(DEV, schema, 'test')
        with self.assertRaises(ValueError):
            Field('x', 'trade_ins', 'role', 'Role', 'text')
        with self.assertRaises(ValueError):
            Field('x', 'trade_ins', 'x', 'X', 'javascript')
        with self.assertRaises(TypeError):
            Field('x', 'trade_ins', 'x', 'X', 'text', script='execute()')
        with self.assertRaises(ValueError):
            self.service.preview(DEV, sample(), '  ')

    def test_protected_and_destructive_changes(self):
        protected = Field('core', 'trade_ins', 'core', 'Core', 'text', system_protected=True)
        initial = replace(sample(), fields=(protected,)+sample().fields)
        service = SchemaService('sandbox', initial=initial, clock=lambda: NOW)
        with self.assertRaises(ValueError):
            service.preview(DEV, sample(), 'remove core')
        with self.assertRaises(ValueError):
            self.service.preview(DEV, initial, 'create protected')
        self.apply(sample())
        with self.assertRaises(ValueError):
            self.service.preview(DEV, Schema(), 'delete field')
        with self.assertRaises(ValueError):
            self.service.preview(DEV, replace(sample(), fields=(replace(sample().fields[0], type='text', options=()),)), 'change type')
        edited = replace(sample(), fields=(replace(sample().fields[0], label='Updated'),))
        result = self.apply(edited)
        self.assertEqual(result.schema.fields[0].version, 2)

    def test_value_validation(self):
        validate_values(sample(), 'trade_ins', {'condition': 'good'})
        for values in ({}, {'condition': 'bad'}, {'condition': 'good', 'role': 'ADMIN'}):
            with self.assertRaises(ValueError):
                validate_values(sample(), 'trade_ins', values)
        examples = {'text': ('ok', 1), 'long_text': ('ok', False),
                    'number': (1.5, True), 'money': (2, float('nan')),
                    'percentage': (50, 101), 'boolean': (False, 'false'),
                    'date': ('2026-09-21', 'yesterday'),
                    'email': ('synthetic@example.invalid', 'invalid'),
                    'phone': ('+15550000000', 'call me'),
                    'multi_select': (['good'], ['bad'])}
        for kind, (valid, invalid) in examples.items():
            field = Field('value', 'trade_ins', 'value', 'Value', kind,
                          options=('good',) if kind == 'multi_select' else ())
            schema = replace(sample(), fields=(field,), forms=(), menus=())
            with self.subTest(kind=kind):
                validate_values(schema, 'trade_ins', {'value': valid})
                with self.assertRaises(ValueError):
                    validate_values(schema, 'trade_ins', {'value': invalid})

    def test_optional_fields_do_not_accept_wrong_empty_types(self):
        for kind in ('number', 'boolean', 'text'):
            field = Field('value', 'trade_ins', 'value', 'Value', kind)
            schema = replace(sample(), fields=(field,), forms=(), menus=())
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_values(schema, 'trade_ins', {'value': []})

    def test_protected_metadata_and_server_owned_provenance(self):
        protected = replace(sample().fields[0], system_protected=True)
        initial = replace(sample(), fields=(protected,))
        service = SchemaService('sandbox', initial=initial, clock=lambda: NOW)
        changed = replace(initial, fields=(replace(protected, label='Altered'),))
        with self.assertRaises(ValueError):
            service.preview(DEV, changed, 'attempt protected edit')
        forged = replace(sample(), fields=(replace(sample().fields[0], created_by='forged', version=999),))
        result = self.apply(forged)
        self.assertEqual((result.schema.fields[0].created_by, result.schema.fields[0].version), (DEV.id, 1))

    def test_concurrent_confirmation_has_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        previews = [self.service.preview(DEV, sample(), 'parallel synthetic change') for _ in range(2)]
        def confirm(preview):
            try:
                self.service.confirm(DEV, preview.id, preview.confirmation)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(confirm, previews)), [False, True])
        self.assertEqual(len(self.service.history(DEV)), 2)
        self.assertEqual(sum(event.action == 'APPLY' for event in self.service.audit(DEV)), 1)

    def test_validation_limits_and_cross_module_references(self):
        for kwargs in ({'options': ('same', 'same'), 'type': 'select'},
                       {'max_length': 0}, {'min_value': 10, 'max_value': 1},
                       {'min_value': float('nan')}, {'version': -1}):
            args = dict(id='x', module='trade_ins', name='x', label='X', type='text')
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Field(**(args | kwargs))
        schema = replace(sample(), modules=sample().modules + (Module('other', 'Other', 'car', ('ADMIN',)),),
                         forms=(Form('bad', 'other', 'Bad', ('condition',)),), menus=())
        with self.assertRaises(ValueError):
            self.service.preview(DEV, schema, 'cross module')
        schema = replace(sample(), fields=sample().fields + (replace(sample().fields[0], id='duplicate_name'),))
        with self.assertRaises(ValueError):
            self.service.preview(DEV, schema, 'duplicate name')
        schema = replace(sample(), modules=(replace(sample().modules[0], list_fields=('missing',)),))
        with self.assertRaises(ValueError):
            self.service.preview(DEV, schema, 'bad list')
        with self.assertRaises(ValueError):
            validate_values(sample(), 'missing', {})
        number = Field('value', 'trade_ins', 'value', 'Value', 'number', min_value=1, max_value=5)
        schema = replace(sample(), fields=(number,), forms=(), menus=())
        validate_values(schema, 'trade_ins', {})
        for value in (0, 6):
            with self.assertRaises(ValueError):
                validate_values(schema, 'trade_ins', {'value': value})

    def test_immutable_input_and_unknown_history(self):
        with self.assertRaises(TypeError):
            Schema(modules=[])
        with self.assertRaises(ValueError):
            self.service.preview_rollback(DEV, 99, 'test')
        with self.assertRaises(ValueError):
            self.service.preview(DEV, Schema(), 'no op')


if __name__ == '__main__':
    unittest.main()
