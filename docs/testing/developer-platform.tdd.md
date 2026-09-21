# Task 020 — Developer platform handoff

## Scope and status

PASS for the isolated schema foundation; live application integration remains
pending. Changes are intentionally uncommitted for the external supervisor.
Only `backend/developer_platform`, `tests/developer_platform`, and this handoff
were added. No deployment, providers, database access, credentials, inherited
uploads, production modification, or Git mutation is part of this implementation.
The explicit task worktree overrides the older `.dealer-ai/AGENT_RULES.md` app
path. The requested `docs/CODEX-NAVIGATION-GUIDE.md` is absent.

## Test evidence

- Initial RED: focused tests could not import the intended new schema module.
- Initial GREEN: 8 tests and 21 parameterized subtests passed.
- Edge-case RED: optional number/boolean/text accepted an empty list.
- Final GREEN: 12 tests and 29 parameterized subtests passed, including that fix.
- `python3 -m compileall -q backend/developer_platform tests/developer_platform`:
  PASS. No frontend changes require a frontend build.
- Standard-library `trace` with unittest discovery: all 12 tests PASS; schema
  module line coverage 97% (329 executable lines). This is line coverage, not
  branch coverage. Reports are under `/tmp/task-020-coverage`.
- `git diff --check`: PASS; explicit whitespace checks also passed for all new
  untracked source, tests, and documentation.
- Baseline commercial test attempt was blocked during collection because system
  Python lacks Pydantic. No dependencies were installed or downloaded. The new
  package needs only Python's standard library. No full-app regression claimed.

Coverage reproduction (run at the worktree root):

```python
import trace
tracer = trace.Trace(count=True, trace=False, ignoredirs=['/usr'])
tracer.run("import unittest; suite = unittest.defaultTestLoader.discover('tests/developer_platform'); result = unittest.TextTestRunner().run(suite); assert result.wasSuccessful()")
tracer.results().write_results(show_missing=True, summary=True,
                              coverdir='/tmp/task-020-coverage')
```

## Security boundary review

PASS within the offline service boundary: nondeveloper, cross-tenant, nonhuman,
stale/future reauthentication, wrong preview owner, wrong confirmation, expired,
replayed, and stale-base attempts cannot activate changes. Concurrent confirmation
has exactly one winner. Protected edits, reserved names, invalid references,
duplicate definitions, and unsupported types are rejected. Field creator/version
are server-owned. Metadata versions and audit append atomically under the local
lock. No imports of server/config/auth/provider/database modules occur.

Limit: Actor is trusted host input, not authentication. Live routes must never
accept it from a caller. Confirmation must be driven by verified human approval.
Persistent storage needs a transaction and cross-process version check; rollback
must undergo record compatibility checks. See the package README for integration
requirements. No authorization regression was observed.

Resource checks remained above configured 15 GiB free disk / 1800 MiB available
RAM minimums (approximately 19 GiB / 4.8 GiB at the latest implementation check).

## Self-evaluation

Using agent-self-evaluation; average 4.0/5.

| Axis | Score | Evidence / improvement |
| --- | --- | --- |
| Accuracy | 4 | Focused tests, compilation, and 97% line coverage; branch coverage could add precision. |
| Completeness | 4 | Requested metadata workflow implemented; live UI/auth/persistence explicitly pending for integration. |
| Clarity | 4 | Trust boundary and rollback semantics documented; a future host adapter will make integration more concrete. |
| Actionability | 4 | Runnable offline suite and clear host obligations; full-app verification needs existing dependencies. |
| Conciseness | 4 | Three bounded areas changed; documentation can be shortened once host integration replaces caveats. |

Highest-impact follow-ups: authenticated host adapter and human approval UI;
durable transactional persistence; record compatibility validation. These are
integration work, not authorization to deploy. Self-check: the assessment should
match a supervisor evaluating a foundation unit, rather than a live feature.
