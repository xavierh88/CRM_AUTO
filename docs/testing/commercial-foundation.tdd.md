# Commercial foundation evidence

Scope: MASTER_BUILD_SPEC §§7/17/18/21, IMPLEMENTATION_PLAN phases 2/5,
DEFINITION_OF_DONE and AGENT_RULES read from `/opt/dealer-ai-v2/app/.dealer-ai`.
Only the authorized crm-finance worktree was modified.

| Guarantee / journey | Test in tests/commercial/test_domain.py | Result |
| --- | --- | --- |
| Preserve inherited fields and leave ambiguous statuses for review | test_legacy_mapping_preserves_input | PASS |
| Support every stage and return detached transition candidates | test_canonical_and_transition | PASS |
| Preserve original attribution and reject invalid acquisition types | test_attribution | PASS |
| Calculate exact costs, funding, gross and net including loss-making deals | test_calculation | PASS |
| Reject invalid money, supplied derived fields and inconsistent sale state | test_validation | PASS |
| Aggregate sold deals, conversion and durations; reject duplicates | test_kpis_and_cohort | PASS |
| Reject approval before acquisition | test_approval_chronology | PASS |
| Supply fresh fictional inventory and validate preference ranges | test_mock_inventory | PASS |

RED: `/tmp/test_venv/bin/python -m unittest discover -s tests/commercial -v`
failed because `backend.commercial.pipeline` did not exist (intended missing
implementation). After implementation seven tests passed. Review added a raw
source preservation test, which failed (`'custom' != ' custom '`). Disabling
whitespace stripping for Attribution resolved it. Final run: eight tests PASS.
No checkpoint commits were made, per user instruction.

Regression: `/tmp/test_venv/bin/python -m unittest discover -s tests/offline -p
 'test_document_paths.py' -v`: six existing synthetic offline tests PASS.
These use temporary fictional files and isolated AST handlers, not server startup.

Build: `/tmp/test_venv/bin/python -m compileall -q backend/commercial tests/commercial`
PASS. `git diff --check` PASS; all changes are additive, existing models and
server.py unchanged.

Coverage: standard library trace used because coverage.py is unavailable:
`/tmp/test_venv/bin/python -m trace --count --summary --missing --coverdir
/tmp/crm-finance-coverage --module unittest discover -s tests/commercial`.
Line coverage exceeds 80% in every commercial module. This is line coverage,
not branch coverage. Artifacts are outside the repository in /tmp.

Limitations: pytest, black, coverage.py and static type/lint tooling are absent
from the available test environment. Runtime Pydantic validation and Python
compilation were verified; no static type/lint PASS is claimed. Full inherited
API tests and frontend build were not run: no server integration or frontend
change was made. No HTTP routes means no newly exposed unauthenticated financial
surface; actual route authorization, persistence and UI integration remain the
supervisor's work, and end-to-end feature PASS is not claimed.

No production, inherited uploads contents, real customer data, deployment,
network integrations or Git mutations were used.

Self-evaluation (agent-self-evaluation skill):

| Axis | Score | Evidence / improvement |
| --- | --- | --- |
| Accuracy | 4 | Exact calculation and compatibility tests pass; business formulas need owner confirmation at integration. |
| Completeness | 4 | All six foundation priorities covered; branch coverage is not measured. |
| Clarity | 4 | README defines cohort and legacy mapping semantics; later API docs should show route contracts. |
| Actionability | 4 | Imports, validation and test commands documented; supervisor must add permission-scoped persistence. |
| Conciseness | 4 | No unrelated application changes; handoff is longer to make financial assumptions explicit. |

Overall 4.0/5. Highest-impact follow-ups: confirm financial accounting policy,
then add permission-scoped integration tests when routes are registered. These
are integration handoffs, not claims of shipped UI functionality. User agreement
self-check: this assessment distinguishes tested domain work from pending wiring.
