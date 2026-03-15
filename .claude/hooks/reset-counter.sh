#!/bin/bash
# Reset counters when relevant files are edited
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

TACTICAL_FILE="$(dirname "$0")/../arc_action_count"
STRATEGIC_FILE="$(dirname "$0")/../arc_strategic_count"
MEMORY_MD="$(dirname "$0")/../../memory.md"
MAX_LINES=200

# memory.md edit → reset both counters
if echo "$FILE_PATH" | grep -q "memory.md"; then
  LINE_COUNT=$(wc -l < "$MEMORY_MD" 2>/dev/null | tr -d ' ')
  if [ "$LINE_COUNT" -gt "$MAX_LINES" ]; then
    echo "memory.md is $LINE_COUNT lines (max $MAX_LINES). Curate it first." >&2
  else
    echo 0 > "$TACTICAL_FILE"
    echo 0 > "$STRATEGIC_FILE"
  fi
fi

# program.md or play.py edit → reset strategic counter
if echo "$FILE_PATH" | grep -qE "program\.md|play\.py"; then
  echo 0 > "$STRATEGIC_FILE"
fi

exit 0
