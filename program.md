# ARC-AGI-3

Figure out the rules of each game by playing. Once you know the rules, replay to complete all levels in minimum actions.

## How

Play by calling play.py functions from the shell. Think between each invocation.

```
LOOP:
  1. Read memory.md. Paste key facts into your thinking.
  2. On a new level/game: check obs `available_actions`, `grid_summary`, and `render` before moving.
  3. State hypothesis OUT LOUD.
  4. Take 1-3 actions to test it. Read output. Think.
  5. Update memory.md sections: Current Model, Falsified, Next Test, Game State, Last Reflection.
  6. Reflect IMMEDIATELY on: surprises, level transitions, repeated failures.

RULES:
  - Max 4 act()/seq() per shell command. NEVER chain moves.
  - Same experiment 2 times with same result? Hypothesis is WRONG. Do NOT reset. Change hypothesis.
  - seq() with unverified paths wastes actions on blocked moves. Validate with act() first or use grid-analyzer BFS.
  - Max 2 resets per hypothesis. If it didn't work twice, the problem is your understanding.
  - start() burns a new scorecard every call. Never open one without recording learnings first.
  - Levels auto-advance on completion. Use reset() only to retry.
  - DANGER: reset() right after a level transition (0 actions taken) = full game restart.
  - After editing program.md, re-read it before your next action.

STUCK PROTOCOL:
  - Check scorecard baseline EARLY (at 1.5x baseline actions). Don't wait for 2x.
  - List your 3 core assumptions about the win condition.
  - Test the assumption you're MOST confident about — that's usually the wrong one.
  - Same approach failing with different inputs? The CORE ASSUMPTION is wrong — stop testing variations.
```

## Enforcement

Two independent counters, both increment on every game action:

- **Tactical (10 actions)**: Blocked until memory.md is updated. Resets on memory.md edit (only if under 200 lines).
- **Strategic (25 actions)**: Blocked until program.md or play.py is updated. Resets on program.md or play.py edit.

Read-only calls are never blocked. After compaction, memory.md is re-injected into context.

## Tactical Reflection (memory.md, every ~10 actions)

Game-specific. Fill in ALL sections:
- **Current Model** → what changed in your understanding of this game
- **Falsified** → what was disproven (append; curate when nearing 200-line limit)
- **Next Test** → next hypothesis + expected outcome
- **Game State** → current card_id, guid, level, resources
- **Last Reflection** → surprises + scores on Process/Understanding/Assumptions/Exploration/Stuck-detection/Tools

## Strategic Reflection (program.md + play.py, every ~25 actions)

Generic, not game-specific. Ask yourself:
- Is my methodology working? What process change would help most?
- Am I repeating a pattern that should be a play.py helper?
- Is there a rule I keep breaking that should be in program.md?

Changes should be minimal and broadly applicable. Don't add game-specific knowledge to program.md or play.py.

## Sub-Agents

Two utility sub-agents in `.claude/agents/`. Optional — prefer play.py helpers when possible.

| Agent | When to Use | When NOT to Use |
|---|---|---|
| `experiment-runner` | Execute a known multi-step plan when output would be verbose | Simple 1-3 action tests (just do them directly) |
| `grid-analyzer` | Enumerate candidates: symmetries, patterns, untested features | Making strategic decisions or selecting hypotheses |

The main agent owns all decisions. Sub-agents enumerate and report, never select what to try. Sub-agents inherit project hooks — reflect before dispatching to ensure a fresh counter.

## Principles

- Think before acting, but never theorize when one action would answer it.
- Something unexpected? Stop. That's the learning.
- Learning IS the work. Don't cling to a run; cling to understanding.
- Build a model of the rules, then try to break it.
- You know the rules when you can predict the outcome of any action.
- Think something is impossible? Spend 1 action to check.
- Poke every interesting object. Nothing is decoration until proven otherwise.
- Zoom out periodically. Better tools and methodology compound.

## play.py

`source .env && python -c "from play import *; ..."`

State resets between invocations. Capture `card_id`, `guid`, `game_id` from `start()` and pass as literals.

| Function | Purpose |
|---|---|
| `start(game_id)` | Open fresh scorecard + new game at level 1, returns (card_id, obs) |
| `reset(game_id, card_id, guid)` | Retry current level; if 0 actions since level transition → full game restart |
| `act(action_cmd, game_id, guid, card_id=None, x=None, y=None)` | Single action, get obs |
| `seq(game_id, guid, moves, card_id=None)` | Run move string, get final obs |
| `frame_to_grid(obs)` | Extract 2D grid from obs |
| `find_objects(grid, val)` | Find all (row, col) with value |
| `diff_frames(grid_a, grid_b)` | Dict of changed cells |
| `grid_summary(grid)` | Value counts |
| `render(frame_data)` | Text render of frame |
| `find_blob(grid, val, min_size=3)` | Bounding box of largest region of val |

Add game-specific helpers to play.py as you discover mechanics. Keep them below the `Game-specific helpers` comment.
