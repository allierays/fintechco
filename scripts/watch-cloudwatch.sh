#!/usr/bin/env bash
#
# Watches CloudWatch for routing errors, then triggers Claude Code to diagnose and open a PR.
#
# Usage:
#   ./scripts/watch-cloudwatch.sh          # polls every 30s
#   ./scripts/watch-cloudwatch.sh --once   # check once and exit
#

set -euo pipefail

LOG_GROUP="/aws/lambda/fintechco-sync"
REGION="us-east-1"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
POLL_INTERVAL=30
ONCE=false
LAST_CHECK_FILE="/tmp/fintechco-cloudwatch-last-check"

if [[ "${1:-}" == "--once" ]]; then
  ONCE=true
fi

check_for_errors() {
  local since
  if [[ -f "$LAST_CHECK_FILE" ]]; then
    since=$(cat "$LAST_CHECK_FILE")
  else
    # Look back 5 minutes on first run
    since=$(( $(date +%s) * 1000 - 300000 ))
  fi

  local now=$(( $(date +%s) * 1000 ))

  local errors
  errors=$(aws logs filter-log-events \
    --log-group-name "$LOG_GROUP" \
    --region "$REGION" \
    --start-time "$since" \
    --filter-pattern "ERROR" \
    --query 'events[].message' \
    --output text 2>/dev/null || true)

  echo "$now" > "$LAST_CHECK_FILE"

  if [[ -n "$errors" && "$errors" != "None" ]]; then
    echo ""
    echo "=== ROUTING ERROR DETECTED ==="
    echo "$errors"
    echo "==============================="
    echo ""
    echo "Launching Claude Code to diagnose and fix..."
    echo ""

    cd "$REPO_DIR"
    claude -p "CloudWatch just logged these errors from our routing service:

$errors

Diagnose the root cause in this codebase. Look at the routing code in src/routing/router.py.
Find the bug, write the fix, and open a PR with your changes. The PR should explain:
1. What the bug was
2. Why it caused excess cost
3. What the fix does

Create a new branch named fix/routing-cost-weight and push it."

    return 0
  fi

  return 1
}

echo "Watching CloudWatch log group: $LOG_GROUP"
echo "Region: $REGION"
echo "Repo: $REPO_DIR"
echo ""

if $ONCE; then
  if check_for_errors; then
    echo "Error found and Claude Code triggered."
  else
    echo "No errors found."
  fi
  exit 0
fi

echo "Polling every ${POLL_INTERVAL}s... (Ctrl+C to stop)"
echo ""

while true; do
  if check_for_errors; then
    echo ""
    echo "Claude Code has been triggered. Exiting watcher."
    exit 0
  fi
  sleep $POLL_INTERVAL
done
