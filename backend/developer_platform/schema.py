"""Typed metadata only. Trusted host supplies authenticated actors, never LLM input."""
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
import math
import re
from threading import RLock
from uuid import uuid4


KINDS = frozenset(('text', 'long_text', 'number', 'phone', 'email', 'date',
                   'boolean', 'select', 'multi_select', 'money', 'percentage'))
ROLES = frozenset(('ADMIN', 'MANAGER', 'BDC', 'SALESPERSON'))
RESERVED = frozenset(('id', '_id', 'role', 'roles', 'permissions', 'tenant',
                      'tenant_id', 'password', 'password_hash', 'created_by'))


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', value):
        raise ValueError('Invalid metadata identifier')


def label(value, limit=160):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError('Nonempty bounded text required')
    if any(ord(c) < 32 for c in value):
        raise ValueError('Control characters forbidden')


def immutable_sequence(value, item_type):
    if type(value) is not tuple or any(type(x) is not item_type for x in value):
        raise TypeError('An immutable typed tuple is required')


def aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('Timezone-aware timestamp required')


@dataclass(frozen=True)
class Actor:
    id: str
    tenant: str
    role: str
    reauthenticated_at: datetime
    human: bool = True


@dataclass(frozen=True)
class Field:
    id: str
    module: str
    name: str
    label: str
    type: str
    required: bool = False
    options: tuple[str, ...] = ()
    active: bool = True
    system_protected: bool = False
    created_by: str = ''
    version: int = 0
    min_value: float | None = None
    max_value: float | None = None
    max_length: int = 4096

    def __post_init__(self):
        for value in (self.id, self.module, self.name):
            identifier(value)
        label(self.label)
        if self.name in RESERVED or self.type not in KINDS:
            raise ValueError('Reserved field or unsupported type')
        for flag in (self.required, self.active, self.system_protected):
            if type(flag) is not bool:
                raise TypeError('Boolean flags required')
        immutable_sequence(self.options, str)
        if len(self.options) > 100 or len(set(self.options)) != len(self.options):
            raise ValueError('Invalid options')
        for option in self.options:
            label(option)
        if bool(self.options) != (self.type in ('select', 'multi_select')):
            raise ValueError('Selection fields require options exclusively')
        if type(self.max_length) is not int or not 1 <= self.max_length <= 10000:
            raise ValueError('Invalid length bound')
        for bound in (self.min_value, self.max_value):
            if bound is not None and (type(bound) not in (int, float) or not math.isfinite(bound)):
                raise ValueError('Invalid numeric bound')
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError('Inverted bounds')
        if type(self.version) is not int or self.version < 0 or not isinstance(self.created_by, str):
            raise ValueError('Invalid provenance')


@dataclass(frozen=True)
class Module:
    id: str
    label: str
    icon: str
    permissions: tuple[str, ...]
    list_fields: tuple[str, ...] = ()
    detail_fields: tuple[str, ...] = ()

    def __post_init__(self):
        identifier(self.id)
        identifier(self.icon)
        label(self.label)
        for values in (self.permissions, self.list_fields, self.detail_fields):
            immutable_sequence(values, str)


@dataclass(frozen=True)
class Form:
    id: str
    module: str
    label: str
    fields: tuple[str, ...]

    def __post_init__(self):
        identifier(self.id)
        identifier(self.module)
        label(self.label)
        immutable_sequence(self.fields, str)


@dataclass(frozen=True)
class Menu:
    id: str
    label: str
    module: str
    form: str

    def __post_init__(self):
        for value in (self.id, self.module, self.form):
            identifier(value)
        label(self.label)


@dataclass(frozen=True)
class Schema:
    modules: tuple[Module, ...] = ()
    fields: tuple[Field, ...] = ()
    forms: tuple[Form, ...] = ()
    menus: tuple[Menu, ...] = ()

    def __post_init__(self):
        for values, kind in ((self.modules, Module), (self.fields, Field),
                             (self.forms, Form), (self.menus, Menu)):
            immutable_sequence(values, kind)


def validate_schema(schema):
    if type(schema) is not Schema:
        raise TypeError('Typed schema required')
    for values in (schema.modules, schema.fields, schema.forms, schema.menus):
        if len(values) > 200 or len({v.id for v in values}) != len(values):
            raise ValueError('Duplicate IDs or schema limit exceeded')
    modules = {m.id: m for m in schema.modules}
    fields = {f.id: f for f in schema.fields}
    forms = {f.id: f for f in schema.forms}
    if len({(f.module, f.name) for f in schema.fields}) != len(schema.fields):
        raise ValueError('Duplicate field name')
    for field in schema.fields:
        if field.module not in modules:
            raise ValueError('Unknown field module')
    def references(module, ids):
        if len(set(ids)) != len(ids) or any(
            key not in fields or fields[key].module != module or not fields[key].active for key in ids
        ):
            raise ValueError('Invalid field references')
    for module in schema.modules:
        if not module.permissions or not set(module.permissions) <= ROLES:
            raise ValueError('Unsupported module permissions')
        references(module.id, module.list_fields)
        references(module.id, module.detail_fields)
    for form in schema.forms:
        if form.module not in modules:
            raise ValueError('Unknown form module')
        references(form.module, form.fields)
    for menu in schema.menus:
        if menu.module not in modules or menu.form not in forms or forms[menu.form].module != menu.module:
            raise ValueError('Invalid menu target')


def validate_values(schema, module, values):
    """Validate custom-value payloads; host must separately enforce record/module RBAC."""
    validate_schema(schema)
    if module not in {m.id for m in schema.modules} or type(values) is not dict:
        raise ValueError('Unknown module or invalid values')
    fields = {f.name: f for f in schema.fields if f.module == module and f.active}
    if values.keys() - fields.keys():
        raise ValueError('Unknown or inactive custom field')
    for name, field in fields.items():
        value = values.get(name)
        if value is None or value == '' or (field.type == 'multi_select' and value == []):
            if field.required:
                raise ValueError('Required field missing')
            continue
        kind = field.type
        valid = True
        if kind in ('number', 'money', 'percentage'):
            valid = type(value) in (int, float) and math.isfinite(value)
            if valid:
                valid = ((field.min_value is None or value >= field.min_value)
                         and (field.max_value is None or value <= field.max_value)
                         and (kind != 'percentage' or 0 <= value <= 100))
        elif kind == 'boolean':
            valid = type(value) is bool
        elif kind == 'multi_select':
            valid = (type(value) is list and all(type(v) is str and v in field.options for v in value)
                     and len(value) == len(set(value)))
        else:
            valid = isinstance(value, str) and len(value) <= field.max_length
            if valid and kind == 'select':
                valid = value in field.options
            if valid and kind == 'email':
                valid = re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value) is not None
            if valid and kind == 'phone':
                valid = re.fullmatch(r'\+?[0-9]{7,15}', value) is not None
            if valid and kind == 'date':
                try:
                    valid = date.fromisoformat(value).isoformat() == value
                except ValueError:
                    valid = False
        if not valid:
            raise ValueError('Invalid custom field value: ' + name)


@dataclass(frozen=True)
class Version:
    version: int
    schema: Schema


@dataclass(frozen=True)
class Preview:
    id: str
    who: str
    base_version: int
    schema: Schema
    changes: tuple[str, ...]
    reason: str
    expires_at: datetime
    confirmation: str
    rollback_to: int | None = None


@dataclass(frozen=True)
class Audit:
    who: str
    role: str
    tenant: str
    action: str
    timestamp: datetime
    old_version: int
    new_version: int
    reason: str
    changes: tuple[str, ...]
    preview_id: str
    rollback_to: int | None


def changes_between(old, new):
    changes = []
    for group in ('modules', 'fields', 'forms', 'menus'):
        before = {item.id: item for item in getattr(old, group)}
        after = {item.id: item for item in getattr(new, group)}
        for key in sorted(before.keys() | after.keys()):
            if before.get(key) != after.get(key):
                action = 'added' if key not in before else 'removed' if key not in after else 'updated'
                changes.append(f'{group}:{key}:{action}')
    return tuple(changes)


class SchemaService:
    """Thread-safe MOCK repository. Do not expose Actor construction to clients/tools."""
    def __init__(self, tenant, initial=Schema(), clock=None):
        label(tenant)
        validate_schema(initial)
        self._tenant = tenant
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._versions = [Version(0, initial)]
        self._previews = {}
        self._audit = []
        self._lock = RLock()

    def _authorize(self, actor):
        now = self._clock()
        aware(now)
        if type(actor) is not Actor:
            raise PermissionError('Authenticated human developer required')
        aware(actor.reauthenticated_at)
        if (actor.role != 'SYSTEM_DEVELOPER' or actor.tenant != self._tenant
                or actor.human is not True or not actor.id
                or not timedelta(0) <= now - actor.reauthenticated_at <= timedelta(minutes=5)):
            raise PermissionError('Recent human developer reauthentication required')
        return now

    def current(self, actor):
        with self._lock:
            self._authorize(actor)
            return self._versions[-1]

    def history(self, actor):
        with self._lock:
            self._authorize(actor)
            return tuple(self._versions)

    def audit(self, actor):
        with self._lock:
            self._authorize(actor)
            return tuple(self._audit)

    def preview(self, actor, schema, reason):
        with self._lock:
            now = self._authorize(actor)
            validate_schema(schema)
            old = self._versions[-1].schema
            before = {f.id: f for f in old.fields}
            after = {f.id: f for f in schema.fields}
            if before.keys() - after.keys():
                raise ValueError('Field deletion requires a separate data migration; deactivate instead')
            stamped = []
            for field in schema.fields:
                previous = before.get(field.id)
                # Provenance is server-owned, never accepted from a proposal.
                candidate = replace(field, created_by=previous.created_by if previous else actor.id,
                                    version=previous.version if previous else 1)
                if previous:
                    if previous.system_protected and candidate != previous:
                        raise ValueError('SYSTEM_PROTECTED field cannot change')
                    if (field.module, field.name, field.type, field.system_protected) != (
                            previous.module, previous.name, previous.type, previous.system_protected):
                        raise ValueError('Unsafe field identity/type/protection change')
                    if candidate != previous:
                        candidate = replace(candidate, version=previous.version + 1)
                elif field.system_protected:
                    raise ValueError('Protection is reserved for host-owned fields')
                stamped.append(candidate)
            schema = replace(schema, fields=tuple(stamped))
            return self._preview(actor, schema, reason, now, None)

    def preview_rollback(self, actor, version, reason):
        with self._lock:
            now = self._authorize(actor)
            if type(version) is not int or not 0 <= version < len(self._versions):
                raise ValueError('Unknown rollback version')
            return self._preview(actor, self._versions[version].schema, reason, now, version)

    def _preview(self, actor, schema, reason, now, rollback_to):
        label(reason, 1000)
        current = self._versions[-1]
        changes = changes_between(current.schema, schema)
        if not changes:
            raise ValueError('No schema changes')
        # Bound pending state and discard expired proposals without changing metadata.
        self._previews = {key: value for key, value in self._previews.items() if value.expires_at > now}
        if len(self._previews) >= 100:
            raise ValueError('Pending preview limit reached')
        key = str(uuid4())
        preview = Preview(key, actor.id, current.version, schema, changes, reason,
                          now + timedelta(minutes=5), f'CONFIRM {key}', rollback_to)
        self._previews[key] = preview
        self._record(actor, preview, 'PREVIEW_ROLLBACK' if rollback_to is not None else 'PREVIEW',
                     now, current.version)
        return preview

    def confirm(self, actor, preview_id, confirmation):
        with self._lock:
            now = self._authorize(actor)
            preview = self._previews.get(preview_id)
            if preview is None:
                raise ValueError('Unknown or consumed preview')
            if preview.who != actor.id:
                raise PermissionError('Preview belongs to another developer')
            if (preview.expires_at <= now or preview.base_version != self._versions[-1].version
                    or confirmation != preview.confirmation):
                raise ValueError('Expired, stale, or unconfirmed preview')
            result = Version(preview.base_version + 1, preview.schema)
            self._versions.append(result)
            self._record(actor, preview, 'ROLLBACK' if preview.rollback_to is not None else 'APPLY',
                         now, result.version)
            del self._previews[preview_id]
            return result

    def _record(self, actor, preview, action, now, new_version):
        self._audit.append(Audit(actor.id, actor.role, self._tenant, action, now,
                                 preview.base_version, new_version, preview.reason,
                                 preview.changes, preview.id, preview.rollback_to))
