# Task 060 — demo QA handoff

Status: IMPLEMENTED FOUNDATION / VERIFICATION BLOCKED. Uncommitted; no deployment.

The worktree already contained the demo entry, UI, session model, backend guards
and initial tests at the start of this unit. They were preserved and reviewed.
This run added explicit synthetic/MOCK action markers and cross-feature reset
regression coverage. No prior RED/GREEN history is claimed for inherited changes.

Entry: `/demo` and `/demo/*` select the lazy demo component before CRM App loads.
The demo uses detached, in-memory fictional customers, actions, leads,
appointments, vehicles, messages, sales, finances and prequalifications.
Exact fixture membership resolves customer drill-downs. No token, authentication
provider, persistence or API transport is used by the demo modules. Reset creates
fresh data and clears selection/search; the EN/ES tour supports restart and bounded
completion. External integrations remain MOCK/PENDING_EXTERNAL.

Security-boundary review:
- Backend enabled-user validation rejects demo role, is_demo marker and demo-ID
  prefix. SessionAuth invokes this guard before returning an authenticated user.
- CRMAccess rejects demo identities before collection lookup or scope generation;
  document policy denies them before owner lookup or admin allowance.
- No demo credentials or backend demo accounts are issued. The client-side demo
  identity is display/session state, never a server authority.
- Demo source imports only React, local fixture/model helpers and local CSS.
  Static checks exclude common transports, storage, CRM auth and document paths.
- These are source-review findings, not a runtime authorization or browser PASS.
  Backend runtime and full browser network isolation still require verification.

Validation performed:
- Initial frontend demo tests: PASS (5 cases).
- RED: `node frontend/tests/demo-mode.test.mjs` failed the new all-records
  synthetic test on `actions: demo-action-1` (missing marker, not an auth failure).
- GREEN: `node --experimental-test-coverage frontend/tests/demo-mode.test.mjs`:
  6 passed; demo-session.mjs 100% lines/branches/functions. Combined loaded source
  85.71% lines; JSX interaction coverage is not measured.
- Related regression: `node frontend/tests/dealer-os.test.mjs`: 4 passed.
  Justification: shared fixture model, customer search and pipeline behavior.
- `python3 -m py_compile` on the three modified backend modules and demo test:
  PASS. Compilation does not establish runtime authorization.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/demo/test_isolation.py`:
  BLOCKED at collection, FastAPI missing. Existing /tmp/test_venv and
  /tmp/security-core-venv also lacked pytest; no packages installed or fetched.
- `npm run build --prefix frontend`: BLOCKED, craco not found. No dotenv loader ran.
- `git diff --check`: PASS. No unresolved Git conflicts found.

Supervisor follow-up: provide approved offline dependencies, run focused demo
backend tests first, then authentication and CRM/document authorization regression
in an isolated synthetic harness. Stop on any authorization regression. Compile
frontend in a credential-free environment (existing CRACO config loads dotenv),
then test demo navigation, customer drill-down, empty search, reset, tour language
and completion in a browser with external requests blocked. Verify that /demo
never loads CRM authentication or calls APIs, including with stale CRM browser
storage. Do not integrate this unit as fully verified until those gates pass.

Safety: no production modifications, inherited uploads reads, .env reads,
credentials, real communications, external provider requests, database operations,
Git mutations or deployment. Resource checks: about 22.4 GiB disk free and
3.8 GiB RAM available, above previously documented 15 GiB / 1800 MiB minima;
inspected local safety policy does not specify numerical minima.
The requested CODEX-NAVIGATION-GUIDE.md is absent.

Self-evaluation (agent-self-evaluation skill): accuracy 4 (executed results and
blocked gates distinguished; runtime proof pending), completeness 3 (build,
backend and browser verification blocked), clarity 4 (entry and scope documented;
UI copy partly English), actionability 4 (explicit supervisor verification steps;
offline dependencies needed), conciseness 4 (bounded changes; detailed handoff).
Overall 3.8/5. Highest-impact improvement: restore approved offline dependencies,
then verify runtime authorization and browser network isolation. User-agreement
self-check: this unit is not claimed complete or ready for integration.
