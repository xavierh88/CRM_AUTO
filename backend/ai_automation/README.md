# AI automation foundation

Offline Python/Pydantic foundation; no HTTP routes, database connections, LLM
provider, scheduler, or message delivery. External integration is PENDING_EXTERNAL.

Supported Jarvis contracts: `match_vehicle` (validated VehiclePreference) and
`update_appointment` (ID and allowlisted status). Extra fields, arbitrary tools,
queries, supplied role/confirmation flags and arbitrary updates are rejected.
All appointment mutations require authorization and human confirmation.
Other tools, appointment creation/rescheduling and destructive operations remain
unsupported and fail validation.

Required integration chain:
Jarvis -> PermissionEngine -> CRMTools implementation -> database.
Host code creates TrustedContext from its authenticated session and current CRM
object policy, including tenant-scoped tool/object grants. Never deserialize it
from model output. Grants must be refreshed on every call; the database adapter
must recheck ownership/tenant scope at write time. No role implies global access.
The two CRMTools methods are typed integration contracts, not a live DB adapter.

Only the trusted human confirmation endpoint may call PermissionEngine.confirm,
after displaying the exact request. Never expose confirm as a Jarvis tool.
Approvals bind actor, tenant, session and exact intent, expire in 120 seconds,
and are consumed once under a lock. Storage is bounded and process-local;
restart loses approvals. Multi-worker integration requires shared atomic storage.
Audit sink receives trusted actor, tool and outcome, without customer payload.
It must durably record attempts before execution. Completion-audit failure can
occur after an API write: never automatically retry; reconcile manually. No
exactly-once mutation guarantee is claimed.

Guardian suggests reminders within 24 hours, no-show review for elapsed active
appointments, and recovery review for explicitly recorded no-shows. It never
changes appointment state or sends anything. Recovery classifies no-show and
abandoned prequalify HOT; other inactivity reasons WARM; active leads without
signals COLD/NONE. Seven days defines stale. These defaults require product
review before scheduling automation. Datetimes must include timezones.

Matching filters available fictional inventory by budget, year and body type,
then orders by asking price and ID. Down payment, payment preference and credit
constraints flag financing review; they never establish credit eligibility,
affordable payments or financing approval. No-match returns an empty tuple.

Validation commands (repository root):

```
/tmp/test_venv/bin/python -m unittest discover -s tests/ai_automation -v
/tmp/test_venv/bin/python -m unittest discover -s tests/commercial -v
/tmp/test_venv/bin/python -m compileall -q backend/ai_automation tests/ai_automation
git diff --check
```

Tests use fictional data and mocks. Production integration and UI E2E are pending.
