#!/bin/bash
# Reset action counter when strategy.md is edited — but only if it's under the size limit
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

COUNTER_FILE="$(dirname "$0")/../arc_action_count"
STRATEGY_FILE="$(dirname "$0")/../../strategy.md"
MAX_LINES=200

if echo "$FILE_PATH" | grep -q "strategy.md"; then
  LINE_COUNT=$(wc -l < "$STRATEGY_FILE" 2>/dev/null | tr -d ' ')
  if [ "$LINE_COUNT" -gt "$MAX_LINES" ]; then
    echo "strategy.md is $LINE_COUNT lines (max $MAX_LINES). Curate it — trim old Falsified entries, tighten Current Model. Counter stays locked until under limit." >&2
  else
    echo 0 > "$COUNTER_FILE"
  fi
fi

exit 0
