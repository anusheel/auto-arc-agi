#!/bin/bash
# Stop hook: force reflection every 10 play.py actions
INPUT=$(cat)

# Avoid infinite loop: if stop_hook_active, let it stop
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  exit 0
fi

COUNTER_FILE="$(dirname "$0")/../arc_action_count"
COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)

if [ "$COUNT" -ge 10 ]; then
  echo "MANDATORY REFLECTION ($COUNT actions since last update)." >&2
  echo "Update strategy.md sections: Current Model, Falsified, Next Test, Game State, Last Reflection." >&2
  echo "Note any surprises. Score: Process/Understanding/Assumptions/Exploration/Stuck-detection/Tools." >&2
  exit 2
fi

exit 0
