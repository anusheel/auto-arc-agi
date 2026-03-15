#!/bin/bash
# PreToolUse[Bash]: block state-mutating game actions when reflection is overdue
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

COUNTER_FILE="$(dirname "$0")/../arc_action_count"
COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)

# Only check if counter is high AND command is a state-mutating game action
if [ "$COUNT" -ge 10 ] && \
   echo "$COMMAND" | grep -qE 'from play import' && \
   echo "$COMMAND" | grep -qE '\bact\(|\bseq\(|\bstart\(|\breset\(|\bnavigate\('; then
  echo "BLOCKED: $COUNT actions since last reflection. Update strategy.md before taking more game actions." >&2
  exit 2
fi

exit 0
