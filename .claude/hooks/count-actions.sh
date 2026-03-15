#!/bin/bash
# Increment action counter only for STATE-MUTATING play.py calls
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

COUNTER_FILE="$(dirname "$0")/../arc_action_count"

# Only count state-mutating game actions, not read-only helpers
if echo "$COMMAND" | grep -qE 'from play import' && \
   echo "$COMMAND" | grep -qE '\bact\(|\bseq\(|\bstart\(|\breset\(|\bnavigate\('; then
  COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
  echo $((COUNT + 1)) > "$COUNTER_FILE"
fi

exit 0
