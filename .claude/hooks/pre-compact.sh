#!/bin/bash
# Before compaction: inject reminder to save learnings (does NOT block — blocking risks deadlock)
INPUT=$(cat)
COUNTER_FILE="$(dirname "$0")/../arc_action_count"
COUNT=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)

if [ "$COUNT" -gt 0 ]; then
  echo "WARNING: Compaction happening with $COUNT unsaved actions. Update memory.md ASAP after compaction."
fi

# Always exit 0 — never block compaction, it risks deadlocking if context is full
exit 0
