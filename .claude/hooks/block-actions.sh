#!/bin/bash
# PreToolUse[Bash]: block state-mutating game actions when reflection is overdue
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

TACTICAL_FILE="$(dirname "$0")/../arc_action_count"
STRATEGIC_FILE="$(dirname "$0")/../arc_strategic_count"
TACTICAL=$(cat "$TACTICAL_FILE" 2>/dev/null || echo 0)
STRATEGIC=$(cat "$STRATEGIC_FILE" 2>/dev/null || echo 0)

# Only check if command is a state-mutating game action
if echo "$COMMAND" | grep -qE 'from play import' && \
   echo "$COMMAND" | grep -qE '\bact\(|\bseq\(|\bstart\(|\breset\(|\bnavigate\('; then

  if [ "$TACTICAL" -ge 10 ]; then
    echo "BLOCKED: $TACTICAL actions since last tactical reflection." >&2
    echo "Update memory.md before taking more game actions:" >&2
    echo "  - Current Model, Falsified, Next Test, Game State, Last Reflection" >&2
    exit 2
  fi

  if [ "$STRATEGIC" -ge 25 ]; then
    echo "BLOCKED: $STRATEGIC actions since last strategic reflection." >&2
    echo "Time for strategic reflection. Review and optionally update:" >&2
    echo "  - program.md: methodology improvements (generic, not game-specific)" >&2
    echo "  - play.py: reusable helpers for patterns you keep repeating" >&2
    echo "Edit program.md or play.py to unblock (even a small change counts)." >&2
    exit 2
  fi
fi

exit 0
