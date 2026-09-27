#!/usr/bin/env bash
set -uo pipefail

BASE="/opt/dealer-ai-v2/worktrees/070-final-product-completion"
cd "$BASE" || exit 1

LOG="$BASE/.autonomous/logs/voice-worker.log"
TASK="$BASE/.autonomous/voice-task.txt"

echo "VOICE WORKER START: $(date -Is)" > "$LOG"

/root/.opencode/bin/opencode run -m opencode/nemotron-3.5-lightning-free "$(cat "$TASK")" --print-logs 2>&1 | tee -a "$LOG"

RC=${PIPESTATUS[0]}

echo >> "$LOG"
echo "VOICE WORKER EXIT: $(date -Is)" >> "$LOG"
echo "EXIT_CODE=$RC" >> "$LOG"

exit "$RC"
