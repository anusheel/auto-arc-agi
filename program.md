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
  2. On a new level/game: catalog all structures BEFORE any movement. Full grid
     render + grid_summary, then extract_pattern + render_pattern for each
     distinct object (blocks, targets, goal patterns). Save these to memory —
     they're your "before" baseline for detecting shape changes later.
  3. State hypothesis OUT LOUD. Say what you expect the next action to change.
  4. Take EXACTLY 1 action using the observe() helper. It calls act(), diffs
     against the saved pre-grid, prints all changes, then saves the post-grid
     for the next diff. NEVER call act() raw during exploration — always go
     through observe().
  5. Read the observe() output. State OUT LOUD: what changed, what surprised you,
     what confirmed/refuted your hypothesis.
     IMPORTANT: grid_summary only shows value counts — it hides spatial
     rearrangements (rotations, reflections, reshaping). After any interaction
     with a key object, use extract_pattern + render_pattern to inspect the
     shape of movable objects, targets, and goals.
  6. Write what you learned to the appropriate memory file.
  7. Reflect: What's my updated hypothesis and what single action tests it next?
     Am I repeating a failed approach?

LEVEL COMPLETE:
  When a level completes (levels_completed increments):
  1. STOP. Do NOT continue to the next level yet.
  2. Write down WHICH action won and WHY you think it worked.
  3. If you don't know why, reset and replay the level action-by-action with
     observe() to identify the exact winning mechanic.
  4. Update your rules model in memory. You must be able to PREDICT the win
     condition for the next level before proceeding.
  5. Only then: catalog the new level and continue.

RULES:
  - NEVER batch multiple actions in one Python invocation during exploration.
    One shell command → one observe() call → read output → think → next command.
  - seq() is ONLY for replaying exact move strings that you have already
    executed action-by-action and confirmed work. "I think this path should
    work" is NOT proven — you must have seen each step succeed via observe().
  - Same experiment 2 times with same result? Hypothesis is WRONG. Change it.
  - Max 2 resets per hypothesis. If it didn't work twice, the problem is your understanding.
  - start() burns a new scorecard every call. Never open one without recording learnings first.
  - Levels auto-advance on completion. Use reset() only to retry.
  - After reset() or start(), call save_grid(obs) to set the diff baseline.
    The grid persists to disk, so observe() diffs work across invocations.
    seq() calls save_grid() automatically.
  - NEVER modify REFLECT_EVERY or RETHINK_EVERY in play.py. These limits exist
    to force you to write observations and revisit your approach. If they fire,
    that means you're acting without thinking.
  - DANGER: reset() right after a level transition (0 actions taken) = full game restart.
  - After editing program.md, re-read it before your next action.

RETHINK (every 50 actions):
  Triggered by the RETHINK exception. Step back and revisit your entire approach.
  1. Write observations and learnings to memory/.
  2. Re-read program.md. Consider:
     - Are the instructions still accurate for how the game actually works?
     - Did you discover a workflow improvement or pitfall worth codifying?
     - Is anything misleading or missing?
     - Are there new helper functions worth documenting in the play.py table?
  3. If yes, edit program.md — then re-read it before your next action.
  4. If no, move on. Don't edit for the sake of editing.
  5. Resume play.

STUCK PROTOCOL:
  - Check scorecard baseline EARLY (at 1.5x baseline actions). Don't wait for 2x.
  - List your 3 core assumptions about the win condition.
  - Test the assumption you're MOST confident about — that's usually the wrong one.
  - Same approach failing with different inputs? The CORE ASSUMPTION is wrong — stop testing variations.
```

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

Local Python state resets between invocations. Capture `card_id`, `guid`, `game_id` from `start()` and pass as literals.

| Function | Purpose |
|---|---|
| `start(game_id)` | Open fresh scorecard + new game at level 1, returns (card_id, obs) |
| `reset(game_id, card_id, guid)` | Retry current level; if 0 actions since level transition → full game restart |
| `act(action_cmd, game_id, guid, card_id=None, x=None, y=None)` | Single action, get obs |
| `seq(game_id, guid, moves, card_id=None)` | Run move string, get final obs. **Only for proven paths.** |
| `frame_to_grid(obs)` | Extract 2D grid from obs |
| `find_objects(grid, val)` | Find all (row, col) with value |
| `find_blob(grid, val, min_size=3)` | Bounding box of largest region of val |
| `diff_frames(grid_a, grid_b)` | Dict of changed cells |
| `grid_summary(grid)` | Value counts |
| `render(frame_data)` | Text render of frame |
| `observe(action_cmd, game_id, guid, card_id=None, x=None, y=None)` | Wraps act() with auto-diff. Prints all changes and grid_summary. Returns (obs, new_guid). **Use this for exploration.** |
| `save_grid(obs)` | Set the diff baseline for observe(). Persists to disk. Call after reset()/start(). |
| `extract_pattern(grid, r0, c0, r1, c1, bg=None)` | Extract a sub-grid region as a list of lists |
| `render_pattern(pattern, label=None)` | Render a small pattern to text (. for 0/None) |
| `patterns_match(a, b)` | True if two patterns have identical non-zero shapes (position-normalized) |

Add game-specific helpers to play.py as you discover mechanics. Keep them below the `Game-specific helpers` comment. Examples of useful patterns:
- **level catalog** — enumerate structures, special values, reachable positions on a new level
- **pathfinder** — BFS or similar for navigating through corridors
- **speedrun** — replay solved levels efficiently once solutions are proven
