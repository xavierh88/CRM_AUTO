#!/usr/bin/env bash
set -u

cd /opt/dealer-ai-v2/worktrees/070-final-product-completion || exit 1

PLAN=".autonomous/MASTER_PLAN.md"
LOG=".autonomous/logs/worker.log"

echo "==================================================" >> "$LOG"
echo "AUTONOMOUS WORK START: $(date -Is)" >> "$LOG"
echo "WORKTREE=$(pwd)" >> "$LOG"
echo "==================================================" >> "$LOG"

/root/.opencode/bin/opencode run \
"Work autonomously inside the CURRENT worktree only.

First read:
.autonomous/MASTER_PLAN.md

Then execute that plan block-by-block.

Important:
- Continue automatically between blocks.
- Apply the REUSE-FIRST rule.
- Research reusable tools/libraries/repos/skills when useful.
- Prefer reliable existing solutions when they reduce implementation time and complexity.
- For Conversations, perform the required reuse/integration research before major new integration work.
- Build, test, inspect, fix and retest.
- Update .autonomous/state/progress.txt continuously.
- Create the required reports under .autonomous/reports/.
- Never mark anything APROBADO.
- Maximum autonomous state is LISTO_PARA_TU_PRUEBA.
- Do not deploy, merge or push.
- Do not touch production.
- Do not touch SoyEcua.
- Do not send real external communications.
- Do not use real customer data.
- Never fake successful integrations.
- If human configuration is required, mark that item WAITING_CONFIG and continue other independent work.
- Preserve already working functionality.
- Continue until all safe autonomous work in MASTER_PLAN.md has been attempted.
- At completion create .autonomous/reports/FINAL_REPORT.md and leave AUTONOMOUS_WORK_COMPLETE / WAITING_FOR_OWNER_REVIEW.

Do not request permission for files inside this current worktree.
Do not access files outside this worktree except normal installed executables/system dependencies required to build or test the application." \
>> "$LOG" 2>&1

RC=$?

echo >> "$LOG"
echo "AUTONOMOUS WORK EXIT: $(date -Is)" >> "$LOG"
echo "EXIT_CODE=$RC" >> "$LOG"

exit "$RC"
