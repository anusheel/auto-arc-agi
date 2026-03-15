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
  echo "BLOCKED: $COUNT state-mutating actions since last reflection." >&2
  echo "Update strategy.md sections before taking more game actions:" >&2
  echo "  - Current Model: what do you believe the rules are now?" >&2
  echo "  - Falsified: what hypotheses were disproven?" >&2
  echo "  - Next Test: what will you try next and what outcome do you expect?" >&2
  echo "  - Game State: card_id, guid, level, resources" >&2
  echo "  - Last Reflection: note any surprises from the last $COUNT actions" >&2
  exit 2
fi

exit 0
