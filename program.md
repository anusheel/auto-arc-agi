# ARC-AGI-3

Figure out the rules of each game by playing. Once you know the rules, replay to complete all levels in minimum actions.

## How

Play by calling play.py functions from the shell. Think between each invocation.

```
LOOP:
  1. Read strategy.md. Paste key facts into your thinking.
  2. On a new level/game: check obs `available_actions` and run `level_status` before moving.
  3. State hypothesis OUT LOUD.
  4. Take 1-3 actions to test it. Read output. Think.
  5. Update strategy.md with what you learned.
  6. Every ~10 actions or after completing/failing: REFLECT (see below),
     update play.py and program.md (generic only), commit and push.

RULES:
  - Max 3 act()/seq() per shell command. NEVER chain moves.
  - No strategy.md update in last 3 messages? STOP and update now.
  - Never open a new scorecard without recording learnings first.
  - Same experiment 3 times? STOP — you're stuck (see Principles).
  - After editing program.md, re-read it before your next action.
  - Levels auto-advance on completion — no reset needed. Use reset(game_id, card_id, guid) only to retry.
  - start() burns a new scorecard every call. Use reset() to retry within the same scorecard.
  - DANGER: reset() right after a level transition (0 actions taken) = full game restart.
```

## Principles

- Think before acting, but never theorize when one action would answer it.
- Every action tests a hypothesis. Curiosity counts — "what does this do?" is valid.
- Something unexpected? Stop. That's the learning.
- Learning IS the work. Don't cling to a run; cling to understanding.
- Build a model of the rules, then try to break it. Seek edge cases that would disprove your understanding.
- You know the rules when you can predict the outcome of any action. Until then, keep testing.
- Think something is impossible? Spend 1 action to check. Untested constraints are the costliest assumptions.
- Stuck 3+ times on the same idea? ESCALATE — try something qualitatively different.
- Poke every interesting object. Nothing is decoration until proven otherwise.
- Zoom out periodically. Better tools and methodology compound.

## Self-Reflection

Every ~10 actions, score yourself on each dimension. Note one concrete change per dimension.

- **Process** — Did you follow the loop? Skipping steps means repeating mistakes.
- **Understanding** — Did each action advance your model of the rules? If not, choose better experiments.
- **Assumptions** — What did you "know" without testing? Name them to catch them.
- **Exploration** — What haven't you tried? Avoidance is usually a hidden assumption.
- **Stuck detection** — How many actions before you changed approach? What signal did you miss?
- **Tools** — Done the same thing 3 times by hand? Write a helper.

## play.py

`source .env && uv run python -c "from play import *; ..."`

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
| `level_status(obs)` | Print block pos, markers, resources |
| `maze_map(grid)` | Coarse 5x5 grid view of corridors, walls, block, markers |
| `find_path(grid, sr, sc, tr, tc)` | BFS shortest path (UDLR string) between two positions |
| `reachable(grid, sr, sc)` | All positions reachable from start on 5-cell grid |
| `navigate(game_id, guid, tr, tc)` | Auto-navigate block to target using BFS |
| `block_pos(obs)` / `block_pos_from_grid(grid)` | Get block top-left (r, c) |
| `find_blob(grid, val, min_size=3)` | Bounding box of largest region of val |
| `can_place(grid, r, c, w=5, h=5)` | Check if 5x5 unit fits at position |
| `result(msg)` | Set final learning message for dashboard |
