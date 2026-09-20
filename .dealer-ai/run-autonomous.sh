#!/usr/bin/env bash
set -u

WORKSPACE="/opt/dealer-ai-v2/app"
EXPECTED_BRANCH="dealer-ai-v2"
SAFE_BASE="4e5a293"
RUNTIME="$WORKSPACE/.dealer-ai/runtime"
LOG="$RUNTIME/autonomous.log"
PROMPT="$RUNTIME/autonomous-prompt.txt"
MAX_RUNTIME="8h"

cd "$WORKSPACE" || exit 10
mkdir -p "$RUNTIME"

echo "==================================================" >> "$LOG"
echo "DEALER AI V2 AUTONOMOUS SESSION" >> "$LOG"
date -Is >> "$LOG"
echo "SAFE_BASE=$SAFE_BASE" >> "$LOG"
echo "==================================================" >> "$LOG"

BRANCH="$(git branch --show-current)"

if [ "$BRANCH" != "$EXPECTED_BRANCH" ]; then
    echo "ABORT: unexpected branch: $BRANCH" | tee -a "$LOG"
    exit 20
fi

# HEAD must remain descended from the reviewed safe checkpoint.
if ! git merge-base --is-ancestor "$SAFE_BASE" HEAD; then
    echo "ABORT: HEAD is not descended from safe checkpoint $SAFE_BASE." | tee -a "$LOG"
    exit 22
fi

# Production MongoDB must never appear in tracked V2 backend/control source.
# Exclude the safety runner itself because its prompt intentionally contains
# the literal forbidden endpoint as an instruction to Codex.
if grep -RIn     --exclude-dir=.git     --exclude-dir=.venv     --exclude-dir=node_modules     --exclude-dir=runtime     --exclude='*.lock'     --exclude='run-autonomous.sh'     -E 'mongodb://(localhost|127\.0\.0\.1):27017|localhost:27017|127\.0\.0\.1:27017'     backend .dealer-ai 2>/dev/null
then
    echo "ABORT: forbidden production MongoDB endpoint detected in V2 source." | tee -a "$LOG"
    exit 23
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "ABORT: workspace is not clean before autonomous run." | tee -a "$LOG"
    git status --short >> "$LOG"
    exit 21
fi

cat > "$PROMPT" <<'PROMPT_EOF'
You are performing a controlled autonomous development session for Dealer AI OS V2.

GIT OWNERSHIP / SANDBOX RULE:
- You are running inside a workspace-write sandbox.
- Do NOT attempt to write Git metadata.
- Do NOT run git add, git commit, git checkout, git switch, git merge, git rebase, git reset, git stash, git push, or git tag.
- You MAY use read-only Git commands such as git status, git diff, git log, and git show.
- Modify application files directly in the workspace.
- Run the required tests/builds and review your diffs.
- Update .dealer-ai/NIGHTLY_REPORT.md with exact validation evidence.
- Leaving verified workspace changes uncommitted is EXPECTED.
- The external safety runner/owner is responsible for Git checkpoints.
- Do NOT block merely because Git metadata is not writable.

AUTHORITATIVE PROJECT DOCUMENTS

Before making any change, read completely:

.dealer-ai/AGENT_RULES.md
.dealer-ai/MASTER_BUILD_SPEC.md
.dealer-ai/DEFINITION_OF_DONE.md
.dealer-ai/IMPLEMENTATION_PLAN.md

Those project documents override generic ECC guidance.

WORKSPACE

You may modify ONLY:

/opt/dealer-ai-v2/app

You must remain on branch:

dealer-ai-v2

ABSOLUTE PROHIBITIONS

Never access /var/www/carplus.
Never switch to, modify, merge into, or deploy main.
Never modify production services.
Never use sudo.
Never use systemctl.
Never manipulate Docker.
Never execute real external communications.
Never send SMS, WhatsApp or email.
Never perform real credit/prequalification requests.
Never use real customer information.
Never read or expose secrets.
Never execute database migrations.
Never connect to production MongoDB.
Never use localhost:27017.
Never git push.
Never deploy.

External services must remain adapters/mocks/PENDING_EXTERNAL unless explicitly authorized by the owner in a future session.

AUTONOMOUS OBJECTIVE

Continue implementing Dealer AI OS V2 according to the audited IMPLEMENTATION_PLAN and MASTER_BUILD_SPEC.

Work sequentially.

Prioritize foundational architecture, security, isolation and testability before advanced features.

Do not attempt to finish the entire product in one uncontrolled change.

For each implementation unit:

1. Inspect existing implementation.
2. Define a small testable change.
3. Use TDD where practical.
4. Implement.
5. Run relevant safe tests.
6. Run relevant build/static validation.
7. Review the diff.
8. Apply security review where relevant.
9. Fix failures.
10. Re-run verification.
11. Document evidence.
12. Commit a verified checkpoint to dealer-ai-v2 before proceeding.

ECC

Use relevant ECC capabilities where appropriate, including:

architect
fastapi-reviewer
react-reviewer
security-reviewer
e2e-runner
verification-loop
tdd-guide / tdd-workflow
agent-self-evaluation

MongoDB-specific decisions must be based on this project's actual Motor/MongoDB architecture rather than PostgreSQL/Supabase assumptions.

SAFETY STOP CONDITIONS

STOP rather than guessing if:

- production access would be required;
- real credentials are required;
- real customer data would be required;
- an external provider must be activated;
- requirements materially conflict;
- a destructive operation appears necessary;
- tests expose an existing high-risk condition requiring owner review;
- safe progress cannot continue.

Do not mark anything PASS unless actually verified.

REPORTING

AUTONOMOUS CONTINUATION RULE - IMPORTANT:

This is a long-running autonomous development session, not a single-task session.
Completing one safe implementation unit is NOT sufficient reason to end the session.

After each completed safe unit:
1. Run the relevant tests and verification.
2. Record evidence in NIGHTLY_REPORT.md.
3. Inspect IMPLEMENTATION_PLAN.md and the controlling specifications.
4. Select the next highest-priority SAFE unfinished unit.
5. Continue implementing automatically.

Repeat this cycle for as many safe sequential units as possible during the available runtime.
Do NOT stop merely because one task, subtask, test set, or Phase 1 improvement is complete.
Do NOT stop merely because Git metadata cannot be written from the Codex sandbox; leave verified workspace changes uncommitted for the external owner/safety checkpoint process.

If one task is blocked but another independent safe task can proceed without bypassing the blocker, document the blocker and CONTINUE with that safe task.

Stop early ONLY for a genuine safety/architecture blocker, required owner approval, prohibited production/credential/real-data/real-communication/real-credit/destructive/deployment action, conflict with controlling rules, or when no additional safe work remains.

AUTONOMOUS_SESSION_COMPLETE means no additional safe planned work can reasonably be performed in this session. It does NOT mean only that the current unit finished.

Maintain:

.dealer-ai/NIGHTLY_REPORT.md

Record:

- starting commit;
- phases/tasks attempted;
- files changed;
- tests executed;
- PASS/FAIL results;
- security findings;
- architectural decisions;
- mock/pending integrations;
- blockers;
- commits created;
- unfinished work;
- recommended next step.

At the end perform a final verification of all work completed during this session.

Do not deploy.

Finish with one of:

AUTONOMOUS_SESSION_COMPLETE
AUTONOMOUS_SESSION_BLOCKED
AUTONOMOUS_SESSION_FAILED
PROMPT_EOF

echo "Starting controlled Codex session..." | tee -a "$LOG"

timeout --signal=TERM --kill-after=2m "$MAX_RUNTIME" \
    /home/dealerai/.local/node_modules/.bin/codex exec \
    --sandbox workspace-write \
    "$(cat "$PROMPT")" \
    >> "$LOG" 2>&1

RC=$?

echo >> "$LOG"
echo "==================================================" >> "$LOG"
echo "CODEX_EXIT_CODE=$RC" >> "$LOG"
date -Is >> "$LOG"
echo "FINAL_BRANCH=$(git branch --show-current)" >> "$LOG"
echo "FINAL_HEAD=$(git rev-parse --short HEAD)" >> "$LOG"
echo "FINAL_STATUS:" >> "$LOG"
git status --short >> "$LOG"
echo "==================================================" >> "$LOG"

exit "$RC"
