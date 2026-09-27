#!/usr/bin/env bash
set -uo pipefail

BASE="/opt/dealer-ai-v2/worktrees/070-final-product-completion"
MISSION="$BASE/.autonomous/CURRENT_MISSION.md"
LOG="$BASE/.autonomous/logs/screen-worker.log"

cd "$BASE" || exit 1

mkdir -p .autonomous/logs .autonomous/state .autonomous/reports

echo "SCREEN WORKER START: $(date -Is)" > "$LOG"
echo "MISSION=$MISSION" >> "$LOG"
echo "WORKTREE=$BASE" >> "$LOG"
echo >> "$LOG"

if [ ! -s "$MISSION" ]; then
    echo "ERROR: CURRENT_MISSION.md missing" | tee -a "$LOG"
    exit 1
fi

PROMPT="$(cat "$MISSION")

IMPORTANT:
Execute the mission. Do not merely summarize it.
Start with PRIORITY 0 Jarvis Voice.
Preserve all current uncommitted work.
Perform actual implementation, builds and safe verification.
Continue automatically through independent safe priorities.
Update .autonomous/state/progress.txt and .autonomous/reports continuously.
Maximum state is LISTO_PARA_TU_PRUEBA.
Never mark anything APROBADO.
Never touch production, SoyEcua or /var/www/carplus.
Never merge, force-push, reset --hard or git clean.
Never use real customer data or send real external communications.
If human credentials/configuration are required, mark WAITING_CONFIG and continue independent work.
At completion create .autonomous/reports/FINAL_REPORT.md."

echo "Launching OpenCode..." | tee -a "$LOG"

/root/.opencode/bin/opencode run "$PROMPT" --print-logs 2>&1 | tee -a "$LOG"

RC=${PIPESTATUS[0]}

echo | tee -a "$LOG"
echo "SCREEN WORKER EXIT: $(date -Is)" | tee -a "$LOG"
echo "EXIT_CODE=$RC" | tee -a "$LOG"

exit "$RC"
