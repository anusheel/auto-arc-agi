#!/bin/bash
# Reset action counter when strategy.md is edited
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

COUNTER_FILE="$(dirname "$0")/../arc_action_count"

if echo "$FILE_PATH" | grep -q "strategy.md"; then
  echo 0 > "$COUNTER_FILE"
fi

exit 0
