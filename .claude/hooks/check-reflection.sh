#!/bin/bash
# Stop hook: force reflection when counters are high
INPUT=$(cat)

# Avoid infinite loop: if stop_hook_active, let it stop
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')
if [ "$STOP_HOOK_ACTIVE" = "true" ]; then
  exit 0
fi

TACTICAL_FILE="$(dirname "$0")/../arc_action_count"
STRATEGIC_FILE="$(dirname "$0")/../arc_strategic_count"
TACTICAL=$(cat "$TACTICAL_FILE" 2>/dev/null || echo 0)
STRATEGIC=$(cat "$STRATEGIC_FILE" 2>/dev/null || echo 0)

if [ "$TACTICAL" -ge 10 ]; then
  echo "MANDATORY REFLECTION ($TACTICAL actions since last update)." >&2
  echo "Update memory.md sections: Current Model, Falsified, Next Test, Game State, Last Reflection." >&2
  exit 2
fi

if [ "$STRATEGIC" -ge 25 ]; then
  echo "MANDATORY STRATEGIC REFLECTION ($STRATEGIC actions since last update)." >&2
  echo "Review and update program.md or play.py with methodology improvements." >&2
  exit 2
fi

exit 0
