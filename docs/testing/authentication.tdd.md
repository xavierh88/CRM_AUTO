# Task 040 authentication — pass 2 handoff

Overall: **PARTIAL**. Safe local runtime integration is implemented; live storage,
full configured startup and browser/authenticator validation are not claimed.
All changes remain uncommitted. Task 050 was not started.

## Delivered and status

| Boundary | Status | Evidence / limit |
|---|---|---|
| Safe bcrypt foundation and runtime fallback | COMPLETE (local) | Shared helpers; existing login contract retained; invalid enrollment input returns 422. |
| HTTP login/me/logout/password reauthentication | COMPLETE (isolated runtime) | Real route functions/decorators mounted in FastAPI with synthetic storage; eight new tests cover HTTP and service boundaries. |
| Server-authoritative roles/account status | COMPLETE (local) | Every request reloads account; role downgrade, disabled/deleted account, unknown role and registration escalation tests. |
| Persistent sessions and throttling | PARTIAL | Mongo collection operations wired; synthetic tests verify revocation, expiry, shared attempt records and fail-closed insertion failure. No live Mongo/multiworker verification. |
| Auditable authentication state | PARTIAL | Session creation/revocation/latest reauthentication timestamps and denial events persisted; not an append-only transactional audit trail. |
| Single-use confirmation foundation | COMPLETE (process-local scope only) | Existing 47 foundation tests preserved; no external action executor exposed. |
| Developer structural integration | PARTIAL | No new structural routes. Existing role restrictions unchanged; future host must bind tenant, role, session, recent reauthentication and immutable action payload. Password reauthentication alone never grants developer access or proves human presence. |
| WebAuthn/passkeys/biometric verification | PENDING_EXTERNAL | Options report unavailable. No successful ceremony, Face ID, Touch ID or Windows Hello claim; no biometric storage. |
| Full startup/live database/browser validation | BLOCKED in this authorized run | Would exceed the allowed synthetic/no-credentials/no-provider scope. |

## Runtime changes

`backend/authentication/runtime.py` is shared by `backend/server.py` and
`backend/auth.py`. Existing username/email-in-`email` password login returns
`{token, user}`. New sessions use random IDs; only their SHA-256 digests are stored.
JWTs expire, require a persisted session, and never authorize from a role claim.
Older stateless tokens deliberately require a fresh password login.

New routes: `POST /api/auth/logout`, `POST /api/auth/reauthenticate` with password,
and `GET /api/auth/passkeys/options` (unavailable only). User output is allowlisted.
Registration remains inactive and telemarketer regardless of submitted role.
No frontend edits; the frontend build is therefore not applicable.

The database adapter uses existing Mongo `_id` uniqueness and atomic increment
for ten attempts per identifier per five-minute fixed window. Attempt identifiers
are HMACed. This includes reauthentication. Source-wide rate limiting, retention,
TTL indexes and load testing remain pending. Bcrypt remains synchronous, and
per-account throttling does not prevent attempts across many distinct identifiers.
Session creation/revocation and latest reauthentication timestamps live alongside
state; denial events contain no submitted identifiers, passwords or bearer tokens.
No database was contacted and no migrations/index creation were performed.

## TDD and validation evidence

Interpreter: `/opt/dealer-ai-v2/app/.venv/bin/python` (FastAPI 0.110.1).

- Initial new-test dependency issue: `httpx` is absent. Replaced the client with
  a small in-process ASGI transport; no dependency installation or network use.
- RED: runtime module missing after transport setup; then GREEN with route/session
  implementation. Subsequent RED: eleventh shared login attempt succeeded;
  GREEN after persisted atomic attempt limiting. Registration RED: overlong
  password raised uncaught ValueError; GREEN after HTTP 422 translation.
- `python -m pytest tests/authentication -q`: **55 passed** (47 foundation + 8 new).
- `python -m pytest tests/offline/test_document_authorization.py -q`: **7 passed,
  1,589 subtests passed** standalone after the loader fix.
- Combined final run using the polling policy: **78 passed, 1,589 subtests passed**
  (55 authentication, 16 security, 7 document authorization tests).
- Security regression: unchanged 16 tests pass using the validation-only polling
  policy below. Ordinary execution stalls at `test_upload_validation_and_path`.
- Backend compilation: **45 Python files compiled**, using `py_compile` with
  temporary output, excluding uploads, symlink directories and virtualenvs.
- `git diff --check`: PASS; untracked additions separately whitespace checked.
- Coverage percentage not measured: neither environment provides `coverage`.
  Passing behavior tests do not establish 80% coverage.

### Document collection diagnosis

The standalone command failed with `ModuleNotFoundError: document_authorization`.
`load_module('crm_authorization')` executes a file that imports its sibling by
name, without placing backend on `sys.path`. The security test incidentally adds
that path, masking the standalone failure. The document test now adds its own
backend path explicitly. No assertions or production authorization were weakened.

### Security regression execution caveat

A 15-second timeout with `-o faulthandler_timeout=5` found the main thread waiting
in the selector and the AnyIO worker waiting in its queue. A separate minimal
`anyio.to_thread.run_sync(lambda: 'worker done')` also timed out without any
application imports; adding a periodic asyncio timer allowed it to complete.
This supports an environment wakeup limitation rather than an authentication
regression, but normal event-loop behavior still requires verification elsewhere.
No production or regression-test changes were made to conceal this limitation.

Reproducible validation-only workaround (run from this worktree):

```python
# Execute with /opt/dealer-ai-v2/app/.venv/bin/python
import asyncio
import pytest

class PollingLoop(asyncio.SelectorEventLoop):
    def _run_once(self):
        self.call_later(0.05, lambda: None)
        super()._run_once()

class Policy(asyncio.DefaultEventLoopPolicy):
    _loop_factory = PollingLoop

asyncio.set_event_loop_policy(Policy())
raise SystemExit(pytest.main([
    'tests/authentication',
    'tests/offline/test_security_core.py',
    'tests/offline/test_document_authorization.py', '-q',
]))
```

## Security review

- Authorization bypass / role escalation: current DB role/status controls access;
  forged or missing sessions fail; registration cannot assign privileges.
- Replay: revoked/expired sessions fail; existing confirmation single-use and
  binding checks remain intact. Active bearer tokens remain reusable until
  revocation/expiry by design; they are not single-use action confirmations.
- Insecure fallback: password verification fails closed for malformed hashes and
  oversized values; passkeys cannot authenticate or silently create credentials.
- Biometric storage: none; no endpoint accepts an authenticator assertion.
- Secret/token exposure: no passwords or raw tokens in stored session/audit data;
  response fields are allowlisted; tokens are returned only by successful login.
- Session regression: username/password fallback retained; legacy token rejection
  is intentional. Logout is backend-accessible; frontend wiring was not added.
- Structural actions: distributed confirmation/action/audit transaction remains
  pending; process-local gate is not exposed as a production authorization service.

Safety: no .env access, inherited uploads access, real customer data, external
providers, production access, service changes, deployment or Git mutations.
Root AGENTS.md and the referenced navigation guide are absent; supplied user
instructions govern this authorized worktree. No commits were made despite the
TDD skill's checkpoint convention, following the user's explicit prohibition.

## Self-evaluation

Applied agent-self-evaluation after review:

| Axis | Score | Evidence / improvement |
|---|---|---|
| Accuracy | 4 | Passing synthetic tests; live database and normal-loop verification still needed. |
| Completeness | 4 | Local runtime paths implemented; external and transactional limits remain explicit. |
| Clarity | 4 | Status table distinguishes implementation from validation; deployment review should retain these limits. |
| Actionability | 4 | Reproducible tests and workaround included; next authorized unit needs isolated live-storage validation. |
| Conciseness | 4 | Detailed caveats retained because they materially affect review. |

Overall 4.0/5. Highest-impact next steps: isolated live MongoDB/multiworker tests,
source throttling/retention, then separately authorized browser WebAuthn work.
Self-check: this is a reviewable local integration, not a production-complete
authentication system.
