# Developer Mode schema foundation

Status: **MOCK / offline foundation verified**. No HTTP routes, live database,
frontend wiring, provider calls, or deployment. This follows the isolated
foundation pattern in `backend/communications` and `backend/commercial`.

`schema.py` supports all eleven specified custom field types, bounded declarative
validation, active/required fields, selection options, host-owned field provenance
and versions, SYSTEM_PROTECTED fields, forms, menus, module permissions, and
list/detail field references. Menus resolve to schema IDs, never arbitrary URLs.
Definitions contain no scripts, expressions, SQL, or executable callbacks.
Labels are plain text; future renderers must escape them, never inject HTML.

## Workflow and trust boundary

1. A trusted host verifies the session, tenant, SYSTEM_DEVELOPER role, human
   origin, and successful reauthentication. It constructs `Actor` from those
   verified facts. Never deserialize Actor from request bodies or LLM tool args.
2. Use one `SchemaService` per tenant. The host may seed core protected fields
   through `initial`; proposals cannot create or alter protection.
3. Call `preview(actor, schema, reason)`. It validates the entire schema, stamps
   field provenance, returns an immutable proposed snapshot and explicit change
   list, and records PREVIEW without activating anything.
4. Present the snapshot and changes to the human. After their explicit approval,
   call `confirm(actor, preview.id, preview.confirmation)`. The host must not
   auto-confirm or give a nonhuman tool access to confirmation. The confirmation
   text is a binding mechanism, not a credential or proof of user interaction.
5. Confirmation rechecks role, tenant, human origin, recent reauthentication,
   preview owner, five-minute expiry, and current version. Successful confirmation
   consumes the preview and appends a version and audit event under one lock.
6. `preview_rollback(actor, version, reason)` uses the same confirmation flow.
   Rollback restores a prior metadata snapshot in a **new** schema version;
   history is retained. Field-level versions/provenance are restored with the
   snapshot. No customer records or database columns are deleted or migrated.

Read/history/audit operations use the same Developer authorization boundary.
Audit events identify tenant, actor, role, action, timestamp, reason, old/new
version, preview, rollback target, and per-module/field/form/menu changes.
Audit/history results and metadata are immutable tuples and frozen objects.
This is an in-process append-only log, not durable or tamper-evident storage.
Rejected operations raise errors and do not activate metadata; the host should
record authorization denials in its security log.

Normal changes reject field deletion and identity/type/protection changes;
deactivate a field and remove its form/list references instead. Schema and field
limits are bounded, references stay within a module, and only explicit operational
roles can appear in module permission declarations. Those declarations never
assign user roles or grant backend access. `validate_values` rejects unknown or
inactive custom keys and validates supplied values; the host must separately
check record access and module permission. Keep custom values in a namespaced
container, never merge them into core records.

## Remaining integration work

- Connect verified authentication and actual password/passkey reauthentication;
  the five-minute timestamp check does not itself authenticate anyone.
- Map canonical module permission roles to the application's existing role
  model and enforce them in each record endpoint. SYSTEM_DEVELOPER is checked
  here only; this package does not add or grant that role in the application.
- Add authenticated routes and a protected preview/confirmation UI. No live
  Developer Mode toggle or custom-form renderer is shipped in this unit.
- Replace memory storage with durable, atomic version + audit persistence and
  database compare-and-swap for multiple processes. State resets on restart.
- Check existing records before tightening required/options/validation rules
  or activating rollback in a persistent installation. This service knows only
  metadata, not customer data. It must not be used as a database migration engine.
- External integrations remain PENDING_EXTERNAL; none are needed or contacted.

## Verification

From the worktree root:

```sh
python3 -m pytest tests/developer_platform -q
python3 -m compileall -q backend/developer_platform tests/developer_platform
```

See [unit handoff](../../docs/testing/developer-platform.tdd.md) for evidence.
