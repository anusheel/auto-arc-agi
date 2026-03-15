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
  echo "MANDATORY REFLECTION ($COUNT actions since last update). You MUST:" >&2
  echo "1. Score yourself on Process/Understanding/Assumptions/Exploration/Stuck-detection/Tools" >&2
  echo "2. Update strategy.md with new learnings" >&2
  echo "3. State your next hypothesis OUT LOUD" >&2
  echo "Do NOT take another game action until strategy.md is updated." >&2
  exit 2
fi

exit 0
