#!/usr/bin/env bash
set -uo pipefail

BASE="/opt/dealer-ai-v2/worktrees/070-final-product-completion"
MISSION="$BASE/.autonomous/CURRENT_MISSION.md"
LOG="$BASE/.autonomous/logs/current-mission.log"

cd "$BASE" || exit 1

mkdir -p .autonomous/logs .autonomous/state .autonomous/reports

echo "CURRENT MISSION START: $(date -Is)" > "$LOG"
echo "WORKTREE=$BASE" >> "$LOG"
echo "MISSION=$MISSION" >> "$LOG"
echo >> "$LOG"

if [ ! -s "$MISSION" ]; then
    echo "ERROR: CURRENT_MISSION.md missing or empty" >> "$LOG"
    exit 1
fi

PROMPT="$(cat "$MISSION")

IMPORTANT EXECUTION INSTRUCTIONS:

Execute this mission against the EXISTING worktree.
Do actual implementation, builds, tests and verification.
Do not merely summarize the mission.

Preserve all existing uncommitted work.

Update:
.autonomous/state/progress.txt
.autonomous/reports/

continuously as work progresses.

Start with PRIORITY 0 — FINISH JARVIS VOICE.

Continue automatically through independent safe priorities.

Maximum status is LISTO_PARA_TU_PRUEBA.
Never mark anything APROBADO.

At completion create:
.autonomous/reports/FINAL_REPORT.md

Do not deploy production, merge, push, reset, clean, use real customer data,
send real external communications, or weaken authentication/tenant isolation."

echo "Launching OpenCode..." >> "$LOG"

export OPENCODE_PROMPT="$PROMPT"

script -q -e -c \
'/root/.opencode/bin/opencode run "$OPENCODE_PROMPT" --print-logs' \
"$LOG"

RC=$?

echo >> "$LOG"
echo "CURRENT MISSION EXIT: $(date -Is)" >> "$LOG"
echo "EXIT_CODE=$RC" >> "$LOG"

exit "$RC"
