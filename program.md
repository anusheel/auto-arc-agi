# ARC-AGI-3

Figure out the rules of each game by playing. Once you know the rules, replay to complete all levels in minimum actions.

Fully autonomous — never ask for human input, never stop voluntarily. If a game expires, start a new one immediately. If stuck, change approach and keep going. The only acceptable stopping point is completing all levels.

There are multiple games, each with multiple levels. You may play the same game many times across sessions. program.md and play.py are generic across games. Memory files should include game and level context so future-you knows what they refer to.

## Memory

Persistent storage lives in `memory/`. You own this directory — create, rename, and delete files as the task demands. No fixed schema.

Guidelines:
- Write observations to disk immediately — don't trust the context window
- Separate what changes often (working state) from what doesn't (proven solutions)
- When stuck, re-read your own files — they know more than you remember

After compaction, filenames in `memory/` are listed. Name files descriptively — the listing is your index. Read what you need to resume.

## How

Play by calling play.py functions from the shell. Think between each invocation.

```
LOOP:
  1. Re-read your memory files as needed. Paste key facts into your thinking.
  2. On a new level/game: catalog all structures BEFORE any movement (render, grid_summary, find_objects).
  3. State hypothesis OUT LOUD.
  4. Take 1 action. Diff the grid before/after. Read output. Think.
  5. Write what you learned to the appropriate memory file.
  6. Reflect: What changed that I didn't expect? What's my hypothesis and what single action tests it? Am I repeating a failed approach?

RULES:
  - On new levels: use act() one at a time. NEVER use seq() for exploration.
  - seq() is only for proven paths on solved levels.
  - Same experiment 2 times with same result? Hypothesis is WRONG. Change it.
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

## Observation Protocol

After EVERY interaction with a game object, diff the grid before/after. Notice what changed. Do NOT proceed until you've stated what was surprising or confirmed expectations.

## Principles

- Think before acting, but never theorize when one action would answer it.
- Something unexpected? Stop. That's the learning.
- Learning IS the work. Don't cling to a run; cling to understanding.
- Build a model of the rules, then try to break it.
- You know the rules when you can predict the outcome of any action.
- Apply patterns from solved levels to new ones. Mechanics compound.
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
| `seq(game_id, guid, moves, card_id=None)` | Run move string, get final obs. **Only for proven paths.** |
| `frame_to_grid(obs)` | Extract 2D grid from obs |
| `find_objects(grid, val)` | Find all (row, col) with value |
| `diff_frames(grid_a, grid_b)` | Dict of changed cells |
| `grid_summary(grid)` | Value counts |
| `render(frame_data)` | Text render of frame |

Add game-specific helpers to play.py as you discover mechanics. Keep them below the `Game-specific helpers` comment.

Build game-specific helpers as you discover mechanics. Examples of useful patterns:
- **observe/diff** — compare grids before/after an action, report all changes
- **level catalog** — enumerate structures, special values, reachable positions on a new level
- **pathfinder** — BFS or similar for navigating through corridors
- **speedrun** — replay solved levels efficiently once solutions are proven
